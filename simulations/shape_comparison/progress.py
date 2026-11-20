"""Compact progress snapshot from persisted outputs (does not launch jobs)."""
from datetime import datetime
from zoneinfo import ZoneInfo
from simulate import BASE, SHAPES, INITIALS, json, dump


def snapshot():
    status=json.loads((BASE/'status.json').read_text(encoding='utf-8'))
    complete=lambda name:(BASE/'runs'/name/'summary.json').exists()
    counts={
        'static_2nm':sum(complete(f'{s}_2nm_static_{a}') for s in SHAPES for a in 'xyz'),
        'zero_2nm':sum(complete(f'{s}_2nm_zero_{i}') for s in SHAPES for i in INITIALS),
        'loops_2nm':sum(complete(f'{s}_2nm_loop_seeded') for s in SHAPES),
        'static_1nm':sum(complete(f'{s}_1nm_static_{a}') for s in SHAPES for a in 'xyz'),
        'zero_1nm':sum(complete(f'{s}_1nm_zero_{i}') for s in SHAPES for i in ('plus','domains')),
        'loops_1nm':sum(complete(f'{s}_1nm_loop_seeded') for s in SHAPES)}
    current=[]
    for path in sorted((BASE/'runs').glob('*/progress.json')):
        if not (path.parent/'summary.json').exists():
            current.append(dict(run_id=path.parent.name,**json.loads(path.read_text())))
    details=BASE/'verification_details.json'
    result=dict(time=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),status=status,
                completed=counts,current_paths=current,
                completed_verification_branches=len(json.loads(details.read_text())) if details.exists() else 0)
    dump(BASE/'live_progress.json',result)
    return result


if __name__=='__main__':
    print(json.dumps(snapshot(),ensure_ascii=False,indent=2))
