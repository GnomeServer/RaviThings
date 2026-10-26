#!/usr/bin/env python3
"""Public-CLI readiness behavior. Disk fixtures never establish a GUI observation."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
HELPER = MODULE / "scripts/obsidian_readiness.py"
SUCCESS = "PASS: Obsidian file round-trip; GUI observation still required"


class ObsidianReadinessBehavior(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="obsidian-readiness-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "external practice with spaces"

    def cli(self, command, root=None):
        environment = dict(os.environ)
        environment.pop("OPENROUTER_API_KEY", None)
        return subprocess.run(
            [sys.executable, str(HELPER), command, "--root", str(root or self.root)],
            cwd=self.base,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def hold(self, result):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("HOLD:", result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn(SUCCESS, result.stdout + result.stderr)

    def files(self, root=None):
        directory = root or self.root
        return {
            path.relative_to(directory).as_posix(): path.read_bytes()
            for path in directory.rglob("*") if path.is_file() and not path.is_symlink()
        }

    def assert_preserved(self, before, root=None):
        after = self.files(root)
        for name, contents in before.items():
            self.assertIn(name, after, f"existing file removed: {name}")
            self.assertEqual(after[name], contents, f"existing file changed: {name}")

    def initialize(self):
        self.success(self.cli("initialize"))
        self.assertTrue(self.files(), "initialize created no practice files")

    def token(self):
        source = (self.root / "vault/Token.md").read_text(encoding="utf-8")
        tokens = re.findall(r"^[0-9a-f]{32}$", source, re.MULTILINE)
        self.assertEqual(len(tokens), 1, "source must expose one current identity token")
        return tokens[0]

    def reply(self, text=None):
        # An explicitly synthetic disk edit; this is never evidence of GUI use.
        (self.root / "vault/Reply.md").write_text(
            self.token() + "\n" if text is None else text, encoding="utf-8"
        )

    def recorded_check(self, status):
        before = self.files()
        result = self.cli("check")
        if status == 0:
            self.success(result)
            self.assertIn(SUCCESS, result.stdout)
        else:
            self.hold(result)
        self.assert_preserved(before)
        added = set(self.files()) - set(before)
        self.assertEqual(len(added), 1, "each completed check needs its own record")
        name = added.pop()
        self.assertTrue(name.startswith("observations/check-"), name)
        record = json.loads((self.root / name).read_text(encoding="utf-8"))
        self.assertEqual(record["operation"], "check")
        self.assertEqual(record["exit_code"], status)
        self.assertIs(record["gui_observed"], False)
        self.assertIs(record["gui_observation_required"], True)
        self.assertEqual(record["root"], str(self.root.resolve()))
        return record

    def test_initialize_links_resolve_token_is_random_and_reply_is_blank(self):
        self.initialize()
        vault = self.root / "vault"
        self.assertEqual((vault / "Reply.md").read_bytes(), b"")
        start = (vault / "Start.md").read_text(encoding="utf-8")
        source = (vault / "Token.md").read_text(encoding="utf-8")
        start_links = set(re.findall(r"\[\[([^]|]+)(?:\|[^]]+)?\]\]", start))
        token_links = set(re.findall(r"\[\[([^]|]+)(?:\|[^]]+)?\]\]", source))
        self.assertIn("Token", start_links)
        self.assertIn("Start", token_links)
        self.assertIn("Reply", start_links | token_links)
        for target in start_links | token_links:
            self.assertTrue((vault / f"{target}.md").is_file(), target)
        record = json.loads((self.root / "expected/000001.json").read_text())
        self.assertEqual(record["token"], self.token())
        self.assertEqual(record["generation"], 1)
        self.assertEqual(record["root"], str(self.root.resolve()))
        self.assertIsNone(record["previous_sha256"])
        self.assertFalse(list(vault.rglob("*.json")), "machine records must stay outside the vault")
        other = self.base / "independent attempt"
        self.success(self.cli("initialize", other))
        other_record = json.loads((other / "expected/000001.json").read_text())
        self.assertNotEqual(record["token"], other_record["token"])

    def test_blank_wrong_and_extra_text_replies_hold_then_exact_token_passes(self):
        self.initialize()
        for text in ("", "wrong-token\n", self.token() + "\nextra text\n", " " + self.token()):
            with self.subTest(reply=text):
                self.reply(text)
                self.recorded_check(1)
        for ending in ("", "\n", "\r\n"):
            with self.subTest(ending=repr(ending)):
                (self.root / "vault/Reply.md").write_bytes((self.token() + ending).encode())
                self.recorded_check(0)

    def test_success_record_binds_actual_file_bytes_and_expected_identity(self):
        self.initialize()
        self.reply()
        record = self.recorded_check(0)
        expected = (self.root / "expected/000001.json").read_bytes()
        self.assertEqual(record["expected_sha256"], hashlib.sha256(expected).hexdigest())
        self.assertEqual(record["generation"], 1)
        self.assertEqual(set(record["files"]), {"Start.md", "Token.md", "Reply.md"})
        for name, identity in record["files"].items():
            data = (self.root / "vault" / name).read_bytes()
            self.assertEqual(identity["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(identity["size"], len(data))
        self.recorded_check(0)  # same bytes still require a distinct observation

    def test_refresh_rotates_source_preserves_reply_and_old_records(self):
        self.initialize()
        self.reply()
        self.recorded_check(0)
        old_token = self.token()
        before = self.files()
        self.success(self.cli("refresh"))
        self.assert_preserved({name: data for name, data in before.items()
                               if name != "vault/Token.md"})
        self.assertNotEqual(self.token(), old_token)
        self.assertEqual((self.root / "vault/Reply.md").read_text(), old_token + "\n")
        first = self.root / "expected/000001.json"
        next_record = json.loads((self.root / "expected/000002.json").read_text())
        self.assertEqual(next_record["generation"], 2)
        self.assertEqual(next_record["token"], self.token())
        self.assertEqual(next_record["previous_sha256"], hashlib.sha256(first.read_bytes()).hexdigest())
        self.recorded_check(1)  # an old correct reply cannot pass after refresh
        self.reply()
        self.assertEqual(self.recorded_check(0)["generation"], 2)
        # A later CLI process reads saved bytes, independently of app metadata.
        config = self.root / "vault/.obsidian"
        config.mkdir()
        (config / "workspace.json").write_text('{"synthetic_test": true}\n')
        self.recorded_check(0)

    def test_missing_or_redirected_link_holds_without_repairing_learner_bytes(self):
        self.initialize()
        self.reply()
        start = self.root / "vault/Start.md"
        original = start.read_text(encoding="utf-8")
        for replacement in ("Token", "[[Missing]]", "[[../outside]]"):
            with self.subTest(replacement=replacement):
                start.write_text(original.replace("[[Token]]", replacement), encoding="utf-8")
                self.recorded_check(1)
        start.write_text(original, encoding="utf-8")
        self.recorded_check(0)

    def test_source_token_tampering_holds_even_if_reply_matches_tampered_source(self):
        self.initialize()
        original = self.token()
        wrong = ("0" if original[0] != "0" else "1") + original[1:]
        source = self.root / "vault/Token.md"
        source.write_text(source.read_text().replace(original, wrong), encoding="utf-8")
        self.reply(wrong + "\n")
        self.recorded_check(1)
        before = self.files()
        self.hold(self.cli("refresh"))
        self.assertEqual(self.files(), before, "failed refresh must not rotate damaged content")

    def test_missing_required_files_hold_and_check_records_preserve_failure(self):
        self.initialize()
        self.reply()
        for relative in ("vault/Start.md", "vault/Token.md", "vault/Reply.md", "expected/000001.json"):
            with self.subTest(relative=relative):
                path = self.root / relative
                saved = path.read_bytes()
                path.unlink()
                record = self.recorded_check(1)
                named_failure = path.parent if relative.startswith("expected/") else path
                self.assertIn(str(named_failure), record["result"])
                self.assertFalse(path.exists(), "check must not silently recreate inputs")
                path.write_bytes(saved)
        self.recorded_check(0)

    def test_invalid_expected_records_hold_without_overwriting_them(self):
        self.initialize()
        self.reply()
        path = self.root / "expected/000001.json"
        original = path.read_bytes()
        valid = json.loads(original)
        wrong_root = dict(valid, root=str(self.base / "another root"))
        wrong_generation = dict(valid, generation=2)
        duplicates = original.decode().replace('"generation": 1', '"generation": 1, "generation": 1')
        for broken in (b"{", b"[]", json.dumps(wrong_root).encode(),
                       json.dumps(wrong_generation).encode(), duplicates.encode()):
            with self.subTest(broken=broken):
                path.write_bytes(broken)
                self.recorded_check(1)
                before = self.files()
                self.hold(self.cli("refresh"))
                self.assertEqual(self.files(), before)
        path.write_bytes(original)
        self.recorded_check(0)

    def test_changed_prior_expected_generation_breaks_refresh_chain(self):
        self.initialize()
        self.success(self.cli("refresh"))
        self.reply()
        self.recorded_check(0)
        first = self.root / "expected/000001.json"
        original = first.read_bytes()
        first.write_bytes(original + b"\n")
        self.recorded_check(1)
        first.write_bytes(original)
        self.recorded_check(0)

    def test_initialize_refuses_existing_attempt_without_overwrite(self):
        self.initialize()
        before = self.files()
        self.hold(self.cli("initialize"))
        self.assertEqual(self.files(), before)

    def test_initialize_preserves_unrelated_existing_directory_and_file(self):
        self.root.mkdir()
        (self.root / "personal.md").write_text("Keep this note.\n", encoding="utf-8")
        before = self.files()
        self.hold(self.cli("initialize"))
        self.assertEqual(self.files(), before)
        existing_file = self.base / "ordinary-file"
        existing_file.write_bytes(b"keep ordinary file\n")
        self.hold(self.cli("initialize", existing_file))
        self.assertEqual(existing_file.read_bytes(), b"keep ordinary file\n")

    def test_missing_root_is_a_named_hold_without_creation(self):
        for command in ("refresh", "check"):
            with self.subTest(command=command):
                result = self.cli(command)
                self.hold(result)
                self.assertFalse(self.root.exists())

    def test_invalid_command_is_usage_error_without_creation(self):
        result = self.cli("not-a-command")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(self.root.exists())
        self.assertNotIn("Traceback", result.stderr)

    def test_initialize_refuses_dangling_root_link_without_creating_target(self):
        target = self.base / "absent target"
        try:
            self.root.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"filesystem cannot create test symlink: {error}")
        self.hold(self.cli("initialize"))
        self.assertTrue(self.root.is_symlink())
        self.assertFalse(target.exists())

    def test_linked_reply_is_rejected_without_touching_external_file(self):
        self.initialize()
        outside = self.base / "personal-reply.md"
        contents = (self.token() + "\n").encode()
        outside.write_bytes(contents)
        reply = self.root / "vault/Reply.md"
        reply.unlink()
        try:
            reply.symlink_to(outside)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"filesystem cannot create test symlink: {error}")
        self.recorded_check(1)
        before = self.files()
        self.hold(self.cli("refresh"))
        self.assertEqual(self.files(), before)
        self.assertTrue(reply.is_symlink())
        self.assertEqual(outside.read_bytes(), contents)

    def test_existing_operation_reservation_preserves_attempt(self):
        self.initialize()
        self.reply()
        reservation = self.root / ".readiness-operation"
        reservation.mkdir()
        (reservation / "owner.txt").write_text("another operation owns this reservation\n")
        before = self.files()
        for command in ("check", "refresh"):
            with self.subTest(command=command):
                self.hold(self.cli(command))
                self.assertEqual(self.files(), before)
                self.assertTrue(reservation.is_dir())

    def test_checkout_destination_holds_without_creating_practice_files(self):
        checkout = self.base / "disposable-checkout"
        checkout.mkdir()
        (checkout / ".git").mkdir()
        target = checkout / "practice"
        self.hold(self.cli("initialize", target))
        self.assertFalse(target.exists())
        self.assertEqual(list(checkout.iterdir()), [checkout / ".git"])


if __name__ == "__main__":
    unittest.main()
