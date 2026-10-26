#!/usr/bin/env python3
"""Boundaries of scripts/longform.py that a learner relies on, checked without paid calls.

The launcher is replaced in-process by a stand-in that writes each declared output, so
these tests cover what the helper decides: which files each review session can see,
which sections a revision may touch, and when it refuses to start.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
SCRIPT = MODULE / "scripts" / "longform.py"
CASE = MODULE / "shared" / "case"
sys.path.insert(0, str(SCRIPT.parent))
import longform  # noqa: E402

BRIEF = "\n".join(f"{label} filled" for label in longform.BRIEF_LABELS) + "\n"
TESTS = "# Tests\n\n## Must say\n- 40 requested\n\n## Must never say or imply\n- a pickup time\n\n## A reader must be able to answer\n- Who owns the release?\n"
OUTLINE = "# North Shelf status\n\n" + "".join(
    f"## {n}. Part {n}\nJob: do part {n}\nFacts: fact {n} (S{n})\nWords: 120\n\n" for n in range(1, 6)
)
REVIEW_OUTPUT = {
    "tests-pass.md": "Test: 40 requested\nResult: MET\nSection: 1\nQuote: \"x\"\nFix: none\n",
    "fact-questions.md": "Q1\nSection: 2\nClaim: \"27 kits are on hand.\"\nQuestion: How many kits are on hand?\n",
    "fact-answers.md": "Q1\nAnswer: 27\nSource: S2-count-sheet.md\n",
    "reader-pass.md": "Action: wait\nBecause: \"x\"\nSection: 5\n",
    "style-pass.md": "No findings.\n",
}


class LongformBoundaries(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="longform-test-"))
        self.work, self.evidence = self.root / "work", self.root / "evidence"
        self.work.mkdir()
        self.evidence.mkdir()
        for name in ("REQUEST.md", "STYLE.md"):
            shutil.copyfile(CASE / name, self.work / name)
        shutil.copytree(CASE / "sources", self.work / "sources")
        (self.work / "brief.md").write_text(BRIEF, encoding="utf-8")
        (self.work / "tests.md").write_text(TESTS, encoding="utf-8")
        (self.work / "outline.md").write_text(OUTLINE, encoding="utf-8")
        self.seen: dict[str, set[str]] = {}
        self.saved_session, self.saved_ready = longform.run_session, longform.ready_to_launch
        longform.run_session = self.fake_session
        longform.ready_to_launch = lambda: None

    def tearDown(self) -> None:
        longform.run_session, longform.ready_to_launch = self.saved_session, self.saved_ready
        shutil.rmtree(self.root)

    def fake_session(self, workdir: Path, prompt: Path, evidence: Path, label: str, outputs: list[str]):
        self.seen[label] = {p.relative_to(workdir).as_posix() for p in workdir.rglob("*") if p.is_file()}
        for output in outputs:
            target = workdir / output
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(REVIEW_OUTPUT.get(output, f"New text for {output}.\n"), encoding="utf-8")
        return evidence / "receipts" / label, []

    def draft_all(self) -> None:
        self.assertEqual(longform.freeze(self.work, self.evidence), 0)
        self.assertEqual(longform.draft(self.work, self.evidence, None, True), 0)
        self.assertTrue((self.work / "draft-v1.md").is_file())

    def test_review_sessions_see_only_their_packets(self) -> None:
        self.draft_all()
        (self.work / "notes.md").write_text("my working notes\n", encoding="utf-8")
        self.assertEqual(longform.critique(self.work, self.evidence, "v1", "1"), 0)
        answers = next(files for label, files in self.seen.items() if label.endswith("fact-answers"))
        self.assertNotIn("draft.md", answers)
        self.assertIn("questions.md", answers)
        self.assertTrue(any(name.startswith("sources/") for name in answers))
        for label, files in self.seen.items():
            if label.startswith("r1-"):
                self.assertFalse({"notes.md", "outline.md", "brief.md"} & files, label)
        questions = next(p for p in (self.evidence / "packets").rglob("questions.md"))
        self.assertNotIn("27 kits are on hand", questions.read_text(encoding="utf-8"))
        merged = (self.work / "review/r1/facts-pass.md").read_text(encoding="utf-8")
        self.assertIn("Answer from the sources: 27", merged)

    def test_revision_rewrites_only_named_sections(self) -> None:
        self.draft_all()
        before = {n: (self.work / longform.section_file("v1", n)).read_bytes() for n in range(1, 6)}
        (self.work / "fixes.md").write_text(
            "# Fixes\n\n## Accepted\n\nSection: 2\nQuote: \"x\"\nFix: y\nWhy: S2\n\n## Rejected\n\n- Section: 4 would lose a fact\n",
            encoding="utf-8",
        )
        self.assertEqual(longform.revise(self.work, self.evidence, "v1", "v2", "fixes.md"), 0)
        for n in (1, 3, 4, 5):
            self.assertEqual((self.work / longform.section_file("v2", n)).read_bytes(), before[n], f"section {n}")
        self.assertNotEqual((self.work / longform.section_file("v2", 2)).read_bytes(), before[2])
        self.assertIn("## 2. Part 2\n\nNew text for draft/v2/02.md.", (self.work / "draft-v2.md").read_text(encoding="utf-8"))

    def test_changed_plan_refuses_before_any_session(self) -> None:
        self.assertEqual(longform.freeze(self.work, self.evidence), 0)
        with (self.work / "outline.md").open("a", encoding="utf-8") as handle:
            handle.write("\n")
        self.assertEqual(longform.draft(self.work, self.evidence, 1, False), 1)
        self.assertEqual(self.seen, {})
        self.assertFalse((self.work / "draft").exists())

    def test_missing_key_refuses_without_writing(self) -> None:
        env = {key: value for key, value in os.environ.items() if key != "OPENROUTER_API_KEY"}
        before = sorted(p.name for p in self.work.iterdir())
        result = subprocess.run([sys.executable, str(SCRIPT), "outline", str(self.work), str(self.evidence)],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("OPENROUTER_API_KEY unavailable", result.stderr)
        self.assertEqual(sorted(p.name for p in self.work.iterdir()), before)


if __name__ == "__main__":
    unittest.main()
