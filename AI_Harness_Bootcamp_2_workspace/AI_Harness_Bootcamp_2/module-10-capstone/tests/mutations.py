#!/usr/bin/env python3
"""Deterministic mutations that must each be caught by the Module 10 oracle."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Mutation:
    cid: str
    what: str
    apply: object


def append(rel: str, text: str):
    def go(root: Path) -> None:
        path = root / rel
        current = path.read_text(encoding="utf-8")
        path.write_text(current + text, encoding="utf-8")
    return go


def replace_exact(rel: str, old: str, new: str, expected: int = 1):
    def go(root: Path) -> None:
        path = root / rel
        current = path.read_text(encoding="utf-8")
        found = current.count(old)
        if found != expected:
            raise RuntimeError(f"anchor count {found} != {expected} in {rel}")
        path.write_text(current.replace(old, new), encoding="utf-8")
    return go


def flip_ref_hash(root: Path) -> None:
    path = root / "reference/REFERENCE.sha256"
    text = path.read_text(encoding="utf-8").strip()
    first = "0" if text[0] != "0" else "1"
    path.write_text(first + text[1:] + "\n", encoding="utf-8")


def drop_restore_field(root: Path) -> None:
    """A package without a Restore section must not pass the structural check."""
    path = root / "scripts/check_package.py"
    current = path.read_text(encoding="utf-8")
    old = '"stop", "restore", "strongest evidence", "limitations", "next owner",'
    new = '"stop", "strongest evidence", "limitations", "next owner",'
    if current.count(old) != 1:
        raise RuntimeError("FIELDS restore anchor missing")
    current = current.replace(old, new)
    path.write_text(current, encoding="utf-8")

def leave_temp_files(root: Path) -> None:
    """Exclusive publication must remove its temporary file after linking."""
    path = root / "scripts/local_ai.py"
    current = path.read_text(encoding="utf-8")
    old = "        raise\n    tmp.unlink(missing_ok=True)\n\n\ndef load_card"
    new = "        raise\n\n\ndef load_card"
    if current.count(old) != 1:
        raise RuntimeError("final temp cleanup anchor missing")
    path.write_text(current.replace(old, new), encoding="utf-8")


CHECKER = "scripts/check_package.py"
ADAPTER = "scripts/local_ai.py"

MUTATIONS = [
    Mutation("M10-REF", "flip the frozen reference digest", flip_ref_hash),
    Mutation("M10-CHK-MISSING", "treat a missing package as success",
             replace_exact(CHECKER, 'print("HOLD: missing input", file=sys.stderr)\n        return 1', 'return 0')),
    Mutation("M10-CHK-ARGS", "accept a missing package argument",
             replace_exact(CHECKER, 'if len(argv) != 2:\n        print("usage: check_package.py <package.md>", file=sys.stderr)\n        return 1', 'if len(argv) < 2:\n        return 0')),
    Mutation("M10-PACKAGE-STRUCTURE", "accept a package without any restore requirement", drop_restore_field),
    Mutation("M10-PACKAGE-PATH", "skip path confinement",
             replace_exact(CHECKER, 'if not resolved.is_relative_to(root.resolve()):', 'if False:')),
    Mutation("M10-BEHAV-VERIFY", "accept any digest",
             replace_exact(ADAPTER, 'if actual_hash != card["weight_sha256"]:', 'if False:')),
    Mutation("M10-BEHAV-DISABLE", "ignore the disabled control",
             replace_exact(ADAPTER, 'if not enabled:\n        return finish("control disabled", 1)', 'if False:\n        return finish("control disabled", 1)')),
    Mutation("M10-BEHAV-EXISTS", "allow overwriting existing outputs",
             replace_exact(ADAPTER, 'except FileExistsError:\n            return finish("output exists", 2)', 'except FileExistsError:\n            overlay_path.unlink(missing_ok=True)\n            overlay_path.write_bytes(overlay.encode("utf-8"))\n            launch_path.unlink(missing_ok=True)\n            launch_path.write_bytes(dump(launch))')),
    Mutation("M10-BEHAV-MALFORMED", "succeed on a malformed identity card",
             replace_exact(ADAPTER, 'except ValueError as error:\n            return finish(str(error), 2)\n        try:\n            payload = read_regular(model_path)', 'except ValueError as error:\n            return 0\n        try:\n            payload = read_regular(model_path)')),
    Mutation("M10-BEHAV-WIRE", "accept any port",
             replace_exact(ADAPTER, 'if not 1024 <= port <= 65535:', 'if port <= 0:')),
    Mutation("M10-BEHAV-PROBE", "report a dead port as reachable",
             replace_exact(ADAPTER, 'if not reachable or \'"status":"ok"\' not in body.replace(" ", ""):', 'if False:')),
    Mutation("M10-BEHAV-STOP", "skip the reachability recheck",
             replace_exact(ADAPTER, 'reachable, _ = health_probe(port)\n        if reachable:', 'reachable, _ = (False, "")\n        if False:')),
    Mutation("M10-BEHAV-ATOMIC", "leave temp files behind", leave_temp_files),
    Mutation("M10-BEHAV-FRESH", "make wire outputs nondeterministic",
             replace_exact(ADAPTER, 'launch = {\n            "argv": [', 'launch = {\n            "issued_at": __import__("datetime").datetime.now().isoformat(),\n            "argv": [')),
    Mutation("M10-BEHAV-LOOPBACK", "permit a non-loopback bind",
             replace_exact(ADAPTER, 'LOOPBACK = "127.0.0.1"', 'LOOPBACK = "0.0.0.0"')),
]
