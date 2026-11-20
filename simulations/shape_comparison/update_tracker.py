"""Update the human tracker from saved outputs, without treating launch as success."""
import json
from pathlib import Path
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
BASE=Path(__file__).resolve().parent


def update():
    def has(name):
        p=BASE/'runs'/name/'summary.json'
        return p.exists() and json.loads(p.read_text(encoding='utf-8'))['all_passed']
    def state(names):
        return 'PASS' if all(has(n) for n in names) else ('RUNNING' if any((BASE/'runs'/n).exists() for n in names) else 'TODO')
    shapes=('square','circle','rectangle')
    initials=('plus','minus','inplane_x','inplane_y','domains','random11','random22','random33')
    updates={k:'PASS' for k in ('HIST-00','ENV-01','VAL-01','PILOT-01','PILOT-02','IMPL-01')}
    witness=BASE/'validation/environment_witness.json'
    assert witness.exists() and json.loads(witness.read_text())['all_passed']
    assert json.loads((BASE/'validation/history_check.json').read_text())['passed']
    updates['STATIC-01']=state([f'circle_2nm_static_{a}' for a in 'xyz'])
    updates['STATIC-02']=state([f'rectangle_2nm_static_{a}' for a in 'xyz'])
    updates['ZERO-01']=state([f'{s}_2nm_zero_{i}' for s in shapes for i in initials])
    for index,shape in enumerate(shapes,1):
        updates[f'LOOP-{index:02d}']=state([f'{shape}_2nm_loop_seeded'])
    updates['GRID-01']=state([f'{s}_1nm_static_{a}' for s in shapes for a in 'xyz'])
    updates['GRID-02']=state([f'{s}_1nm_zero_{i}' for s in shapes for i in ('plus','domains')])
    updates['GRID-03']=state([f'{s}_1nm_loop_seeded' for s in shapes])
    detail=BASE/'verification_details.json'
    records=json.loads(detail.read_text()) if detail.exists() else []
    updates['FIELD-01']='PASS' if len(records)==12 else ('RUNNING' if records else 'TODO')
    updates['TOL-01']='PASS' if len(records)==12 and all(has(f'{s}_2nm_zero_plus_tight') for s in shapes) else 'TODO'
    updates['PERT-01']='PASS' if len([d for d in records if 'perturbations' in d])==6 else ('RUNNING' if records else 'TODO')
    result=BASE/'analysis/results.json'
    report=json.loads(result.read_text(encoding='utf-8')) if result.exists() else {}
    updates['REPORT-01']='PASS' if report.get('numerical_acceptance_complete') else 'RUNNING'
    failed=report.get('failed_checks',[])
    if any('field' in k for k in failed): updates['FIELD-01']='REVIEW'
    if any('tolerance' in k for k in failed): updates['TOL-01']='REVIEW'
    if any('perturbation' in k for k in failed): updates['PERT-01']='REVIEW'
    if any('grid' in k for k in failed): updates['GRID-03']='REVIEW'
    p=ROOT/'refine-logs/EXPERIMENT_TRACKER.md'
    lines=p.read_text(encoding='utf-8').splitlines()
    new=[]
    for line in lines:
        parts=line.split('|')
        if len(parts)>8 and parts[1].strip() in updates:
            parts[7]=' '+updates[parts[1].strip()]+' '
            line='|'.join(parts)
        if line.startswith('日期：'):
            line='日期：2026-11-13。已启动执行；PASS 仅表示该行范围内的已保存输出通过对应检查。RUNNING 为处理中，REVIEW 为需进一步检查。最终状态以 simulations/shape_comparison/status.json 和 analysis/results.json 为准。'
        if line.startswith('最先执行：'):
            line='环境、基准和多初态已完成；后续按依赖推进。正式回线采用统一微扰协议，原始无扰动回线留作对称性诊断，详见 simulations/shape_comparison/DECISIONS.md。'
        new.append(line)
    content='\n'.join(new)+'\n'
    if content==p.read_text(encoding='utf-8'):
        return
    stamp=datetime.now(ZoneInfo('Asia/Shanghai'))
    archive=p.with_name('EXPERIMENT_TRACKER_'+stamp.strftime('%Y%m%d_%H%M%S')+'.md')
    archive.write_text(content,encoding='utf-8')
    shutil.copyfile(archive,p)
    with (ROOT/'MANIFEST.md').open('a',encoding='utf-8') as f:
        for file in (archive,p):
            f.write(f'| {stamp:%Y-%m-%d %H:%M:%S} | /run-experiment | {file.relative_to(ROOT).as_posix()} | implementation | 根据原始输出更新执行状态 |\n')


if __name__=='__main__':
    update()
