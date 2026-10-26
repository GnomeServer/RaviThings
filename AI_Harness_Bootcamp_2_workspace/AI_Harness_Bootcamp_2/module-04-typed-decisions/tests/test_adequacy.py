#!/usr/bin/env python3
"""Prove the Module 4 oracle can fail each live criterion."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from mutations import MUTATIONS

MODULE = Path(__file__).resolve().parents[1]
CID_RE = re.compile(r"^\s*(?:PASS|FAIL)\s+(M4-[A-Z0-9-]+):", re.M)
FAIL_RE = re.compile(r"^\s*FAIL\s+(M4-[A-Z0-9-]+):", re.M)


REPO = MODULE.parents[1]


def run_oracle(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tests/test_module_04.py"],
        cwd=root,
        capture_output=True,
        text=True,
    )


def mirror(tmp: Path) -> Path:
    """Copy the module into tmp/AI_Harness_Bootcamp_2/<name> and link the shared helpers, so repository-relative paths resolve."""
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
    mutation_cids = {m.cid for m in MUTATIONS}
    unproven = live_ids - mutation_cids
    survivors: list[str] = []
    unapplied: list[str] = []

    for mutation in MUTATIONS:
        with tempfile.TemporaryDirectory() as tmp:
            copy = mirror(Path(tmp))
            try:
                mutation.apply(copy)
            except Exception as exc:
                unapplied.append(f"{mutation.cid}: {exc!r}")
                print(f"  SKIP {mutation.cid} {mutation.what} — {exc!r}")
                continue
            after = run_oracle(copy)
            killed = mutation.cid in set(FAIL_RE.findall(after.stdout + after.stderr))
            print(f"  {'killed' if killed else 'SURVIVED'} {mutation.cid} {mutation.what}")
            if not killed:
                survivors.append(f"{mutation.cid} survived: {mutation.what}")

    ok = not survivors and not unapplied and not unproven
    if survivors:
        print(f"SURVIVORS: {len(survivors)}")
        for item in survivors:
            print("   ", item)
    if unapplied:
        print(f"UNAPPLIED: {len(unapplied)}")
        for item in unapplied:
            print("   ", item)
    if unproven:
        print(f"UNPROVEN: {sorted(unproven)}")
    if ok:
        print(f"PASS: {len(MUTATIONS)} mutations, 0 survivors")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
