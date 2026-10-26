#!/usr/bin/env python3
"""Check a downloaded White Rack sheet against the source lots.

A complete sheet is not a correct routing decision. This prints REVIEW lines
for rows that do not match the rules, and HOLD only when the file itself is
not a usable sheet.
"""

from __future__ import annotations

import csv
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
HEADER = ("lot", "route", "status", "reason")
LOTS = tuple(f"LW-{n:02d}" for n in range(1, 81))


def fail(message: str) -> None:
    print(f"HOLD: {message}", file=sys.stderr)
    raise SystemExit(1)


def column_index(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha())
    index = 0
    for ch in letters:
        index = index * 26 + ord(ch.upper()) - 64
    return index - 1


def read_xlsx(path: Path) -> list[list[str]]:
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        fail("the .xlsx file is not a spreadsheet archive")
    with archive:
        names = set(archive.namelist())
        if "xl/worksheets/sheet1.xml" not in names:
            fail("the spreadsheet has no first sheet")
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("m:si", NS):
                shared.append("".join(node.text or "" for node in item.iter(MAIN + "t")))
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows: list[list[str]] = []
        for row in root.findall("m:sheetData/m:row", NS):
            values: list[str] = []
            for cell in row.findall("m:c", NS):
                index = column_index(cell.attrib.get("r", "A"))
                while len(values) <= index:
                    values.append("")
                kind = cell.attrib.get("t")
                value = cell.find("m:v", NS)
                if kind == "s" and value is not None and value.text:
                    values[index] = shared[int(value.text)]
                elif kind == "inlineStr":
                    inline = cell.find("m:is", NS)
                    values[index] = "".join(node.text or "" for node in inline.iter(MAIN + "t")) if inline is not None else ""
                elif value is not None and value.text:
                    values[index] = value.text
            rows.append(values)
    return rows


def read_csv(path: Path) -> list[list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [row for row in csv.reader(handle) if any(cell.strip() for cell in row)]


def rows_from(path: Path) -> list[dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        grid = read_xlsx(path)
    elif suffix == ".csv":
        grid = read_csv(path)
    else:
        fail("use the downloaded .xlsx, or a .csv saved from that spreadsheet")
    if not grid:
        fail("the spreadsheet has no rows")
    header = [cell.strip() for cell in grid[0]]
    if tuple(header[:4]) != HEADER:
        fail("header must start lot,route,status,reason")
    records = []
    for raw in grid[1:]:
        cells = list(raw) + [""] * 4
        records.append({name: cells[index].strip() for index, name in enumerate(HEADER)})
    return records


def source_lots(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        found = [row["lot"].strip() for row in csv.DictReader(handle)]
    if found != list(LOTS):
        fail("the source batch is not the White Rack wave")
    return set(found)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        fail("usage: check_sheet.py <white-rack.xlsx> <wave1.csv>")
    sheet_path, source_path = map(Path, argv[1:])
    if not sheet_path.is_file():
        fail(f"spreadsheet not found: {sheet_path}")
    if not source_path.is_file():
        fail(f"source batch not found: {source_path}")
    raw = sheet_path.read_bytes()
    if b"sk-or-" in raw or b"OPENROUTER_API_KEY" in raw:
        fail("the spreadsheet contains key material; delete this copy and do not keep it")
    expected = source_lots(source_path)
    records = rows_from(sheet_path)
    seen = [row["lot"] for row in records]
    missing = [lot for lot in LOTS if lot not in seen]
    extra = [lot for lot in seen if lot not in expected]
    duplicate = sorted({lot for lot in seen if seen.count(lot) > 1})
    if missing or extra or duplicate or len(seen) != 80:
        detail = []
        if missing:
            detail.append("missing " + ",".join(missing))
        if extra:
            detail.append("unexpected " + ",".join(extra))
        if duplicate:
            detail.append("duplicate " + ",".join(duplicate))
        fail("sheet does not have each source lot once: " + "; ".join(detail))
    print("PASS: sheet has the 80 source lots")
    print("REVIEW: compare these rows with SHEET_RULES.md. A fluent agent reply is not this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
