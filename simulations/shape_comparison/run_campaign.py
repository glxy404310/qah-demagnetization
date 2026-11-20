"""Serial, checkpointed execution of the approved simulation matrix."""
import argparse
import traceback
from datetime import datetime
from simulate import *


def status(phase, **extra):
    dump(BASE/'status.json',dict(phase=phase,updated=datetime.now().astimezone().isoformat(),**extra))


def crossings(s):
    rows=s['stages']
    return [i for i in range(1,len(rows)) if rows[i-1]['mean_m'][2]*rows[i]['mean_m'][2]<0]


def check_loop(s):
    rows=s['stages']
    for i in (0,len(rows)//2,len(rows)-1):
        sign=1 if rows[i]['b_T']>0 else -1
        assert sign*rows[i]['mean_m'][2]>=0.999, f'Unsaturated endpoint {s["config"]["run_id"]} stage {i}'
    assert len(crossings(s))==2, f'Expected two reversals in {s["config"]["run_id"]}'


def refine(s, branch, step, stop=0.01, label=''):
    i=crossings(s)[branch]
    before=s['stages'][max(0,i-2)]
    after=s['stages'][i]
    direction=np.sign(after['b_T']-before['b_T'])
    endpoint=-0.6 if direction<0 else 0.6
    # Recompute fine interval, then replay remainder of this branch to saturation.
    end=round(after['b_T']+direction*0.02,10)
    fine=np.arange(before['b_T']+direction*step,end+direction*step*0.1,direction*step)
    tail=np.arange(end+direction*0.02,endpoint+direction*0.001,direction*0.02)
    fields=np.r_[fine,tail]
    if abs(fields[-1]-endpoint)>1e-8:
        fields=np.r_[fields,endpoint]
    cfg=s['config']
    run_id=f'{cfg["shape"]}_{cfg["cell_nm"]}nm_refine_b{branch}_{round(step*1e6)}uT{label}'
    r=seeded_path(run_id,cfg['shape'],cfg['cell_nm'],fields=fields,stop=stop,
           predecessor=spin_path(s,max(0,i-2)))
    assert len(crossings(r))==1, f'Refinement did not capture reversal: {run_id}'
    return r


def bracket(s, which=0):
    i=crossings(s)[which]
    return [s['stages'][i-1]['b_T'],s['stages'][i]['b_T']]


def verify_mesh(cell):
    path=BASE/'verification_details.json'
    details=json.loads(path.read_text()) if path.exists() else []
    for shape in SHAPES:
        coarse=json.loads((BASE/f'runs/{shape}_{cell}nm_loop_seeded/summary.json').read_text(encoding='utf-8'))
        for branch in (0,1):
            r10=refine(coarse,branch,0.01)
            r5=refine(coarse,branch,0.005)
            bc10,bc5=map(lambda s:float(np.mean(bracket(s))),(r10,r5))
            final=r5
            field_change=abs(bc10-bc5)
            if field_change>max(0.002,0.05*abs(bc5)):
                final=refine(coarse,branch,0.0025)
                field_change=abs(float(np.mean(bracket(final)))-bc5)
            tight=refine(coarse,branch,0.005,stop=0.005,label='_tight')
            item=dict(shape=shape,cell_nm=cell,branch=branch,bracket_T=bracket(final),
                      tight_bracket_T=bracket(tight),field_check_T=field_change,
                      coarse_field_check_T=abs(bc10-bc5),final_run=final['config']['run_id'])
            if cell==2:
                j=crossings(final)[0]
                item['perturbations']=[]
                for eps in (0.0001,0.001,0.01):
                    p=seeded_path(f'{shape}_2nm_perturb_b{branch}_eps{eps:g}',shape,
                                  fields=bracket(final),predecessor=spin_path(final,j-1),epsilon=eps)
                    item['perturbations'].append(dict(epsilon=eps,mz=[r['mean_m'][2] for r in p['stages']]))
            details=[d for d in details if (d['shape'],d['cell_nm'],d['branch'])!=(shape,cell,branch)]
            details.append(item)
            dump(path,details)


def campaign(phase):
    if phase in ('all','primary'):
        status('M1_static')
        for shape in SHAPES:
            ns=[]
            for axis in 'xyz':
                s=case(f'{shape}_2nm_static_{axis}',shape,initial=axis,static=True)
                ns.append(s['stages'][0]['N_field'])
            assert abs(sum(ns)-1)<1e-6
            print(f'TRACE {shape}: {sum(ns):.12f}',flush=True)
        status('M2_multiple_initial_states')
        for shape in SHAPES:
            for init in INITIALS:
                case(f'{shape}_2nm_zero_{init}',shape,initial=init)
        status('M3_hysteresis')
        for shape in SHAPES:
            s=case(f'{shape}_2nm_loop',shape,fields=loop_fields())
            # Original unperturbed curves are retained as symmetry diagnostics.
            if len(crossings(s))!=2:
                print(f'DIAGNOSTIC {shape}: unperturbed loop has {len(crossings(s))} reversals',flush=True)
        for shape in SHAPES:
            s=seeded_path(f'{shape}_2nm_loop_seeded',shape)
            check_loop(s)
        status('M3_reversal_trajectories')
        from trajectory import replay_switches
        replay_switches()
        status('M3_primary_complete')
        from report import build_report
        build_report()
    if phase in ('all','verification'):
        status('M3_field_and_tolerance_2nm')
        verify_mesh(2)
        from report import build_report
        build_report()
        current=json.loads((BASE/'analysis/results.json').read_text(encoding='utf-8'))
        protocol_failures=[k for k in current['failed_checks'] if any(t in k for t in ('_field','_tolerance','_perturbation'))]
        if protocol_failures:
            raise RuntimeError('2 nm protocol checks require follow-up before fine-grid batch: '+str(protocol_failures))
        status('M4_grid_static_and_zero')
        for shape in SHAPES:
            ns=[]
            for axis in 'xyz':
                s=case(f'{shape}_1nm_static_{axis}',shape,cell=1,initial=axis,static=True)
                ns.append(s['stages'][0]['N_field'])
            assert abs(sum(ns)-1)<1e-6
            for init in ('plus','domains'):
                case(f'{shape}_1nm_zero_{init}',shape,cell=1,initial=init)
            case(f'{shape}_2nm_zero_plus_tight',shape,stop=0.005)
        status('M4_grid_hysteresis')
        for shape in SHAPES:
            s=seeded_path(f'{shape}_1nm_loop_seeded',shape,cell=1)
            check_loop(s)
        status('M4_field_and_tolerance_1nm')
        verify_mesh(1)
        status('M4_simulations_complete')
    if phase in ('all','report'):
        from report import build_report
        build_report()
        final=json.loads((BASE/'analysis/results.json').read_text(encoding='utf-8'))
        status('COMPLETE' if final['numerical_acceptance_complete'] else 'REQUIRES_REVIEW',
               pending=final['pending'],failed_checks=final['failed_checks'])


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--phase',choices=('all','primary','verification','report'),default='all')
    args=p.parse_args()
    try:
        campaign(args.phase)
    except Exception as e:
        status('FAILED',error=str(e),traceback=traceback.format_exc())
        raise
