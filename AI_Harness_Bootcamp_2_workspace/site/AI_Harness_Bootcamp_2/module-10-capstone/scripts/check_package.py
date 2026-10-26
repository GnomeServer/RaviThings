#!/usr/bin/env python3
"""Check package completeness and local dependencies, not independent transfer."""

from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

BANNED = (
    "246 kg",
    "1,404 kg",
    "3 minutes late",
    "module-01-mission-thread",
    "W-9",
    "RC-0",
    "RUNNABLE_PACKAGE",
    "0.0.0.0",
    "route R-71",
)
SOURCE_IDS = tuple(f"S0{n}" for n in range(1, 10))
FIELDS = (
    "purpose", "bounds", "inputs", "controls / config identity", "run", "check",
    "stop", "restore", "strongest evidence", "limitations", "next owner",
)
LOCAL_PATH = re.compile(r"\b(?:scripts|shared|out)[/\\][A-Za-z0-9_.\\/+-]+")


def check(text: str) -> list[str]:
    hits: list[str] = []
    for token in BANNED:
        if token in text:
            hits.append(token)
    for token in SOURCE_IDS:
        if re.search(rf"\b{token}(?:_|-|\b)", text):
            hits.append(token)
    return hits


def structure_errors(text: str, root: Path) -> list[str]:
    """Read the package's fixed named fields; never execute its command text."""
    fields: dict[str, list[str]] = {}
    current = None
    fence = False
    errors = []
    for line in text.splitlines():
        if line.startswith("```"):
            fence = not fence
            if fence and not line[3:].strip():
                errors.append("code block lacks a language")
            if current:
                fields[current].append(line)
            continue
        if not fence and line.startswith("## "):
            current = line[3:].strip().lower()
            if current in fields:
                errors.append(f"duplicate field: {current}")
            fields[current] = []
        elif current:
            fields[current].append(line)
    if fence:
        errors.append("unclosed code block")
    for name in FIELDS:
        content = fields.get(name, [])
        if not any(line.strip() and not line.startswith("```") for line in content):
            errors.append(f"missing or empty field: {name}")

    def commands(name: str, script: str) -> list[list[str]]:
        found = []
        for line in fields.get(name, []):
            try:
                words = shlex.split(line, comments=True)
            except ValueError:
                continue
            if words[:1] == ["&"]:
                words = words[1:]
            words = [word.replace("\\", "/") for word in words]
            if len(words) >= 2 and words[0] == "$PY" and words[1] == script:
                found.append(words)
        return found

    for name in ("run", "stop", "restore"):
        calls = commands(name, "scripts/local_ai.py")
        if not calls:
            errors.append(f"{name} lacks a complete local_ai command")
    if not any(len(call) == 3 and call[2] == "shared/PACKAGE.md" for call in commands("check", "scripts/check_package.py")):
        errors.append("check lacks the package-check command")

    paths = {value.replace("\\", "/") for value in LOCAL_PATH.findall(text)}
    for name in ("inputs", "controls / config identity"):
        if not LOCAL_PATH.search("\n".join(fields.get(name, []))):
            errors.append(f"{name} lacks a local path")
    for value in sorted(paths):
        if value.startswith("out/"):
            continue
        path = root / value
        if not path.is_file():
            errors.append(f"missing local dependency: {value}")
        try:
            resolved = path.resolve()
            if not resolved.is_relative_to(root.resolve()):
                errors.append(f"dependency path leaves the package: {value}")
        except (OSError, ValueError):
            errors.append(f"dependency path cannot be resolved: {value}")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_package.py <package.md>", file=sys.stderr)
        return 1
    path = Path(argv[1])
    if not path.is_file():
        print("HOLD: missing input", file=sys.stderr)
        return 1
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        print(f"HOLD: unreadable package: {error}", file=sys.stderr)
        return 1
    hits = check(text)
    if hits:
        print("HOLD: package cites " + ", ".join(hits))
        return 1
    root = (path.parent.parent if path.parent.name == "shared" else path.parent).resolve()
    try:
        errors = structure_errors(text, root)
    except (OSError, ValueError) as error:
        errors = [f"cannot inspect package paths: {error}"]
    if errors:
        print("HOLD: " + "; ".join(errors), file=sys.stderr)
        return 1
    print("PASS: package structure checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
