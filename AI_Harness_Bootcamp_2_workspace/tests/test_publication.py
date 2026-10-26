#!/usr/bin/env python3
"""Workspace safety regressions; every mutation is in a disposable source tree."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepare_work", ROOT / "shared/prepare_work.py")
prepare_work = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare_work)


class WorkspaceBehavior(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="course-work-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "checkout/reformation"
        self.boot = self.root / "AI_Harness_Bootcamp_2"
        self.boot.mkdir(parents=True)

    def module(self, module_id):
        module = self.boot / f"module-{module_id}-test"
        if module_id == "07":
            for relative in ("shared/batch/wave1.csv", "shared/SHEET_RULES.md", "scripts/check_sheet.py"):
                target = module / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"exercise input\r\n")
            return module
        for sub in prepare_work.SHARED[module_id]:
            directory = module / "shared" / sub
            directory.mkdir(parents=True)
            (directory / "input.txt").write_text("original input\n", encoding="utf-8")
        (module / "scripts").mkdir()
        for script in prepare_work.SCRIPTS[module_id]:
            (module / "scripts" / script).write_text("# authored test control\n", encoding="utf-8")
        return module

    def test_preserves_attempt_and_rejects_repository_overlap(self):
        self.module("02")
        work = self.base / "existing"
        work.mkdir()
        (work / "decision.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            prepare_work.prepare("02", work, self.root)
        self.assertEqual((work / "decision.txt").read_text(), "keep")
        with self.assertRaises(ValueError):
            prepare_work.prepare("02", self.root.parent / "unrelated-new-work", self.root)
        self.assertFalse((self.root.parent / "unrelated-new-work").exists())

    def test_filters_staff_history_and_verifier_from_all_depths(self):
        module = self.module("09")
        for relative in ("shared/case/verify_safeguards.py", "shared/case/tests/test.py", "shared/case/history/old.txt", "shared/case/__pycache__/old.pyc", "shared/case/assessment/private.json"):
            target = module / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("must not enter W", encoding="utf-8")
        work = prepare_work.prepare("09", self.base / "attempt/deep/work", self.root)
        self.assertEqual((work / "shared/case/input.txt").read_text(), "original input\n")
        self.assertEqual({path.relative_to(work).as_posix() for path in work.rglob("*") if path.is_file()}, {"shared/case/input.txt", "shared/controls/input.txt"})

    def test_missing_control_holds_before_destination_creation(self):
        module = self.module("05")
        (module / "scripts/orchestrate.py").unlink()
        work = self.base / "attempt/work"
        with self.assertRaisesRegex(ValueError, "required source"):
            prepare_work.prepare("05", work, self.root)
        self.assertFalse(work.exists())
        self.assertFalse(work.parent.exists())

    def test_linked_source_and_broken_destination_link_refuse(self):
        module = self.module("03")
        secret = self.base / "outside.txt"
        secret.write_text("outside", encoding="utf-8")
        (module / "shared/vault/link.txt").symlink_to(secret)
        with self.assertRaisesRegex(ValueError, "linked"):
            prepare_work.prepare("03", self.base / "work", self.root)
        self.assertFalse((self.base / "work").exists())
        (self.base / "broken").symlink_to(self.base / "absent")
        with self.assertRaises(FileExistsError):
            prepare_work.prepare("03", self.base / "broken", self.root)
        self.assertTrue((self.base / "broken").is_symlink())

    def test_module_03_prepares_the_vault_and_the_connection_files(self):
        module = self.module("03")
        (module / "shared/mcp/mcp.template.json").write_text('{"mcpServers": {"vault": {"args": ["{{WORK}}/shared/mcp/vault_mcp.py", "--root", "{{WORK}}/vault"]}}}', encoding="utf-8")
        (module / "shared/mcp/AUTHORITY.template.md").write_text("# Authority\n", encoding="utf-8")
        work = prepare_work.prepare("03", self.base / "work with spaces", self.root)
        self.assertEqual((work / "vault/input.txt").read_text(), "original input\n")
        self.assertTrue((work / "shared/mcp/input.txt").is_file() and (work / "shared/prompts/input.txt").is_file())
        self.assertEqual([path for path in (work / "vault/Drafts").iterdir()], [])
        self.assertTrue((work / "vault/Estimate/Releasable").is_dir())
        entry = json.loads((work / "mcp.json").read_text(encoding="utf-8"))["mcpServers"]["vault"]["args"]
        self.assertEqual(entry, [str(work / "shared/mcp/vault_mcp.py"), "--root", str(work / "vault")])
        self.assertEqual((work / "AUTHORITY.md").read_text(), "# Authority\n")
        self.assertEqual(prepare_work.next_arguments("03")[1:], ["shared/mcp/mcp_inspect.py", "--config", "mcp.json"])

    def test_module_07_excludes_unpublished_inputs_and_preserves_source_bytes(self):
        module = self.module("07")
        for relative in ("shared/controls/CONTRACT.md", "shared/controls/router-private.json",
                         "shared/controls/compare-receipts.js", "shared/batch/answer.csv"):
            target = module / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("private", encoding="utf-8")
        work = prepare_work.prepare("07", self.base / "browser work", self.root)
        copied = {p.relative_to(work).as_posix() for p in work.rglob("*") if p.is_file()}
        self.assertEqual(copied, {"shared/batch/wave1.csv", "shared/SHEET_RULES.md", "scripts/check_sheet.py"})
        for relative in copied:
            self.assertEqual((work / relative).read_bytes(), (module / relative).read_bytes())
        self.assertTrue((work / "out").is_dir())
        self.assertEqual(list((work / "out").iterdir()), [])
        self.assertEqual(prepare_work.next_arguments("07"), [])

    def test_module_07_missing_or_linked_download_holds_before_creation(self):
        module = self.module("07")
        source = module / "shared/SHEET_RULES.md"
        source.unlink()
        work = self.base / "attempt/work"
        with self.assertRaisesRegex(ValueError, "SHEET_RULES.md"):
            prepare_work.prepare("07", work, self.root)
        self.assertFalse(work.parent.exists())
        source.symlink_to(module / "shared/batch/wave1.csv")
        with self.assertRaisesRegex(ValueError, "SHEET_RULES.md"):
            prepare_work.prepare("07", work, self.root)
        self.assertFalse(work.parent.exists())

    def test_noncanonical_module_ids_refuse(self):
        for module_id in ("2", "00", "01", "10", " 02", "02 ", "../02"):
            with self.subTest(module_id=module_id), self.assertRaises(ValueError):
                prepare_work.prepare(module_id, self.base / "work", self.root)
        self.assertFalse((self.base / "work").exists())


if __name__ == "__main__":
    unittest.main()
