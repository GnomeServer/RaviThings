#!/usr/bin/env python3
"""Release the visible practice change only after the baseline freeze exists."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "facilitator/fixtures/SEALED_CHANGE.md"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workdir", type=Path)
    args = parser.parse_args()
    work = args.workdir.resolve()
    freeze = work / "baseline-freeze.json"
    target = work / "REVEALED_CHANGE.md"
    release = work / "change-release.json"
    if not freeze.exists():
        print("HOLD: freeze baseline before revealing the change")
        return 1
    if target.exists() or release.exists():
        print("HOLD: practice change was already released")
        return 1
    shutil.copyfile(SOURCE, target)
    release.write_text(json.dumps({
        "case_id": "COLD-LANTERN-PRACTICE",
        "released_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_freeze": str(freeze),
        "change_file": target.name,
        "change_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "practice_only": True,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: practice change copied to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
