#!/usr/bin/env python3
"""Check frozen research integrity and the staff supply graph, not prose wording.

Published instructional structure is checked by build_course.py --check. Capability
progression and human performance require review and observed exercises, not tokens.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "docs/analysis/2026-08-09-reformation-core-standard-reference.md"
REFERENCE_SHA256 = "419a41a094673ac7cdc775b03c643ff8d8f6e50a680dc11ed8dea019713d0fc1"
SOURCE_LOG = ROOT / "docs/analysis/gauntlet-standard/source-access-log.txt"


def field(body: str, name: str) -> str:
    match = re.search(rf"^\*\*{re.escape(name)}:\*\*\s*(.+?)\s*$", body, re.MULTILINE)
    if not match:
        raise ValueError(f"missing staff contract field: {name}")
    return match.group(1).strip()


def tokens(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def check() -> None:
    digest = hashlib.sha256(REFERENCE.read_bytes()).hexdigest()
    if digest != REFERENCE_SHA256:
        raise ValueError(f"frozen historical research reference changed: {digest}")
    sources = SOURCE_LOG.read_text(encoding="utf-8")
    if sum("\t200\t" in line for line in sources.splitlines()) < 12:
        raise ValueError("historical source-access evidence is incomplete")

    modules = sorted((ROOT / "modules/core").glob("[0-9][0-9]-*.md"))
    if [path.name[:2] for path in modules] != [f"{i:02d}" for i in range(11)]:
        raise ValueError("the supply graph must contain exactly Modules 00–10")
    course_map = (ROOT / "COURSE_MAP.md").read_text(encoding="utf-8")
    rows = {}
    for line in course_map.splitlines():
        cells = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(cells) == 7 and re.fullmatch(r"\d{2}", cells[0]):
            if cells[0] in rows:
                raise ValueError(f"duplicate module in course map: {cells[0]}")
            rows[cells[0]] = (re.findall(r"`([^`]+)`", cells[3]), re.findall(r"`([^`]+)`", cells[4]))
    if set(rows) != {f"{i:02d}" for i in range(11)}:
        raise ValueError("course map is missing a module supply contract")
    produced: set[str] = set()
    consumed: set[str] = set()
    owners: set[str] = set()
    for module in modules:
        body = module.read_text(encoding="utf-8")
        owner = field(body, "Primary objective")
        if owner in owners:
            raise ValueError(f"duplicate primary capability owner: {module.name}")
        owners.add(owner)
        inputs = tokens(field(body, "Consumes"))
        outputs = tokens(field(body, "Produces"))
        if not inputs or not outputs:
            raise ValueError(f"empty supply boundary: {module.name}")
        if len(inputs) != len(set(inputs)) or len(outputs) != len(set(outputs)):
            raise ValueError(f"duplicate supply edge: {module.name}")
        if any(not item.startswith("VERIFY:") for item in inputs):
            raise ValueError(f"input lacks a verification boundary: {module.name}")
        if produced.intersection(outputs):
            raise ValueError(f"two modules own the same product: {module.name}")
        if rows[module.name[:2]] != (inputs, outputs):
            raise ValueError(f"course map and module supply boundaries disagree: {module.name}")
        consumed.update(inputs)
        produced.update(outputs)
    if consumed.intersection(produced):
        raise ValueError("a supplied case depends on another module's product")


def main() -> int:
    try:
        check()
    except (OSError, ValueError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 1
    print("PASS: frozen research identity and eleven-module supply graph")
    print("MANUAL: capability progression, responsible decisions, and timing require separate evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
