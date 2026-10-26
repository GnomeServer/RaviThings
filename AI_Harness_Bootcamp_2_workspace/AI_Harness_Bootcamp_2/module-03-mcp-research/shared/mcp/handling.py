#!/usr/bin/env python3
"""Shared helpers for the handling-rule tools: tables, notes, and the four movement elements.

The detectors here are the single definition of "location", "time", "route", and "cargo"
for the staging, scanning, and checking tools. Nothing here touches the network.
"""
from __future__ import annotations

import re

LEVELS = ("OPEN", "PARTNER", "STAFF")
RANK = {name: index for index, name in enumerate(LEVELS)}
NOTE_ID = re.compile(r"KH-\d{3}")

ELEMENT_PATTERNS = {
    "location": r"\bGRID\s+\d{2}[A-Z]\s+[A-Z]{2}\s+\d{4}\s+\d{4}\b",
    "time": r"\b\d{6}[ZL]\b|\b\d{4}[ZL]\b|\b\d{2}:\d{2}\s?[ZL]\b",
    "route": r"\b(?:MSR|ASR)\s+[A-Z][a-z]+\b",
    "cargo": r"\b\d+\s+(?:burn-dressing\s+)?cases?\b|\bL-\d{4}\b",
}
ELEMENT_REGEX = {name: re.compile(pattern) for name, pattern in ELEMENT_PATTERNS.items()}

# Distinctive facts a summary could repeat: lot and vehicle style identifiers, DTGs, grids, routes, quantities with units.
TOKEN_PATTERNS = (
    r"\b[A-Z]{1,3}-\d{1,4}\b",
    r"\b\d{6}[ZL]\b",
    r"\bGRID\s+\d{2}[A-Z]\s+[A-Z]{2}\s+\d{4}\s+\d{4}\b",
    r"\b(?:MSR|ASR)\s+[A-Z][a-z]+\b",
    r"\b\d+(?:\.\d+)?\s?(?:km|MLC|cases?|kg|tons?)\b",
)
TOKEN_REGEX = [re.compile(pattern) for pattern in TOKEN_PATTERNS]


def element_classes(text: str) -> list[str]:
    """Return the names of the movement elements the text contains, in a fixed order."""
    return [name for name, pattern in ELEMENT_REGEX.items() if pattern.search(text)]


def split_header(text: str) -> tuple[str | None, str]:
    """Return (header text, body). The header is None when the note has none."""
    if not text.startswith("---\n"):
        return None, text
    lines = text.split("\n")
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r") == "---":
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1:])
    return None, text


def tokens_of(text: str) -> set[str]:
    """Distinctive tokens in a note's body (the header and note identifiers are ignored)."""
    _, body = split_header(text)
    found: set[str] = set()
    for pattern in TOKEN_REGEX:
        for match in pattern.finditer(body):
            token = " ".join(match.group(0).split())
            if not NOTE_ID.fullmatch(token):
                found.add(token)
    return found


def table_rows(text: str) -> list[list[str]]:
    """Rows of a markdown table whose first cell is a note id, as lists of trimmed cells."""
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and NOTE_ID.fullmatch(cells[0]):
            rows.append(cells)
    return rows


def level_of(cell: str) -> str | None:
    value = cell.strip().upper()
    return value if value in LEVELS else None


def parse_register(text: str) -> dict[str, dict]:
    """Map note id to {proposed, final, rule, reason} from the Handling register table."""
    result: dict[str, dict] = {}
    for cells in table_rows(text):
        if len(cells) < 5:
            continue
        note = cells[0]
        if note in result:
            raise ValueError(f"{note} has more than one row in the register")
        result[note] = {"proposed": level_of(cells[1]), "final": level_of(cells[2]), "final_text": cells[2], "rule": cells[3], "reason": cells[4]}
    return result


def parse_calibration(text: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for cells in table_rows(text):
        if len(cells) < 4:
            continue
        note = cells[0]
        if note in result:
            raise ValueError(f"{note} has more than one row in the calibration table")
        result[note] = {"marking": level_of(cells[1]), "marking_text": cells[1], "rule": cells[2], "reason": cells[3]}
    return result


WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
