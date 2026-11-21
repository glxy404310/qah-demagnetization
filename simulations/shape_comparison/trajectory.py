"""Replay one descending reversal per shape, adding snapshots only."""
import shutil
from simulate import *


def replay_switches():
    from run_campaign import crossings
    reports=[]
    for shape in SHAPES:
        loop=json.loads((BASE/f'runs/{shape}_2nm_loop_seeded/summary.json').read_text(encoding='utf-8'))
        index=crossings(loop)[0]
        record=loop['stages'][index]
        source=BASE/'runs'/record['source_run']
        out=BASE/'trajectories'/shape
        if (out/'summary.json').exists():
            report=json.loads((out/'summary.json').read_text())
            assert report['passed'] and report['source_run']==source.name
            reports.append(report)
            continue
        if out.exists():
            raise RuntimeError(f'Incomplete trajectory retained at {out}')
        out.mkdir(parents=True)
        shutil.copy2(source/'initial.omf',out/'initial.omf')
        mif=(source/'input.mif').read_text(encoding='utf-8')+'\nSchedule Oxs_TimeDriver::Spin archive Step 50\n'
        (out/'input.mif').write_text(mif,encoding='utf-8')
        dump(out/'config.json',dict(source_run=source.name,source_config=json.loads((source/'config.json').read_text()),
                                   source_mif_file_sha256=hashlib.sha256((source/'input.mif').read_bytes()).hexdigest(),
                                   snapshot_step=50,change='Only add Spin archive Step 50'))
        print(f'TRAJECTORY START {shape}: {source.name}',flush=True)
        result=run([TCL,OOMMF,'boxsi','+fg','-tk','0','-threads','8','-exitondone','1','-kill','all',
                    '-outdir',out,out/'input.mif'],out/'console.log',7200)
        dump(out/'run.json',result)
        assert result['returncode']==0,(shape,result)
        files=sorted(out.glob('*Spin*.omf'),key=lambda p:int(p.stem.split('-')[-1]))
        g,mask,_=geometry(shape,2)
        samples=[]
        for path in files:
            m=ovf(path)[0][mask]
            mean=m.mean(axis=0)
            samples.append(dict(file=path.name,iteration=int(path.stem.split('-')[-1]),
                                mean_m=mean.tolist(),mean_norm=float(np.linalg.norm(mean)),
                                mean_abs_mz=float(np.abs(m[:,2]).mean()),negative_fraction=float((m[:,2]<0).mean())))
        original=ovf(source/record['spin_file'].split('/')[-1])[0]
        final=ovf(files[-1])[0]
        error=float(np.max(np.abs(final[mask]-original[mask])))
        d=table(next(out.glob('*.odt')))
        rate=float(d['Oxs_RungeKuttaEvolve:evolve:Max dm/dt'][-1])
        report=dict(shape=shape,source_run=source.name,b_T=record['b_T'],samples=samples,
                    final_spin_max_difference=error,max_dm_dt_deg_ns=rate,
                    minimum_mean_norm=min(s['mean_norm'] for s in samples),passed=error<1e-5 and rate<=0.01)
        dump(out/'summary.json',report)
        assert report['passed'],report
        reports.append(report)
        print(f'TRAJECTORY PASS {shape}: {len(samples)} snapshots, final error={error:.3g}',flush=True)
    return reports


if __name__=='__main__':
    replay_switches()
