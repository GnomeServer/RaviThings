#!/usr/bin/env python3
"""Isolated synthetic native-record fixtures; never presented as live OMP proof."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE / "scripts"))
import orchestrate
import orchestration_evidence as evidence


OMP_V1 = "omp/18.3.5"
OMP_V2 = "omp/19.0.0"


def jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


class NativeFixture:
    """Synthetic native records with real local source files."""

    def __init__(self, work, output, policy, omp_version):
        self.work, self.output, self.policy, self.omp_version = work, output, policy, omp_version
        self.parent_path = output / "sessions/fixture-parent.jsonl"
        self.guard = []
        self.sequences = {}
        self.reports = {}

    def agent(self, role):
        return {"kind": "main", "id": "Main", "name": "main", "depth": 0} if role == "main" else {
            "kind": "sub", "id": role.title(), "name": role, "depth": 1, "parentId": "Main"}

    def log(self, role, kind, **fields):
        self.guard.append({"run_id": self.policy["run_id"], "stage": self.policy["stage"],
                           "agent": self.agent(role), "type": kind, **fields})

    def start(self, role):
        header = {"type": "session", "id": f"fixture-{role}", "cwd": str(self.output / ".runtime/home/cwd")}
        if role != "main":
            header["parentSession"] = str(self.parent_path)
        rows = [{"type": "title", "title": "SYNTHETIC TEST FIXTURE — NOT A LIVE RUN"}, header,
                {"type": "model_change", "model": evidence.SELECTOR, "resolvedModelIsFallback": False}]
        self.log(role, "guard_ready", provider=evidence.PROVIDER, model=evidence.MODEL,
                 policy_sha256=evidence.digest(evidence.json_bytes(self.policy)),
                 active_tools=self.policy["parent_tools"] if role == "main" else ["course_read", "yield"],
                 role_sha256=None if role == "main" else self.policy["role_files"][role]["sha256"])
        self.sequences[role] = 0
        return rows

    def assistant(self, rows, role, content):
        self.sequences[role] += 1
        sequence = self.sequences[role]
        self.log(role, "provider_request", sequence=sequence, provider=evidence.PROVIDER, model=evidence.MODEL)
        rows.append({"type": "message", "message": {"role": "assistant", "provider": evidence.PROVIDER,
                     "model": evidence.MODEL, "responseId": f"synthetic-{role}-{sequence}",
                     "usage": {"totalTokens": 1}, "content": content}})

    def tool(self, rows, role, name, args, details, *, failed=False, execution=None):
        call_id = f"fixture-{role}-{len(rows)}-{name}"
        self.assistant(rows, role, [{"type": "toolCall", "id": call_id, "name": name, "arguments": args}])
        self.log(role, "decision", call_id=call_id, tool=name, arguments=args, allow=True)
        if execution is not None:
            self.log(role, "execution_result", call_id=call_id, tool=name, **execution)
        self.log(role, "tool_result", call_id=call_id, tool=name, isError=failed, details=details)
        rows.append({"type": "message", "message": {"role": "toolResult", "toolName": name, "toolCallId": call_id,
                     "isError": failed, "details": details, "content": [{"type": "text", "text": "synthetic fixture result"}]}})
        return call_id

    def read_inputs(self, rows, role):
        for logical, binding in self.policy["reads"].get(role, {}).items():
            if binding["sha256"] is None:
                self.tool(rows, role, "course_read", {"path": logical}, {}, failed=True,
                          execution={"path": logical, "ok": False, "code": "ENOENT"})
            else:
                details = {"path": logical, "sha256": binding["sha256"]}
                self.tool(rows, role, "course_read", {"path": logical}, details,
                          execution={**details, "ok": True})

    def report(self, role):
        logical, binding = next(iter(self.policy["reads"][role].items()))
        if binding["sha256"] is None:
            return {"role": role, "status": "blocked", "source_path": logical, "source_sha256": None,
                    "source_id": None, "revision": None, "supersedes": None, "facts": {},
                    "reason": f"Missing assigned file: {logical}; ENOENT"}
        source = evidence.load_json(self.output / f"inputs/sources/{role}.json")
        # The fixture's truth is explicit revision 2, not the checker under test.
        record = next(row for row in source["records"] if row["revision"] == 2)
        return {"role": role, "status": "complete", "source_path": logical, "source_sha256": binding["sha256"],
                "source_id": source["source_id"], "revision": 2, "supersedes": 1,
                "facts": record["facts"], "reason": "Explicit revision 2 supersedes revision 1."}

    def child(self, item, index):
        role = item["agent"]
        rows = self.start(role)
        task = "Complete assignment thoroughly:\n\n" + item["task"].strip()
        rows.append({"type": "session_init", "agent": role, "resolvedModel": evidence.SELECTOR,
                     "tools": ["course_read", "yield"], "outputSchema": item["outputSchema"], "outputSchemaMode": "strict",
                     "systemPrompt": evidence.role_body((self.output / f"inputs/roles/{role}.md").read_text(), role) + "\n" + evidence.CONTEXT,
                     "task": task})
        self.read_inputs(rows, role)
        payload = self.report(role) if role in evidence.ROLES else {
            "role": "review", "status": "accepted", "candidate_sha256": evidence.file_hash(self.output / "candidate.json"), "issues": []}
        self.tool(rows, role, "yield", {"data": payload}, {"data": payload, "status": "success"})
        child_path = self.parent_path.with_suffix("") / f"{item['name']}.jsonl"
        jsonl(child_path, rows)
        evidence.write_json(child_path.with_suffix(".json"), payload)
        child_path.with_suffix(".md").write_bytes(evidence.json_bytes(payload))
        self.log("main", "subagent_spawn", requested_role=role, spawnKey=item["name"], invocationKind="task", allow=True)
        return {"index": index, "id": item["name"], "agent": role, "agentSource": "project",
                "assignment": item["task"].strip(), "task": task, "exitCode": 0, "aborted": False, "truncated": False,
                "resolvedModelIdentity": evidence.SELECTOR, "resolvedModelIsFallback": False,
                "structuredOutput": {"source": "caller", "mode": "strict", "status": "valid", "data": payload},
                "output": evidence.json_bytes(payload).decode(), "outputPath": str(child_path.with_suffix(".md"))}

    def finish(self, reports):
        parent = self.start("main")
        events = []
        if self.policy["dispatched"]:
            children = [self.child(item, index) for index, item in enumerate(self.policy["task_call"]["tasks"])]
            details = {"results": children}
            task_id = self.tool(parent, "main", "task", self.policy["task_call"], details)
            events.append({"type": "tool_execution_end", "toolName": "task", "toolCallId": task_id,
                           "result": {"details": details}, "isError": False})
        else:
            self.read_inputs(parent, "main")
            provenance = {role: {"attempt_id": value["attempt_id"], "child_id": value["child_id"],
                                "source_id": value["report"]["source_id"], "revision": 2,
                                "sha256": value["report"]["source_sha256"]} for role, value in reports.items()}
            candidate = {"movement": "CS-2", "quantity_scanned": 72, "quantity_usable": 68, "release_status": "HOLD",
                         "not_before": "2026-10-16T18:00:00-06:00", "decision": "HOLD",
                         "decision_reasons": ["AUTHORITY_HOLD", "TIMING_NOT_OPEN"], "evidence": provenance}
            evidence.write_json(self.work / evidence.CANDIDATE, candidate)
            evidence.write_json(self.output / "candidate.json", candidate)
            details = {"path": evidence.CANDIDATE, "sha256": evidence.file_hash(self.output / "candidate.json")}
            self.tool(parent, "main", "course_write", {"path": evidence.CANDIDATE, "content": evidence.json_bytes(candidate).decode()}, details,
                      execution={**details, "ok": True})
        self.assistant(parent, "main", [{"type": "text", "text": "Synthetic fixture complete, not a provider observation."}])
        jsonl(self.parent_path, parent)
        jsonl(self.output / "stdout.jsonl", events + [{"type": "agent_end"}])
        jsonl(self.output / "guard.jsonl", self.guard)
        (self.output / "stderr.txt").write_text("")
        evidence.write_json(self.output / "process.json", {"returncode": 0, "aborted": False, "timed_out": False,
                            "omp_version": self.omp_version, "binary_sha256": "f" * 64, "fixture": True})
        evidence.write_json(self.output / "work-after.json", evidence.work_snapshot(self.work))
        audit = evidence.audit_attempt(self.work, self.output, sealed=False)
        evidence.write_json(self.output / "reports.json", audit["reports"])
        evidence.write_json(self.output / "result.json", evidence.summary(audit))
        evidence.seal_attempt(self.output)
        return audit


class OrchestrationBehavior(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="copper-evidence-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.work = self.root / "work"
        shutil.copytree(MODULE / "scripts", self.work / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        for directory in ("case", "controls", "agents", "prompts"):
            shutil.copytree(MODULE / "shared" / directory, self.work / "shared" / directory)
        (self.work / "out").mkdir()
        self.serial = 0

    def stage(self, stage, prior=None, omp_version=OMP_V1):
        self.serial += 1
        assignments = orchestrate.inspect_work(self.work)
        reference, reports, reused, dispatched = orchestrate.select_prior(self.work, stage, prior, assignments, omp_version)
        output, policy, _cwd, _prompt = orchestrate.prepare_attempt(self.work, self.root / f"{stage}-{self.serial}", stage,
                                                                   assignments, reference, reports, reused, dispatched, omp_version)
        audit = NativeFixture(self.work, output, policy, omp_version).finish(reports)
        return output, audit

    def repair_input(self):
        brief = self.work / "shared/prompts/timing.md"
        brief.write_text(brief.read_text().replace("Input: shared/case/timing-pending.json", "Input: shared/case/timing.json", 1))

    def repaired(self):
        first, first_audit = self.stage("fanout")
        self.repair_input()
        repair, repaired = self.stage("repair", first)
        return first, first_audit, repair, repaired

    def test_partial_completion_and_selective_repair_keep_original_attribution(self):
        first, initial, repair, repaired = self.repaired()
        self.assertEqual(evidence.summary(initial)["accepted_roles"], ["inventory", "authority"])
        self.assertEqual(evidence.summary(initial)["blocked_roles"], ["timing"])
        self.assertEqual(repaired["dispatched"], ["timing"])
        self.assertEqual(repaired["reused"], ["inventory", "authority"])
        self.assertEqual(evidence.summary(repaired)["status"], "PASS")
        self.assertEqual(repaired["reports"]["inventory"], initial["reports"]["inventory"])
        self.assertEqual(repaired["reports"]["authority"], initial["reports"]["authority"])
        self.assertNotEqual(repaired["reports"]["timing"]["attempt_id"], initial["reports"]["timing"]["attempt_id"])
        evidence.verify_seal(first)
        self.assertEqual(evidence.summary(evidence.audit_attempt(self.work, repair))["status"], "PASS")

    def test_integration_and_review_require_their_actual_dependencies(self):
        first, _ = self.stage("fanout")
        for stage in ("integrate", "review"):
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                orchestrate.select_prior(self.work, stage, first, orchestrate.inspect_work(self.work), OMP_V1)
        self.repair_input()
        repair, _ = self.stage("repair", first)
        integrate, integrated = self.stage("integrate", repair)
        review, reviewed = self.stage("review", integrate)
        self.assertEqual(evidence.summary(integrated)["status"], "PASS")
        self.assertEqual(evidence.summary(reviewed)["status"], "PASS")
        self.assertEqual(evidence.load_json(self.work / evidence.CANDIDATE)["decision"], "HOLD")
        evidence.write_json(self.work / evidence.CANDIDATE, {"movement": "CS-2", "decision": "READY"})
        with self.assertRaises(ValueError):
            evidence.audit_attempt(self.work, review)

    def test_changed_source_invalidates_its_consumer_not_independent_work(self):
        _first, _initial, repair, repaired = self.repaired()
        source = self.work / "shared/case/authority.json"
        source.write_text(source.read_text() + "\n")
        audit = evidence.audit_attempt(self.work, repair)
        self.assertEqual(evidence.summary(audit)["accepted_roles"], ["inventory", "timing"])
        _prior, _reports, reusable, dispatched = orchestrate.select_prior(self.work, "repair", repair, orchestrate.inspect_work(self.work), OMP_V1)
        self.assertEqual(reusable, ["inventory", "timing"])
        self.assertEqual(dispatched, ["authority"])
        with self.assertRaises(ValueError):
            orchestrate.select_prior(self.work, "integrate", repair, orchestrate.inspect_work(self.work), OMP_V1)

    def test_changed_role_and_brief_invalidate_their_handoffs(self):
        _first, _initial, repair, _repaired = self.repaired()
        for relative in ("shared/agents/inventory.md", "shared/prompts/authority.md"):
            path = self.work / relative
            path.write_text(path.read_text() + "\nKeep the source boundary explicit.\n")
        _prior, _reports, reusable, dispatched = orchestrate.select_prior(self.work, "repair", repair, orchestrate.inspect_work(self.work), OMP_V1)
        self.assertEqual(reusable, ["timing"])
        self.assertEqual(dispatched, ["inventory", "authority"])

    def test_unchanged_consumer_line_endings_do_not_make_frozen_briefs_stale(self):
        for stage, newline in (("integrate", b"\r\n"), ("review", b"\n")):
            path = self.work / f"shared/prompts/{stage}.md"
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", newline))
        _first, _initial, repair, _repaired = self.repaired()
        integrate, integrated = self.stage("integrate", repair)
        self.assertEqual(evidence.summary(integrated)["status"], "PASS")
        review, _reviewed = self.stage("review", integrate)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = orchestrate.check_stage(self.work, review)
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "PASS")

    def test_changed_consumer_instructions_invalidate_review_not_specialists(self):
        _first, _initial, repair, _repaired = self.repaired()
        integrate, _integrated = self.stage("integrate", repair)
        review, _reviewed = self.stage("review", integrate)
        for relative in ("shared/prompts/integrate.md", "shared/prompts/review.md", "shared/agents/review.md"):
            with self.subTest(relative=relative):
                path = self.work / relative
                original = path.read_text()
                try:
                    path.write_text(original + "\nRequire explicit source authority in the decision.\n")
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        status = orchestrate.check_stage(self.work, review)
                    self.assertEqual(status, 1)
                    self.assertEqual(json.loads(output.getvalue())["status"], "HOLD")
                    self.assertEqual(evidence.summary(evidence.audit_attempt(self.work, repair))["status"], "PASS")
                    if relative == "shared/prompts/integrate.md":
                        with self.assertRaises(ValueError):
                            orchestrate.select_prior(self.work, "review", integrate, orchestrate.inspect_work(self.work), OMP_V1)
                finally:
                    path.write_text(original)

    def test_missing_child_or_guard_execution_cannot_be_replaced_by_summary(self):
        for damage in ("child", "execution"):
            with self.subTest(damage=damage):
                first, _ = self.stage("fanout")
                if damage == "child":
                    next((first / "sessions").rglob("Inventory.jsonl")).unlink()
                else:
                    path = first / "guard.jsonl"
                    rows = [row for row in evidence.read_jsonl(path) if not (row.get("type") == "execution_result" and row["agent"]["id"] == "Inventory")]
                    jsonl(path, rows)
                # Reseal to reach semantic validation, rather than only testing a hash mismatch.
                evidence.seal_attempt(first)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = orchestrate.check_stage(self.work, first)
                self.assertEqual(status, 1)
                self.assertEqual(json.loads(output.getvalue())["status"], "HOLD")

    def test_duplicate_spawn_and_wrong_model_are_rejected_after_reseal(self):
        for damage in ("duplicate", "model"):
            with self.subTest(damage=damage):
                first, _ = self.stage("fanout")
                path = first / "guard.jsonl"
                rows = evidence.read_jsonl(path)
                if damage == "duplicate":
                    rows.append(copy.deepcopy(next(row for row in rows if row["type"] == "subagent_spawn")))
                else:
                    next(row for row in rows if row["type"] == "guard_ready" and row["agent"]["id"] == "Inventory")["model"] = "unapproved-model"
                jsonl(path, rows)
                evidence.seal_attempt(first)
                with self.assertRaises(ValueError):
                    evidence.audit_attempt(self.work, first)

    def test_prior_and_native_record_changes_are_not_reusable(self):
        first, _initial, repair, _repaired = self.repaired()
        reports = first / "reports.json"
        reports.write_text(reports.read_text() + "\n")
        with self.assertRaises(ValueError):
            evidence.audit_attempt(self.work, repair)
        evidence.seal_attempt(first)
        with self.assertRaises(ValueError):
            evidence.audit_attempt(self.work, repair)

    def test_current_revision_beats_later_archive_receipt_and_unresolved_branch_holds(self):
        source = evidence.load_json(self.work / "shared/case/authority.json")
        self.assertGreater(source["records"][0]["recorded_at"], source["records"][1]["recorded_at"])
        self.assertEqual(evidence.current_record(source)["facts"]["release_status"], "HOLD")
        source["records"].append({"revision": 3, "supersedes": None, "recorded_at": "2026-10-16T12:14:00-06:00",
                                  "authority": "Conflicting office", "facts": {"release_status": "RELEASED"}})
        with self.assertRaises(ValueError):
            evidence.current_record(source)

    def test_wrong_source_role_and_unsafe_inputs_stop_before_dispatch(self):
        brief = self.work / "shared/prompts/authority.md"
        text = brief.read_text()
        brief.write_text(text.replace("Input: shared/case/authority.json", "Input: shared/case/inventory.json"))
        with self.assertRaises(ValueError):
            orchestrate.inspect_work(self.work)
        for path in ("../secret", "/secret", "file://secret", "shared/case/inventory.json:1-3"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                evidence.work_file(self.work, path)

    def test_fresh_evidence_never_overwrites_existing_attempt(self):
        first, _ = self.stage("fanout")
        original_seal = (first / "seal.json").read_bytes()
        assignments = orchestrate.inspect_work(self.work)
        with self.assertRaises(ValueError):
            orchestrate.prepare_attempt(self.work, first, "fanout", assignments, None, {}, [], list(evidence.ROLES), OMP_V1)
        self.assertEqual((first / "seal.json").read_bytes(), original_seal)

    def test_a_different_release_identity_accepts_an_independent_chain(self):
        self.repair_input()
        output, _audit = self.stage("fanout", omp_version=OMP_V2)
        checked = evidence.audit_attempt(self.work, output)
        self.assertEqual(evidence.summary(checked)["status"], "PASS")

    def test_version_mismatch_rejects_saved_evidence_and_prior_reuse(self):
        first, _audit = self.stage("fanout", omp_version=OMP_V1)
        with self.assertRaises(ValueError):
            orchestrate.select_prior(self.work, "repair", first, orchestrate.inspect_work(self.work), OMP_V2)
        process_path = first / "process.json"
        process = evidence.load_json(process_path)
        process["omp_version"] = OMP_V2
        evidence.write_json(process_path, process)
        evidence.seal_attempt(first)
        with self.assertRaises(ValueError):
            evidence.audit_attempt(self.work, first)


if __name__ == "__main__":
    unittest.main()
