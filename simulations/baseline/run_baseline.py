"""Run the OOMMF baseline locally; never overwrite an existing result directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from datetime import datetime

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
TCL = Path('C:/Program Files/Git/ucrt64/bin/tclsh.exe')
OOMMF = ROOT / '.tools/oommf20b0/oommf/oommf.tcl'
MIF = BASE / 'square.mif'
CASES = {
    **{f'{nm}nm_static_{axis}': (nm, 'static', axis, 0.01)
       for nm in (2, 1) for axis in 'xyz'},
    '2nm_relax': (2, 'relax', 'z', 0.01),
    '1nm_relax': (1, 'relax', 'z', 0.01),
    '2nm_tight': (2, 'relax', 'z', 0.005),
}


def completed(out):
    tables = list(out.glob('*.odt'))
    return (len(tables) == 1 and '# Table End' in tables[0].read_text()
            and len(list(out.glob('*.omf'))) == 1
            and len(list(out.glob('*.ohf'))) == 2)


def run_case(name, threads, output_root):
    nm, mode, axis, stop = CASES[name]
    out = output_root / f'oommf_{name}'
    if out.exists():
        if completed(out):
            snapshot = out / 'input.mif'
            if not snapshot.exists() or snapshot.read_bytes() != MIF.read_bytes():
                raise RuntimeError(f'{out}: input snapshot is missing or differs; inspect before reuse.')
            print(f'{name}: existing completed output retained', flush=True)
            return
        raise RuntimeError(f'Incomplete output at {out}; inspect it before rerunning.')
    out.mkdir(parents=True)
    shutil.copy2(MIF, out / 'input.mif')
    stem = f'static_{axis}' if mode == 'static' else 'relax'
    params = f'cell {nm}e-9 mode {mode} axis {axis} stop {stop} basename {stem}'
    command = [str(TCL), str(OOMMF), 'boxsi', '+fg', '-tk', '0',
               '-threads', str(threads), '-exitondone', '1', '-kill', 'all',
               '-outdir', str(out), '-parameters', params, str(MIF)]
    env = os.environ.copy()
    env['PATH'] = str(ROOT / '.tools/oommf-runtime') + os.pathsep + str(TCL.parent) + os.pathsep + env['PATH']
    manifest = {'started': datetime.now().astimezone().isoformat(),
                'command': command, 'cell_nm': nm, 'mode': mode,
                'axis': axis, 'stopping_dm_dt_deg_ns': stop,
                'mif_sha256': hashlib.sha256(MIF.read_bytes()).hexdigest()}
    print(f'{name}: running on {threads} CPU threads', flush=True)
    started = time.monotonic()
    with (out / 'console.log').open('wb') as log:
        proc = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                              stderr=subprocess.STDOUT, timeout=1800,
                              creationflags=subprocess.CREATE_NO_WINDOW)
    manifest.update(returncode=proc.returncode, wall_seconds=time.monotonic()-started)
    (out / 'run.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    if proc.returncode or not completed(out):
        raise RuntimeError(f'{name} did not finish; inspect {out / "console.log"}')
    print(f'{name}: finished in {manifest["wall_seconds"]:.1f} s; numerical validation follows', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=CASES, action='append')
    parser.add_argument('--threads', type=int, default=8)
    parser.add_argument('--output-root', type=Path, default=BASE,
                        help='Use a new directory to reproduce results without overwriting them.')
    args = parser.parse_args()
    if not TCL.is_file() or not OOMMF.is_file():
        raise SystemExit('Missing OOMMF or Tcl; see README.md for the local environment.')
    for case in args.case or CASES:
        run_case(case, args.threads, args.output_root.resolve())
