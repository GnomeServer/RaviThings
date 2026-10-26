#!/usr/bin/env python3
"""Check a partner extract before anyone sends it.

Usage: scan_extract.py --extract FILE --vault VAULT [--allowed-prefix Estimate/Releasable/] [--json]

Three checks, each with the rule that decides it:

  citation     every line of the extract ends in a link to a note under the allowed folder
  protected    no distinctive fact that appears only in notes you marked STAFF
  aggregation  fewer than three of the four movement elements (H5): a location grid, a time
               with a zone letter, a named route, and a cargo quantity or lot

A scan cannot decide whether a sentence is wise to share. It checks what a program can check.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from handling import ELEMENT_PATTERNS, WIKILINK, element_classes, parse_register, split_header, tokens_of  # noqa: E402,F401

DEFAULT_PREFIX = "Estimate/Releasable/"


def resolve_link(target: str, vault: Path, prefix: str) -> Path | None:
    target = target.strip()
    rel = target if "/" in target else prefix + target
    if not rel.endswith(".md"):
        rel += ".md"
    if not rel.startswith(prefix) or ".." in rel.split("/"):
        return None
    path = vault / rel
    return path if path.is_file() else None


def content_lines(text: str):
    _, body = split_header(text)
    for number, line in enumerate(body.splitlines(), 1):
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            yield number, stripped


def protected_tokens(vault: Path) -> set[str]:
    register = parse_register((vault / "Estimate" / "Handling register.md").read_text(encoding="utf-8"))
    staff, shared = set(), set()
    for note, row in register.items():
        path = vault / "Sources" / f"{note}.md"
        if not path.is_file():
            continue
        found = tokens_of(path.read_text(encoding="utf-8"))
        if row["final"] == "STAFF":
            staff |= found
        elif row["final"] in ("OPEN", "PARTNER"):
            shared |= found
    return staff - shared


def scan(extract: Path, vault: Path, prefix: str) -> dict:
    text = extract.read_text(encoding="utf-8")
    findings = []
    for number, line in content_lines(text):
        links = WIKILINK.findall(line)
        if not links:
            findings.append({"check": "citation", "line": number, "rule": "H6", "detail": f"line {number} has no [[link]] to a note under {prefix}"})
            continue
        for target in links:
            if resolve_link(target, vault, prefix) is None:
                findings.append({"check": "citation", "line": number, "rule": "H6", "detail": f"line {number} cites [[{target}]], which is not a note under {prefix}"})
    protected = protected_tokens(vault)
    body = split_header(text)[1]
    for token in sorted(protected):
        if token in " ".join(body.split()):
            findings.append({"check": "protected", "line": None, "rule": "H4", "detail": f"'{token}' appears only in notes you marked STAFF"})
    classes = element_classes(body)
    if len(classes) >= 3:
        findings.append({"check": "aggregation", "line": None, "rule": "H5", "detail": f"the extract holds {len(classes)} of the 4 movement elements ({', '.join(classes)}); three or more make it STAFF"})
    return {"extract": str(extract), "elements": classes, "findings": findings, "verdict": "PASS" if not findings else "HOLD"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--extract", required=True, type=Path)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--allowed-prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = scan(args.extract, args.vault, args.allowed_prefix)
    except (OSError, ValueError, UnicodeDecodeError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for finding in report["findings"]:
            print(f"HOLD {finding['rule']} {finding['check']}: {finding['detail']}")
        print(f"movement elements present: {', '.join(report['elements']) or 'none'}")
        print("PASS: the extract is cited, repeats no STAFF-only fact, and stays below three movement elements" if report["verdict"] == "PASS"
              else f"HOLD: {len(report['findings'])} finding(s)")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
