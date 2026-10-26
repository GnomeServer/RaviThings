#!/usr/bin/env python3
"""Mutation corpus: proof that the oracle's checks can fail. Reference v2 section 6 C6.

Each mutation breaks the module in exactly one way and names the criterion that must
catch it. A criterion with no mutation here is unproven, and test_module_00.py fails on
that. This is DeMillo/Lipton/Sayward mutation adequacy (1978) pointed at a document set:
a check that no mutant kills is not a check.

Mutations append or create wherever possible rather than editing existing prose, so the
corpus survives ordinary revision of the module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Mutation:
    cid: str                      # criterion that must FAIL
    what: str                     # what was broken
    apply: Callable[[Path], None]


def append(rel: str, text: str) -> Callable[[Path], None]:
    def go(root: Path) -> None:
        p = root / rel
        p.write_text(p.read_text(encoding="utf-8") + text, encoding="utf-8")
    return go


def sub(rel: str, pattern: str, repl: str, required: bool = True, count: int = 0) -> Callable[[Path], None]:
    """Replace ALL occurrences by default. Replacing only the first leaves a second copy
    behind, and a mutation that only half-breaks the module proves nothing."""
    def go(root: Path) -> None:
        p = root / rel
        text = p.read_text(encoding="utf-8")
        new, n = re.subn(pattern, repl, text, count=count, flags=re.M | re.I)
        if required and n == 0:
            raise AssertionError(f"mutation anchor {pattern!r} not found in {rel}")
        p.write_text(new, encoding="utf-8")
    return go



GUIDE = "platforms/macos.md"
LAB = "shared/MODULE_00_LAB.md"


MUTATIONS: list[Mutation] = [
    # Class A
    Mutation("A7", "a block persists an empty PATH element",
             append(GUIDE, "\n```bash\nexport PATH=\"$HOME/.local/bin::$PATH\"\n```\n")),
    Mutation("A8", "a pasted line after the credential read would be captured as the key",
             append(GUIDE, "\n```bash\nIFS= read -r -s OPENROUTER_API_KEY\nexport OPENROUTER_API_KEY\n```\n")),
    Mutation("A10", "an installer runs without being inspected",
             append(GUIDE, "\n```bash\ncurl -fsSL https://example.invalid/download_cli.sh -o /tmp/x.sh\n"
                           "bash /tmp/x.sh\n```\n")),
    Mutation("A11", "a box loses the closing brace of its function",
             append(GUIDE, "\n```bash\ncourse_broken() {\n  printf 'ready\\n'\ncourse_broken\n```\n")),
    Mutation("A12", "a PowerShell script gains a typographic dash",
             append("scripts/verify-setup.ps1", "\n# Report \u2014 written by the checker\n")),
    # Class B
    Mutation("B1-B6", "the practice checker stops binding numbers to their subject",
             lambda root: (p := root / "shared/case/check_artifact.py",
                           p.write_text(re.sub(
                               r'    on_hand = attached\(text, ON_HAND_SUBJECT, ON_HAND_PATTERNS\)',
                               '    on_hand = {27} if re.search(r"on.?hand", text, re.I) else set()',
                               p.read_text(encoding="utf-8")),
                           encoding="utf-8"))[0]),
    Mutation("B8", "the readiness check accepts any file with the right bytes",
             sub("shared/case/verify_tool_proof.py", r"        return 1", "        return 0")),
    # Class C
    Mutation("C1", "a file the learner is sent to read is parked where the scan does not look",
             lambda root: ((root / "reference/EXTRA_HANDOUT.md").write_text(
                 "# Extra handout\n\n```text\nsudo npm install -g something -g\n```\n", encoding="utf-8"),
                 append("README.md", "\nRead the [extra handout](reference/EXTRA_HANDOUT.md).\n")(root))),
    Mutation("C2", "a dangerous command hides in a new learner file",
             lambda root: (root / "shared/case/EXTRA_HANDOUT.md").write_text(
                 "# Extra handout\n\n```text\nsudo npm install --global something -g\n```\n", encoding="utf-8")),
    Mutation("C2", "a dangerous command hides in a ```text fence",
             append(LAB, "\n```text\nsudo npm install --global whatever -g\n```\n")),
    Mutation("C2", "a learner block deletes the course checkout",
             append(LAB, '\n```bash\nrm -rf "$HOME/Documents/AIHB_OCT_2026"\n```\n')),
    # Class D
    Mutation("REF", "the frozen Reference is edited without re-freezing",
             append("reference/REFERENCE.md", "\nAn unrecorded change.\n")),
]