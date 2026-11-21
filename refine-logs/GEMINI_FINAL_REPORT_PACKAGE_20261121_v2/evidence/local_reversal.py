"""Read saved uniform +z fields, descending-loop scalar traces and coarse snapshots."""
import hashlib
import json
import numpy as np
from simulate import A, BASE, KU, MS, MU0, SHAPES, dump, geometry, ovf, table
import matplotlib.pyplot as plt


def analyze():
    lex = np.sqrt(2*A/(MU0*MS**2))*1e9
    result = dict(exchange_length_nm=lex, B_K_T=2*KU/MS, fields=[], traces=[], first_reverse=[])
    fig,axes=plt.subplots(2,3,figsize=(10,5.3),sharex=True,layout='constrained')
    for col,shape in enumerate(SHAPES):
        for cell in (2, 1):
            g, mask, (x,y,_) = geometry(shape, cell)
            r = np.hypot(x,y)
            distance = (np.sqrt(40000/np.pi)-r if shape=='circle' else
                        np.minimum(g['lx_nm']/2-np.abs(x),g['ly_nm']/2-np.abs(y)))
            f = next((BASE/f'runs/{shape}_{cell}nm_static_z').glob('*Demag*.ohf'))
            hd = ovf(f)[0][...,2]
            row = dict(shape=shape,cell_nm=cell,source=str(f.relative_to(BASE)),
                       sha256=hashlib.sha256(f.read_bytes()).hexdigest())
            for name,region in [('point',r==r.min()),('core',r<=lex),('edge',distance<=lex),
                                ('interior',distance>lex),('all',mask)]:
                h = hd[region & mask]
                row[name]=dict(cells=h.size,N=-h.mean()/MS,B_mT=1000*MU0*h.mean())
            recorded=json.loads((f.parent/'summary.json').read_bytes())
            assert recorded['all_passed'] and abs(recorded['stages'][0]['N_field']-row['all']['N'])<1e-10
            result['fields'].append(row)

            f=BASE/f'runs/{shape}_{cell}nm_loop_seeded_s040'
            c=json.loads((f/'config.json').read_bytes())
            s=json.loads((f/'summary.json').read_bytes())
            assert s['all_passed'] and c['fields_T']==[-0.2]
            d=table(next(f.glob('*.odt')))
            means=np.array([d['Oxs_TimeDriver::m'+a] for a in 'xyz']).T
            norm=np.linalg.norm(means,axis=1)
            end=ovf(f/s['stages'][0]['spin_file'])[0][mask].mean(axis=0)
            initial=ovf(f/'initial.omf')[0][mask].mean(axis=0)
            before=ovf(c['predecessor'])[0][mask].mean(axis=0)
            assert np.allclose([initial,end],means[[0,-1]],rtol=0,atol=1e-8)
            energy=d['Oxs_RungeKuttaEvolve:evolve:Total energy']
            steps=d['Oxs_TimeDriver::Iteration']
            for ax,values in zip(axes[:,col],(norm,(energy-energy[0])/g['volume_m3']/1000)):
                ax.plot(steps/steps[-1],values,label=f'{cell} nm',linestyle='-' if cell==1 else '--')
                ax.grid(alpha=.2)
            axes[0,col].set_title(shape.capitalize())
            axes[1,col].set_xlabel('Iteration / final iteration')
            result['traces'].append(dict(shape=shape,cell_nm=cell,source=f.name,
                sample_count=len(norm),iteration_end=int(d['Oxs_TimeDriver::Iteration'][-1]),
                iteration_min_norm=int(d['Oxs_TimeDriver::Iteration'][norm.argmin()]),
                min_norm=norm.min(),energy_delta_J=float(energy[-1]-energy[0]),
                max_positive_energy_increment_J=max(0,float(np.diff(energy).max())),
                predecessor_mz=before[2],end_mz=end[2],end_rate=d['Oxs_RungeKuttaEvolve:evolve:Max dm/dt'][-1]))

        trajectory=BASE/'trajectories'/shape
        seq=json.loads((trajectory/'summary.json').read_bytes())
        assert seq['passed']
        sample=next(k for k in seq['samples'] if k['negative_fraction']>0)
        _,mask,(x,y,_)=geometry(shape,2)
        reversed_cells=mask & (ovf(trajectory/sample['file'])[0][...,2]<0)
        result['first_reverse'].append(dict(shape=shape,file=sample['file'],step=sample['iteration'],
            count=int(reversed_cells.sum()),x_min_nm=x[reversed_cells].min(),x_max_nm=x[reversed_cells].max(),
            y_min_nm=y[reversed_cells].min(),y_max_nm=y[reversed_cells].max()))
    dump(BASE/'analysis/local_reversal.json',result)
    for ax in axes[0]:
        ax.set_ylim(0.38, 1.03)
    axes[0,0].set_ylabel('Norm of mean spin')
    axes[1,0].set_ylabel('Energy change (kJ/m³)')
    axes[0,0].legend()
    fig.suptitle('Descending reversal at −0.20 T')
    fig.savefig(BASE/'figures/cross_mesh_reversal_odt.png',dpi=180)
    plt.close(fig)


if __name__=='__main__':
    analyze()
