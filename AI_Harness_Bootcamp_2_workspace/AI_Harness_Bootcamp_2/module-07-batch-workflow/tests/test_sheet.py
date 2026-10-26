#!/usr/bin/env python3
"""The sheet checker accepts a complete download and rejects a broken one."""

from __future__ import annotations

import subprocess
import sys
import html
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_sheet.py"
SOURCE = ROOT / "shared/batch/wave1.csv"
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def run(sheet: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(sheet), str(SOURCE)],
        capture_output=True,
        text=True,
    )


def write_xlsx(path: Path, rows: list[list[str]]) -> None:
    shared = []
    index = {}
    for row in rows:
        for cell in row:
            if cell not in index:
                index[cell] = len(shared)
                shared.append(cell)

    def cell(col: int, row_number: int, value: str) -> str:
        ref = f"{chr(ord('A') + col)}{row_number}"
        return f'<c r="{ref}" t="s"><v>{index[value]}</v></c>'

    body = []
    for row_number, row in enumerate(rows, start=1):
        cells = "".join(cell(col, row_number, value) for col, value in enumerate(row))
        body.append(f'<row r="{row_number}">{cells}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<worksheet xmlns="{NS}"><sheetData>{"".join(body)}</sheetData></worksheet>'
    )
    strings = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="{NS}" count="{len(shared)}" uniqueCount="{len(shared)}">'
        + "".join(f"<si><t>{html.escape(value)}</t></si>" for value in shared)
        + "</sst>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", strings)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


def lots() -> list[str]:
    return [f"LW-{n:02d}" for n in range(1, 81)]


def complete_rows() -> list[list[str]]:
    rows = [["lot", "route", "status", "reason"]]
    rows.extend([lot, "hold", "OPEN", "unchecked"] for lot in lots())
    return rows


def main() -> int:
    failures = 0

    def check(name: str, condition: bool, detail: str) -> None:
        nonlocal failures
        print(("PASS" if condition else "FAIL"), name, detail)
        failures += not condition

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        good = folder / "white-rack.xlsx"
        write_xlsx(good, complete_rows())
        result = run(good)
        check("complete xlsx", result.returncode == 0 and "PASS: sheet has the 80 source lots" in result.stdout, result.stderr)

        short = folder / "short.xlsx"
        write_xlsx(short, complete_rows()[:-1])
        result = run(short)
        check("missing lot holds", result.returncode == 1 and "HOLD:" in result.stderr, result.stderr)

        leaked = folder / "leaked.xlsx"
        rows = complete_rows()
        rows[1][3] = "sk-or-secret"
        write_xlsx(leaked, rows)
        result = run(leaked)
        check("key material holds", result.returncode == 1 and "key material" in result.stderr, result.stderr)

        csv_path = folder / "white-rack.csv"
        csv_path.write_text("".join(",".join(row) + "\n" for row in complete_rows()), encoding="utf-8")
        result = run(csv_path)
        check("complete csv", result.returncode == 0 and "PASS: sheet has the 80 source lots" in result.stdout, result.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
