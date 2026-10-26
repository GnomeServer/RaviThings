#!/usr/bin/env python3
"""Hash every markdown file in a Module 1 work inbox."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workdir", type=Path)
    args = parser.parse_args()
    inbox = args.workdir.expanduser().resolve() / "inbox"
    files = sorted(inbox.glob("*.md")) if inbox.is_dir() else []
    if len(files) != 9:
        print(f"HOLD: expected 9 inbox markdown files, observed {len(files)}", file=sys.stderr)
        return 1
    for path in files:
        print(f"{hashlib.sha256(path.read_bytes()).hexdigest()} {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
