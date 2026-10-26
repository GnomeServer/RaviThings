#!/usr/bin/env python3
"""Freeze your own handling decisions before the AI sees anything.

Usage: freeze_calibration.py --vault VAULT --out FILE

Reads Estimate/Calibration.md (six notes, your marking, and the rule) and
writes a record with the time and the file's fingerprint. Run it before any research
run, then compare your decisions with the AI's afterward.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from handling import parse_calibration  # noqa: E402

EXPECTED_ROWS = 6


def freeze(vault: Path) -> dict:
    path = vault / "Estimate" / "Calibration.md"
    if not path.is_file():
        raise ValueError(f"{path} not found")
    data = path.read_bytes()
    rows = parse_calibration(data.decode("utf-8"))
    if len(rows) != EXPECTED_ROWS:
        raise ValueError(f"the calibration table needs {EXPECTED_ROWS} note rows; found {len(rows)}")
    problems = []
    for note, row in rows.items():
        if row["marking"] is None:
            problems.append(f"{note}: My marking must be OPEN, PARTNER, or STAFF")
        if not row["rule"].strip():
            problems.append(f"{note}: name the rule that decides it")
    if problems:
        raise ValueError("; ".join(problems))
    return {"schema_version": 1, "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "calibration_sha256": hashlib.sha256(data).hexdigest(),
            "rows": [{"note": note, "marking": row["marking"], "rule": row["rule"]} for note, row in rows.items()]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.out.exists() or args.out.is_symlink():
            raise ValueError(f"{args.out} already exists; the first freeze is the one that counts")
        record = freeze(args.vault)
    except (ValueError, OSError, UnicodeDecodeError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 2
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(f"PASS: froze {len(record['rows'])} calibration decisions at {record['frozen_at_utc']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
