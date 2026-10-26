#!/usr/bin/env python3
"""Copy the AI's proposed handling into your register, and nothing else.

Usage: seed_register.py --vault VAULT

Reads Drafts/research/handling-proposal.md and fills the "AI proposed" column of
Estimate/Handling register.md. The Final, Rule, and Reason columns stay yours: the
register records what you decided, next to what the AI proposed.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from handling import NOTE_ID, level_of, table_rows  # noqa: E402

ROW = re.compile(r"^(\|\s*)(KH-\d{3})(\s*\|)([^|]*)(\|.*)$")


def proposals(vault: Path) -> dict[str, str]:
    path = vault / "Drafts" / "research" / "handling-proposal.md"
    if not path.is_file():
        raise ValueError(f"{path} not found; run the research step first")
    found: dict[str, str] = {}
    for cells in table_rows(path.read_text(encoding="utf-8")):
        level = level_of(cells[1]) if len(cells) > 1 else None
        if level and cells[0] not in found:
            found[cells[0]] = level
    return found


def seed(vault: Path) -> tuple[int, list[str]]:
    register = vault / "Estimate" / "Handling register.md"
    if not register.is_file():
        raise ValueError(f"{register} not found")
    given = proposals(vault)
    lines, seeded, missing = [], 0, []
    for line in register.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match and NOTE_ID.fullmatch(match.group(2)):
            note = match.group(2)
            value = given.get(note, "")
            if not value:
                missing.append(note)
            line = f"{match.group(1)}{note}{match.group(3)} {value} {match.group(5)}" if value else f"{match.group(1)}{note}{match.group(3)}  {match.group(5)}"
            seeded += 1
        lines.append(line)
    register.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return seeded, missing


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        seeded, missing = seed(args.vault)
    except (ValueError, OSError, UnicodeDecodeError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 2
    print(f"PASS: filled the AI proposed column for {seeded - len(missing)} of {seeded} notes")
    if missing:
        print(f"The AI gave no usable proposal for {', '.join(missing)}; their cells stay empty and you decide them from the rules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
