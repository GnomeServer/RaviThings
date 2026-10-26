#!/usr/bin/env python3
"""Copy the notes you decided may be shared into Estimate/Releasable/.

Usage: stage_releasable.py --vault VAULT

Reads Estimate/Handling register.md. Every note in Sources/ needs a Final decision of
OPEN, PARTNER, or STAFF. Estimate/Releasable/ then holds byte-identical copies of
exactly the notes you marked OPEN or PARTNER. Sources/ is never changed.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from handling import parse_register  # noqa: E402


def stage(vault: Path) -> tuple[list[str], list[str], list[str]]:
    register_path = vault / "Estimate" / "Handling register.md"
    sources = vault / "Sources"
    releasable = vault / "Estimate" / "Releasable"
    if not register_path.is_file() or not sources.is_dir():
        raise ValueError(f"{vault} does not look like the research vault")
    register = parse_register(register_path.read_text(encoding="utf-8"))
    note_ids = sorted(p.stem for p in sources.glob("KH-*.md"))
    missing = [note for note in note_ids if note not in register]
    blanks = [note for note in note_ids if note in register and register[note]["final"] is None]
    if missing or blanks:
        parts = []
        if missing:
            parts.append("no row for " + ", ".join(missing))
        if blanks:
            parts.append("Final must be OPEN, PARTNER, or STAFF for " + ", ".join(blanks))
        raise ValueError("the register is not finished: " + "; ".join(parts))
    wanted = {note for note in note_ids if register[note]["final"] in ("OPEN", "PARTNER")}
    releasable.mkdir(parents=True, exist_ok=True)
    for entry in releasable.iterdir():
        if entry.is_dir() or entry.is_symlink() and entry.is_dir():
            raise ValueError(f"{entry} is a folder; Estimate/Releasable/ holds only note files")
    added, removed, unchanged = [], [], []
    for entry in sorted(releasable.iterdir()):
        if entry.stem not in wanted or entry.suffix != ".md":
            entry.unlink()
            removed.append(entry.name)
    for note in sorted(wanted):
        source, target = sources / f"{note}.md", releasable / f"{note}.md"
        if target.exists() and target.read_bytes() == source.read_bytes():
            unchanged.append(note)
            continue
        shutil.copyfile(source, target)
        added.append(note)
    return added, removed, sorted(wanted)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        added, removed, wanted = stage(args.vault)
    except (ValueError, OSError, UnicodeDecodeError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 2
    print(f"added {len(added)}: {', '.join(added) or '-'}")
    print(f"removed {len(removed)}: {', '.join(removed) or '-'}")
    print(f"PASS: Estimate/Releasable/ holds {len(wanted)} notes, the ones you marked OPEN or PARTNER")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
