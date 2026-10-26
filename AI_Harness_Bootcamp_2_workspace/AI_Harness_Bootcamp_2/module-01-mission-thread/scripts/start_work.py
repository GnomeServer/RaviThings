#!/usr/bin/env python3
"""Create a new Module 1 work folder without overwriting an existing attempt."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "shared/templates"
CASE = ROOT / "shared/case"
INBOX_MAP = CASE / "INBOX_MAP.json"
FILES = {
    "source-register.csv": TEMPLATES / "source-register.csv",
    "thread-ledger.csv": TEMPLATES / "thread-ledger.csv",
    "changed-thread-ledger.csv": TEMPLATES / "thread-ledger.csv",
}
MARKDOWN = [
    "challenge-matrix.md", "corrected-brief.md", "baseline-verdict.md",
    "change-prediction.md", "changed-brief.md", "changed-verdict.md", "handoff.md",
]
DESK = """# Desk · 14:05 MDT 6 October 2026

Open [REQUEST.md](REQUEST.md) first. Then open every file under [inbox/](inbox/). Hash the inbox before you trust a filename.

The 14:05 AI file is a finished `GO`. You did not write it. Treat it as output to verify.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    destination = args.destination.expanduser().resolve()
    if destination.exists():
        print(f"HOLD: destination already exists: {destination}")
        return 1
    mapping = json.loads(INBOX_MAP.read_text(encoding="utf-8"))["sources"]
    destination.mkdir(parents=True)
    for name, source in FILES.items():
        shutil.copyfile(source, destination / name)
    for name in MARKDOWN:
        (destination / name).write_text(f"# {name.removesuffix('.md').replace('-', ' ').title()}\n\n", encoding="utf-8")
    shutil.copyfile(CASE / "REQUEST.md", destination / "REQUEST.md")
    (destination / "desk.md").write_text(DESK, encoding="utf-8")
    inbox = destination / "inbox"
    inbox.mkdir()
    for entry in mapping:
        shutil.copyfile(CASE / "sources" / entry["canonical"], inbox / entry["inbox"])
    incoming = sorted(mapping, key=lambda item: item["received"])
    (inbox / "INCOMING.txt").write_text(
        "".join(f"{item['received']}\t{item['inbox']}\n" for item in incoming),
        encoding="utf-8",
    )
    print(f"PASS: created {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
