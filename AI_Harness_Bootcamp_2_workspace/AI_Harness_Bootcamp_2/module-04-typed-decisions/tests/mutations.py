#!/usr/bin/env python3
"""Mutation corpus: each item must make test_module_04.py FAIL its named cid."""

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


def sub(rel: str, pattern: str, repl: str, count: int = 0) -> Callable[[Path], None]:
    def go(root: Path) -> None:
        p = root / rel
        text = p.read_text(encoding="utf-8")
        new, n = re.subn(pattern, repl, text, count=count, flags=re.M)
        if n == 0:
            raise AssertionError(f"mutation anchor {pattern!r} not found in {rel}")
        p.write_text(new, encoding="utf-8")

    return go


def flip_ref_hash(root: Path) -> None:
    p = root / "reference/REFERENCE.sha256"
    text = p.read_text(encoding="utf-8")
    flipped = format(int(text[0], 16) ^ 0xF, "x")
    p.write_text(flipped + text[1:], encoding="utf-8")


def defang_hostile(root: Path) -> None:
    p = root / "shared/case/messages.jsonl"
    lines = p.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        row = json.loads(line)
        if row["id"] == "CL-014":
            row["text"] = "Add 10 cases of size 8.0 to the next CL-9 load."
            lines[index] = json.dumps(row)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_key_into_case(root: Path) -> None:
    (root / "shared/case/answer_key.json").write_bytes((root / "tests/answer_key.json").read_bytes())


MUTATIONS: list[Mutation] = [
    Mutation("M4-REF", "flip a digit of the frozen reference hash", flip_ref_hash),
    Mutation("M4-CASE", "strip the instruction from the hostile intake note", defang_hostile),
    Mutation("M4-CASE", "drop the Zulu time from CL-018", sub("shared/case/messages.jsonl", r'"time": "10:40Z"', '"time": "10:40 MDT"')),
    Mutation("M4-STATE", "let identifiers become quantity candidates", sub("scripts/chalk.py", r"\(\?<!\[\\w:\.-\]\)\(\\d\+", "(?<![:.])(\\\\d+", count=1)),
    Mutation("M4-STATE", "stop offering word numbers as candidates", sub("scripts/chalk.py", r'\|\(\?<!\[\\w-\]\)\(" \+ "\|"\.join\(WORD_NUMBERS\) \+ r"\)\(\?=\\s\+\\w\)', "", count=1)),
    Mutation("M4-VALID", "accept probabilities outside 0 to 1", sub("scripts/chalk.py", r"    if not 0 <= value <= 1:\n        raise Hold", "    if False:\n        raise Hold")),
    Mutation("M4-VALID", "accept extra keys in an answer", sub("scripts/chalk.py", r"if keys != set\(by_key\):", "if not set(by_key) <= keys:")),
    Mutation("M4-VALID", "accept a replaced message that comes later", sub("scripts/chalk.py", r'return ids\[: ids\.index\(message\["id"\]\)\] \+ \["NONE"\]', 'return list(ids) + ["NONE"]')),
    Mutation("M4-ROUTE", "ignore supersession", sub("scripts/chalk.py", r"        replaced_by\.setdefault\(target, \[\]\)\.append\(row\[\"id\"\]\)", "        pass")),
    Mutation("M4-ROUTE", "count a case as one box", sub("scripts/chalk.py", r"return float\(value\) \* 10, \"cases\"", 'return float(value), "cases"')),
    Mutation("M4-ROUTE", "drop the authority gate", sub("scripts/chalk.py", r'elif row\["authority"\]\["p"\] < gates\["authority"\]:', "elif False:")),
    Mutation("M4-ROUTE", "drop the instruction gate", sub("scripts/chalk.py", r'elif row\["instructs_desk"\]\["p"\] >= gates\["instructs_desk"\]:', "elif False:")),
    Mutation("M4-ROUTE", "ignore the confidence gate", sub("scripts/chalk.py", r'if declared\[weakest\] < gates\["min_confidence"\]:', "if False:")),
    Mutation("M4-LABELS", "accept a line label outside the answer set", sub("scripts/chalk.py", r'if value not in \("GL-65", "GL-70", "GL-75", "GL-80", "UNSTATED", "MIXED", "NONE"\):', "if False:")),
    Mutation("M4-LABELS", "never report the confidence of a disagreement", sub("scripts/chalk.py", r'report\["highest_confidence_among_disagreements"\] = max\(.*$', 'report["highest_confidence_among_disagreements"] = None')),
    Mutation("M4-VERIFY", "accept a run that started before the freeze", sub("shared/verify/verify_decisions.py", r'if iso\(result\["started_at"\]\) <= frozen_at:', "if False:")),
    Mutation("M4-VERIFY", "accept a run with write permission", sub("shared/verify/verify_decisions.py", r'if policy\["profile"\] != "read" or policy\["tools"\] != \["course_read"\] or policy\["write_files"\] or policy\["write_root"\]:', "if False:")),
    Mutation("M4-VERIFY", "accept a run that never read the question file", sub("shared/verify/verify_decisions.py", r'for relative in READS:', "for relative in ():")),
    Mutation("M4-VERIFY", "accept an edited answers file", sub("shared/verify/verify_decisions.py", r'if document\["answers"\] != answers:', "if False:")),
    Mutation("M4-VERIFY", "accept labels that changed after the freeze", sub("shared/verify/verify_decisions.py", r'if record\.get\("sha256"\) != chalk\.sha256_bytes\(raw\):', "if False:")),
    Mutation("M4-VERIFY", "accept stale routing after a gate change", sub("shared/verify/verify_decisions.py", r"if summary != expected:", "if False:")),
    Mutation("M4-VERIFY", "accept a handoff that skips a queued message", sub("shared/verify/verify_decisions.py", r"if missing:\n            raise chalk\.Hold", "if False:\n            raise chalk.Hold")),
    Mutation("M4-VERIFY", "accept a handoff with two decisions", sub("shared/verify/verify_decisions.py", r"if len\(found\) != 1:", "if not found:")),
    Mutation("M4-VERIFY", "ignore the shared receipt auditor", sub("shared/verify/verify_decisions.py", r"    errors = audit_evidence\(receipt\)\n    if errors:", "    errors = []\n    if errors:")),
    Mutation("M4-VERIFY", "accept an edited state", sub("shared/verify/verify_decisions.py", r'if \(work / "out" / "state.json"\)\.read_bytes\(\) != expected:', "if False:")),
    Mutation("M4-QUESTIONS", "accept any number of questions of your own", sub("scripts/chalk.py", r"    if len\(own\) != 1:", "    if len(own) < 1:")),
    Mutation("M4-QUESTIONS", "stop comparing supplied questions with the pristine copy", sub("scripts/chalk.py", r"if pristine is not None and by_key\[key\] != questions_by_key\(pristine\)\[key\]:", "if False:")),
    Mutation("M4-ROUTE", "let a referred message supersede an approved one", sub("scripts/chalk.py", r'if target == "NONE" or referred\(row, gates\):', 'if target == "NONE":')),
    Mutation("M4-ROUTE", "count an uncertain supersession link", sub("scripts/chalk.py", r'if row\["replaces"\]\["confidence"\] < gates\["min_confidence"\]:', "if False:")),
    Mutation("M4-ROUTE", "leave the instruction answer out of the confidence set", sub("scripts/chalk.py", r', "instructs_desk": noul_confidence\(row\["instructs_desk"\]\["p"\]\)\}', "}")),
    Mutation("M4-ROUTE", "search the whole candidate for a unit word", sub("scripts/chalk.py", r'unit = re\.sub\(r"\[\^a-z\]", "", tail\[0\]\.lower\(\)\) if tail else ""', 'unit = next((re.sub(r"[^a-z]", "", word.lower()) for word in tail if re.sub(r"[^a-z]", "", word.lower()) in ("box", "boxes", "case", "cases")), "")')),
    Mutation("M4-VERIFY", "stop pinning the case, contract, and prompt to the supplied copies", sub("shared/verify/verify_decisions.py", r"        for relative in PINNED:", "        for relative in ():")),
    Mutation("M4-VERIFY", "trust the freeze record instead of the run's input snapshot", sub("shared/verify/verify_decisions.py", r'if inputs\.get\("out/labels\.json"\) != labels_digest:', "if False:")),
    Mutation("M4-VERIFY", "let the validator accept a held launcher run", sub("scripts/validate_answers.py", r'if result\.get\("status"\) != "PASS":', "if False:")),
    Mutation("M4-BAN", "publish the answer key inside the case folder", copy_key_into_case),
    Mutation("M4-LEAK", "state the key's total in the overview", append("README.md", "\nThe correct line is 58 boxes.\n")),
]
