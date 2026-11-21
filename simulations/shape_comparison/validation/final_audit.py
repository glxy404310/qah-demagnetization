"""Reconcile the final measurements with archived OOMMF fields and paths, read-only on runs."""
import hashlib
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simulate import BASE, MS, MU0, dump, geometry, ovf, table


def read(path):
    return json.loads(path.read_bytes())


def digest(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(None)
def mesh(shape, cell):
    return geometry(shape, cell)[:2]


def inspect_run(folder, audit_row):
    cfg = read(folder / 'config.json')
    saved = read(folder / 'summary.json')
    assert cfg == saved['config'] and saved['all_passed'] and read(folder/'run.json')['returncode'] == 0, folder
    mif = folder/'input.mif'
    assert digest(mif.read_bytes()) == audit_row['mif_file_sha256']
    assert digest(mif.read_text().encode()) == cfg['mif_sha256']
    assert digest(ovf(folder/'initial.omf')[0].astype('<f8').tobytes()) == cfg['initial_sha256']
    if cfg['predecessor']:
        previous = Path(cfg['predecessor']).resolve()
        assert previous.is_relative_to(BASE/'runs') and digest(previous.read_bytes()) == cfg['predecessor_sha256']
    expected_cap = cfg.get('stage_iteration_limit', 100000)
    assert int(re.search(r'stage_iteration_limit\s+(\d+)', mif.read_text())[1]) == expected_cap
    g, mask = mesh(cfg['shape'], cfg['cell_nm'])
    assert read(folder/'geometry.json') == g == saved['geometry']
    assert abs(mask.sum()*cfg['cell_nm']**3*1e-27/g['volume_m3']-1) < 1e-10
    assert abs(g['volume_m3']*1e27/4-g['area_nm2']) < 1e-6
    odt = folder/'result.odt'
    data = table(odt)
    checksums = {odt.name: digest(odt.read_bytes())}
    stage_id = data['Oxs_TimeDriver::Stage']
    assert len(cfg['fields_T']) == len(saved['stages']) == len(np.unique(stage_id))
    for i, (field, record) in enumerate(zip(cfg['fields_T'], saved['stages'])):
        indices = np.flatnonzero(stage_id == i)
        k = indices[-1]
        path = folder/record['spin_file']
        spin = ovf(path)[0][mask]
        avg = spin.mean(axis=0)
        measured = [data['Oxs_TimeDriver::m'+a][k] for a in 'xyz']
        assert np.allclose(avg, measured, rtol=0, atol=1e-8) and np.allclose(avg, record['mean_m'], atol=1e-8), path
        assert np.abs(np.linalg.norm(spin, axis=1)-1).max() < 1e-6
        rate = data['Oxs_RungeKuttaEvolve:evolve:Max dm/dt'][k]
        assert rate <= cfg['stop']*1.00001 and abs(rate-record['max_dm_dt_deg_ns']) < 1e-10
        assert data['Oxs_TimeDriver::Stage iteration'][k] < expected_cap
        suffix = path.name.split('Spin-')[-1].replace('.omf','.ohf')
        hd_path = folder/('result-Oxs_Demag-demag-Field-'+suffix)
        h_path = folder/('result-Oxs_RungeKuttaEvolve-evolve-Total_field-'+suffix)
        for raw in (path, hd_path, h_path):
            checksums[raw.name] = digest(raw.read_bytes())
        hd = ovf(hd_path)[0][mask]
        ed = -0.5*MU0*MS*g['volume_m3']*np.einsum('ij,ij->',spin,hd)/len(spin)
        assert abs(ed-data['Oxs_Demag:demag:Energy'][k]) < 1e-25
        if cfg['static']:
            continue
        h = ovf(h_path)[0][mask]
        transverse = np.cross(spin,h)
        rhs = np.linalg.norm(transverse,axis=1).max()*2.21e5*0.5/1.25*180/np.pi*1e-9
        assert abs(rhs-rate) < max(1e-6, rate*1e-5) and rhs <= cfg['stop']*1.00001
        assert abs(data['Oxs_UZeeman:zeeman:Bz'][k]/1000-field) < 1e-10
        assert abs(data['Oxs_UZeeman:zeeman:Energy'][k] + MS*g['volume_m3']*field*avg[2]) < 1e-25
        assert np.all(np.diff(data['Oxs_RungeKuttaEvolve:evolve:Total energy'][indices]) <= 1e-25)
    return dict(stages=len(saved['stages']), raw_files=len(checksums),
                sha256_of_sorted_filename_hash_pairs=digest(json.dumps(sorted(checksums.items())).encode()))


def main():
    runs = BASE/'runs'
    analysis = BASE/'analysis'
    result = read(analysis/'results.json')
    verification = read(BASE/'verification_details.json')
    audit = read(analysis/'output_audit.json')
    assert result['pending'] == result['failed_checks'] == [] and result['verification'] == verification
    assert len({(x['shape'],x['cell_nm'],x['branch']) for x in verification}) == len(verification) == 12
    rows = {r['run_id']:r for r in audit['runs']}
    assert set(rows) == {s.parent.name for s in runs.glob('*/summary.json')}
    assert all(all(r['checks'].values()) for r in rows.values())
    assert sum(len(r['checks']) for r in rows.values()) == audit['checks']
    raw = {name:inspect_run(runs/name, row) for name,row in rows.items() if (runs/name/'input.mif').is_file()}
    for name in rows.keys()-raw.keys():
        aggregate = read(runs/name/'summary.json')
        for i, record in enumerate(aggregate['stages']):
            source = runs/record['source_run']
            spin = (runs/name/record['spin_file']).resolve()
            assert record['source_run'] in raw and spin.parent == source.resolve()
            part = read(source/'summary.json')
            stage = int(spin.stem.split('-')[-2])
            reference = part['stages'][stage]
            assert spin.name == reference['spin_file'] and record['stage'] == i
            for k in ('mean_m','iterations','energy_J','max_dm_dt_deg_ns','b_T'):
                assert record[k] == reference[k]
    for folder in (BASE/'trajectories').iterdir():
        if not (folder/'summary.json').exists():
            continue
        replay = read(folder/'summary.json')
        last = replay['samples'][-1]['file']
        assert np.array_equal(ovf(folder/last)[0],ovf(runs/replay['source_run']/last)[0])
    traces = []
    for v in verification:
        sign = 1 if v['branch'] else -1
        for label, spacing, stop in [('10000uT',0.01,0.01),('5000uT',0.005,0.01),('5000uT_tight',0.005,0.005)]:
            path = runs/(v['final_run'].replace('5000uT',label))
            summary = read(path/'summary.json')
            stages = summary['stages']
            changes = np.flatnonzero(np.diff(np.sign([s['mean_m'][2] for s in stages])))
            assert len(changes) == 1 and summary['config']['stop'] == stop
            pre, post = stages[changes[0]:changes[0]+2]
            assert np.allclose([pre['b_T'],post['b_T']],sign*np.array([0.18,0.18+spacing]))
            if label == '10000uT':
                continue
            assert np.allclose([pre['b_T'],post['b_T']],v['tight_bracket_T' if 'tight' in label else 'bracket_T'])
            assert abs(v['field_check_T']-0.0025)<1e-12 and v['field_check_T']<0.009125
            part = runs/post['source_run']
            d = table(part/'result.odt')
            g,mask = mesh(v['shape'],v['cell_nm'])
            pre_mz,post_mz = (float(ovf(path/s['spin_file'])[0][mask][:,2].mean()) for s in (pre,post))
            assert sign*pre_mz < -0.99 and sign*post_mz > 0.99
            select = np.isclose(d['Oxs_UZeeman:zeeman:Bz'],sign*185)
            norm = np.linalg.norm(np.column_stack([d['Oxs_TimeDriver::m'+a][select] for a in 'xyz']),axis=1)
            energy = d['Oxs_RungeKuttaEvolve:evolve:Total energy'][select]
            iteration = d['Oxs_TimeDriver::Iteration'][select]
            traces.append(dict(shape=v['shape'],cell_nm=v['cell_nm'],branch=v['branch'],stop=stop,
                source=part.name,pre_mz=pre_mz,post_mz=post_mz,min_norm=float(norm.min()),
                iteration_min=int(iteration[norm.argmin()]),iteration_end=int(iteration[-1]),
                final_rate=post['max_dm_dt_deg_ns'],max_energy_increment_J=float(np.diff(energy).max())))
    dump(BASE/'validation/final_audit.json',dict(branches=len(verification),output_checks=audit['checks'],
         audited_directories=len(rows),physical_runs=len(raw),raw_stages=sum(r['stages'] for r in raw.values()),
         raw_files=sum(r['raw_files'] for r in raw.values()),raw=raw,refined_reversal=traces))
    print('Verified',len(rows),'directories,',len(raw),'physical runs,',len(traces),'refined switch traces.')


if __name__ == '__main__':
    main()
