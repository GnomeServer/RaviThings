#!/usr/bin/env python3
"""Freeze the baseline ledger, prediction, and verdict before the practice change."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = (
    "source-register.csv",
    "thread-ledger.csv",
    "challenge-matrix.md",
    "corrected-brief.md",
    "baseline-verdict.md",
    "change-prediction.md",
    "producer-rebuttal.md",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workdir", type=Path)
    args = parser.parse_args()
    work = args.workdir.resolve()
    marker = work / "baseline-freeze.json"
    if marker.exists():
        print(f"HOLD: baseline already frozen: {marker}")
        return 1
    records = []
    for name in REQUIRED:
        path = work / name
        if not path.exists() or path.stat().st_size == 0:
            print(f"HOLD: missing or empty {name}")
            return 1
        records.append({"file": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    payload = {
        "case_id": "COLD-LANTERN-PRACTICE",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": records,
    }
    marker.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: baseline frozen at {marker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
