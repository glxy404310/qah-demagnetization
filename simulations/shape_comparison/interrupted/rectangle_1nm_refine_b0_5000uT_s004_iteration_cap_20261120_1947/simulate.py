"""Finite-film OOMMF experiments with explicit geometry, history and validation."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from datetime import datetime
import numpy as np
from runtime import ROOT, TCL, OOMMF, run

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'simulations/baseline'))
from analyze import ovf, table
sys.path.insert(0, str(ROOT / '理论学习资料/辅助文件/output/demag-learning'))
from rectangular_demag import rectangular_factors

MU0 = 4*math.pi*1e-7
MS, A, KU = 3e5, 5e-12, 8e4
SHAPES = ('square', 'circle', 'rectangle')
INITIALS = ('plus', 'minus', 'inplane_x', 'inplane_y', 'domains', 'random11', 'random22', 'random33')


def dump(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False,
                              default=lambda x: x.item() if isinstance(x, np.generic) else str(x)), encoding='utf-8')
    tmp.replace(path)


def geometry(shape, cell):
    lx, ly = {'square': (200, 200), 'circle': (228, 228), 'rectangle': (400, 100)}[shape]
    nx, ny, nz = round(lx/cell), round(ly/cell), round(4/cell)
    x = (np.arange(nx)+0.5)*cell-lx/2
    y = (np.arange(ny)+0.5)*cell-ly/2
    z = (np.arange(nz)+0.5)*cell
    zz, yy, xx = np.meshgrid(z, y, x, indexing='ij')
    mask = np.ones((nz, ny, nx), dtype=bool)
    if shape == 'circle':
        mask = xx**2+yy**2 < 40000/math.pi
    area = int(mask[0].sum())*cell**2
    assert abs(area/40000-1) <= 0.005
    return dict(shape=shape, cell_nm=cell, lx_nm=lx, ly_nm=ly, nz=nz, ny=ny, nx=nx,
                magnetic_cells=int(mask.sum()), area_nm2=area, volume_m3=int(mask.sum())*(cell*1e-9)**3,
                area_fraction_error=area/40000-1), mask, (xx, yy, zz)


def initial_field(name, coords):
    xx, yy, zz = coords
    m = np.zeros(xx.shape+(3,))
    if name in ('x', 'y', 'z'):
        m[..., 'xyz'.index(name)] = 1
    elif name in ('plus', 'minus'):
        m[..., 0], m[..., 2] = 0.01, 1
        if name == 'minus':
            m *= -1
    elif name.startswith('inplane_'):
        m[..., 'xyz'.index(name[-1])] = 1
        m[..., 2] = 0.01
    elif name == 'domains':
        # Bloch-type smooth wall: pi*Delta ~= 41 nm, mz changes sign at x=0.
        m[..., 2] = np.tanh(xx/13.0)
        m[..., 1] = 1/np.cosh(xx/13.0)
    elif name.startswith('random'):
        rng = np.random.default_rng(int(name[6:]))
        m[..., 2] = 1
        # Same physical Fourier field on both meshes, bounded by 0.05 per component.
        for component in (0, 1):
            for _ in range(8):
                kx, ky = rng.integers(1, 5, size=2)
                phase = rng.uniform(0, 2*math.pi)
                m[..., component] += 0.05/8*np.sin(2*math.pi*(kx*xx+ky*yy)/200+phase)
    else:
        raise ValueError(name)
    m /= np.linalg.norm(m, axis=-1, keepdims=True)
    return m


def write_ovf(path, m, g):
    c = g['cell_nm']*1e-9
    lines = ['# OOMMF OVF 2.0', '# Segment count: 1', '# Begin: Segment', '# Begin: Header',
             '# Title: initial normalized magnetization', '# meshtype: rectangular', '# meshunit: m',
             '# valuedim: 3', '# valuelabels: mx my mz', '# valueunits: 1 1 1']
    for axis, length, count, lower in [('x', g['lx_nm']*1e-9, g['nx'], -g['lx_nm']*0.5e-9),
                                      ('y', g['ly_nm']*1e-9, g['ny'], -g['ly_nm']*0.5e-9),
                                      ('z', 4e-9, g['nz'], 0)]:
        lines += [f'# {axis}min: {lower:.17g}', f'# {axis}max: {lower+length:.17g}',
                  f'# {axis}base: {lower+c/2:.17g}', f'# {axis}stepsize: {c:.17g}', f'# {axis}nodes: {count}']
    lines += ['# End: Header', '# Begin: Data Binary 8']
    with Path(path).open('wb') as f:
        f.write(('\n'.join(lines)+'\n').encode())
        f.write(np.array([123456789012345.0], dtype='<f8').tobytes())
        f.write(np.asarray(m, dtype='<f8').tobytes())
        f.write(b'\n# End: Data Binary 8\n# End: Segment\n')


def make_mif(g, fields, stop, static):
    lx, ly, c = g['lx_nm']*1e-9, g['ly_nm']*1e-9, g['cell_nm']*1e-9
    extent = f'xrange {{{-lx/2:.17g} {lx/2:.17g}}}\n yrange {{{-ly/2:.17g} {ly/2:.17g}}}\n zrange {{0 4e-9}}'
    if g['shape'] == 'circle':
        atlas = f'''proc Circle {{x y z}} {{
 set dx [expr {{($x-0.5)*{g['lx_nm']}}}]
 set dy [expr {{($y-0.5)*{g['ly_nm']}}}]
 if {{$dx*$dx+$dy*$dy < {40000/math.pi:.17g}}} {{return 1}}
 return 0
}}
Specify Oxs_ScriptAtlas:atlas {{
 {extent}
 regions {{film}}
 script Circle
}}'''
    else:
        atlas = f'Specify Oxs_BoxAtlas:atlas {{\n name film\n {extent}\n}}'
    ranges = '\n'.join(f'{{0 0 {b:.17g} 0 0 {b:.17g} 0}}' for b in fields)
    energy = '' if static else f'''Specify Oxs_UniformExchange:exchange {{ A {A} }}
Specify Oxs_UniaxialAnisotropy:anisotropy {{ K1 {KU} axis {{0 0 1}} }}
Specify Oxs_UZeeman:zeeman {{
 multiplier {1/MU0:.17g}
 Hrange {{ {ranges} }}
}}'''
    fixed = 'fixed_spins { :atlas film }' if static else ''
    return f'''# MIF 2.2
SetOptions {{ basename result scalar_output_format %.17g vector_field_output_format {{binary 8}} }}
{atlas}
Specify Oxs_RectangularMesh:mesh {{ cellsize {{{c} {c} {c}}} atlas :atlas }}
Specify Oxs_Demag:demag {{}}
{energy}
Specify Oxs_RungeKuttaEvolve:evolve {{
 alpha 0.5 gamma_G 2.21e5 do_precess 0 method rkf54 relative_step_error 1e-7
 {fixed}
}}
Specify Oxs_TimeDriver {{
 evolver :evolve mesh :mesh
 Ms {{ Oxs_AtlasScalarField {{ atlas :atlas default_value 0 values {{film {MS}}} }} }}
 m0 {{ Oxs_FileVectorField {{ file initial.omf spatial_scaling {{1 1 1}} spatial_offset {{0 0 0}} norm 1 }} }}
 stopping_dm_dt {stop}
 stage_iteration_limit 100000
 total_iteration_limit {max(100000, len(fields)*100000)}
 stage_count {len(fields)}
 checkpoint_interval -1
 normalize_aveM_output 1
}}
Destination archive mmArchive
Schedule DataTable archive Step 100
Schedule DataTable archive Stage 1
Schedule DataTable archive Done
Schedule Oxs_TimeDriver::Spin archive Stage 1
Schedule Oxs_Demag:demag:Field archive Stage 1
Schedule {{Oxs_RungeKuttaEvolve:evolve:Total field}} archive Stage 1
'''


def field_file(folder, pattern, stage):
    found = [p for p in folder.glob(pattern) if int(p.stem.split('-')[-2]) == stage]
    if len(found) != 1:
        raise ValueError(f'{folder}: stage {stage}: expected one {pattern}, found {len(found)}')
    return found[0]


def analyze_case(folder):
    config = json.loads((folder/'config.json').read_text())
    g, mask, _ = geometry(config['shape'], config['cell_nm'])
    d = table(next(folder.glob('*.odt')))
    stages = d['Oxs_TimeDriver::Stage'].astype(int)
    report = []
    for stage, b in enumerate(config['fields_T']):
        indices = np.flatnonzero(stages == stage)
        if not len(indices):
            raise ValueError(f'Missing stage {stage}')
        k = int(indices[-1])
        spin = field_file(folder, '*Spin*.omf', stage)
        m = ovf(spin)[0]
        hd = ovf(field_file(folder, '*Demag*.ohf', stage))[0]
        heff = ovf(field_file(folder, '*Total_field*.ohf', stage))[0]
        mm, hh = m[mask], hd[mask]
        energy = {key: float(values[k]) for key, values in d.items() if key.endswith(':Energy')}
        total = float(d['Oxs_RungeKuttaEvolve:evolve:Total energy'][k])
        rate = float(d['Oxs_RungeKuttaEvolve:evolve:Max dm/dt'][k])
        rhs = -2.21e5*0.5/(1+0.5**2)*np.cross(mm, np.cross(mm, heff[mask]))
        rhs_rate = float(np.linalg.norm(rhs, axis=-1).max()*180/math.pi*1e-9)
        ed = float(-0.5*MU0*MS*g['volume_m3']*np.sum(mm*hh, axis=-1).mean())
        demag = energy['Oxs_Demag:demag:Energy']
        norm_error = float(np.max(np.abs(np.linalg.norm(mm, axis=-1)-1)))
        prev = int(d['Oxs_TimeDriver::Iteration'][np.flatnonzero(stages==stage-1)[-1]]) if stage else 0
        iterations = int(d['Oxs_TimeDriver::Iteration'][k])-prev
        checks = dict(unit_m=norm_error<1e-6,
                      energy_sum=abs(sum(energy.values())-total)<max(1e-26, abs(total)*1e-8),
                      field_energy=abs(ed-demag)<max(1e-26, abs(demag)*1e-8),
                      converged=rate<=config['stop']*1.00001 and iterations<100000)
        if config['static']:
            checks['frozen'] = iterations == 0 and np.max(np.abs(mm-np.eye(3)['xyz'.index(config['initial'])]))<1e-12
        else:
            checks['independent_rhs'] = abs(rhs_rate-rate)<max(1e-6, rate*1e-5)
            checks['independent_convergence'] = rhs_rate<=config['stop']*1.00001
            stage_energy=d['Oxs_RungeKuttaEvolve:evolve:Total energy'][indices]
            checks['fixed_field_energy_nonincreasing'] = bool(np.all(np.diff(stage_energy)<=1e-25))
        rec = dict(stage=stage, b_T=b, mean_m=mm.mean(axis=0).tolist(),
                   mean_abs_mz=float(np.abs(mm[:,2]).mean()), negative_fraction=float((mm[:,2]<0).mean()),
                   min_mz=float(mm[:,2].min()), max_mz=float(mm[:,2].max()),
                   energy_J=energy, total_energy_J=total, energy_density_J_m3=total/g['volume_m3'],
                   max_dm_dt_deg_ns=rate, independent_dm_dt_deg_ns=rhs_rate,
                   max_norm_error=norm_error, iterations=iterations, checks=checks,
                   spin_file=spin.name, mean_Hd_A_m=hh.mean(axis=0).tolist())
        if config['static']:
            axis = 'xyz'.index(config['initial'])
            rec['N_field'] = float(-hh[:,axis].mean()/MS)
            rec['N_energy'] = 2*demag/(MU0*MS**2*g['volume_m3'])
            rec['checks']['N_field_energy'] = abs(rec['N_field']-rec['N_energy'])<1e-8
            if config['shape'] != 'circle':
                rec['N_analytic'] = rectangular_factors(g['lx_nm'], g['ly_nm'], 4)[axis]
                rec['checks']['N_analytic'] = abs(rec['N_field']-rec['N_analytic'])<1e-4
        report.append(rec)
    result = dict(config=config, geometry=g, stages=report,
                  all_passed=all(all(r['checks'].values()) for r in report))
    dump(folder/'summary.json', result)
    if not result['all_passed']:
        raise ValueError(f'Failed numerical checks: {folder}: '+str([(r['stage'],r['checks']) for r in report if not all(r['checks'].values())]))
    return result


def case(run_id, shape, cell=2, initial='plus', fields=None, stop=0.01,
         static=False, predecessor=None, epsilon=0, timeout=43200):
    fields = [0.0] if fields is None else [float(round(b, 10)) for b in fields]
    g, mask, coords = geometry(shape, cell)
    if predecessor:
        predecessor = Path(predecessor).resolve()
        m = ovf(predecessor)[0]
        assert m.shape == mask.shape+(3,)
        # Zero-Ms cells still need a nonzero initial unit direction for the file reader.
        m[~mask] = [0,0,1]
    else:
        m = initial_field(initial, coords)
    if epsilon:
        m[...,0] += epsilon
        m[...,1] += epsilon*0.37
        m /= np.linalg.norm(m,axis=-1,keepdims=True)
    config = dict(run_id=run_id, shape=shape, cell_nm=cell, initial=initial, fields_T=fields,
                  stop=stop, static=static, epsilon=epsilon,
                  predecessor=str(predecessor) if predecessor else None,
                  predecessor_sha256=hashlib.sha256(predecessor.read_bytes()).hexdigest() if predecessor else None,
                  initial_sha256=hashlib.sha256(np.asarray(m,dtype='<f8').tobytes()).hexdigest(),
                  material=dict(Ms=MS,A=A,Ku=KU,alpha=0.5), protocol_version=1)
    out = BASE/'runs'/run_id
    mif = make_mif(g, fields, stop, static)
    config['mif_sha256'] = hashlib.sha256(mif.encode()).hexdigest()
    if out.exists():
        if not (out/'summary.json').exists():
            if ((out/'run.json').exists() and (out/'config.json').exists()
                    and json.loads((out/'config.json').read_text()) == config
                    and json.loads((out/'run.json').read_text())['returncode'] == 0):
                return analyze_case(out)
            raise RuntimeError(f'Incomplete directory retained: {out}; inspect before resume')
        old = json.loads((out/'summary.json').read_text(encoding='utf-8'))
        if old['config'] != config or not old['all_passed']:
            raise RuntimeError(f'Existing result mismatch or failure: {out}')
        return old
    out.mkdir(parents=True)
    dump(out/'config.json', config)
    dump(out/'geometry.json', g)
    write_ovf(out/'initial.omf', m, g)
    # OOMMF changes cwd to the MIF directory when reading relative field paths.
    (out/'input.mif').write_text(mif, encoding='utf-8')
    print(f'START {run_id}: {len(fields)} stages', flush=True)
    result = run([TCL, OOMMF, 'boxsi', '+fg', '-tk', '0', '-threads', '8', '-exitondone', '1',
                  '-kill', 'all', '-outdir', out, out/'input.mif'], out/'console.log', timeout)
    result['finished'] = datetime.now().astimezone().isoformat()
    dump(out/'run.json', result)
    if result['returncode']:
        raise RuntimeError(f'OOMMF exit {result["returncode"]}: {out}/console.log')
    summary = analyze_case(out)
    print(f'PASS {run_id}: {result["wall_seconds"]:.1f}s, mz={summary["stages"][-1]["mean_m"][2]:.8f}', flush=True)
    return summary


def spin_path(summary, stage=-1):
    return BASE/'runs'/summary['config']['run_id']/summary['stages'][stage]['spin_file']


def loop_fields(step=0.02, maximum=0.6):
    n = round(2*maximum/step)
    return np.r_[np.linspace(maximum,-maximum,n+1),np.linspace(-maximum,maximum,n+1)[1:]].tolist()


def seeded_path(run_id, shape, cell=2, fields=None, stop=0.01, predecessor=None, epsilon=0.001):
    """Perturb every opposing-field point; group aligned-field points without reseeding.

    This avoids zero-torque unstable states while preserving genuine field history.
    Every sub-run remains an independently inspectable OOMMF input/output directory.
    """
    fields=[float(round(x,10)) for x in (loop_fields() if fields is None else fields)]
    out=BASE/'runs'/run_id
    config=dict(run_id=run_id,shape=shape,cell_nm=cell,fields_T=fields,stop=stop,
                protocol='epsilon applied before each opposing-field point',epsilon=epsilon,
                predecessor=str(Path(predecessor).resolve()) if predecessor else None,
                predecessor_sha256=hashlib.sha256(Path(predecessor).read_bytes()).hexdigest() if predecessor else None)
    if (out/'summary.json').exists():
        result=json.loads((out/'summary.json').read_text(encoding='utf-8'))
        assert result['config']==config and result['all_passed']
        return result
    out.mkdir(parents=True,exist_ok=True)
    dump(out/'config.json',config)
    g,mask,_=geometry(shape,cell)
    mean_z=float(ovf(predecessor)[0][mask,2].mean()) if predecessor else 1.0
    rows=[]
    start=0
    current=predecessor
    while start<len(fields):
        opposing=fields[start]*mean_z<0
        end=start+1
        if not opposing:
            while end<len(fields) and fields[end]*mean_z>=0:
                end+=1
        part_id=f'{run_id}_s{start:03d}'
        part=case(part_id,shape,cell,fields=fields[start:end],stop=stop,
                  predecessor=current,epsilon=epsilon if opposing else 0)
        for record in part['stages']:
            r=dict(record)
            r['stage']=start+record['stage']
            r['spin_file']='../'+part_id+'/'+record['spin_file']
            r['source_run']=part_id
            r['applied_epsilon']=epsilon if opposing else 0
            rows.append(r)
        current=spin_path(part)
        mean_z=rows[-1]['mean_m'][2]
        start=end
        dump(out/'progress.json',dict(completed_stages=start,total_stages=len(fields),last_b_T=fields[start-1],mean_mz=mean_z))
    result=dict(config=config,geometry=g,stages=rows,all_passed=all(all(r['checks'].values()) for r in rows))
    dump(out/'summary.json',result)
    print(f'PATH PASS {run_id}: {len(rows)} stages',flush=True)
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--run-id',required=True)
    p.add_argument('--shape',choices=SHAPES,required=True)
    p.add_argument('--cell',type=int,default=2)
    p.add_argument('--initial',default='plus')
    p.add_argument('--static',action='store_true')
    p.add_argument('--loop',action='store_true')
    args=p.parse_args()
    case(args.run_id,args.shape,args.cell,args.initial,fields=loop_fields() if args.loop else None,static=args.static)
