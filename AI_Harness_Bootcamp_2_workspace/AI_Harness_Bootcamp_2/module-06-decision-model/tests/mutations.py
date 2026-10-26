#!/usr/bin/env python3
"""Mutation corpus: each item must make test_module_06.py FAIL its named check."""
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


def sub(rel: str, pattern: str, repl: str) -> Callable[[Path], None]:
    def go(root: Path) -> None:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        new, count = re.subn(pattern, repl, text, count=1, flags=re.M)
        if count == 0:
            raise AssertionError(f"mutation anchor {pattern!r} not found in {rel}")
        path.write_text(new, encoding="utf-8")
    return go


def edit_json(rel: str, change: Callable[[dict], None]) -> Callable[[Path], None]:
    def go(root: Path) -> None:
        path = root / rel
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return go


def remove(rel: str) -> Callable[[Path], None]:
    return lambda root: (root / rel).unlink()


SCRIPT = "scripts/blue_gauge.py"
MUTATIONS = [
    Mutation("M6-CASE", "future-issued acceptance becomes applicable at the snapshot", sub(SCRIPT, r'and date\(record\["issued_at"\]\) <= at', 'and True')),
    Mutation("M6-AUTH", "instruction precedence is dropped in screen_step", sub(SCRIPT, r'if answers\["instructs_reader"\]\["bool"\] >= gates\["instruction_review"\]:', 'if False:')),
    Mutation("M6-FAN", "fan-out requests staged need only instead of all six screen questions", sub(SCRIPT, r'wanted = step\["need"\] if plan\["mode"\] == "serial" else list\(CONTRACT\) if step\["route"\] is None else \[\]', 'wanted = step["need"]')),
    Mutation("M6-CONFIDENCE", "higher twin confidence overrides the weaker answer", sub(SCRIPT, r'confidence = min\(first\["confidence"\], second\["confidence"\]\)', 'confidence = max(first["confidence"], second["confidence"])')),
    Mutation("M6-SCORE", "composite scoring omits normalization before weighting", sub(SCRIPT, r'normalized = answer\["score"\] / \(len\(questions\[key\]\["criteria"\]\) - 1\)', 'normalized = float(answer.get("score", 0))')),
    Mutation("M6-INTENT", "low-confidence intent bypasses human review", sub(SCRIPT, r'elif intent\["confidence"\] < config\["handlers"\]\["intent_confidence"\]:', 'elif False:')),
    Mutation("M6-NATIVE", "one-use eval cell admission allows reuse of consumed plan", sub(SCRIPT, r'if not active or active\["consumed"\]:', 'if False:  # mutated one-use admission allows reuse')),
    Mutation("M6-EVIDENCE", "sealed report HOLD reasons are ignored during audit recomputation", sub(SCRIPT, r'if report\["decision"\] == "HOLD":', 'if False:  # sealed recompute bypass')),
    Mutation("M6-PREP", "prepared work safety rejects repo-relative or symlink work folders", sub(SCRIPT, r'if work\.is_symlink\(\) or not work\.is_dir\(\) or work\.resolve\(\) != work or work\.is_relative_to\(REPO\):', 'if work.is_symlink() or not work.is_dir() or work.resolve() != work or False:')),
]
