#!/usr/bin/env python3
"""Deterministic launcher regressions. Synthetic receipts never count as live proof."""
from __future__ import annotations
import copy
import importlib.util
import json
import os
import subprocess
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "shared/run_omp.py"
SPEC = importlib.util.spec_from_file_location("run_omp", LAUNCHER)
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)

SYNTH_OMP_VERSION = "omp/18.3.5"


class LauncherBehavior(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="course-launch-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.work = self.base / "work"
        self.work.mkdir()
        (self.work / "source.txt").write_text("input", encoding="utf-8")
        self.prompt = self.base / "prompt.md"
        self.prompt.write_text("Read source.txt without changing it.", encoding="utf-8")
        self.evidence = self.base / "evidence"

    def cli(self, extra=(), key=""):
        environment = dict(os.environ, OPENROUTER_API_KEY=key)
        return subprocess.run([sys.executable, str(LAUNCHER), "--workdir", str(self.work), "--prompt", str(self.prompt), "--evidence", str(self.evidence), *extra], capture_output=True, text=True, env=environment, cwd=self.base, timeout=20)

    def test_missing_key_stops_without_runtime_outputs_or_work_mutation(self):
        before = runtime.work_snapshot(self.work)
        result = self.cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("OPENROUTER_API_KEY unavailable", result.stderr)
        self.assertFalse(self.evidence.exists())
        self.assertEqual(runtime.work_snapshot(self.work), before)

    def test_missing_empty_instruction_and_permission_conflicts_are_prerequisites(self):
        empty = self.base / "empty.md"
        empty.write_text(" \n", encoding="utf-8")
        for args in (("--instruction", str(self.base / "missing")), ("--instruction", str(empty)), ("--allow-write", "../escape"), ("--allow-write", "source.txt"), ("--mcp-config", "missing.json"), ("--authority", "missing.md"), ("--mcp-config", "missing.json", "--authority", "missing.md", "--allow-write", "new.txt")):
            with self.subTest(args=args):
                result = self.cli(args)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertFalse(self.evidence.exists())

    def test_declared_policy_exact_schema_and_unknown_keys(self):
        declaration = self.work / "AGENT_POLICY.md"
        declaration.write_text("# Policy\n\n```json\n" + json.dumps(runtime.DECLARATION) + "\n```\n", encoding="utf-8")
        self.assertEqual(runtime.parse_declaration(declaration), runtime.DECLARATION)
        for update in ({"extra": True}, {"write_root": "."}, {"tools": ["course_read"]}, {"yolo": True}):
            changed = {**runtime.DECLARATION, **update}
            declaration.write_text("```json\n" + json.dumps(changed) + "\n```\n", encoding="utf-8")
            with self.subTest(update=update), self.assertRaises(ValueError):
                runtime.parse_declaration(declaration)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            runtime.strict_json('{"enabled":true,"enabled":false}')

    def test_isolation_removes_author_state_and_keeps_only_course_credential(self):
        isolated = self.base / "runtime"
        isolated.mkdir()
        poison = {"PI_CODING_AGENT_DIR": "/author", "OMP_PROFILE": "author", "ANTHROPIC_API_KEY": "direct", "OPENAI_API_KEY": "direct", "OPENROUTER_BASE_URL": "bad", "COURSE_GUARD_POLICY": "bad", "HOME": "/author", "APPDATA": "/author", "LANG": "C", "HTTPS_PROXY": "http://proxy.invalid"}
        with patch.dict(os.environ, poison):
            environment = runtime.isolated_env(isolated, self.evidence / "policy.json", "synthetic-key")
        self.assertFalse(set(poison).intersection(environment) - {"HOME", "APPDATA", "LANG", "HTTPS_PROXY", "COURSE_GUARD_POLICY"})
        self.assertEqual(environment["OPENROUTER_API_KEY"], "synthetic-key")
        self.assertEqual(environment["COURSE_GUARD_POLICY"], str(self.evidence / "policy.json"))
        for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
            self.assertTrue(Path(environment[name]).is_relative_to(isolated))

    def receipt(self):
        policy = dict.fromkeys(runtime.POLICY_KEYS)
        policy.update(schema_version=1, run_id="synthetic", work_root=str(self.work), profile="read", tools=["course_read"], write_files=[], write_root=None, provider=runtime.PROVIDER, model=runtime.MODEL, omp_version=SYNTH_OMP_VERSION)
        assistant = {"role": "assistant", "provider": runtime.PROVIDER, "model": runtime.MODEL, "stopReason": "stop", "content": [{"type": "text", "text": "Source describes custody only."}]}
        events = [{"type": "agent_start"}, {"type": "message_end", "message": assistant}, {"type": "agent_end", "isTerminal": True, "messages": [assistant]}]
        guard = [{"type": "guard_ready", "run_id": "synthetic", "provider": runtime.PROVIDER, "model": runtime.MODEL, "active_tools": ["course_read"]}, {"type": "provider_request", "run_id": "synthetic", "provider": runtime.PROVIDER, "model": runtime.MODEL}, {"type": "guard_end", "run_id": "synthetic", "ready": True, "failed": False, "provider_requests": 1}]
        before = runtime.snapshot(self.work, [self.base / "outside.txt"])
        return policy, events, guard, {"before": before, "after": copy.deepcopy(before)}

    def test_incomplete_error_duplicate_or_drift_receipts_hold(self):
        policy, events, guard, snapshots = self.receipt()
        self.assertEqual(runtime.validate_run(policy, events, guard, snapshots, 0), [])
        for reason in ("no-terminal", "duplicate-terminal", "truncated", "model-drift", "missing-guard", "retry", "guard-failed", "request-count", "offline-cutoff"):
            p, e, g, s = copy.deepcopy((policy, events, guard, snapshots))
            if reason == "no-terminal": e[-1]["isTerminal"] = False
            elif reason == "duplicate-terminal": e.append(e[-1])
            elif reason == "truncated": e[1]["message"]["stopReason"] = "length"
            elif reason == "model-drift": e[1]["message"]["model"] = "other"
            elif reason == "missing-guard": g.pop()
            elif reason == "retry": e.insert(1, {"type": "auto_retry_start"})
            elif reason == "guard-failed": g[-1]["failed"] = True
            elif reason == "request-count": g[-1]["provider_requests"] = 2
            elif reason == "offline-cutoff": e = [{"type": "session"}]; g.pop(1); g[-1]["provider_requests"] = 0
            with self.subTest(reason=reason):
                self.assertTrue(runtime.validate_run(p, e, g, s, 0))

    def test_session_completion_timestamp_does_not_mask_terminal_drift(self):
        policy, events, guard, snapshots = self.receipt()
        events[1]["message"] = copy.deepcopy(events[1]["message"])
        events[1]["message"]["completedAt"] = 1790808511557
        self.assertEqual(runtime.validate_run(policy, events, guard, snapshots, 0), [])
        for field, value in (
            ("content", [{"type": "text", "text": "Changed answer"}]),
            ("model", "other"),
            ("stopReason", "error"),
            ("usage", {"cost": {"total": 999}}),
            ("timestamp", 123),
            ("completedAt", 1790808511558),
        ):
            changed = copy.deepcopy(events)
            changed[-1]["messages"][-1][field] = value
            with self.subTest(field=field):
                self.assertIn("terminal and streamed assistant records disagree", runtime.validate_run(policy, changed, guard, snapshots, 0))

    def test_unpaired_calls_and_forbidden_effects_hold(self):
        policy, events, guard, snapshots = self.receipt()
        events[1]["message"]["content"].append({"type": "toolCall", "id": "unpaired", "name": "course_read", "arguments": {"path": "source.txt"}})
        self.assertIn("unmatched assistant calls, executions, or results", runtime.validate_run(policy, events, guard, snapshots, 0))
        policy, events, guard, snapshots = self.receipt()
        snapshots["after"]["work"]["source.txt"]["sha256"] = "changed"
        snapshots["after"]["work"]["release.txt"] = {"type": "file", "sha256": "unreceipted"}
        snapshots["after"]["watch"][str(self.base / "outside.txt")] = {"type": "file", "sha256": "forbidden"}
        errors = runtime.validate_run(policy, events, guard, snapshots, 0)
        self.assertIn("watched target changed", errors)
        self.assertTrue(any("existing input/control" in error for error in errors))
        self.assertTrue(any("unreceipted output" in error for error in errors))

    def test_successful_tool_receipts_bind_execution_identity_path_and_order(self):
        policy, events, guard, snapshots = self.receipt()
        call = {"type": "toolCall", "id": "read-1", "name": "course_read", "arguments": {"path": "source.txt"}}
        assistant = {"role": "assistant", "provider": runtime.PROVIDER, "model": runtime.MODEL, "stopReason": "toolUse", "content": [call]}
        content = [{"type": "text", "text": "input"}]
        events[1:1] = [
            {"type": "message_end", "message": assistant},
            {"type": "tool_execution_start", "toolCallId": "read-1", "toolName": "course_read", "args": call["arguments"]},
            {"type": "tool_execution_end", "toolCallId": "read-1", "toolName": "course_read", "result": {"content": content}, "isError": False},
            {"type": "message_end", "message": {"role": "toolResult", "toolCallId": "read-1", "toolName": "course_read", "content": content, "isError": False}},
        ]
        decision = {"run_id": "synthetic", "type": "decision", "call_id": "read-1", "tool": "course_read", "arguments": call["arguments"], "allow": True, "resolved_path": str(self.work / "source.txt")}
        guard[-1:-1] = [decision, {**decision, "type": "execution_check"}, {"run_id": "synthetic", "type": "executed", "call_id": "read-1", "tool": "course_read", "resolved_path": str(self.work / "source.txt"), "output_sha256": None}]
        self.assertEqual(runtime.validate_run(policy, events, guard, snapshots, 0), [])
        for defect in ("wrong-tool", "wrong-path", "execution-before-authorization", "authorized-outside-read"):
            changed = copy.deepcopy(guard)
            if defect == "wrong-tool": changed[-2]["tool"] = "course_write"
            elif defect == "wrong-path": changed[-2]["resolved_path"] = str(self.base / "outside.txt")
            elif defect == "execution-before-authorization": changed[2:5] = [changed[4], changed[2], changed[3]]
            else:
                for row in changed[2:5]:
                    row["resolved_path"] = str(self.base / "outside.txt")
            with self.subTest(defect=defect):
                self.assertTrue(runtime.validate_run(policy, events, changed, snapshots, 0))

    def test_saved_evidence_rejects_altered_result_hashes_and_later_forbidden_effects(self):
        policy, events, guard, snapshots = self.receipt()
        self.evidence.mkdir()
        overlay = {"retry": {"enabled": False, "modelFallback": False}, "providers": {"cacheWarming": "off"}, "tools": {"approval": {"course_read": "allow"}, "intentTracing": False}}
        (self.evidence / "runtime-config.yml").write_bytes(runtime.json_bytes(overlay))
        policy["runtime_config_sha256"] = runtime.file_hash(self.evidence / "runtime-config.yml")
        (self.evidence / "policy.json").write_bytes(runtime.json_bytes(policy))
        policy_hash = runtime.file_hash(self.evidence / "policy.json")
        for row in guard:
            if row["type"] in {"guard_ready", "guard_end"}:
                row["policy_sha256"] = policy_hash
        for name, rows in (("events", events), ("guard", guard)):
            (self.evidence / f"{name}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        (self.evidence / "snapshots.json").write_bytes(runtime.json_bytes(snapshots))
        result = {"run_id": "synthetic", "provider": runtime.PROVIDER, "model": runtime.MODEL, "omp_version": SYNTH_OMP_VERSION, "status": "PASS", "exit_code": 0, "policy_sha256": policy_hash, "guard_sha256": runtime.file_hash(self.evidence / "guard.jsonl"), "instruction_sha256": None, "declared_policy_sha256": None, "input_sha256": {"source.txt": runtime.file_hash(self.work / "source.txt")}, "output_sha256": {}}
        (self.evidence / "result.json").write_bytes(runtime.json_bytes(result))
        (self.evidence / "response.md").write_text("Source describes custody only.", encoding="utf-8")
        self.assertEqual(runtime.audit_evidence(self.evidence), [])
        (self.evidence / "result.json").write_bytes(runtime.json_bytes({**result, "omp_version": "omp/99.0.0"}))
        self.assertIn("result omp_version differs from policy", runtime.audit_evidence(self.evidence))
        (self.evidence / "result.json").write_bytes(runtime.json_bytes(result))
        (self.evidence / "response.md").write_text("A substituted answer.", encoding="utf-8")
        self.assertIn("saved response differs from final assistant event", runtime.audit_evidence(self.evidence))
        (self.evidence / "response.md").write_text("Source describes custody only.", encoding="utf-8")
        altered = {**result, "input_sha256": {}}
        (self.evidence / "result.json").write_bytes(runtime.json_bytes(altered))
        self.assertIn("input_sha256 differs", runtime.audit_evidence(self.evidence))
        (self.evidence / "result.json").write_bytes(runtime.json_bytes(result))
        (self.base / "outside.txt").write_text("forbidden later effect")
        self.assertTrue(any("watched target changed after" in error for error in runtime.audit_evidence(self.evidence)))

    def test_jsonl_rejects_partial_or_non_event_records(self):
        target = self.base / "stream.jsonl"
        for raw in (b'{"type":"agent_end"}', b'{"type":', b'{}\n', b'\n'):
            target.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                runtime.read_jsonl(target)

    def mcp_receipt(self):
        """A synthetic MCP run: one allowed read, one server refusal, one runtime refusal, one new draft."""
        known = [f"mcp__vault_{name}" for name in ("list_directory", "read_note", "read_multiple_notes", "search_notes", "get_frontmatter", "get_vault_stats", "write_note", "patch_note", "update_frontmatter", "manage_tags", "move_note", "delete_note")]
        allow = ["mcp__vault_read_note", "mcp__vault_write_note"]
        flags = {"read_only": False, "read_prefixes": ["Sources/"], "write_prefixes": ["Drafts/"], "no_overwrite": True, "max_results": 20}
        offered = [name.removeprefix("mcp__vault_") for name in known]
        policy = dict.fromkeys(runtime.POLICY_KEYS)
        policy.update(schema_version=1, run_id="synthetic", work_root=str(self.work), profile="mcp", tools=[], write_files=[], write_root=None, provider=runtime.PROVIDER, model=runtime.MODEL, omp_version=SYNTH_OMP_VERSION)
        policy["mcp"] = {"server": "vault", "script": {"path": "vault_mcp.py", "sha256": "script"}, "phase": "research", "allow_tools": ["read_note", "write_note"], "allow_names": allow, "known_names": known,
                         "read_scope": ["Sources/"], "write_scope": ["Drafts/"], "create_only": True, "flags": flags, "tools_offered": offered}
        policy["snapshot_exclude"] = ["vault/.obsidian"]
        shutil.rmtree(self.work / "vault", ignore_errors=True)
        (self.work / "vault/Sources").mkdir(parents=True)
        (self.work / "vault/Drafts").mkdir()
        (self.work / "vault/Sources/KH-001.md").write_text("source", encoding="utf-8")
        draft = "# finding\n"
        digest = runtime.sha256(draft.encode())
        calls = [("read-1", "mcp__vault_read_note", {"path": "Sources/KH-001.md"}), ("deny-1", "mcp__vault_write_note", {"path": "Sources/KH-001.md", "content": "x", "mode": "overwrite"}),
                 ("gone-1", "mcp__vault_patch_note", {"path": "Sources/KH-001.md", "oldString": "s", "newString": "t"}), ("write-1", "mcp__vault_write_note", {"path": "Drafts/finding.md", "content": draft, "mode": "create"})]
        blocks = [{"type": "toolCall", "id": identifier, "name": name, "arguments": arguments} for identifier, name, arguments in calls]
        assistant = {"role": "assistant", "provider": runtime.PROVIDER, "model": runtime.MODEL, "stopReason": "toolUse", "content": blocks}
        final = {"role": "assistant", "provider": runtime.PROVIDER, "model": runtime.MODEL, "stopReason": "stop", "content": [{"type": "text", "text": "done"}]}
        events = [{"type": "agent_start"}, {"type": "message_end", "message": assistant}]
        failed = {"deny-1": "DENIED: OUTSIDE_WRITE_SCOPE refused", "gone-1": "Tool mcp__vault_patch_note not found"}
        for identifier, name, arguments in calls:
            text = failed.get(identifier, "ok")
            content = [{"type": "text", "text": text}]
            events += [{"type": "tool_execution_start", "toolCallId": identifier, "toolName": name, "args": arguments},
                       {"type": "tool_execution_end", "toolCallId": identifier, "toolName": name, "result": {"content": content}, "isError": identifier in failed},
                       {"type": "message_end", "message": {"role": "toolResult", "toolCallId": identifier, "toolName": name, "content": content, "isError": identifier in failed, "details": {"mcpToolName": name.removeprefix("mcp__vault_")}}}]
        events += [{"type": "message_end", "message": final}, {"type": "agent_end", "isTerminal": True, "messages": [assistant, final]}]
        decisions = [{"run_id": "synthetic", "type": "decision", "call_id": identifier, "tool": name, "arguments": arguments, "allow": True} for identifier, name, arguments in calls if identifier != "gone-1"]
        guard = [{"type": "guard_ready", "run_id": "synthetic", "provider": runtime.PROVIDER, "model": runtime.MODEL, "active_tools": sorted(allow)}, *decisions,
                 {"type": "provider_request", "run_id": "synthetic", "provider": runtime.PROVIDER, "model": runtime.MODEL, "tools": sorted(allow)},
                 {"type": "guard_end", "run_id": "synthetic", "ready": True, "failed": False, "provider_requests": 1}]
        redact = runtime.redact_arguments
        audit = [{"seq": 1, "type": "server_start", "flags": flags, "script_sha256": "script", "tools_offered": offered},
                 {"seq": 2, "type": "tool_call", "tool": "read_note", "arguments": {"path": "Sources/KH-001.md"}, "allowed": True, "is_error": False, "reads": ["Sources/KH-001.md"], "effect": None},
                 {"seq": 3, "type": "tool_call", "tool": "write_note", "arguments": redact(calls[1][2]), "allowed": False, "is_error": True, "reads": [], "effect": None},
                 {"seq": 4, "type": "tool_call", "tool": "write_note", "arguments": redact(calls[3][2]), "allowed": True, "is_error": False, "reads": [], "effect": {"op": "create", "path": "Drafts/finding.md", "sha256_before": None, "sha256_after": digest}}]
        before = runtime.snapshot(self.work, [], ("vault/.obsidian",))
        (self.work / "vault/Drafts/finding.md").write_text(draft, encoding="utf-8")
        after = runtime.snapshot(self.work, [], ("vault/.obsidian",))
        return policy, events, guard, {"before": before, "after": after}, audit

    def test_mcp_receipts_join_each_call_to_the_servers_own_audit_and_the_disk(self):
        policy, events, guard, snapshots, audit = self.mcp_receipt()
        self.assertEqual(runtime.validate_run(policy, events, guard, snapshots, 0, audit), [])
        calls = {block["id"]: block for row in events if row.get("type") == "message_end" for block in row["message"].get("content", []) if block.get("type") == "toolCall"}
        results = {row["message"]["toolCallId"]: row["message"] for row in events if row.get("type") == "message_end" and row["message"].get("role") == "toolResult"}
        ends = {row["toolCallId"]: row for row in events if row.get("type") == "tool_execution_end"}
        decisions = {row["call_id"]: row for row in guard if row["type"] == "decision"}
        records, errors = runtime.join_mcp(policy, calls, results, ends, decisions, audit)
        self.assertEqual(errors, [])
        self.assertEqual([record["classification"] for record in records], ["EXECUTED", "DENIED_BY_SERVER", "DENIED_BY_RUNTIME", "EXECUTED"])
        self.assertEqual(records[3]["effect"]["path"], "Drafts/finding.md")

    def test_mcp_receipts_hold_on_missing_extra_or_contradicting_server_records(self):
        defects = {
            "a successful call with no audit row": ("no matching server audit row", lambda p, e, g, s, a: a.pop(1)),
            "an audit call the harness never made": ("never made", lambda p, e, g, s, a: a.append({"seq": 5, "type": "tool_call", "tool": "read_note", "arguments": {"path": "Sources/KH-002.md"}, "allowed": True, "is_error": False, "reads": [], "effect": None})),
            "a read outside the declared scope": ("outside read_scope", lambda p, e, g, s, a: a[1].update(reads=["Estimate/Calibration.md"])),
            "a server that started with other limits": ("limits that differ", lambda p, e, g, s, a: a[0].update(flags={**a[0]["flags"], "no_overwrite": False})),
            "a server that offered other tools": ("different tool set", lambda p, e, g, s, a: a[0].update(tools_offered=["read_note"])),
            "an overwrite although create_only is declared": ("create_only is declared", lambda p, e, g, s, a: a[3]["effect"].update(op="overwrite")),
            "a write outside the declared folder": ("outside write_scope", lambda p, e, g, s, a: a[3]["effect"].update(path="Estimate/finding.md")),
            "a change to a source note": ("unreceipted vault change", lambda p, e, g, s, a: s["after"]["work"].__setitem__("vault/Sources/KH-001.md", {"type": "file", "sha256": "changed"})),
            "a file nobody receipted": ("unreceipted vault change", lambda p, e, g, s, a: s["after"]["work"].__setitem__("vault/Drafts/stray.md", {"type": "file", "sha256": "stray"})),
            "a provider request that offered an undeclared tool": ("outside the declaration", lambda p, e, g, s, a: g[-2].update(tools=["mcp__vault_read_note", "mcp__vault_write_note", "mcp__vault_delete_note"])),
            "a declared tool that was not active": ("active tools differ", lambda p, e, g, s, a: g[0].update(active_tools=["mcp__vault_read_note"])),
        }
        for label, (fragment, defect) in defects.items():
            policy, events, guard, snapshots, audit = self.mcp_receipt()
            defect(policy, events, guard, snapshots, audit)
            with self.subTest(label):
                errors = runtime.validate_run(policy, events, guard, snapshots, 0, audit)
                self.assertTrue(any(fragment in error for error in errors), f"{label}: {errors}")

    def test_a_revoked_phase_holds_when_any_call_reaches_a_server(self):
        policy, events, guard, snapshots, audit = self.mcp_receipt()
        policy["mcp"].update(phase="revoked", allow_names=[], allow_tools=[], read_scope=[], write_scope=[], create_only=False, server=None, flags=None, script=None, tools_offered=[])
        guard[0]["active_tools"] = []
        guard[-2]["tools"] = []
        self.assertTrue(any("revoked phase executed or reached a tool" in error for error in runtime.validate_run(policy, events, guard, snapshots, 0, audit)))

    def test_completed_revoked_mcp_run_remains_independently_auditable(self):
        config = self.work / "mcp.json"
        authority = self.work / "AUTHORITY.md"
        config.write_text('{"mcpServers": {}}\n', encoding="utf-8")
        declared = {"schema_version": 1, "phase": "revoked", "allow_tools": [], "read_scope": [], "write_scope": [], "create_only": False}
        authority.write_text("```json\n" + json.dumps(declared) + "\n```\n", encoding="utf-8")
        self.prompt.write_text("State that no tools are authorized.", encoding="utf-8")

        def launch(*args, **kwargs):
            policy_file = Path(kwargs["env"]["COURSE_GUARD_POLICY"])
            policy = json.loads(policy_file.read_text(encoding="utf-8"))
            _, events, guard, _ = self.receipt()
            events[1]["message"]["content"] = [{"type": "text", "text": "No tools are authorized."}]
            guard[0]["active_tools"] = []
            guard[1]["tools"] = []
            for row in guard:
                row["run_id"] = policy["run_id"]
                if row["type"] in {"guard_ready", "guard_end"}:
                    row["policy_sha256"] = runtime.file_hash(policy_file)
            Path(policy["guard_log"]).write_text("".join(json.dumps(row) + "\n" for row in guard), encoding="utf-8")
            stream = "".join(json.dumps(row) + "\n" for row in events).encode()
            return SimpleNamespace(returncode=0, communicate=lambda *a, **kw: (stream, b""))

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "synthetic-test-key"}), \
             patch.object(runtime.shutil, "which", return_value="/synthetic/omp"), \
             patch.object(runtime.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="omp/99.2.0\n")), \
             patch.object(runtime.subprocess, "Popen", side_effect=launch):
            self.assertEqual(runtime.main(["--workdir", str(self.work), "--prompt", str(self.prompt), "--evidence", str(self.evidence),
                                           "--mcp-config", str(config), "--authority", str(authority)]), 0)
        self.assertEqual(runtime.audit_evidence(self.evidence), [])
        result = json.loads((self.evidence / "result.json").read_text(encoding="utf-8"))
        result["mcp"]["calls"] = 1
        (self.evidence / "result.json").write_bytes(runtime.json_bytes(result))
        self.assertIn("mcp differs", runtime.audit_evidence(self.evidence))

    def test_a_connection_that_differs_from_its_declaration_is_refused_before_any_model_call(self):
        work = self.base / "mcp-work"
        script = work / "shared/mcp/vault_mcp.py"
        script.parent.mkdir(parents=True)
        script.write_bytes((ROOT / "AI_Harness_Bootcamp_2/module-03-mcp-research/shared/mcp/vault_mcp.py").read_bytes())
        (work / "vault").mkdir()
        declaration = {"schema_version": 1, "phase": "research", "allow_tools": ["read_note", "write_note"], "read_scope": ["Sources/"], "write_scope": ["Drafts/research/"], "create_only": True}
        entry = lambda *flags: {"mcpServers": {"vault": {"type": "stdio", "command": "python", "args": [str(script), "--root", str(work / "vault"), *flags]}}}
        matching = ["--read-prefix", "Sources/", "--write-prefix", "Drafts/research/", "--no-overwrite"]

        def prepare(config, declared=declaration):
            (work / "mcp.json").write_text(json.dumps(config), encoding="utf-8")
            (work / "AUTHORITY.md").write_text("```json\n" + json.dumps(declared) + "\n```\n", encoding="utf-8")
            return runtime.prepare_mcp({"path": str(work / "mcp.json")}, {"path": str(work / "AUTHORITY.md")}, work.resolve())

        self.assertEqual(prepare(entry(*matching))["parsed"]["write_prefixes"], ["Drafts/research/"])
        for label, flags in (("no create-only flag", matching[:-1]), ("a wider read folder", ["--read-prefix", "Sources/", "--read-prefix", "Estimate/", *matching[2:]]), ("no write folder", ["--read-prefix", "Sources/", "--no-overwrite"])):
            with self.subTest(label), self.assertRaisesRegex(ValueError, "limits differ|create_only|read-only"):
                prepare(entry(*flags))
        with self.assertRaisesRegex(ValueError, "program|Python|supplied"):
            prepare({"mcpServers": {"vault": {"type": "stdio", "command": "/bin/sh", "args": [str(script), "--root", str(work / "vault"), *matching]}}})
        with self.assertRaisesRegex(ValueError, "exactly one server"):
            prepare({"mcpServers": {}})
        script.write_text("# edited\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differs from the course"):
            prepare(entry(*matching))

    def test_the_judge_setting_accepts_only_the_pinned_decision_model(self):
        setting = self.base / "JUDGE.yml"
        for text in ("modelRoles:\n  judge: openrouter/typesafe/jev-1.13\n", "# pinned\nmodelRoles:\n    judge: 'openrouter/typesafe/jev-1.13'\n"):
            setting.write_text(text, encoding="utf-8")
            self.assertEqual(runtime.parse_judge_config(setting), runtime.JUDGE_SELECTOR)
        refused = {
            "the moving alias": ("modelRoles:\n  judge: openrouter/~typesafe/jev-latest\n", "alias"),
            "the router": ("modelRoles:\n  judge: openrouter/typesafe/jev-router\n", "not the pinned"),
            "a chat model as judge": ("modelRoles:\n  judge: openrouter/anthropic/claude-sonnet-4.6\n", "not the pinned"),
            "a second setting": ("modelRoles:\n  judge: openrouter/typesafe/jev-1.13\n  default: openrouter/anthropic/claude-sonnet-4.6\n", "exactly two"),
            "a one-line mapping": ('modelRoles: {judge: "openrouter/typesafe/jev-1.13"}\n', "exactly two"),
        }
        for label, (text, message) in refused.items():
            setting.write_text(text, encoding="utf-8")
            with self.subTest(label), self.assertRaisesRegex(ValueError, message):
                runtime.parse_judge_config(setting)

    def test_question_files_must_fit_the_pinned_judge_bridge(self):
        target = self.base / "QUESTIONS.json"
        good = {"claims_release": {"type": "bool", "instructions": "Does `note` claim a release?", "criteria": {"true": "Claims it.", "false": "Does not."}},
                "status": {"type": "choice", "instructions": "Which status does `note` give?", "criteria": {"received": "Received only.", "not_stated": "No status."}},
                "urgency": {"type": "score", "instructions": "How urgent is `note`?", "criteria": ["Routine", "Immediate"]}}
        target.write_text(json.dumps({"schema_version": 1, "questions": good}), encoding="utf-8")
        self.assertEqual(set(runtime.parse_questions(target)), set(good))
        broken = {
            "object option text": {"status": {**good["status"], "criteria": {"received": {"what": "Received"}, "not_stated": "No status."}}},
            "a one-option choice": {"status": {**good["status"], "criteria": {"received": "Received only."}}},
            "a one-level score": {"urgency": {**good["urgency"], "criteria": ["Routine"]}},
            "a yes/no criterion that is not true or false": {"claims_release": {**good["claims_release"], "criteria": {"yes": "Claims it."}}},
            "an unknown field": {"claims_release": {**good["claims_release"], "weight": 2}},
            "an id with capitals": {"ClaimsRelease": good["claims_release"]},
        }
        for label, change in broken.items():
            target.write_text(json.dumps({"schema_version": 1, "questions": {**good, **change}}), encoding="utf-8")
            with self.subTest(label), self.assertRaises(ValueError):
                runtime.parse_questions(target)

    def judge_receipt(self):
        """A synthetic judge run: one frozen cell, two judged notes, one served build."""
        work = self.work.resolve()
        (work / "notes").mkdir()
        for key, text in (("BG-001", "OC-2001 received at East Yard."), ("BG-002", "OC-2002 released under RA-5521.")):
            (work / "notes" / f"{key}.json").write_text(json.dumps({"id": key, "state": {"note": text}}), encoding="utf-8")
        (work / "out").mkdir()
        questions = {"claims_release": {"type": "bool", "instructions": "Does `note` claim a release?"},
                     "status": {"type": "choice", "instructions": "Which status does `note` give?", "criteria": {"received": "Received only.", "released": "Released for issue.", "not_stated": "No status."}},
                     "urgency": {"type": "score", "instructions": "How urgent is `note`?", "criteria": ["Routine", "Today", "Immediate"]}}
        (work / "QUESTIONS.json").write_text(json.dumps({"schema_version": 1, "questions": questions}), encoding="utf-8")
        (work / "JUDGE.yml").write_text("modelRoles:\n  judge: openrouter/typesafe/jev-1.13\n", encoding="utf-8")
        self.evidence.mkdir()
        args = SimpleNamespace(judge_config=str(work / "JUDGE.yml"), judge_questions=str(work / "QUESTIONS.json"), judge_states=str(work / "notes"), judge_output="out/run-1")
        prompt, judge = runtime.judge_launch_files(runtime.prepare_judge(args, work), work, self.evidence)
        self.assertIn(judge["cell_code"], prompt)
        policy = dict.fromkeys(runtime.POLICY_KEYS)
        policy.update(schema_version=1, run_id="synthetic", work_root=str(work), profile="judge", tools=["eval"], write_files=[], write_root=None, provider=runtime.PROVIDER, model=runtime.MODEL, omp_version=SYNTH_OMP_VERSION, judge=judge)
        before = runtime.snapshot(work, [])
        call_args = {"language": "js", "code": judge["cell_code"], "title": "Judge runner", "timeout": 120, "reset": None}
        executed_args = runtime.normalize_arguments(call_args)
        content = [{"type": "text", "text": "judged 2/2; failed 0"}]
        call = {"type": "toolCall", "id": "judge-1", "name": "eval", "arguments": call_args}
        assistant = {"role": "assistant", "provider": runtime.PROVIDER, "model": runtime.MODEL, "stopReason": "toolUse", "content": [call]}
        final = {"role": "assistant", "provider": runtime.PROVIDER, "model": runtime.MODEL, "stopReason": "stop", "content": [{"type": "text", "text": "judged 2/2; failed 0"}]}
        events = [{"type": "agent_start"}, {"type": "message_end", "message": assistant},
                  {"type": "tool_execution_start", "toolCallId": "judge-1", "toolName": "eval", "args": executed_args},
                  {"type": "tool_execution_end", "toolCallId": "judge-1", "toolName": "eval", "result": {"content": content}, "isError": False},
                  {"type": "message_end", "message": {"role": "toolResult", "toolCallId": "judge-1", "toolName": "eval", "content": content, "isError": False}},
                  {"type": "message_end", "message": final}, {"type": "agent_end", "isTerminal": True, "messages": [assistant, final]}]
        request = {"type": "provider_request", "run_id": "synthetic", "provider": runtime.PROVIDER, "model": runtime.MODEL, "tools": ["eval"]}
        guard = [{"type": "guard_ready", "run_id": "synthetic", "provider": runtime.PROVIDER, "model": runtime.MODEL, "active_tools": ["eval"]}, request,
                 {"run_id": "synthetic", "type": "decision", "call_id": "judge-1", "tool": "eval", "arguments": executed_args, "allow": True, "reason": "frozen judge cell"}, request,
                 {"type": "guard_end", "run_id": "synthetic", "ready": True, "failed": False, "provider_requests": 2}]
        return policy, events, guard, before

    def write_judgments(self, policy, rows=None, status=None):
        build = "openrouter/typesafe/jev-1.13-20260917"
        def answers(release, choice):
            spread = {"received": 0.05, "released": 0.05, "not_stated": 0.05, choice: 0.9}
            return {"claims_release": {"type": "bool", "bool": release}, "status": {"type": "choice", "choice": choice, "probabilities": spread, "confidence": 0.85},
                    "urgency": {"type": "score", "score": 0.2, "legend": {"0": "Routine", "1": "Today", "2": "Immediate"}, "probabilities": {"0": 0.8, "1": 0.2, "2": 0.0}, "confidence": 0.7}}
        rows = rows if rows is not None else [{"key": "BG-001", "answers": answers(0.03, "received"), "error": None, "model": build}, {"key": "BG-002", "answers": answers(0.96, "released"), "error": None, "model": build}]
        status = status or {"id": "jdgb-1", "intent": "Judging 2 states", "total": 2, "done": 2, "failed": 0, "cost": 0.00004, "running": False, "model": build, "elapsedS": 1.2}
        folder = Path(policy["work_root"]) / policy["judge"]["output"]
        folder.mkdir(exist_ok=True)
        (folder / "judgments.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        (folder / "batch-status.json").write_text(json.dumps(status), encoding="utf-8")
        return rows, status

    def test_a_judge_run_binds_the_frozen_cell_every_answer_and_one_served_build(self):
        policy, events, guard, before = self.judge_receipt()
        rows, status = self.write_judgments(policy)
        after = runtime.snapshot(Path(policy["work_root"]), [])
        self.assertEqual(runtime.validate_run(policy, events, guard, {"before": before, "after": after}, 0), [])
        self.assertEqual(runtime.judge_output_errors(policy)[1]["served_model"], "openrouter/typesafe/jev-1.13-20260917")
        chat = copy.deepcopy(rows); chat[0]["model"] = "openrouter/anthropic/claude-sonnet-4.6"
        newer = copy.deepcopy(rows); newer[1]["model"] = "openrouter/typesafe/jev-1.13-20261001"
        outside = copy.deepcopy(rows); outside[0]["answers"]["status"]["choice"] = "cleared"
        defects = {
            "a chat model answered as judge": ("not the pinned judge", chat, None),
            "two builds answered one batch": ("more than one judge build", newer, None),
            "a note was never judged": ("every state exactly once", rows[:1], {**status, "total": 1, "done": 1}),
            "an answer outside the frozen options": ("outside the frozen options", outside, None),
            "a failed item": ("judged without failure", rows, {**status, "failed": 1}),
        }
        for label, (fragment, changed_rows, changed_status) in defects.items():
            self.write_judgments(policy, changed_rows, changed_status)
            snapshots = {"before": before, "after": runtime.snapshot(Path(policy["work_root"]), [])}
            with self.subTest(label):
                errors = runtime.validate_run(policy, events, guard, snapshots, 0)
                self.assertTrue(any(fragment in error for error in errors), f"{label}: {errors}")
        self.write_judgments(policy)
        other_cell = copy.deepcopy(events)
        other_cell[1]["message"]["content"][0]["arguments"]["code"] = "return 1;"
        self.assertIn("eval ran code other than the frozen judge cell", runtime.validate_run(policy, other_cell, guard, {"before": before, "after": after}, 0))
        (Path(policy["work_root"]) / "out/run-1/notes.txt").write_text("stray", encoding="utf-8")
        stray = runtime.snapshot(Path(policy["work_root"]), [])
        self.assertTrue(any("beyond its declared output" in error for error in runtime.validate_run(policy, events, guard, {"before": before, "after": stray}, 0)))

    def test_judge_invocations_that_cannot_run_stop_before_any_model_call(self):
        (self.work / "JUDGE.yml").write_text("modelRoles:\n  judge: openrouter/~typesafe/jev-latest\n", encoding="utf-8")
        (self.work / "QUESTIONS.json").write_text(json.dumps({"schema_version": 1, "questions": {"q": {"type": "bool", "instructions": "Is `note` empty?"}}}), encoding="utf-8")
        (self.work / "notes").mkdir()
        (self.work / "notes/BG-001.json").write_text(json.dumps({"id": "BG-001", "state": {"note": "x"}}), encoding="utf-8")
        judge = ["--judge-config", str(self.work / "JUDGE.yml"), "--judge-questions", str(self.work / "QUESTIONS.json"), "--judge-states", str(self.work / "notes"), "--judge-output", "out-1"]
        environment = dict(os.environ, OPENROUTER_API_KEY="")
        run = lambda *args: subprocess.run([sys.executable, str(LAUNCHER), "--evidence", str(self.evidence), *args], capture_output=True, text=True, env=environment, cwd=self.base, timeout=20)
        cases = {
            "an alias as judge": (("--workdir", str(self.work), *judge), "alias"),
            "a partial judge request": (("--workdir", str(self.work), *judge[:4]), "go together"),
            "a judge run with a prompt": (("--workdir", str(self.work), "--prompt", str(self.prompt), *judge), "writes its own prompt"),
            "a candidate listing with a work folder": (("--list-judges", "--workdir", str(self.work)), "takes only --evidence"),
        }
        for label, (args, message) in cases.items():
            with self.subTest(label):
                result = run(*args)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn(message, result.stderr)
                self.assertFalse(self.evidence.exists())

    def test_a_different_release_identity_is_accepted_without_a_course_pin(self):
        policy, events, guard, snapshots = self.receipt()
        policy["omp_version"] = "omp/99.2.0"
        self.assertEqual(runtime.validate_run(policy, events, guard, snapshots, 0), [])

    def test_malformed_recorded_runtime_identities_hold_the_audit(self):
        policy, events, guard, snapshots = self.receipt()
        for version in (None, "", "omp/", "omp/latest", "18.3.5", "omp/18.6"):
            with self.subTest(version=version):
                policy["omp_version"] = version
                self.assertIn("omp_version is not a recorded valid OMP identity",
                              runtime.validate_run(policy, events, guard, snapshots, 0))

if __name__ == "__main__":
    unittest.main()
