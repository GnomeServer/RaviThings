#!/usr/bin/env python3
"""Freeze your filled-in labels: record their digest and the UTC time in the evidence folder.

Usage: freeze_labels.py <workdir> <evidence-dir>
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chalk  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: freeze_labels.py <workdir> <evidence-dir>", file=sys.stderr)
        return 2
    work, evidence = (Path(value).expanduser().resolve() for value in argv[1:])
    try:
        state = chalk.load_json(work / "out" / "state.json")
        raw = (work / "out" / "labels.json").read_bytes()
        chalk.check_labels(chalk.strict_json(raw.decode("utf-8")), state)
        digest = chalk.sha256_bytes(raw)
        record = {"schema": "chalk-line/labels-frozen/1", "sha256": digest, "frozen_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "sample": list(chalk.SAMPLE_IDS)}
        chalk.write_new(evidence / "labels.sha256", chalk.canonical(record))
    except FileExistsError:
        print("HOLD: labels were already frozen in this evidence folder; keep that freeze", file=sys.stderr)
        return 1
    except (OSError, chalk.Hold) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 1
    print(f"LABELS FROZEN {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
