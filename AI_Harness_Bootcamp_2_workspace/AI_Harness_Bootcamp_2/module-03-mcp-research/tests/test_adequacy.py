#!/usr/bin/env python3
"""Prove the Module 3 oracle can fail each live criterion.

The module is copied into a throwaway tree that mirrors the repository layout, so the verifier
finds the shared launcher the way it does in a real checkout. Each mutation is applied to the
copy and the oracle must report its named criterion as FAIL.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from mutations import MUTATIONS, REQUIRED_COVERAGE

MODULE = Path(__file__).resolve().parents[1]
REPO = MODULE.parents[1]
CID_RE = re.compile(r"^\s*(?:PASS|FAIL)\s+(M3-[A-Z0-9-]+):", re.M)
FAIL_RE = re.compile(r"^\s*FAIL\s+(M3-[A-Z0-9-]+):", re.M)


def run_oracle(module: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "tests/test_module_03.py"], cwd=module, capture_output=True, text=True)


def mirror(tmp: Path) -> Path:
    """Copy the module into tmp/AI_Harness_Bootcamp_2/<name> and link the shared helpers."""
    copy = tmp / "AI_Harness_Bootcamp_2" / MODULE.name
    shutil.copytree(MODULE, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (tmp / "shared").symlink_to(REPO / "shared", target_is_directory=True)
    return copy


def main() -> int:
    live = run_oracle(MODULE)
    output = live.stdout + live.stderr
    print(output, end="" if output.endswith("\n") else "\n")
    if live.returncode != 0:
        print("LIVE ORACLE FAIL — adequacy does not run against a red module")
        return 1
    live_ids = set(CID_RE.findall(output))
    mutation_ids = {m.cid for m in MUTATIONS}
    coverage_gap = live_ids != REQUIRED_COVERAGE or mutation_ids != REQUIRED_COVERAGE
    if coverage_gap:
        print(f"COVERAGE live={sorted(live_ids)} mutations={sorted(mutation_ids)} required={sorted(REQUIRED_COVERAGE)}")
    if "--quick" in sys.argv:
        if coverage_gap:
            return 1
        print(f"QUICK PASS — live oracle green; {len(live_ids)} criterion IDs")
        return 0
    survivors: list[str] = []
    unapplied: list[str] = []
    for mutation in MUTATIONS:
        with tempfile.TemporaryDirectory() as temp:
            copy = mirror(Path(temp))
            try:
                mutation.apply(copy)
            except Exception as error:
                unapplied.append(f"{mutation.cid}: {error!r}")
                print(f"  SKIP {mutation.cid} {mutation.what} — {error!r}")
                continue
            after = run_oracle(copy)
            if mutation.cid in set(FAIL_RE.findall(after.stdout + after.stderr)):
                print(f"  killed {mutation.cid} {mutation.what}")
            else:
                survivors.append(f"{mutation.cid} survived: {mutation.what}")
                print(f"  SURVIVED {mutation.cid} {mutation.what}")
    ok = not survivors and not unapplied and not coverage_gap
    for title, items in (("SURVIVORS", survivors), ("UNAPPLIED", unapplied)):
        if items:
            print(f"{title}: {len(items)}")
            for item in items:
                print("   ", item)
    if ok:
        print(f"PASS: {len(MUTATIONS)} mutations, 0 survivors")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
