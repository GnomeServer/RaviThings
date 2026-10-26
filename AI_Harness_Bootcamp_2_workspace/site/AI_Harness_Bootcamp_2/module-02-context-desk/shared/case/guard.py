#!/usr/bin/env python3
"""Screen one retrieved note for instruction-like wording.

This is a file screen for the Ledger Pike pile, not model enforcement.
It reads the path you pass, prints PASS or HOLD, and writes nothing.
A person can still paste a quoted order into chat. This screen never sees that paste.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERN = re.compile(
    r"(?i)SYSTEM OVERRIDE|Ignore later|Do not mention these instructions|Treat this (?:note|document) as"
)


def run(text: str) -> list[tuple[str, bool, str]]:
    if PATTERN.search(text):
        return [
            (
                "hostile-instruction",
                False,
                "retrieved text contains instruction-like language",
            )
        ]
    return [("source-as-data", True, "no instruction-like language found")]


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: guard.py <file>", file=sys.stderr)
        return 1
    path = Path(argv[1])
    if not path.is_file():
        print(f"HOLD: missing input {path}", file=sys.stderr)
        return 1
    results = run(path.read_text(encoding="utf-8"))
    ok = True
    for name, passed, detail in results:
        print(f"{'PASS' if passed else 'HOLD'} {name}: {detail}")
        if not passed:
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
