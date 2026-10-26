#!/usr/bin/env python3
"""Module 0 acceptance suite. Reference v2 section 6.

Two things run here, and the second is the one that matters:

  1. The oracle against the real module.
  2. The oracle against a mutated copy of the module, once per mutation, asserting that
     the named criterion actually FAILS. A criterion no mutant kills is decoration --
     the v1 suite reported 171 PASS / 0 FAIL on a module containing three of its own
     absolute failures, because nothing ever proved its checks could fail.

Usage:
    python3 tests/test_module_00.py           run everything
    python3 tests/test_module_00.py --quick   skip the mutation corpus
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import oracle  # noqa: E402
from mutations import MUTATIONS  # noqa: E402

MODULE = Path(__file__).resolve().parents[1]


def sandbox(dest: Path) -> Path:
    """Copy of the module tree for mutation (repo/ subdir keeps verifier parents[4] as dest); no git init."""
    work = dest / "repo"
    mod = work / MODULE.name
    shutil.copytree(MODULE, mod, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # layout for B8
    reform = MODULE.parents[1]
    run_omp_src = reform / "shared" / "run_omp.py"
    if not run_omp_src.exists():
        raise RuntimeError(f"missing {run_omp_src} required for B8 verifier layout")
    (dest / "shared").mkdir(exist_ok=True)
    shutil.copy(run_omp_src, dest / "shared" / "run_omp.py")
    return mod
def failing(results: list[oracle.Result]) -> set[str]:
    return {r.cid for r in results if r.state == oracle.FAIL}


def main() -> int:
    # Exercise the public readiness CLI once, outside the legacy prose-mutation
    # loop. These synthetic disk checks do not establish desktop GUI readiness.
    readiness = subprocess.run(
        [sys.executable, str(MODULE / "tests/test_obsidian_readiness.py")],
        cwd=MODULE, capture_output=True, text=True, timeout=180,
    )
    print(readiness.stdout, end="")
    print(readiness.stderr, end="", file=sys.stderr)
    readiness_ok = readiness.returncode == 0
    print("=" * 78)
    print("1. The module against the oracle")
    print("=" * 78)
    live = oracle.run(MODULE)
    for r in live:
        print(" ", r)
    live_fail = failing(live)
    print(f"\n  {len(live) - len(live_fail)} PASS / {len(live_fail)} FAIL")

    if "--quick" in sys.argv:
        return 0 if not live_fail and readiness_ok else 1

    print()
    print("=" * 78)
    print("2. The oracle against a broken module (each mutation must be caught)")
    print("=" * 78)

    covered = {r.cid for r in live}
    unproven = covered - {m.cid for m in MUTATIONS}
    survivors: list[str] = []
    unapplied: list[str] = []

    for m in MUTATIONS:
        with tempfile.TemporaryDirectory() as tmp:
            mod = sandbox(Path(tmp))
            try:
                m.apply(mod)
            except AssertionError as exc:
                unapplied.append(f"{m.cid}: {exc}")
                print(f"  SKIP {m.cid:<7} {m.what} — anchor gone")
                continue
            except Exception as exc:  # a mutation that cannot run proves nothing
                unapplied.append(f"{m.cid}: {exc!r}")
                print(f"  SKIP {m.cid:<7} {m.what} — {exc!r}")
                continue

            after = failing(oracle.run(mod))
            if m.cid in after:
                print(f"  killed {m.cid:<7} {m.what}")
            else:
                survivors.append(f"{m.cid} survived: {m.what}")
                print(f"  SURVIVED {m.cid:<5} {m.what}")

    print()
    print("=" * 78)
    ok = True
    if survivors:
        ok = False
        print(f"C6 FAIL — {len(survivors)} mutation(s) not caught:")
        for s in survivors:
            print("   ", s)
    if unapplied:
        ok = False
        print(f"C6 FAIL — {len(unapplied)} mutation(s) could not be applied:")
        for s in unapplied:
            print("   ", s)
    if unproven:
        ok = False
        print(f"C6 FAIL — criteria with no mutation proving they can fail: {sorted(unproven)}")
    if ok:
        print(f"C6 PASS — all {len(MUTATIONS)} mutations caught; every criterion is proven to fail")

    print()
    if not readiness_ok:
        print("MODULE HOLD — Obsidian readiness CLI behavior failed")
    elif live_fail:
        print(f"MODULE HOLD — {len(live_fail)} criteria failing: {sorted(live_fail)}")
    elif ok:
        print("MODULE PASS — every criterion passes, and every criterion is proven able to fail")
    return 0 if (not live_fail and ok and readiness_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
