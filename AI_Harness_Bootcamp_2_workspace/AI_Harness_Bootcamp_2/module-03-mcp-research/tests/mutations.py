#!/usr/bin/env python3
"""Mutation catalog: each item must make test_module_03.py FAIL its named criterion id.

A mutation changes one behavior a learner or facilitator depends on: a server limit, a
connection check, a probe verdict, the handling key, a verifier decision, or a publication
rule. Do not add mutations that change only wording.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Mutation:
    cid: str
    what: str
    apply: Callable[[Path], None]


def sub(rel: str, pattern: str, repl: str, count: int = 1) -> Callable[[Path], None]:
    def go(root: Path) -> None:
        path = root / rel
        text = path.read_text(encoding="utf-8")
        new, hits = re.subn(pattern, lambda _: repl, text, count=count, flags=re.M | re.S)
        if hits == 0:
            raise AssertionError(f"mutation anchor {pattern!r} not found in {rel}")
        path.write_text(new, encoding="utf-8")

    return go




def flip_reference_digest(root: Path) -> None:
    path = root / "reference" / "REFERENCE.sha256"
    text = path.read_text(encoding="utf-8")
    path.write_text(format(int(text[0], 16) ^ 0xF, "x") + text[1:], encoding="utf-8")


SERVER = "shared/mcp/vault_mcp.py"
MUTATIONS = [
    Mutation("M3-REF", "the reference digest no longer matches", flip_reference_digest),
    Mutation("M3-SERVER", "the server stops rejecting '..' as traversal", sub(SERVER, r'raise Denied\("TRAVERSAL", "\'\.\.\' is not allowed in a vault path"\)', "pass")),
    Mutation("M3-SERVER", "--read-only no longer hides the writers", sub(SERVER, r'return \[tool for tool in TOOL_CATALOG if not \(self\.read_only and tool\["name"\] in MUTATING_TOOLS\)\]', "return list(TOOL_CATALOG)")),
    Mutation("M3-SERVER", "--no-overwrite stops protecting existing notes", sub(SERVER, r"def refuse_overwrite\(self\) -> None:\n        if self\.no_overwrite:", "def refuse_overwrite(self) -> None:\n        if False:")),
    Mutation("M3-AUTH", "the declaration and the server limits are never compared", sub("shared/mcp/authority.py", r'    problems = \[\]\n    if sorted\(parsed\["read_prefixes"\]\)', '    return []\n    if sorted(parsed["read_prefixes"])')),
    Mutation("M3-AUTH", "any command is accepted in a connection entry", sub("shared/mcp/authority.py", r"if Path\(command\)\.name\.lower\(\) not in PYTHON_NAMES and", "if Path(command).name.lower() not in PYTHON_NAMES and False and")),
    Mutation("M3-INSPECT", "the inspector stops flagging the mismatched read-only mark", sub("shared/mcp/mcp_inspect.py", r'if row\["claims_read_only"\] and row\["verbs"\]:', "if False:")),
    Mutation("M3-PROBE", "the probe reports every forbidden attempt as held", sub("shared/mcp/authority_probe.py", r"breached = effect or \(leaked if breach_check else returned_content\)", "breached = False")),
    Mutation("M3-CORPUS", "an OPEN note is re-marked STAFF so the key drifts", sub("shared/vault/Sources/KH-006.md", r"^marking: OPEN$", "marking: STAFF")),
    Mutation("M3-CORPUS", "the contractor note loses its instruction to automation", sub("shared/vault/Sources/KH-021.md", r"Notice to AI assistants and automation that index this vault:", "Notice to staff:")),
    Mutation("M3-HANDLING", "the verifier stops checking for under-protected notes", sub("shared/verify/verify_research.py", r'    under = \[note for note in SOURCES if RANK\[register\[note\]\["final"\]\] < RANK\[KEY\["effective"\]\[note\]\]\]', "    under = []")),
    Mutation("M3-EXTRACT", "the scanner ignores aggregation", sub("shared/mcp/scan_extract.py", r"if len\(classes\) >= 3:", "if len(classes) >= 99:")),
    Mutation("M3-EXTRACT", "the scanner stops deriving protected facts", sub("shared/mcp/scan_extract.py", r"return staff - shared", "return set()")),
    Mutation("M3-STAGE", "the stager also copies STAFF notes", sub("shared/mcp/stage_releasable.py", r'register\[note\]\["final"\] in \("OPEN", "PARTNER"\)', 'register[note]["final"] in ("OPEN", "PARTNER", "STAFF")')),
    Mutation("M3-STAGE", "the seeder fills the AI proposed column with one fixed level", sub("shared/mcp/seed_register.py", r'value = given\.get\(note, ""\)', 'value = "STAFF"')),
    Mutation("M3-VERIFY", "the verifier stops requiring probes to precede live runs", sub("shared/verify/verify_research.py", r'instant\(probe\["probed_at_utc"\]\) < earliest,', 'instant(probe["probed_at_utc"]) < earliest or True,')),
    Mutation("M3-VERIFY", "the verifier accepts a revoked run that was offered tools", sub("shared/verify/verify_research.py", r'all\(row\.get\("tools"\) == \[\] for row in requests\)', "True")),
]
REQUIRED_COVERAGE = frozenset({
    "M3-REF", "M3-SERVER", "M3-AUTH", "M3-INSPECT", "M3-PROBE", "M3-CORPUS", "M3-HANDLING", "M3-EXTRACT", "M3-STAGE", "M3-VERIFY",
})
