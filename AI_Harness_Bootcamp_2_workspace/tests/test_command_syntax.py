#!/usr/bin/env python3
"""Behavioral regressions for complete, non-executing command-fence parsing."""
from pathlib import Path
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_command_syntax as syntax


class FenceTests(unittest.TestCase):
    def test_nested_example_is_not_a_runnable_fence_or_heading(self):
        text = "# Actual heading\n````markdown\n# False heading\n```bash\nnot valid }\n```\n````\n~~~sh\ntrue\n~~~\n"
        fences = syntax.extract_fences(text, "procedure.md")
        self.assertEqual([(f.heading, f.language, f.number, f.source_line) for f in fences], [("Actual heading", "sh", 2, 9)])

    def test_shorter_delimiter_and_payload_headings_preserve_here_document(self):
        text = "## Run\n````bash\ncat <<'PAYLOAD'\n# Not a heading\n```\n} invalid shell payload\nPAYLOAD\n````\n### Next\n```sh\ntrue\n```\n"
        fences = syntax.extract_fences(text, "procedure.md")
        self.assertEqual(fences[0].body, "cat <<'PAYLOAD'\n# Not a heading\n```\n} invalid shell payload\nPAYLOAD\n")
        self.assertEqual(fences[1].heading, "Run / Next")
        self.assertEqual(fences[1].source_line, 11)

    def test_unclosed_non_shell_fence_cannot_hide_later_commands(self):
        with self.assertRaisesRegex(ValueError, r"procedure.md:2: unclosed fence #1"):
            syntax.extract_fences("# Run\n````text\n```sh\ntrue\n```\n", "procedure.md")


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="course-parser-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.environment = syntax.parser_environment(self.directory)

    def executable(self, name):
        path = shutil.which(name)
        self.assertIsNotNone(path, f"required parser missing: {name}")
        return path

    def test_shell_parse_never_executes_here_document_or_substitution(self):
        marker = self.directory / "must-not-exist"
        body = f"printf '%s' \"$(touch '{marker}')\"\ncat <<'DATA'\n}} not shell syntax\nDATA\n"
        for name in ("bash", "zsh", "sh"):
            with self.subTest(parser=name):
                self.assertEqual(syntax.parse_shell(name, self.executable(name), body, self.environment), [])
        self.assertFalse(marker.exists(), "syntax checking executed a command substitution")

    def test_separate_fences_cannot_close_each_others_braces(self):
        blocks = syntax.extract_fences("# Prepare\n```bash\nfunction prepare() {\n  true\n```\n## Close\n```bash\n}\n```\n", "guide.md")
        for name in ("bash", "zsh"):
            for block in blocks:
                with self.subTest(parser=name, fence=block.number):
                    errors = syntax.parse_shell(name, self.executable(name), block.body, self.environment)
                    self.assertTrue(errors, "independent malformed fence was accepted")
                    receipt = syntax.diagnostic(block, name, errors[0])
                    self.assertEqual((receipt["file"], receipt["heading"], receipt["fence"]), ("guide.md", block.heading, block.number))
                    self.assertEqual(receipt["line"], block.source_line + errors[0]["line"] - 1)

    def test_powershell_here_strings_and_call_operator_without_execution(self):
        name = "powershell.exe" if os.name == "nt" else "pwsh"
        marker = str(self.directory / "not written.txt").replace("'", "''")
        bodies = [
            f"$payload = @'\n}} not PowerShell syntax\n'@\nSet-Content -LiteralPath '{marker}' -Value $payload\n& $PY -c 'print(1)'\n",
            '"$PY" -c "print(1)"\n',
            "function unfinished {\n",
        ]
        fences = [syntax.Fence("native guide.md", "Run", i + 1, "powershell", 1, 2, body) for i, body in enumerate(bodies)]
        result = syntax.parse_powershell(self.executable(name), fences, self.environment, self.directory)
        self.assertEqual(result["results"][0]["errors"], [])
        self.assertTrue(result["results"][1]["errors"], "missing call operator was accepted")
        self.assertTrue(result["results"][2]["errors"], "missing closing brace was accepted")
        self.assertFalse((self.directory / "not written.txt").exists(), "ParseInput executed the source")


if __name__ == "__main__":
    unittest.main()
