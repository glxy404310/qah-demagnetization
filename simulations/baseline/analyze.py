"""Validate OOMMF outputs against analytic N and independent field/energy checks."""
import csv
import argparse
import json
import math
import os
from pathlib import Path
import re
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.tools/matplotlib-cache'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, str(ROOT / '理论学习资料/辅助文件/output/demag-learning'))
from rectangular_demag import rectangular_factors

MU0 = 4 * math.pi * 1e-7
MS, A, KU, ALPHA, GAMMA_G = 3e5, 5e-12, 8e4, 0.5, 2.21e5
VOLUME = 200e-9 * 200e-9 * 4e-9
REFERENCE = np.array(rectangular_factors(200, 200, 4))


def ovf(path):
    """Read rectangular OVF 2 binary-8 fields, checking endian marker and shape."""
    with Path(path).open('rb') as handle:
        header = {}
        while True:
            line = handle.readline()
            if not line:
                raise ValueError(f'Missing binary data in {path}')
            text = line.decode('utf-8', errors='replace').strip()
            if text.lower() == '# begin: data binary 8':
                break
            if text.startswith('# ') and ':' in text:
                key, value = text[2:].split(':', 1)
                header[key.lower()] = value.strip()
        marker = handle.read(8)
        dtype = '<f8' if np.frombuffer(marker, dtype='<f8')[0] == 123456789012345.0 else '>f8'
        if np.frombuffer(marker, dtype=dtype)[0] != 123456789012345.0:
            raise ValueError(f'Invalid OVF check value in {path}')
        nx, ny, nz = (int(header[f'{a}nodes']) for a in 'xyz')
        nc = int(header.get('valuedim', '3'))
        size = nx * ny * nz * nc
        data = np.frombuffer(handle.read(size * 8), dtype=dtype).copy()
        if data.size != size or not np.isfinite(data).all():
            raise ValueError(f'Invalid/truncated field in {path}')
    return data.reshape(nz, ny, nx, nc), header


def table(path):
    lines = path.read_text(encoding='utf-8').splitlines()
    header = next(line[len('# Columns: '):] for line in lines if line.startswith('# Columns: '))
    names = [a or b for a, b in re.findall(r'\{([^}]+)\}|(\S+)', header)]
    rows = np.array([[float(x) for x in line.split()] for line in lines
                     if line.strip() and not line.startswith('#')])
    if rows.shape[1] != len(names) or not np.isfinite(rows).all():
        raise ValueError(f'Invalid table in {path}')
    return {name: rows[:, i] for i, name in enumerate(names)}


def field(folder, pattern):
    paths = list(folder.glob(pattern))
    if len(paths) != 1:
        raise ValueError(f'Expected one {pattern} in {folder}, found {len(paths)}')
    return ovf(paths[0])[0]


def validate():
    checks = {}
    static = []
    for nm in (2, 1):
        for i, axis in enumerate('xyz'):
            folder = BASE / f'oommf_{nm}nm_static_{axis}'
            data = table(next(folder.glob('*.odt')))
            spin = field(folder, '*.omf')
            hd = field(folder, '*Demag*.ohf')
            expected = np.eye(3)[i]
            n_field = float(-hd[..., i].mean()/MS)
            e_table = float(data['Oxs_Demag:demag:Energy'][-1])
            n_energy = 2*e_table/(MU0*MS**2*VOLUME)
            e_field = float(-0.5*MU0*MS*VOLUME*np.sum(spin*hd, axis=-1).mean())
            deviation = float(np.max(np.abs(spin-expected)))
            record = dict(cell_nm=nm, axis=axis, N_analytic=float(REFERENCE[i]),
                          N_field=n_field, N_energy=n_energy,
                          abs_error=abs(n_field-REFERENCE[i]),
                          energy_J=e_table, energy_from_field_J=e_field,
                          mean_Hd_A_m=hd.mean(axis=(0,1,2)).tolist(),
                          max_uniform_m_error=deviation,
                          iterations=int(data['Oxs_TimeDriver::Iteration'][-1]))
            static.append(record)
            checks[f'{nm}nm_{axis}_N'] = record['abs_error'] < 1e-4
            checks[f'{nm}nm_{axis}_field_energy'] = abs(n_field-n_energy) < 1e-10
            checks[f'{nm}nm_{axis}_frozen'] = deviation < 1e-14 and record['iterations'] == 0
        current = [r['N_field'] for r in static if r['cell_nm'] == nm]
        checks[f'{nm}nm_trace'] = abs(sum(current)-1) < 1e-8
        checks[f'{nm}nm_xy_symmetry'] = abs(current[0]-current[1]) < 1e-10

    relaxation, arrays = {}, {}
    for name, stop in [('2nm_relax', 0.01), ('1nm_relax', 0.01), ('2nm_tight', 0.005)]:
        folder = BASE / f'oommf_{name}'
        data = table(next(folder.glob('*.odt')))
        m = field(folder, '*.omf')
        hd = field(folder, '*Demag*.ohf')
        heff = field(folder, '*Total_field*.ohf')
        rhs = -GAMMA_G*ALPHA/(1+ALPHA**2)*np.cross(m, np.cross(m, heff))
        rhs_rate = float(np.linalg.norm(rhs, axis=-1).max()*180/math.pi*1e-9)
        reported_rate = float(data['Oxs_RungeKuttaEvolve:evolve:Max dm/dt'][-1])
        energies = {term: float(data[key][-1]) for term, key in {
            'demag':'Oxs_Demag:demag:Energy',
            'exchange':'Oxs_UniformExchange:exchange:Energy',
            'anisotropy':'Oxs_UniaxialAnisotropy:anisotropy:Energy',
            'zeeman':'Oxs_FixedZeeman:zeeman:Energy'}.items()}
        total = data['Oxs_RungeKuttaEvolve:evolve:Total energy']
        record = dict(mean_m=m.mean(axis=(0,1,2)).tolist(),
                      mean_abs_mz=float(np.abs(m[...,2]).mean()),
                      min_mz=float(m[...,2].min()), max_mz=float(m[...,2].max()),
                      negative_mz_fraction=float(np.mean(m[...,2] < 0)),
                      max_tilt_deg=float(np.arccos(np.clip(m[...,2],-1,1)).max()*180/math.pi),
                      max_norm_error=float(np.max(np.abs(np.linalg.norm(m,axis=-1)-1))),
                      stopping_dm_dt_deg_ns=stop, reported_max_dm_dt_deg_ns=reported_rate,
                      independent_max_dm_dt_deg_ns=rhs_rate,
                      max_m_cross_H_A_m=float(np.linalg.norm(np.cross(m,heff),axis=-1).max()),
                      initial_energy_J=float(total[0]), final_energy_J=float(total[-1]),
                      energy_terms_J=energies,
                      max_recorded_energy_increase_J=float(np.diff(total).max()),
                      demag_energy_from_field_J=float(-0.5*MU0*MS*VOLUME*np.sum(m*hd,axis=-1).mean()),
                      iterations=int(data['Oxs_TimeDriver::Iteration'][-1]),
                      numerical_relaxation_time_s=float(data['Oxs_TimeDriver::Simulation time'][-1]))
        relaxation[name] = record
        arrays[name] = (m, hd, data)
        checks[f'{name}_converged'] = reported_rate <= stop and rhs_rate <= stop*1.00001
        checks[f'{name}_independent_RHS'] = abs(reported_rate-rhs_rate) < 1e-6
        checks[f'{name}_unit_m'] = record['max_norm_error'] < 1e-12
        checks[f'{name}_energy_decreased'] = total[-1] < total[0]
        checks[f'{name}_energy_monotonic'] = record['max_recorded_energy_increase_J'] <= 1e-25
        checks[f'{name}_energy_sum'] = abs(sum(energies.values())-total[-1]) < 1e-27
        checks[f'{name}_demag_energy'] = abs(record['demag_energy_from_field_J']-energies['demag']) < 1e-27
        checks[f'{name}_iteration_limit_not_hit'] = record['iterations'] < 100000

    coarse, fine, tight = (relaxation[k] for k in ['2nm_relax','1nm_relax','2nm_tight'])
    grid = dict(abs_mean_mz_change=abs(fine['mean_m'][2]-coarse['mean_m'][2]),
                relative_total_energy_change=abs(fine['final_energy_J']/coarse['final_energy_J']-1),
                max_tilt_change_deg=abs(fine['max_tilt_deg']-coarse['max_tilt_deg']),
                note='One mesh refinement; sufficient for this near-uniform baseline, not a universal convergence claim.')
    tolerance = dict(abs_mean_mz_change=abs(tight['mean_m'][2]-coarse['mean_m'][2]),
                     relative_total_energy_change=abs(tight['final_energy_J']/coarse['final_energy_J']-1))
    checks['mesh_mean_mz'] = grid['abs_mean_mz_change'] < 1e-4
    checks['mesh_total_energy'] = grid['relative_total_energy_change'] < 1e-3
    checks['tighter_tolerance_mean_mz'] = tolerance['abs_mean_mz_change'] < 1e-5
    checks['tighter_tolerance_energy'] = tolerance['relative_total_energy_change'] < 1e-5
    checks = {name: bool(passed) for name, passed in checks.items()}
    result = dict(solver='OOMMF 2.0b0',
                  model=dict(size_nm=[200,200,4],Ms_A_m=MS,A_J_m=A,Ku_J_m3=KU,
                             alpha=ALPHA,gamma_G_m_As=GAMMA_G,field_A_m=[0,0,0],
                             initial_m_direction=[0.01,0,1],temperature_K=0,
                             precession=False,boundaries='open'),
                  static=static,relaxation=relaxation,mesh_check=grid,
                  tolerance_check=tolerance,checks=checks,
                  all_passed=all(checks.values()))
    (BASE/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    with (BASE/'demag_factors.csv').open('w',newline='',encoding='utf-8') as handle:
        keys=['cell_nm','axis','N_analytic','N_field','N_energy','abs_error','energy_J']
        writer=csv.DictWriter(handle,fieldnames=keys,extrasaction='ignore')
        writer.writeheader(); writer.writerows(static)
    plot(arrays)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if not result['all_passed']:
        raise SystemExit('FAILED: '+', '.join(k for k,v in checks.items() if not v))


def plot(arrays):
    plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'figure.facecolor':'white'})
    m, hd, data = arrays['2nm_relax']
    uniform_hd = field(BASE/'oommf_2nm_static_z','*Demag*.ohf')
    fig, axes = plt.subplots(2,2,figsize=(11,8),layout='constrained')
    fig.suptitle('方形薄膜基准  |  OOMMF  |  200 × 200 × 4 nm',fontsize=15)
    ax=axes[0,0]
    im=ax.imshow(MU0*uniform_hd[0,:,:,2],origin='lower',extent=[0,200,0,200],cmap='viridis')
    ax.set(title='沿 +z 均匀磁化：退磁场分布',xlabel='x (nm)',ylabel='y (nm)')
    fig.colorbar(im,ax=ax,label=r'$\mu_0 H_{d,z}$ (T)')
    ax=axes[0,1]
    im=ax.imshow(m[0,:,:,2],origin='lower',extent=[0,200,0,200],cmap='RdBu_r',vmin=-1,vmax=1)
    ax.set(title='零场弛豫后：面外磁化（底层）',xlabel='x (nm)',ylabel='y (nm)')
    fig.colorbar(im,ax=ax,label='mz')
    ax.text(0.03,0.04,f'全体积平均 mz = {m[...,2].mean():.9f}',transform=ax.transAxes,
            bbox=dict(facecolor='white',edgecolor='none',alpha=0.9))
    ax=axes[1,0]
    tilt=np.arccos(np.clip(m[0,:,:,2],-1,1))*180/math.pi
    im=ax.imshow(tilt,origin='lower',extent=[0,200,0,200],cmap='magma',vmin=0)
    ax.set(title='微小边缘倾斜（放大色标，2 nm 网格底层）',xlabel='x (nm)',ylabel='y (nm)')
    fig.colorbar(im,ax=ax,label='偏离 +z 的角度（°）')
    ax=axes[1,1]
    for name,color,style in [('2nm_relax','#1864ab','-'),('1nm_relax','#b76a12','--')]:
        d=arrays[name][2]
        it=d['Oxs_TimeDriver::Iteration']
        rate=d['Oxs_RungeKuttaEvolve:evolve:Max dm/dt']
        ax.semilogy(it,rate,style,color=color,label=name.split('_')[0])
    ax.axhline(0.01,color='#555555',ls=':',label='收敛阈值')
    ax.set(title='数值弛豫收敛（关闭进动）',xlabel='求解器接受的步数',ylabel='最大 |dm/dt| (°/ns)')
    ax.grid(alpha=0.2); ax.legend()
    fig.savefig(BASE/'baseline.png',dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-root', type=Path, default=BASE)
    BASE = parser.parse_args().results_root.resolve()
    validate()
