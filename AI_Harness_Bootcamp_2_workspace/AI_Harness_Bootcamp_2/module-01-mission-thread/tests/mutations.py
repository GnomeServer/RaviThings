#!/usr/bin/env python3
"""Mutation corpus: each item must make test_module_01.py FAIL its named cid."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Mutation:
    cid: str
    what: str
    apply: Callable[[Path], None]


def append(rel: str, text: str) -> Callable[[Path], None]:
    def go(root: Path) -> None:
        p = root / rel
        p.write_text(p.read_text(encoding="utf-8") + text, encoding="utf-8")
    return go


def sub(rel: str, pattern: str, repl: str, required: bool = True, count: int = 0) -> Callable[[Path], None]:
    def go(root: Path) -> None:
        p = root / rel
        text = p.read_text(encoding="utf-8")
        new, n = re.subn(pattern, repl, text, count=count, flags=re.M)
        if required and n == 0:
            raise AssertionError(f"mutation anchor {pattern!r} not found in {rel}")
        p.write_text(new, encoding="utf-8")
    return go


def drop(rel: str) -> Callable[[Path], None]:
    def go(root: Path) -> None:
        (root / rel).unlink()
    return go


def flip_ref_hash(root: Path) -> None:
    p = root / "reference/REFERENCE.sha256"
    text = p.read_text(encoding="utf-8")
    if not text or text[0] not in "0123456789abcdefABCDEF":
        raise AssertionError("REFERENCE.sha256 missing a leading hex digit")
    flipped = format(int(text[0], 16) ^ 0xF, "x")
    if text[0].isupper():
        flipped = flipped.upper()
    p.write_text(flipped + text[1:], encoding="utf-8")


def mutate_case_id(root: Path) -> None:
    p = root / "shared/case/SOURCE_MANIFEST.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["case_id"] = "MUTATED"
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def flip_source_byte(root: Path) -> None:
    path = root / "shared/case/sources/S01_MO-27_r4.md"
    data = bytearray(path.read_bytes())
    if not data:
        raise AssertionError("S01 source is empty")
    # keep valid ascii/utf8 so oracle's read_text in M1-ANSWER and learner_text never crashes
    data[0] = (data[0] + 1) % 128
    path.write_bytes(bytes(data))


MUTATIONS: list[Mutation] = [
    Mutation("M1-REF", "flip first hex digit of REFERENCE.sha256", flip_ref_hash),
    Mutation("M1-01", "delete baseline source S01", drop("shared/case/sources/S01_MO-27_r4.md")),
    Mutation("M1-02", "set practice case_id to MUTATED", mutate_case_id),
    Mutation("M1-02", "flip one byte of baseline source S01", flip_source_byte),
    Mutation("M1-14", "force scanned_kits to 0",
             sub("scripts/compute_thread.py",
                 r"return SCANNED_TOTES \* KITS_PER_TOTE",
                 "return 0")),
    Mutation("M1-ANSWER", "leak 246 kg into README.md",
             append("README.md", "\n246 kg\n")),
]
