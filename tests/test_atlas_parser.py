"""Tests for the atlas-chat MAP command extractor.

Verifies extract_map_actions() correctly parses:
  - MAP_CMD: on a single line with inline JSON
  - MAP_CMD: with JSON pretty-printed across multiple lines
  - ```json ... ``` markdown fenced code blocks with action commands
  - ``` ... ``` fenced blocks without a language tag
  - Mixed formats in the same response
  - Streaming partial-state handling (unclosed fences, incomplete JSON)
  - Non-action code blocks (must be left alone)

Run with: python3 tests/test_atlas_parser.py
"""
import os
import sys
import unittest

# Allow importing test_atlas_server from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import without running the server — we only need the parser
# The module has top-level code that connects to env-configured clients,
# so we mock/guard imports if needed.
os.environ.setdefault("SITE_PASSWORD", "")
import test_atlas_server as tas  # noqa: E402


class TestExtractMapActions(unittest.TestCase):
    # ─── MAP_CMD: single-line format (the happy path) ───────────────

    def test_single_line_map_cmd(self):
        text = 'Here is the result.\nMAP_CMD:{"action":"fly_to","lat":39.5,"lon":-105.0}\nDone.'
        cleaned, cmds = tas.extract_map_actions(text, final=True)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["action"], "fly_to")
        self.assertEqual(cmds[0]["lat"], 39.5)
        self.assertNotIn("MAP_CMD:", cleaned)
        # The surrounding prose survives
        self.assertIn("Here is the result.", cleaned)
        self.assertIn("Done.", cleaned)

    def test_map_cmd_at_start_of_text(self):
        text = 'MAP_CMD:{"action":"reset"}\nAll contractors shown.'
        cleaned, cmds = tas.extract_map_actions(text, final=True)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["action"], "reset")
        self.assertEqual(cleaned.strip(), "All contractors shown.")

    def test_multiple_map_cmds(self):
        text = (
            "First I'll reset.\n"
            'MAP_CMD:{"action":"reset"}\n'
            "Then filter.\n"
            'MAP_CMD:{"action":"filter","field":"state","value":"CO","op":"eq"}\n'
            "There you go."
        )
        cleaned, cmds = tas.extract_map_actions(text, final=True)
        self.assertEqual(len(cmds), 2)
        self.assertEqual(cmds[0]["action"], "reset")
        self.assertEqual(cmds[1]["action"], "filter")
        self.assertNotIn("MAP_CMD:", cleaned)

    # ─── MAP_CMD: multi-line pretty-printed JSON (H3) ───────────────

    def test_multiline_map_cmd_pretty_printed(self):
        text = (
            "Flying to Colorado.\n"
            "MAP_CMD:{\n"
            '  "action": "fly_to",\n'
            '  "lat": 39.5,\n'
            '  "lon": -105.0,\n'
            '  "zoom": 7\n'
            "}\n"
            "Look at that view."
        )
        cleaned, cmds = tas.extract_map_actions(text, final=True)
        self.assertEqual(len(cmds), 1, f"expected 1 cmd, got {len(cmds)} from cleaned={cleaned!r}")
        self.assertEqual(cmds[0]["action"], "fly_to")
        self.assertEqual(cmds[0]["zoom"], 7)
        self.assertNotIn("MAP_CMD:", cleaned)
        self.assertNotIn('"action"', cleaned)
        self.assertIn("Flying to Colorado.", cleaned)
        self.assertIn("Look at that view.", cleaned)

    # ─── Markdown ```json``` fenced blocks (H4) ─────────────────────

    def test_markdown_json_block_with_lang_tag(self):
        text = (
            "The system cannot share classified details.\n"
            "```json\n"
            "{\n"
            '  "action": "fly_to",\n'
            '  "lat": 39.5,\n'
            '  "lon": -105.0,\n'
            '  "zoom": 4\n'
            "}\n"
            "```\n"
            "But here's the map."
        )
        cleaned, cmds = tas.extract_map_actions(text, final=True)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["action"], "fly_to")
        self.assertEqual(cmds[0]["zoom"], 4)
        self.assertNotIn("```", cleaned)
        self.assertNotIn('"action"', cleaned)
        self.assertIn("The system cannot share classified details.", cleaned)
        self.assertIn("But here's the map.", cleaned)

    def test_markdown_json_block_without_lang_tag(self):
        text = (
            "Here:\n"
            "```\n"
            '{"action":"reset"}\n'
            "```\n"
            "Done."
        )
        cleaned, cmds = tas.extract_map_actions(text, final=True)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["action"], "reset")
        self.assertNotIn("```", cleaned)

    def test_non_action_code_block_is_preserved(self):
        text = (
            "Here's a Python snippet:\n"
            "```python\n"
            "print('hello')\n"
            "```\n"
            "And a map action:\n"
            'MAP_CMD:{"action":"reset"}\n'
            "Done."
        )
        cleaned, cmds = tas.extract_map_actions(text, final=True)
        # Only the MAP_CMD is extracted; the Python snippet stays in text
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["action"], "reset")
        self.assertIn("```python", cleaned)
        self.assertIn("print('hello')", cleaned)
        self.assertNotIn("MAP_CMD:", cleaned)

    def test_mixed_formats(self):
        text = (
            "First reset:\n"
            'MAP_CMD:{"action":"reset"}\n'
            "Then filter:\n"
            "```json\n"
            '{"action":"filter","field":"state","value":"CO","op":"eq"}\n'
            "```\n"
            "And fly:\n"
            "MAP_CMD:{\n"
            '  "action": "fly_to",\n'
            '  "lat": 39.5,\n'
            '  "lon": -105.0\n'
            "}\n"
            "Done."
        )
        cleaned, cmds = tas.extract_map_actions(text, final=True)
        self.assertEqual(len(cmds), 3)
        self.assertEqual(cmds[0]["action"], "reset")
        self.assertEqual(cmds[1]["action"], "filter")
        self.assertEqual(cmds[2]["action"], "fly_to")
        self.assertNotIn("MAP_CMD:", cleaned)
        self.assertNotIn("```", cleaned)

    # ─── Streaming partial-state handling ───────────────────────────

    def test_partial_unclosed_fence_is_held_back(self):
        # Streaming: received an opening fence but no close yet
        text = "Here:\n```json\n{\"action\":\"fly_to\""
        cleaned, cmds = tas.extract_map_actions(text, final=False)
        # No command extracted yet — wait for more tokens
        self.assertEqual(len(cmds), 0)

    def test_incomplete_map_cmd_multiline_is_held_back(self):
        text = 'Doing it.\nMAP_CMD:{\n  "action": "fly_to",\n  "lat":'
        cleaned, cmds = tas.extract_map_actions(text, final=False)
        self.assertEqual(len(cmds), 0)

    def test_complete_after_being_held(self):
        # Simulate two rounds: first has partial, second has complete
        text1 = 'Doing it.\nMAP_CMD:{\n  "action": "fly_to",\n  "lat":'
        _, cmds1 = tas.extract_map_actions(text1, final=False)
        self.assertEqual(len(cmds1), 0)

        text2 = text1 + ' 39.5,\n  "lon": -105.0\n}\nDone.'
        cleaned, cmds2 = tas.extract_map_actions(text2, final=False)
        self.assertEqual(len(cmds2), 1)
        self.assertEqual(cmds2[0]["action"], "fly_to")
        self.assertNotIn("MAP_CMD:", cleaned)

    # ─── Regression: the real-world payload from the bug report ─────

    def test_real_world_bug_report_payload(self):
        """The exact shape the user reported seeing verbatim in chat."""
        text = (
            "The intelligence system tracks network exposure and "
            "vulnerabilities, not classified program details.\n"
            "```json\n"
            "{\n"
            '"action": "fly_to",\n'
            '"lat": 39.5,\n'
            '"lon": -105.0,\n'
            '"zoom": 4\n'
            "}\n"
            "```"
        )
        cleaned, cmds = tas.extract_map_actions(text, final=True)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["action"], "fly_to")
        self.assertEqual(cmds[0]["lat"], 39.5)
        self.assertEqual(cmds[0]["zoom"], 4)
        # The prose survives, the JSON block is gone
        self.assertIn("intelligence system", cleaned)
        self.assertNotIn("```", cleaned)
        self.assertNotIn('"action"', cleaned)

    # ─── Edge cases ──────────────────────────────────────────────────

    def test_empty_text(self):
        cleaned, cmds = tas.extract_map_actions("", final=True)
        self.assertEqual(cleaned, "")
        self.assertEqual(cmds, [])

    def test_plain_text_no_commands(self):
        text = "This is just some text without any map actions."
        cleaned, cmds = tas.extract_map_actions(text, final=True)
        self.assertEqual(cleaned, text)
        self.assertEqual(cmds, [])

    def test_map_cmd_with_string_containing_braces(self):
        # Make sure brace-matching handles strings correctly
        text = 'MAP_CMD:{"action":"filter","value":"a {weird} string"}\n'
        cleaned, cmds = tas.extract_map_actions(text, final=True)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0]["value"], "a {weird} string")

    def test_invalid_json_in_map_cmd_is_dropped(self):
        text = 'Before\nMAP_CMD:{this is not json}\nAfter'
        cleaned, cmds = tas.extract_map_actions(text, final=True)
        # Invalid JSON is silently dropped, the rest of the text survives
        self.assertEqual(len(cmds), 0)
        self.assertIn("Before", cleaned)
        self.assertIn("After", cleaned)
        self.assertNotIn("MAP_CMD:", cleaned)


class TestBraceBalancer(unittest.TestCase):
    def test_simple_object(self):
        self.assertEqual(tas._find_balanced_json_end('{"a": 1}', 0), 7)

    def test_nested_object(self):
        s = '{"a": {"b": 2}}'
        self.assertEqual(tas._find_balanced_json_end(s, 0), len(s) - 1)

    def test_string_with_brace(self):
        s = '{"a": "}"}'
        self.assertEqual(tas._find_balanced_json_end(s, 0), len(s) - 1)

    def test_escaped_quote_in_string(self):
        s = '{"a": "\\"}"}'
        self.assertEqual(tas._find_balanced_json_end(s, 0), len(s) - 1)

    def test_unbalanced_returns_negative(self):
        self.assertEqual(tas._find_balanced_json_end('{"a": 1', 0), -1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
