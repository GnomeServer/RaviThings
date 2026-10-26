#!/usr/bin/env python3
"""Render the Module 1 work into one local, keyboard-readable HTML review page."""

from __future__ import annotations

import argparse
import csv
import html
import re
from collections import Counter
from pathlib import Path

EXPECTED_STEPS = [
    "Requirement defined",
    "Cargo received",
    "Cargo released",
    "Vehicle made ready",
    "Movement authorized",
    "Route window met",
    "Cargo delivered",
    "Usable effect confirmed",
]
SECTION_FILES = [
    ("Challenge matrix", "challenge-matrix.md"),
    ("Baseline corrected brief", "corrected-brief.md"),
    ("Changed corrected brief", "changed-brief.md"),
    ("Baseline verdict", "baseline-verdict.md"),
    ("Change prediction", "change-prediction.md"),
    ("Changed verdict", "changed-verdict.md"),
    ("Handoff", "handoff.md"),
]
OPTIONAL_SECTIONS = [
    ("Handoff scrutiny", "handoff-scrutiny.md"),
    ("Your reading of the scrutiny", "handoff-scrutiny-decision.md"),
]
RESULT_ORDER = ("CONTRADICTED", "UNRESOLVED", "NOT YET OCCURRED", "SUPPORTED")
QUESTIONS = [
    "What can proceed?",
    "What cannot proceed?",
    "What exact condition blocks the decision?",
    "Which source and calculation establish that result?",
    "What evidence would change it?",
]


def load_register(work: Path) -> dict[str, str]:
    path = work / "source-register.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        register = {
            row.get("source_id", ""): row.get("file", "")
            for row in csv.DictReader(handle)
            if row.get("source_id")
        }
    if (work / "REVEALED_CHANGE.md").is_file():
        register["S10"] = "../REVEALED_CHANGE.md"
    return register


def load_ledger(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def inbox_href(register: dict[str, str], source_id: str) -> str | None:
    name = register.get(source_id, "")
    return f"inbox/{html.escape(name)}" if name else None


def source_link(register: dict[str, str], source_id: str, label: str | None = None) -> str:
    text = html.escape(label or source_id)
    href = inbox_href(register, source_id)
    if href:
        return f"<a href='{href}'>{text}</a>"
    return text


def verdict_value(text: str) -> str:
    for value in ("ACCEPT", "REVISE", "REJECT", "HOLD"):
        if f"Verdict: {value}" in text:
            return value
    return "UNSET"


def field_line(text: str, label: str) -> str:
    match = re.search(rf"^{re.escape(label)}\s*(.*)$", text, re.M)
    return match.group(1).strip() if match else ""


def step_mark(rows: list[dict[str, str]], step: str) -> str:
    counts = Counter(row["result"] for row in rows if row.get("step") == step and row.get("result"))
    if not counts:
        return "No claim assessments recorded"
    order = [*RESULT_ORDER, *sorted(counts.keys() - set(RESULT_ORDER))]
    return "; ".join(f"{counts[result]} {result}" for result in order if counts[result])


def table(path: Path, register: dict[str, str]) -> str:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return "<p>Empty ledger.</p>"
    head, *body = rows
    source_index = head.index("source_id") if "source_id" in head else -1

    def cell(index: int, value: str) -> str:
        escaped = html.escape(value)
        if index == source_index and value:
            href = inbox_href(register, value)
            if href:
                return f"<td><a href='{href}'>{escaped}</a></td>"
        return f"<td>{escaped}</td>"

    return "<div class='scroll'><table><thead><tr>" + "".join(f"<th scope='col'>{html.escape(name)}</th>" for name in head) + "</tr></thead><tbody>" + "".join("<tr>" + "".join(cell(index, value) for index, value in enumerate(row)) + "</tr>" for row in body) + "</tbody></table></div>"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workdir", type=Path)
    args = parser.parse_args()
    work = args.workdir.resolve()
    output = work / "review.html"
    register = load_register(work)
    baseline = load_ledger(work / "thread-ledger.csv")
    base_text = (work / "baseline-verdict.md").read_text(encoding="utf-8") if (work / "baseline-verdict.md").exists() else ""
    changed_text = (work / "changed-verdict.md").read_text(encoding="utf-8") if (work / "changed-verdict.md").exists() else ""
    chip = verdict_value(base_text)
    standing = field_line(base_text, "Standing rule:")
    unresolved = field_line(base_text, "Unresolved condition:")

    steps = "".join(
        f"<li><span class='step'>{html.escape(step)}</span> <span class='mark'>{html.escape(step_mark(baseline, step))}</span></li>"
        for step in EXPECTED_STEPS
    )
    blockers: list[str] = []
    for row in baseline:
        if row.get("result") in {"CONTRADICTED", "UNRESOLVED"}:
            claim = row.get("claim", "") or row.get("claim_id", "")
            blockers.append(
                f"<li>{source_link(register, row.get('source_id', ''))} — {html.escape(row.get('result', ''))}: {html.escape(claim)}</li>"
            )
    if unresolved:
        blockers.append(f"<li>Unresolved condition: {html.escape(unresolved)}</li>")
    blocker_html = "".join(blockers) or "<li>None recorded.</li>"
    delta = ""
    if changed_text.strip():
        delta = f"<section><h2>Change delta</h2><pre>{html.escape(changed_text)}</pre></section>"
    questions = "".join(f"<li>{html.escape(item)}</li>" for item in QUESTIONS)
    sections = []
    for title, name in SECTION_FILES:
        path = work / name
        text = path.read_text(encoding="utf-8") if path.exists() else f"Missing: {name}"
        sections.append(f"<section><h2>{html.escape(title)}</h2><pre>{html.escape(text)}</pre></section>")
    for title, name in OPTIONAL_SECTIONS:
        path = work / name
        if path.is_file() and path.stat().st_size:
            sections.append(f"<section><h2>{html.escape(title)}</h2><pre>{html.escape(path.read_text(encoding='utf-8'))}</pre></section>")
    ledgers = []
    for title, name in (("Source register", "source-register.csv"), ("Baseline thread", "thread-ledger.csv"), ("Changed thread", "changed-thread-ledger.csv")):
        path = work / name
        ledgers.append(f"<section><h2>{title}</h2>{table(path, register) if path.exists() else '<p>Missing ledger.</p>'}</section>")
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cold Lantern desk packet</title><style>
body{{font:18px/1.55 system-ui,sans-serif;max-width:1100px;margin:auto;padding:2rem;color:#171717;background:#fff}}
a{{color:#0645ad}} pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f5f5;padding:1rem;border:1px solid #bbb}}
.scroll{{overflow:auto}} table{{border-collapse:collapse;font-size:.85rem}} th,td{{border:1px solid #777;padding:.45rem;text-align:left;vertical-align:top}} th{{background:#eee;position:sticky;top:0}}
.chip{{display:inline-block;padding:.2rem .7rem;border:2px solid #171717;font-weight:700;letter-spacing:.04em}}
.steps{{display:flex;flex-wrap:wrap;gap:.5rem;list-style:none;padding:0}}
.steps li{{border:1px solid #777;padding:.35rem .55rem}}
.mark{{font-size:.8rem;display:block}}
:focus{{outline:3px solid #005fcc;outline-offset:2px}}
@media print{{
nav{{display:none}}
body{{max-width:none;padding:0;color:#000;background:#fff}}
a{{color:#000;text-decoration:none}}
a[href]::after{{content:" (" attr(href) ")"}}
.chip,.steps li{{border-color:#000}}
}}
</style></head><body>
<h1>Cold Lantern desk packet</h1>
<p>Class-only decision support. This record does not authorize a movement.</p>
<nav aria-label="Review sections"><a href="#decision">Skip to decisions</a></nav>
<p>Verdict <span class="chip">{html.escape(chip)}</span></p>
<h2>Baseline claim assessments by thread step</h2>
<ol class="steps">{steps}</ol>
<p>These counts describe recorded claims, not the operational state of an entire step. A contradicted draft claim does not erase a supported source fact.</p>
<h2>Challenged claims and unresolved conditions</h2>
<ul>{blocker_html}</ul>
<h2>Standing rule</h2>
<blockquote>{html.escape(standing) if standing else "Not recorded."}</blockquote>
{delta}
<ol id="decision" tabindex="-1">{questions}</ol>
{''.join(ledgers)}{''.join(sections)}
</body></html>"""
    output.write_text(document, encoding="utf-8")
    print(f"PASS: wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
