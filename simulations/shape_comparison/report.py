"""Generate source-linked figures, tables and explicit acceptance results."""
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from simulate import *

LABELS={'square':'Square','circle':'Circle','rectangle':'Rectangle (4:1)'}
COLORS={'square':'#2563eb','circle':'#d97706','rectangle':'#059669'}


def load(run_id):
    if run_id.endswith('_loop'):
        run_id+='_seeded'
    path=BASE/'runs'/run_id/'summary.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None


def csv_write(name,rows):
    if not rows:
        return
    with (BASE/'analysis'/name).open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_report():
    from run_campaign import crossings,bracket
    from audit_outputs import audit
    audit_result=audit()
    (BASE/'analysis').mkdir(exist_ok=True)
    (BASE/'figures').mkdir(exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    static,zero,curves=[],[],[]
    for shape in SHAPES:
        for cell in (2,1):
            for axis in 'xyz':
                s=load(f'{shape}_{cell}nm_static_{axis}')
                if s:
                    r=s['stages'][0]
                    static.append(dict(shape=shape,cell_nm=cell,axis=axis,area_nm2=s['geometry']['area_nm2'],
                                       N_field=r['N_field'],N_energy=r['N_energy'],run_id=s['config']['run_id']))
            for init in INITIALS:
                s=load(f'{shape}_{cell}nm_zero_{init}')
                if s:
                    r=s['stages'][0]
                    zr=dict(shape=shape,cell_nm=cell,initial=init,mz=r['mean_m'][2],
                                     mean_abs_mz=r['mean_abs_mz'],negative_fraction=r['negative_fraction'],
                                     energy_density_J_m3=r['energy_density_J_m3'],dm_dt=r['max_dm_dt_deg_ns'],
                                     run_id=s['config']['run_id'])
                    zr.update({key.split(':')[1]+'_J_m3':value/s['geometry']['volume_m3'] for key,value in r['energy_J'].items()})
                    zero.append(zr)
            s=load(f'{shape}_{cell}nm_loop')
            if s:
                for r in s['stages']:
                    curves.append(dict(shape=shape,cell_nm=cell,stage=r['stage'],b_T=r['b_T'],mz=r['mean_m'][2],
                                       mean_abs_mz=r['mean_abs_mz'],negative_fraction=r['negative_fraction'],
                                       energy_density_J_m3=r['energy_density_J_m3'],
                                       dm_dt=r['max_dm_dt_deg_ns'],iterations=r['iterations']))
    csv_write('demag_factors.csv',static)
    csv_write('zero_states.csv',zero)
    csv_write('hysteresis.csv',curves)
    energy_comparison=[]
    for shape in SHAPES:
        single=next((r for r in zero if r['shape']==shape and r['cell_nm']==2 and r['initial']=='plus'),None)
        domain=next((r for r in zero if r['shape']==shape and r['cell_nm']==2 and r['initial']=='domains'),None)
        if single and domain:
            energy_comparison.append(dict(shape=shape,single_J_m3=single['energy_density_J_m3'],
                domains_J_m3=domain['energy_density_J_m3'],
                delta_total_J_m3=domain['energy_density_J_m3']-single['energy_density_J_m3'],
                delta_demag_J_m3=domain['demag_J_m3']-single['demag_J_m3'],
                delta_exchange_J_m3=domain['exchange_J_m3']-single['exchange_J_m3'],
                delta_anisotropy_J_m3=domain['anisotropy_J_m3']-single['anisotropy_J_m3'],
                domain_mean_abs_mz=domain['mean_abs_mz']))
    csv_write('domain_energy_comparison.csv',energy_comparison)
    if energy_comparison:
        fig,ax=plt.subplots(figsize=(9,4.8),layout='constrained')
        x=np.arange(len(energy_comparison)); width=0.19
        for j,(key,label,color) in enumerate([
            ('delta_demag_J_m3','Demagnetizing','#2563eb'),
            ('delta_exchange_J_m3','Exchange','#d97706'),
            ('delta_anisotropy_J_m3','Anisotropy','#059669'),
            ('delta_total_J_m3','Total','#6d28d9')]):
            values=np.array([r[key] for r in energy_comparison])/1000
            ax.bar(x+(j-1.5)*width,values,width,label=label,color=color)
        ax.axhline(0,color='#555',lw=0.8)
        ax.set(xticks=x,xticklabels=[LABELS[r['shape']] for r in energy_comparison],
               ylabel='Two-domain minus near-uniform energy (kJ/m^3)',title='Zero-field stationary states, 2 nm mesh',ylim=(-10,14.5))
        ax.legend(ncol=4,fontsize=9)
        fig.savefig(BASE/'figures/domain_energy_competition.png',dpi=180)
        plt.close(fig)

    # Spatial comparison uses actual coordinates, same color range, and masked vacuum.
    available=[shape for shape in SHAPES if load(f'{shape}_2nm_static_z')]
    if available:
        fig,axes=plt.subplots(2,len(available),figsize=(4.5*len(available),7),squeeze=False,layout='constrained')
        for j,shape in enumerate(available):
            s=load(f'{shape}_2nm_static_z')
            g,mask,coords=geometry(shape,2)
            hd=ovf(field_file(BASE/'runs'/s['config']['run_id'],'*Demag*.ohf',0))[0]
            data=np.where(mask[0],MU0*hd[0,:,:,2],np.nan)
            im=axes[0,j].imshow(data,origin='lower',extent=[-g['lx_nm']/2,g['lx_nm']/2,-g['ly_nm']/2,g['ly_nm']/2],
                                vmin=-0.38,vmax=-0.15,cmap='viridis',aspect='equal')
            axes[0,j].set(title=LABELS[shape],xlabel='x (nm)',ylabel='y (nm)')
            fig.colorbar(im,ax=axes[0,j],label='mu0 Hd,z (T), bottom layer')
            # Average of the two central y rows avoids choosing a side on even meshes.
            pair=data[g['ny']//2-1:g['ny']//2+1]
            count=np.isfinite(pair).sum(axis=0)
            center=np.divide(np.nansum(pair,axis=0),count,out=np.full(count.shape,np.nan),where=count>0)
            axes[1,j].plot(coords[0][0,0],center,color=COLORS[shape])
            axes[1,j].set(xlabel='x (nm)',ylabel='mu0 Hd,z (T)',ylim=(-0.39,-0.14),title='Central line profile')
        fig.savefig(BASE/'figures/demag_comparison.png',dpi=180)
        plt.close(fig)

    loop_shapes=[shape for shape in SHAPES if load(f'{shape}_2nm_loop')]
    if loop_shapes:
        fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
        for shape in loop_shapes:
            for cell,style in ((2,'-'),(1,'--')):
                s=load(f'{shape}_{cell}nm_loop')
                if not s:
                    continue
                rs=s['stages']
                visible_style={'square':'-','circle':'--','rectangle':':'}[shape] if cell==2 else '-.'
                axes[0].plot([r['b_T'] for r in rs],[r['mean_m'][2] for r in rs],visible_style,
                             color=COLORS[shape],label=f'{LABELS[shape]}, {cell} nm')
            rs=load(f'{shape}_2nm_loop')['stages']
            axes[1].plot([r['b_T'] for r in rs[:61]],[r['energy_density_J_m3'] for r in rs[:61]],
                         color=COLORS[shape],label=LABELS[shape])
        axes[0].set(xlabel='mu0 Hext,z (T)',ylabel='<mz>',ylim=(-1.05,1.05),title='Full loops, epsilon=0.001 at opposing fields')
        axes[1].set(xlabel='mu0 Hext,z (T)',ylabel='Total energy / magnetic volume (J/m^3)',title='Descending branch (2 nm)')
        for ax in axes:
            ax.grid(alpha=0.2)
            ax.legend(fontsize=8)
        fig.savefig(BASE/'figures/hysteresis_comparison.png',dpi=180)
        plt.close(fig)
        fig,axes=plt.subplots(1,len(loop_shapes),figsize=(5*len(loop_shapes),4),squeeze=False,layout='constrained')
        for j,shape in enumerate(loop_shapes):
            s=load(f'{shape}_2nm_loop'); rs=s['stages'][:61]
            for term in rs[0]['energy_J']:
                axes[0,j].plot([r['b_T'] for r in rs],[r['energy_J'][term]/s['geometry']['volume_m3'] for r in rs],label=term.split(':')[1])
            axes[0,j].set(title=LABELS[shape]+' / descending',xlabel='mu0 Hext,z (T)',ylabel='Energy density (J/m^3)')
            axes[0,j].legend(fontsize=8)
        fig.savefig(BASE/'figures/energy_components.png',dpi=180)
        plt.close(fig)
        fig,axes=plt.subplots(len(loop_shapes),4,figsize=(13,3.5*len(loop_shapes)),squeeze=False,layout='constrained')
        for row,shape in enumerate(loop_shapes):
            s=load(f'{shape}_2nm_loop'); ci=crossings(s)
            if len(ci)!=2:
                continue
            g,mask,_=geometry(shape,2)
            for col,idx in enumerate((ci[0]-1,ci[0],ci[1]-1,ci[1])):
                m=ovf(spin_path(s,idx))[0]
                im=axes[row,col].imshow(np.where(mask[0],m[0,:,:,2],np.nan),origin='lower',cmap='RdBu_r',vmin=-1,vmax=1,
                                        extent=[-g['lx_nm']/2,g['lx_nm']/2,-g['ly_nm']/2,g['ly_nm']/2])
                axes[row,col].set(title=f'{LABELS[shape]} / {s["stages"][idx]["b_T"]:+.3f} T',xlabel='x (nm)',ylabel='y (nm)')
        fig.colorbar(im,ax=axes,label='mz',shrink=0.8)
        fig.savefig(BASE/'figures/reversal_states.png',dpi=180)
        plt.close(fig)

    selected=[(shape,init) for shape in SHAPES for init in ('plus','domains') if load(f'{shape}_2nm_zero_{init}')]
    if len(selected)==6:
        fig,axes=plt.subplots(2,3,figsize=(12,7),layout='constrained')
        for shape,init in selected:
            j=SHAPES.index(shape); i=0 if init=='plus' else 1
            s=load(f'{shape}_2nm_zero_{init}')
            m=ovf(spin_path(s))[0]
            g,mask,_=geometry(shape,2)
            im=axes[i,j].imshow(np.where(mask[0],m[0,:,:,2],np.nan),origin='lower',vmin=-1,vmax=1,cmap='RdBu_r',
                               extent=[-g['lx_nm']/2,g['lx_nm']/2,-g['ly_nm']/2,g['ly_nm']/2])
            axes[i,j].set(title=f'{LABELS[shape]} / {init}\n<mz>={s["stages"][0]["mean_m"][2]:.5f}',xlabel='x (nm)',ylabel='y (nm)')
        fig.colorbar(im,ax=axes,label='mz',shrink=0.8)
        fig.savefig(BASE/'figures/zero_states.png',dpi=180)
        plt.close(fig)

    checks={'output_provenance_and_fields':audit_result['all_passed']}
    metrics=[]
    details=json.loads((BASE/'verification_details.json').read_text()) if (BASE/'verification_details.json').exists() else []
    refinement_progress=[]
    for p in sorted((BASE/'runs').glob('*_refine_*/summary.json')):
        match=re.fullmatch(r'(square|circle|rectangle)_(\d+)nm_refine_b([01])_(\d+)uT(_tight)?',p.parent.name)
        if match:
            s=json.loads(p.read_text(encoding='utf-8'))
            if len(crossings(s))==1:
                refinement_progress.append(dict(shape=match[1],cell_nm=int(match[2]),branch=int(match[3]),
                    step_mT=int(match[4])/1000,stop=s['config']['stop'],bracket_T=bracket(s),run_id=p.parent.name))
    refined_metrics=[]
    for shape in SHAPES:
        for cell in (2,1):
            by_branch={d['branch']:d for d in details if d['shape']==shape and d['cell_nm']==cell}
            if set(by_branch)=={0,1}:
                minus=sorted(by_branch[0]['bracket_T']); plus=sorted(by_branch[1]['bracket_T'])
                low=(plus[0]-minus[1])/2; high=(plus[1]-minus[0])/2
                refined_metrics.append(dict(shape=shape,cell_nm=cell,bc_minus_low_T=minus[0],
                    bc_minus_high_T=minus[1],bc_plus_low_T=plus[0],bc_plus_high_T=plus[1],
                    coercivity_estimate_T=(low+high)/2,coercivity_low_T=low,coercivity_high_T=high))
    csv_write('coercivity_refined.csv',refined_metrics)
    trajectories=[]
    for shape in SHAPES:
        p=BASE/'trajectories'/shape/'summary.json'
        if p.exists():
            trajectories.append(json.loads(p.read_text()))
    if trajectories:
        fig,axes=plt.subplots(len(trajectories),4,figsize=(13,3.5*len(trajectories)),squeeze=False,layout='constrained')
        for row,t in enumerate(trajectories):
            g,mask,_=geometry(t['shape'],2)
            for col,target in enumerate((0.8,0.2,-0.2,-0.8)):
                sample=min(t['samples'],key=lambda s:abs(s['mean_m'][2]-target))
                m=ovf(BASE/'trajectories'/t['shape']/sample['file'])[0]
                im=axes[row,col].imshow(np.where(mask[0],m[0,:,:,2],np.nan),origin='lower',cmap='RdBu_r',vmin=-1,vmax=1,
                    extent=[-g['lx_nm']/2,g['lx_nm']/2,-g['ly_nm']/2,g['ly_nm']/2])
                axes[row,col].set(title=f'{LABELS[t["shape"]]}\nstep {sample["iteration"]}, <mz>={sample["mean_m"][2]:+.2f}',xlabel='x (nm)',ylabel='y (nm)')
        fig.colorbar(im,ax=axes,label='mz',shrink=0.8)
        fig.savefig(BASE/'figures/reversal_trajectory.png',dpi=180)
        plt.close(fig)
    for t in trajectories:
        checks[f'{t["shape"]}_trajectory_replay']=t['passed']
    for shape in SHAPES:
        for axis in 'xyz':
            a,b=load(f'{shape}_2nm_static_{axis}'),load(f'{shape}_1nm_static_{axis}')
            if a and b:
                checks[f'{shape}_{axis}_grid_N']=abs(a['stages'][0]['N_field']-b['stages'][0]['N_field'])<=1e-3
        for init in ('plus','domains'):
            a,b=load(f'{shape}_2nm_zero_{init}'),load(f'{shape}_1nm_zero_{init}')
            if a and b:
                x,y=a['stages'][0],b['stages'][0]
                checks[f'{shape}_{init}_grid_mz']=abs(x['mean_m'][2]-y['mean_m'][2])<=0.01
                checks[f'{shape}_{init}_grid_energy']=abs(x['energy_density_J_m3']-y['energy_density_J_m3'])<=0.01*max(abs(y['energy_density_J_m3']),1)
        for cell in (2,1):
            s=load(f'{shape}_{cell}nm_loop')
            if not s:
                continue
            rs=s['stages']
            checks[f'{shape}_{cell}nm_loop_reversals']=len(crossings(s))==2
            checks[f'{shape}_{cell}nm_loop_saturated']=all(
                np.sign(rs[i]['b_T'])*rs[i]['mean_m'][2]>=0.999 for i in (0,len(rs)//2,len(rs)-1))
            rem=[r['mean_m'][2] for r in rs if abs(r['b_T'])<1e-9]
            bs=[bracket(s,i) for i in range(len(crossings(s)))]
            metrics.append(dict(shape=shape,cell_nm=cell,remanence=rem,coarse_brackets_T=bs))
        a,b=load(f'{shape}_2nm_loop'),load(f'{shape}_1nm_loop')
        if a and b:
            for j,(x,y) in enumerate(zip([r for r in a['stages'] if abs(r['b_T'])<1e-9],
                                          [r for r in b['stages'] if abs(r['b_T'])<1e-9])):
                checks[f'{shape}_Mr{j}_grid']=abs(x['mean_m'][2]-y['mean_m'][2])<=0.01
        for branch in (0,1):
            sub=[d for d in details if d['shape']==shape and d['branch']==branch]
            for d in sub:
                bc=float(np.mean(d['bracket_T']))
                checks[f'{shape}_{d["cell_nm"]}nm_b{branch}_field']=d['field_check_T']<=max(0.002,0.05*abs(bc))
                checks[f'{shape}_{d["cell_nm"]}nm_b{branch}_tolerance']=abs(bc-np.mean(d['tight_bracket_T']))<=max(0.002,0.05*abs(bc))
                if 'perturbations' in d:
                    sign=1 if branch==0 else -1
                    checks[f'{shape}_b{branch}_perturbation']=all(sign*p['mz'][0]>0 and sign*p['mz'][1]<0 for p in d['perturbations'])
            if len(sub)==2:
                bc0,bc1=[float(np.mean(d['bracket_T'])) for d in sub]
                checks[f'{shape}_b{branch}_grid_Hc']=abs(bc0-bc1)<=max(0.002,0.05*abs(bc1))
    pending=[]
    if len(static)!=18: pending.append('1/2 nm三轴固定态')
    if len([r for r in zero if r['cell_nm']==2])!=24: pending.append('主网格24个多初态')
    if len([r for r in zero if r['cell_nm']==1])<6: pending.append('1 nm代表零场态')
    for shape in SHAPES:
        s=load(f'{shape}_2nm_zero_plus_tight')
        a=load(f'{shape}_2nm_zero_plus')
        if s and a:
            checks[f'{shape}_zero_tolerance']=abs(s['stages'][0]['mean_m'][2]-a['stages'][0]['mean_m'][2])<=0.01
        else:
            pending.append(f'{shape}零场停止阈值复核')
    if len(metrics)!=6: pending.append('三形状两种网格完整磁滞')
    if len(details)!=12: pending.append('两种网格翻转区场步/阈值与扰动检验')
    if len(trajectories)!=3: pending.append('三形状代表翻转过程磁化快照')
    failed=[k for k,v in checks.items() if not v]
    result=dict(completed_runs=len(list((BASE/'runs').glob('*/summary.json'))),metrics=metrics,
                refined_coercivity=refined_metrics,
                completed_refinement_paths=refinement_progress,
                domain_energy_comparison=energy_comparison,
                reversal_trajectories=[{k:v for k,v in t.items() if k!='samples'} for t in trajectories],
                checks=checks,failed_checks=failed,pending=pending,verification=details,
                numerical_acceptance_complete=not pending and not failed)
    dump(BASE/'analysis/results.json',result)
    lines=['# 仿真结果与验证进展','',f'已分析算例目录：{result["completed_runs"]}（包括诊断和聚合路径目录，不能直接当作独立实验数量）。',
           '状态：'+('全部已列数值验收通过。' if result['numerical_acceptance_complete'] else '阶段性结果，最终数值验收尚未完成。'),'',
           '正式磁滞采用统一 ε=10⁻³ 横向扰动协议，仅在外场与上一态平均磁化反向的场点施加。原始无扰动曲线留作驻点诊断，不用于下面的矫顽场统计。详见 [实施记录](DECISIONS.md)。','',
           '## 固定均匀磁化的退磁因子','', '| 形状 | 网格/nm | Nx | Ny | Nz | 实际面积/nm² |','|---|---:|---:|---:|---:|---:|']
    for shape in SHAPES:
        for cell in (2,1):
            ss=[r for r in static if r['shape']==shape and r['cell_nm']==cell]
            if len(ss)==3:
                lines.append(f'| {shape} | {cell} | {ss[0]["N_field"]:.9f} | {ss[1]["N_field"]:.9f} | {ss[2]["N_field"]:.9f} | {ss[0]["area_nm2"]} |')
    lines+=['','## 多初态的能量竞争','',
            '| 形状 | 近单畴能量密度/J·m⁻³ | 双畴能量密度/J·m⁻³ | 双畴减近单畴/J·m⁻³ | 双畴平均绝对 mz |',
            '|---|---:|---:|---:|---:|']
    for r in energy_comparison:
        lines.append(f'| {r["shape"]} | {r["single_J_m3"]:.2f} | {r["domains_J_m3"]:.2f} | {r["delta_total_J_m3"]:.2f} | {r["domain_mean_abs_mz"]:.5f} |')
    if len(energy_comparison)==3 and all(r['delta_total_J_m3']>0 for r in energy_comparison):
        lines+=['', '在当前测试的零场初态中，三种形状的近单畴态均比双畴驻态能量低。分畴降低退磁能，但增加的交换能与各向异性能更大。双畴态的平均 mz 接近零，而平均绝对 mz 仍接近 1，说明净磁化抵消来自上下畴，并非整体面内磁化。该比较仅覆盖本次初态集合。']
    lines+=['','## 磁滞指标','', '| 形状 | 网格/nm | Mr+/Ms | Mr−/Ms | 两支粗场步翻转区间/T |','|---|---:|---:|---:|---|']
    for r in metrics:
        mr=r['remanence']
        lines.append(f'| {r["shape"]} | {r["cell_nm"]} | {mr[0]:.9f} | {mr[1]:.9f} | {r["coarse_brackets_T"]} |')
    coarse_metrics=[r for r in metrics if r['cell_nm']==2]
    if len(coarse_metrics)==3 and all(all(abs(abs(m)-1)<0.001 for m in r['remanence']) for r in coarse_metrics):
        lines+=['', '三种形状在当前零温、无缺陷模型及相同场历史下，撤场后的面外剩磁均接近饱和。末尾小数的微小差别不用于形状优劣排序；翻转场比较使用下面的区间与数值复核。']
    if refinement_progress and not refined_metrics:
        lines+=['','### 已完成的局部场步复算（全套验证进行中）','',
                '| 形状 | 网格/nm | 支路 | 场步/mT | 停止阈值/°·ns⁻¹ | 翻转夹逼/T |',
                '|---|---:|---|---:|---:|---|']
        for r in refinement_progress:
            lines.append(f'| {r["shape"]} | {r["cell_nm"]} | {"下降" if r["branch"]==0 else "返回"} | {r["step_mT"]:g} | {r["stop"]:g} | {r["bracket_T"]} |')
        lines+=['', '这些是已完成路径的直接过零夹逼；停止阈值、扰动幅度、另一支路与网格复核尚未齐备时，不作为最终矫顽场结论。']
    if refined_metrics:
        lines+=['','### 加密后的矫顽场','',
                '| 形状 | 网格/nm | 负支翻转夹逼/T | 正支翻转夹逼/T | 矫顽场估计/T | 矫顽场夹逼/T |',
                '|---|---:|---|---|---:|---|']
        for r in refined_metrics:
            lines.append(f'| {r["shape"]} | {r["cell_nm"]} | [{r["bc_minus_low_T"]:.4f}, {r["bc_minus_high_T"]:.4f}] | [{r["bc_plus_low_T"]:.4f}, {r["bc_plus_high_T"]:.4f}] | {r["coercivity_estimate_T"]:.4f} | [{r["coercivity_low_T"]:.4f}, {r["coercivity_high_T"]:.4f}] |')
        lines+=['', '矫顽场幅值定义为 (bc+−bc−)/2，采用两支翻转区间传播得到夹逼范围。它表示离散场步下的区间，不是重复抽样的统计置信区间。最终形状排序还需通过网格与协议检查。']
    if trajectories:
        lines+=['','## 代表翻转过程','',
                '对每种形状的下降支首个翻转场点重放，保持原始初态、外场和求解参数，仅增加每 50 个接受步保存一次磁化的输出。图中标注求解器迭代步，不作为物理翻转时间。',
                '', '| 形状 | 外场/T | 保存快照数 | 最小平均磁化矢量模长 | 与原终态最大磁化分量差 |',
                '|---|---:|---:|---:|---:|']
        for t in trajectories:
            lines.append(f'| {t["shape"]} | {t["b_T"]:+.3f} | {len(t["samples"])} | {t["minimum_mean_norm"]:.5f} | {t["final_spin_max_difference"]:.3g} |')
        lines+=['', '平均磁化矢量模长明显小于 1 表明中间过程存在空间不均匀，不能仅凭翻转前后均为近单畴态就认定为一致旋转。具体空间变化见下方快照；这些是给定外场与初始化协议下的零温数值弛豫过程。']
        lines+=['快照显示底层网格的 mz，平均量在整个磁性体积内计算。']
        if len(trajectories)==3 and all(abs(t['b_T']+0.2)<1e-9 for t in trajectories):
            lines+=['在本次 −0.20 T 重放快照中，方形和圆形先在中心形成反向区域，再向外扩展；长方形形成中央反向带并向两端推进。该空间过程的描述限定于这组参数、网格和场点，不把关闭进动的迭代快慢解释为物理翻转速度。']
    lines+=['','## 验收记录','',f'未完成项目：{pending or "无"}。',f'未通过检查：{failed or "当前已执行检查中无"}。',
            '细化场区间、扰动结果和每项布尔检查见 [results.json](analysis/results.json)。',
            '每个算例的 config.json 保存初态、前驱状态校验和、外场路径和输入校验和；summary.json 保存每个场点的磁性体积平均、能量和收敛记录。',
            '', '## 图表与解释范围','']
    for name,label in [('demag_comparison','退磁场'),('zero_states','零场代表状态'),('domain_energy_competition','零场能量竞争'),('hysteresis_comparison','磁滞'),
                       ('energy_components','分项能量'),('reversal_states','翻转前后磁化'),('reversal_trajectory','翻转过程磁化快照')]:
        if (BASE/f'figures/{name}.png').exists():
            lines.append(f'![{label}](figures/{name}.png)')
    lines+=['', '所有参数均为教学模型，零温、无缺陷、关闭进动。多初态结果是所测试初态的驻态，不是基态证明；磁滞中的零场点才用于报告剩磁。关闭进动的积分时间不代表物理翻转时间。微磁学结果不直接证明 QAH 或量子化霍尔电导。']
    (BASE/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    from update_tracker import update
    update()
    print('REPORT',json.dumps(dict(pending=pending,failed_checks=failed),ensure_ascii=False),flush=True)
    # A requested worker refresh occurs only at the completed-primary boundary.
    refresh=BASE/'refresh_worker_after_primary.json'
    if refresh.exists() and json.loads((BASE/'status.json').read_text())['phase']=='M3_primary_complete':
        import os
        request=json.loads(refresh.read_text())
        if request['old_pid']==os.getpid():
            dump(BASE/'status.json',dict(phase='RESTARTING_AFTER_PRIMARY',reason=request['reason']))
            refresh.rename(BASE/'refresh_worker_after_primary.completed.json')
            raise SystemExit(75)


if __name__=='__main__':
    build_report()
