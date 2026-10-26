#!/usr/bin/env python3
"""Prove six behavioral criterion groups (M2-*) against applied, isolated mutations. Regressions emit non-M2- labels; baseline must match exactly the six M2- without filtering."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from mutations import MUTATIONS

MODULE = Path(__file__).resolve().parents[1]
CID_RE = re.compile(r'^\s*(?:PASS|FAIL)\s+(M2-[A-Z0-9-]+):', re.M)
FAIL_RE = re.compile(r'^\s*FAIL\s+(M2-[A-Z0-9-]+):', re.M)


def run_oracle(module):
    return subprocess.run([sys.executable, 'tests/test_module_02.py'], cwd=module, capture_output=True, text=True)


def main():
    live = run_oracle(MODULE)
    output = live.stdout + live.stderr
    print(output, end='' if output.endswith('\n') else '\n')
    if live.returncode:
        print('LIVE ORACLE FAIL — adequacy does not run against a red module')
        return 1
    live_ids = set(CID_RE.findall(output))
    expected = {m.cid for m in MUTATIONS}
    if live_ids != expected:
        print(f'UNPROVEN: live={sorted(live_ids)} mutations={sorted(expected)}')
        return 1
    if '--quick' in sys.argv:
        print(f'QUICK PASS — live oracle green; {len(live_ids)} criterion IDs')
        return 0
    survivors, unapplied = [], []
    with tempfile.TemporaryDirectory(prefix='module02-adequacy-') as directory:
        base = Path(directory).resolve()
        pristine = base / 'pristine'
        relative = Path('AI_Harness_Bootcamp_2') / MODULE.name
        shutil.copytree(MODULE, pristine / relative, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (pristine / 'shared').mkdir()
        for name in ['run_omp.py', 'course_guard.mjs']:
            shutil.copyfile(MODULE.parents[1] / 'shared' / name, pristine / 'shared' / name)
        baseline = run_oracle(pristine / relative)
        if baseline.returncode or set(CID_RE.findall(baseline.stdout + baseline.stderr)) != live_ids:
            print('PRISTINE CLONE FAIL — miniature repository must pass the exact live criteria')
            print(baseline.stdout + baseline.stderr)
            return 1
        for index, mutation in enumerate(MUTATIONS):
            clone = base / f'mutant-{index}'
            shutil.copytree(pristine, clone, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            try:
                mutation.apply(clone / relative)
            except Exception as error:
                unapplied.append(mutation.cid)
                print(f'UNAPPLIED {mutation.cid}: {error!r}')
                continue
            result = run_oracle(clone / relative)
            combined = result.stdout + result.stderr
            killed = result.returncode == 1 and mutation.cid in set(FAIL_RE.findall(combined)) and 'ERROR M2-' not in combined
            if killed:
                print(f'  killed {mutation.cid} {mutation.what}')
            else:
                survivors.append(mutation.cid)
                print(f'  SURVIVED {mutation.cid} {mutation.what}\n{combined}')
    if survivors or unapplied:
        print(f'SURVIVORS: {len(survivors)}; UNAPPLIED: {len(unapplied)}')
        return 1
    print(f'PASS: {len(MUTATIONS)} mutations, 0 survivors')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
