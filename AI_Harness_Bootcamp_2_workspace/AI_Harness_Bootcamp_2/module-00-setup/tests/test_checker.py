#!/usr/bin/env python3
"""Adequacy test for the practice checker. Reference v2 section 6 Class B.

Exit code alone is not evidence: a checker that crashes also exits non-zero. Every
failing fixture must be rejected BY THE CHECK NAMED IN THE MANIFEST, and every passing
fixture must clear every check. A check with no killing fixture fails B6.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
CASE = MODULE / "shared/case"
FIX = MODULE / "tests/fixtures"
sys.path.insert(0, str(CASE))
import check_artifact  # noqa: E402


def expected() -> dict[str, str]:
    rows = re.findall(r"^\|\s*`fail/([^`]+)`\s*\|\s*([^|]+?)\s*\|$",
                      (FIX / "MANIFEST.md").read_text(encoding="utf-8"), re.M)
    return dict(rows)


def main() -> int:
    failures: list[str] = []
    exercised: set[str] = set()
    all_checks: set[str] = set()

    for path in sorted((FIX / "pass").glob("*.md")):
        checks = check_artifact.run(path.read_text(encoding="utf-8"))
        all_checks |= {name for name, _, _ in checks}
        bad = [f"{name} ({why})" for name, ok, why in checks if not ok]
        if bad:
            failures.append(f"pass/{path.name} should clear every check, but failed: {bad}")

    for name, negative, positive in (
        ("no vehicle", "No vehicle is assigned", "a vehicle is assigned"),
        ("no permit", "No permit is approved", "the permit is approved"),
        ("no receipt", "No receipt is confirmed", "the receipt is confirmed"),
    ):
        for text, expected_pass in (
            (negative + ".", True),
            (negative + ", but " + positive + ".", False),
            (negative + ". However, " + positive + ".", False),
        ):
            actual = next(ok for label, ok, _ in check_artifact.run(text) if label == name)
            if actual != expected_pass:
                failures.append(f"{name}: incorrect polarity for {text!r}")

    want = expected()
    for path in sorted((FIX / "fail").glob("*.md")):
        checks = check_artifact.run(path.read_text(encoding="utf-8"))
        all_checks |= {name for name, _, _ in checks}
        rejected = [name for name, ok, _ in checks if not ok]
        target = want.get(path.name)
        if target is None:
            failures.append(f"fail/{path.name} has no manifest entry")
        elif not rejected:
            failures.append(f"fail/{path.name} PASSED; it must be rejected on '{target}'")
        elif not any(target.lower() in r.lower() for r in rejected):
            failures.append(f"fail/{path.name} rejected on {rejected}, not on '{target}'")
        else:
            exercised |= {r for r in rejected if target.lower() in r.lower()}

    unexercised = sorted(all_checks - exercised)
    if unexercised:
        failures.append(f"B6: checks with no killing fixture: {unexercised}")

    for f in failures:
        print("FAIL:", f)
    if failures:
        print(f"\nCHECKER ADEQUACY HOLD — {len(failures)} problem(s)")
        return 1
    print(f"PASS: {len(list((FIX / 'pass').glob('*.md')))} faithful drafts clear every check")
    print(f"PASS: {len(want)} corrupted drafts are each rejected on the named check")
    print(f"PASS: all {len(all_checks)} checks have at least one killing fixture")
    print("PASS: nine negative-fact and contradictory-assertion boundaries")
    print("\nCHECKER ADEQUACY PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
