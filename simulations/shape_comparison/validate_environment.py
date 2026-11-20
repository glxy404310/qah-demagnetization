"""Recheck historical data and run two fresh CPU solver witnesses."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
from runtime import ROOT, TCL, OOMMF, run

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'simulations/baseline'))
from analyze import ovf, table


def validate():
    dest = BASE / 'validation/historical'
    dest.mkdir(parents=True, exist_ok=True)
    for src in (ROOT / 'simulations/baseline').glob('oommf_*'):
        if src.is_dir() and not (dest / src.name).exists():
            shutil.copytree(src, dest / src.name)
    with (dest / 'validation.log').open('w', encoding='utf-8') as log:
        subprocess.run([sys.executable, str(ROOT / 'simulations/baseline/analyze.py'),
                        '--results-root', str(dest)], stdout=log, stderr=subprocess.STDOUT, check=True)
    summary = json.loads((dest / 'summary.json').read_text(encoding='utf-8'))
    assert summary['all_passed'] and len(summary['checks']) == 50
    records = []
    for mode in ('static', 'relax'):
        out = BASE / 'validation' / f'pilot_{mode}'
        out.mkdir(parents=True, exist_ok=True)
        mif = out / 'input.mif'
        shutil.copy2(ROOT / 'simulations/baseline/square.mif', mif)
        if not (out / 'run.json').exists():
            result = run([TCL, OOMMF, 'boxsi', '+fg', '-tk', '0', '-threads', '8',
                          '-exitondone', '1', '-kill', 'all', '-outdir', out,
                          '-parameters', f'cell 2e-9 mode {mode} axis z stop 0.01 basename pilot', mif],
                         out / 'console.log', 1800)
            (out / 'run.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        result = json.loads((out / 'run.json').read_text())
        assert result['returncode'] == 0, (out, result)
        d = table(next(out.glob('*.odt')))
        m, _ = ovf(next(out.glob('*.omf')))
        hd, _ = ovf(next(out.glob('*Demag*.ohf')))
        rate = float(d['Oxs_RungeKuttaEvolve:evolve:Max dm/dt'][-1])
        if mode == 'static':
            assert int(d['Oxs_TimeDriver::Iteration'][-1]) == 0
            assert abs(-hd[..., 2].mean()/3e5 - 0.9408621743243292) < 1e-4
        else:
            assert rate <= 0.01 and abs(m[..., 2].mean()-0.9999998468174442) < 1e-6
        records.append(dict(mode=mode, wall_seconds=result['wall_seconds'],
                            mean_mz=float(m[..., 2].mean()), dm_dt=rate))
    rng = np.random.default_rng(11)
    x = rng.normal(size=(16, 16))
    assert np.allclose(x @ x.T, (x @ x.T).T)
    report = dict(historical_checks=50, all_passed=True, pilots=records,
                  numpy_witness=float(np.trace(x @ x.T)), python=sys.version,
                  restricted_token=True)
    (BASE / 'validation/environment_witness.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('WITNESS OOMMF CPU: historical=50/50, pilots=2/2', flush=True)
    print(json.dumps(records), flush=True)


if __name__ == '__main__':
    validate()
