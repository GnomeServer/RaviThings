"""Offline checks for Copper Span's native OMP attempts, not an attestation service."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


PROVIDER = "openrouter"
MODEL = "anthropic/claude-sonnet-4.6"
SELECTOR = f"{PROVIDER}/{MODEL}"
ROLES = ("inventory", "authority", "timing")
STAGES = ("fanout", "repair", "integrate", "review")
CANDIDATE = "out/status-brief.json"
GUARD = "shared/controls/orchestration_guard.mjs"
DECISION_AT = "2026-10-16T12:15:00-06:00"
CONTEXT = (
    "Fictional, class-only Copper Span: CS-2 carries IV fluid cases from Basin Depot "
    "to Clinic F-9. Decision time is 2026-10-16T12:15:00-06:00. No output authorizes "
    "a real movement. Each child is read-only and must use only its assigned input. "
    "Source identity, current_revision and the explicit supersedes chain determine "
    "authority, not timestamp or agreement between agents. A missing input is a "
    "blocked handoff: actually attempt the assigned read, never substitute a file. "
    "Return the caller's structured result through native yield exactly once."
)
REPORT_PROPERTIES = {
    "role": {"type": "string", "enum": list(ROLES)},
    "status": {"type": "string", "enum": ["complete", "blocked"]},
    "source_path": {"type": "string"},
    "source_sha256": {"type": ["string", "null"]},
    "source_id": {"type": ["string", "null"]},
    "revision": {"type": ["integer", "null"]},
    "supersedes": {"type": ["integer", "null"]},
    "facts": {"type": "object"},
    "reason": {"type": "string"},
}
REPORT_SCHEMA = {"type": "object", "properties": REPORT_PROPERTIES,
                 "required": list(REPORT_PROPERTIES), "additionalProperties": False}
REVIEW_PROPERTIES = {
    "role": {"type": "string", "enum": ["review"]},
    "status": {"type": "string", "enum": ["accepted", "hold"]},
    "candidate_sha256": {"type": "string"},
    "issues": {"type": "array", "items": {"type": "string"}},
}
REVIEW_SCHEMA = {"type": "object", "properties": REVIEW_PROPERTIES,
                 "required": list(REVIEW_PROPERTIES), "additionalProperties": False}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def valid_omp_version(version):
    return isinstance(version, str) and bool(re.fullmatch(r"omp/[0-9]+\.[0-9]+\.[0-9]+", version))


def strict_json(text):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"invalid JSON number: {value}")

    return json.loads(text, object_pairs_hook=unique, parse_constant=invalid)


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    path = Path(path)
    require(not path.is_symlink(), f"linked file is not permitted: {path}")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_json(path):
    path = Path(path)
    require(not path.is_symlink(), f"linked evidence: {path}")
    return strict_json(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def read_jsonl(path):
    return [strict_json(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def work_file(work, relative):
    require(isinstance(relative, str) and re.fullmatch(r"[A-Za-z0-9_./-]+", relative), "invalid relative work path")
    parts = Path(relative).parts
    require(parts and not Path(relative).is_absolute() and not any(p in {".", ".."} for p in parts), "unsafe work path")
    target = work
    for part in parts:
        target = target / part
        require(not target.is_symlink(), f"linked work path: {relative}")
    require(target.resolve().is_relative_to(work), "work path escapes root")
    return target


def role_body(text, role):
    normalized = text.replace("\r\n", "\n")
    require(normalized.startswith("---\n"), f"{role}: missing role frontmatter")
    header, separator, body = normalized[4:].partition("\n---\n")
    require(separator and body.strip(), f"{role}: missing role body")
    fields = {}
    for line in header.splitlines():
        key, colon, value = line.partition(":")
        require(colon and key not in fields, f"{role}: malformed or duplicate role field")
        fields[key] = value.strip()
    require(set(fields) == {"name", "description", "model", "tools"}, f"{role}: use the four supplied role fields")
    require(fields["name"] == role and fields["model"] == SELECTOR and fields["tools"] == "course_read", f"{role}: role identity/model/read-only tools changed")
    require(fields["description"], f"{role}: description missing")
    return body.strip()


def assignment(work, role):
    brief_path = f"shared/prompts/{role}.md"
    text = work_file(work, brief_path).read_text(encoding="utf-8")
    inputs = re.findall(r"^Input: (shared/case/[a-z0-9-]+\.json)$", text, re.MULTILINE)
    require(len(inputs) == 1, f"{role}: brief needs exactly one Input: shared/case/<name>.json line")
    source = work_file(work, inputs[0])
    role_path = work_file(work, f"shared/agents/{role}.md")
    role_body(role_path.read_text(encoding="utf-8"), role)
    control = {name: file_hash(work_file(work, name)) for name in
               ("scripts/orchestrate.py", "scripts/orchestration_evidence.py", GUARD)}
    fingerprint = {
        "source_path": inputs[0], "source": file_hash(source) if source.exists() else None,
        "brief": file_hash(work_file(work, brief_path)), "role": file_hash(role_path),
        "control": digest(json_bytes(control)), "context": digest(CONTEXT.encode()),
        "schema": digest(json_bytes(REPORT_SCHEMA)),
    }
    return {"brief": brief_path, "input": inputs[0], "source_exists": source.is_file(),
            "fingerprint": fingerprint, "text": text}


def current_record(source):
    require(isinstance(source, dict) and source.get("movement") == "CS-2", "source movement differs")
    require(isinstance(source.get("source_id"), str) and source["source_id"], "source identity missing")
    records = source.get("records")
    require(isinstance(records, list) and records, "source revisions missing")
    by_revision = {}
    for record in records:
        require(isinstance(record, dict), "malformed source revision")
        revision = record.get("revision")
        require(type(revision) is int and revision > 0 and revision not in by_revision, "duplicate/invalid revision")
        require(isinstance(record.get("facts"), dict) and record.get("authority"), "source facts/authority missing")
        stamp = datetime.fromisoformat(record["recorded_at"])
        require(stamp.tzinfo is not None, "source timestamp needs an offset")
        by_revision[revision] = record
    current = source.get("current_revision")
    require(type(current) is int and current in by_revision, "current source revision missing")
    seen = set()
    cursor = current
    while cursor is not None:
        require(type(cursor) is int and cursor in by_revision and cursor not in seen, "broken/cyclic supersession")
        seen.add(cursor)
        cursor = by_revision[cursor].get("supersedes")
    require(seen == set(by_revision), "unresolved source branch: supersession does not cover every revision")
    return by_revision[current]


def work_snapshot(work):
    result = {}
    for path in sorted(work.rglob("*")):
        relative = path.relative_to(work)
        if "__pycache__" in relative.parts:
            continue
        require(not path.is_symlink(), f"linked work entry: {relative}")
        if path.is_file():
            result[relative.as_posix()] = file_hash(path)
    return result


def evidence_files(evidence):
    result = {}
    for path in sorted(evidence.rglob("*")):
        relative = path.relative_to(evidence)
        if relative.parts[0] == ".runtime" or path.name == "seal.json" or path.name.endswith(".lock.os"):
            continue
        require(not path.is_symlink(), f"linked evidence entry: {relative}")
        if path.is_file():
            result[relative.as_posix()] = file_hash(path)
    return result


def seal_attempt(evidence):
    write_json(evidence / "seal.json", {"schema_version": 1, "files": evidence_files(evidence)})


def verify_seal(evidence):
    seal = load_json(evidence / "seal.json")
    require(seal.get("schema_version") == 1 and seal.get("files") == evidence_files(evidence), "saved evidence changed or is incomplete")


def normalized_arguments(arguments):
    require(isinstance(arguments, dict), "native tool arguments must be an object")
    return {key: value for key, value in arguments.items() if key != "i" and not (key in {"type", "error"} and value is None)}


def native_session(path, *, parent=None):
    rows = read_jsonl(path)
    headers = [row for row in rows if row.get("type") == "session"]
    require(len(headers) == 1 and headers[0].get("id"), "native session header missing/duplicated")
    if parent is not None:
        require(Path(headers[0].get("parentSession", "")).resolve() == parent.resolve(), "native child has wrong parent session")
    else:
        require(not headers[0].get("parentSession"), "parent transcript is a child")
    models = [row for row in rows if row.get("type") == "model_change"]
    require(len(models) == 1 and models[0].get("model") == SELECTOR and models[0].get("resolvedModelIsFallback") is False, "native model identity/fallback differs")
    messages = [row["message"] for row in rows if row.get("type") == "message"]
    assistants = [message for message in messages if message.get("role") == "assistant"]
    require(assistants and all(m.get("provider") == PROVIDER and m.get("model") == MODEL for m in assistants), "assistant provider/model differs")
    require(all(m.get("responseId") and isinstance(m.get("usage"), dict) for m in assistants), "native provider response metadata missing")
    calls, results, positions = {}, {}, {}
    for index, message in enumerate(messages):
        if message.get("role") == "assistant":
            for part in message.get("content", []):
                if part.get("type") == "toolCall":
                    call_id = part.get("id")
                    require(call_id and call_id not in calls, "duplicate native tool call")
                    calls[call_id] = {"name": part["name"], "arguments": normalized_arguments(part["arguments"])}
                    positions[call_id] = [index, None]
        elif message.get("role") == "toolResult":
            call_id = message.get("toolCallId")
            require(call_id in calls and call_id not in results, "orphan/duplicate native tool result")
            require(message.get("toolName") == calls[call_id]["name"], "native tool result name differs")
            results[call_id] = message
            positions[call_id][1] = index
    require(set(calls) == set(results), "native tool call did not return")
    return {"rows": rows, "header": headers[0], "calls": calls, "results": results, "positions": positions}


def check_session_guard(native, guard, policy, agent_id, role):
    rows = [row for row in guard if row.get("agent", {}).get("id") == agent_id]
    expected_kind = "main" if role == "main" else "sub"
    require(rows and all(row.get("agent", {}).get("kind") == expected_kind for row in rows), "guard child identity missing")
    if role != "main":
        require(all(row["agent"].get("name") == role and row["agent"].get("depth") == 1 and row["agent"].get("parentId") == "Main" for row in rows), "guard child role/depth/parent differs")
    ready = [row for row in rows if row.get("type") == "guard_ready"]
    tools = policy["parent_tools"] if role == "main" else ["course_read", "yield"]
    require(len(ready) == 1 and sorted(ready[0].get("active_tools", [])) == sorted(tools), "actual active tools differ")
    require(ready[0].get("provider") == PROVIDER and ready[0].get("model") == MODEL, "guard model identity differs")
    require(ready[0].get("policy_sha256") == digest(json_bytes(policy)), "guard policy identity differs")
    if role != "main":
        require(ready[0].get("role_sha256") == policy["role_files"][role]["sha256"], "actual role identity differs")
    providers = [row for row in rows if row.get("type") == "provider_request"]
    require(providers and len(providers) <= policy["max_provider_requests"], "provider request boundary missing/exceeded")
    require([row.get("sequence") for row in providers] == list(range(1, len(providers) + 1)), "provider request sequence differs")
    require(all(row.get("provider") == PROVIDER and row.get("model") == MODEL for row in providers), "provider request model differs")
    decisions = [row for row in rows if row.get("type") == "decision"]
    require(len(decisions) == len(native["calls"]), "native calls and guard decisions differ")
    by_call = {row.get("call_id"): row for row in decisions}
    require(len(by_call) == len(decisions) and set(by_call) == set(native["calls"]), "guard decision attribution differs")
    observed = {}
    for call_id, call in native["calls"].items():
        decision = by_call[call_id]
        require(decision.get("allow") is True and decision.get("tool") == call["name"], "tool denied or guard tool differs")
        require(normalized_arguments(decision.get("arguments", {})) == call["arguments"], "guard/native arguments differ")
        require(call["name"] in tools, "native tool outside context permissions")
        tool_results = [row for row in rows if row.get("type") == "tool_result" and row.get("call_id") == call_id]
        require(len(tool_results) == 1 and tool_results[0].get("tool") == call["name"], "guard/native tool result join missing")
        result = native["results"][call_id]
        require(bool(tool_results[0].get("isError")) == bool(result.get("isError")), "guard/native error result differs")
        if call["name"] in {"course_read", "course_write"}:
            executions = [row for row in rows if row.get("type") == "execution_result" and row.get("call_id") == call_id]
            require(len(executions) == 1, "real file execution proof missing/duplicated")
            execution = executions[0]
            logical = call["arguments"].get("path")
            require(execution.get("tool") == call["name"] and execution.get("path") == logical, "file execution attribution differs")
            if call["name"] == "course_read":
                binding = policy["reads"].get(role, {}).get(logical)
                require(binding is not None, "read outside assignment")
                if binding["sha256"] is None:
                    require(execution.get("ok") is False and execution.get("code") == "ENOENT" and result.get("isError") is True, "missing input was not actually read and rejected")
                else:
                    require(execution.get("ok") is True and execution.get("sha256") == binding["sha256"] and not result.get("isError"), "source read identity differs")
                    require(result.get("details", {}).get("sha256") == binding["sha256"], "native source hash differs")
                observed[logical] = native["positions"][call_id][1]
            else:
                require(role == "main" and policy["stage"] == "integrate" and logical == CANDIDATE, "write outside sole coordinator output")
                require(execution.get("ok") is True and not result.get("isError"), "coordinator write failed")
                require(execution.get("sha256") == result.get("details", {}).get("sha256"), "native output hash differs")
    require(set(observed) == set(policy["reads"].get(role, {})), f"{role}: required source read missing")
    return observed


def validate_report(report, role, policy, evidence, read_positions, native):
    require(isinstance(report, dict) and set(report) == set(REPORT_PROPERTIES), "malformed specialist report")
    require(report["role"] == role and report["status"] in {"complete", "blocked"}, "wrong specialist/status")
    require(isinstance(report["reason"], str) and isinstance(report["facts"], dict), "malformed report reason/facts")
    binding_map = policy["reads"][role]
    require(len(binding_map) == 1, "specialist must have one assigned input")
    logical, binding = next(iter(binding_map.items()))
    require(logical == policy["fingerprints"][role]["source_path"] and binding["sha256"] == policy["fingerprints"][role]["source"], "read binding differs from frozen source assignment")
    require(report["source_path"] == logical, "reported input differs from assignment")
    yields = [call_id for call_id, call in native["calls"].items() if call["name"] == "yield"]
    require(len(yields) == 1 and all(position < native["positions"][yields[0]][0] for position in read_positions.values()), "handoff precedes required reads")
    if binding["sha256"] is None:
        require(report["status"] == "blocked" and report["facts"] == {} and logical in report["reason"], "missing input promoted into a complete report")
        require(all(report[key] is None for key in ("source_sha256", "source_id", "revision", "supersedes")), "blocked handoff invented source identity")
    else:
        source = load_json(evidence / "inputs" / "sources" / f"{role}.json")
        require(source.get("role") == role, "source belongs to another specialist")
        record = current_record(source)
        require(report["status"] == "complete" and report["source_sha256"] == binding["sha256"], "complete report source hash differs")
        require(report["source_id"] == source["source_id"] and type(report["revision"]) is int and report["revision"] == record["revision"], "report cites non-current source identity/revision")
        require(report["supersedes"] == record["supersedes"] and json_bytes(report["facts"]) == json_bytes(record["facts"]), "report contradicts authoritative facts/supersession")


def expected_brief(reports):
    inventory, authority, timing = (reports[role]["report"]["facts"] for role in ROLES)
    scanned, usable = inventory["quantity_scanned"], inventory["quantity_usable"]
    require(type(scanned) is int and type(usable) is int and 0 <= usable <= scanned, "invalid inventory quantities")
    require(authority["release_status"] in {"HOLD", "RELEASED"}, "invalid release authority status")
    not_before = datetime.fromisoformat(timing["not_before"])
    require(not_before.tzinfo is not None, "timing needs explicit offset")
    reasons = []
    if usable == 0:
        reasons.append("INVENTORY_UNUSABLE")
    if authority["release_status"] != "RELEASED":
        reasons.append("AUTHORITY_HOLD")
    if not_before > datetime.fromisoformat(DECISION_AT):
        reasons.append("TIMING_NOT_OPEN")
    provenance = {}
    for role, handoff in reports.items():
        report = handoff["report"]
        provenance[role] = {"attempt_id": handoff["attempt_id"], "child_id": handoff["child_id"],
                            "source_id": report["source_id"], "revision": report["revision"], "sha256": report["source_sha256"]}
    return {"movement": "CS-2", "quantity_scanned": scanned, "quantity_usable": usable,
            "release_status": authority["release_status"], "not_before": timing["not_before"],
            "decision": "HOLD" if reasons else "READY", "decision_reasons": reasons, "evidence": provenance}


def validate_candidate(candidate, reports):
    require(isinstance(candidate, dict), "candidate is not a JSON object")
    expected = expected_brief(reports)
    actual = dict(candidate)
    require(isinstance(actual.get("decision_reasons"), list), "candidate decision reasons missing")
    actual["decision_reasons"] = sorted(actual["decision_reasons"])
    expected["decision_reasons"] = sorted(expected["decision_reasons"])
    require(json_bytes(actual) == json_bytes(expected), "candidate facts, decision or original handoff attribution differ")


def audit_attempt(work, evidence, *, sealed=True, current=True, ancestry=()):
    evidence = Path(evidence).resolve()
    require(evidence not in ancestry, "cyclic prior evidence chain")
    if sealed:
        verify_seal(evidence)
    policy = load_json(evidence / "policy.json")
    require(policy.get("schema_version") == 1 and policy.get("stage") in STAGES, "invalid evidence policy")
    require(policy.get("provider") == PROVIDER and policy.get("model") == MODEL, "pinned provider/model identity differs")
    omp_ver = policy.get("omp_version")
    require(valid_omp_version(omp_ver), "invalid omp_version format in policy")
    require(Path(policy["work_root"]).resolve() == work and Path(policy["evidence_root"]).resolve() == evidence, "evidence belongs to a different work root or location")
    require(policy["guard_source_sha256"] == file_hash(evidence / "inputs" / "controls" / "orchestration_guard.mjs"), "frozen guard identity differs")
    process = load_json(evidence / "process.json")
    require(process.get("returncode") == 0 and not process.get("aborted") and not process.get("timed_out"), "native process did not complete successfully")
    proc_ver = process.get("omp_version")
    require(proc_ver == omp_ver and re.fullmatch(r"[0-9a-f]{64}", process.get("binary_sha256", "")), "native binary identity missing or mismatched with policy")
    overlay = load_json(evidence / "runtime-config.json")
    require(overlay.get("retry") == {"enabled": False, "modelFallback": False} and overlay.get("async") == {"enabled": False}, "retry/fallback/asynchronous dispatch enabled")
    require(overlay.get("task") == {"batch": True, "maxConcurrency": 3, "maxRecursionDepth": 1}, "team bounds differ")
    stage = policy["stage"]
    before, after = (load_json(evidence / f"work-{when}.json") for when in ("before", "after"))
    changed = {name for name in set(before) | set(after) if before.get(name) != after.get(name)}
    require(changed <= ({CANDIDATE} if stage == "integrate" else set()), "work changed outside coordinator output")
    prior = None
    if policy.get("prior"):
        reference = policy["prior"]
        prior_path = Path(reference["path"]).resolve()
        require(file_hash(prior_path / "seal.json") == reference["seal_sha256"], "prior evidence identity changed")
        prior = audit_attempt(work, prior_path, current=current and stage == "review", ancestry=ancestry + (evidence,))
    if prior is not None:
        require(prior.get("omp_version") == omp_ver, "OMP version changed since the prior attempt; the saved chain is not consistent for reuse")
    require((stage == "fanout") == (prior is None), "stage/prior dependency differs")
    if stage in {"repair", "integrate"}:
        require(prior["stage"] in {"fanout", "repair"}, "specialist stage needs specialist prior evidence")
    if stage == "review":
        require(prior["stage"] == "integrate" and not prior["issues"],
                "review requires a current accepted integration: " + "; ".join(prior["issues"]))
    reports = dict(prior["reports"]) if prior else {}
    reused = policy["reused"]
    require(isinstance(reused, list) and len(reused) == len(set(reused)) and set(reused) <= set(ROLES), "invalid reuse set")
    for role in reused:
        require(role in reports and reports[role]["report"]["status"] == "complete", "reused handoff was not accepted")
        require(reports[role]["fingerprint"] == policy["fingerprints"][role], "stale prior handoff reused")
    dispatch = policy["dispatched"]
    require(isinstance(dispatch, list) and len(dispatch) == len(set(dispatch)), "duplicate dispatch")
    if stage == "fanout":
        require(dispatch == list(ROLES) and not reused, "first fanout must dispatch three independent specialists")
    elif stage == "repair":
        required = [role for role in ROLES if role not in reused]
        require(dispatch == required and dispatch, "repair did not dispatch exactly invalidated work")
    else:
        require(reused == list(ROLES) and dispatch == (["review"] if stage == "review" else []), "dependent stage handoff set differs")
    for role in ROLES:
        require(policy["fingerprints"][role]["source_path"] == policy["assignments"][role]["input"], "frozen assignment differs")
        for kind, key, suffix in (("roles", "role", "md"), ("briefs", "brief", "md")):
            require(file_hash(evidence / "inputs" / kind / f"{role}.{suffix}") == policy["fingerprints"][role][key], "frozen role/brief identity differs")
        source_path = evidence / "inputs" / "sources" / f"{role}.json"
        source_hash = file_hash(source_path) if source_path.exists() else None
        require(source_hash == policy["fingerprints"][role]["source"], "frozen source identity differs")
    guard = read_jsonl(evidence / "guard.jsonl")
    require(guard and all(row.get("run_id") == policy["run_id"] and row.get("stage") == stage for row in guard), "guard attempt identity differs")
    require(not any(row.get("type") == "guard_error" or row.get("allow") is False for row in guard), "guard refused an action")
    events = read_jsonl(evidence / "stdout.jsonl")
    require(sum(row.get("type") == "agent_end" for row in events) == 1, "parent did not reach one terminal native result")
    require(not any(re.search(r"retry|fallback", row.get("type", "")) or row.get("type") in {"model_changed", "extension_error"} for row in events), "native retry/fallback/extension failure")
    parents = list((evidence / "sessions").glob("*.jsonl"))
    require(len(parents) == 1, "native parent session missing/duplicated")
    parent_path = parents[0]
    parent = native_session(parent_path)
    check_session_guard(parent, guard, policy, "Main", "main")
    task_ids = [cid for cid, call in parent["calls"].items() if call["name"] == "task"]
    require(len(task_ids) == (1 if dispatch else 0), "native dispatch count differs")
    expected_children = set()
    if dispatch:
        task_id = task_ids[0]
        require(parent["calls"][task_id]["arguments"] == policy["task_call"], "actual task batch differs from frozen assignments")
        task_result = parent["results"][task_id]
        require(not task_result.get("isError"), "native task failed")
        results = task_result.get("details", {}).get("results")
        require(isinstance(results, list) and len(results) == len(dispatch), "missing/extra native child result")
        stdout_results = [row for row in events if row.get("type") == "tool_execution_end" and row.get("toolCallId") == task_id]
        require(len(stdout_results) == 1 and stdout_results[0].get("result", {}).get("details", {}).get("results") == results, "parent session/stdout task results differ")
        spawns = [row for row in guard if row.get("type") == "subagent_spawn"]
        require(len(spawns) == len(dispatch), "missing/duplicate observed spawn")
        for index, (item, result) in enumerate(zip(policy["task_call"]["tasks"], results)):
            role, child_id = item["agent"], item["name"]
            frozen_brief = evidence / "inputs" / ("stage.md" if role == "review" else f"briefs/{role}.md")
            require(item["task"] == frozen_brief.read_text(encoding="utf-8"), "requested task differs from frozen brief")
            require(item["outputSchema"] == (REVIEW_SCHEMA if role == "review" else REPORT_SCHEMA) and item["schemaMode"] == "strict", "caller handoff schema differs")
            require(policy["role_files"][role]["sha256"] == file_hash(evidence / "inputs" / "roles" / f"{role}.md"), "loaded role differs from its frozen source")
            require(role == dispatch[index] and result.get("index") == index and result.get("agent") == role and result.get("id") == child_id, "requested/returned child identity differs")
            require(result.get("agentSource") == "project" and result.get("assignment") == item["task"].strip(), "native assignment/role source differs")
            require(result.get("exitCode") == 0 and result.get("aborted") is False and not result.get("truncated"), "native child failed/aborted/truncated")
            require(result.get("resolvedModelIdentity") == SELECTOR and result.get("resolvedModelIsFallback") is False, "child model/fallback differs")
            matching_spawns = [row for row in spawns if row.get("requested_role") == role and row.get("spawnKey") == child_id and row.get("allow") is True]
            require(len(matching_spawns) == 1, "requested/executed spawn join differs")
            child_path = parent_path.with_suffix("") / f"{child_id}.jsonl"
            expected_children.add(child_path.resolve())
            require(Path(result.get("outputPath", "")).resolve() == child_path.with_suffix(".md").resolve(), "native child artifact path differs")
            child = native_session(child_path, parent=parent_path)
            initial = [row for row in child["rows"] if row.get("type") == "session_init"]
            require(len(initial) == 1 and initial[0].get("agent") == role and initial[0].get("resolvedModel") == SELECTOR, "native role initialization differs")
            require(sorted(initial[0].get("tools", [])) == ["course_read", "yield"] and initial[0].get("outputSchema") == item["outputSchema"] and initial[0].get("outputSchemaMode") == "strict", "child tool/schema initialization differs")
            body = role_body((evidence / "inputs" / "roles" / f"{role}.md").read_text(encoding="utf-8"), role)
            system_prompt = initial[0].get("systemPrompt", "").replace("\r\n", "\n")
            require(body in system_prompt and CONTEXT in system_prompt and initial[0].get("task") == result.get("task"), "child did not receive frozen role/context/assignment")
            observed = check_session_guard(child, guard, policy, child_id, role)
            yields = [cid for cid, call in child["calls"].items() if call["name"] == "yield"]
            require(len(yields) == 1, "missing/duplicate native yield")
            yield_id = yields[0]
            yielded = child["results"][yield_id]
            payload = child["calls"][yield_id]["arguments"].get("data")
            require(not yielded.get("isError") and yielded.get("details", {}).get("data") == payload, "yield did not return its declared result")
            structured = result.get("structuredOutput", {})
            require(structured.get("status") == "valid" and structured.get("mode") == "strict" and structured.get("data") == payload, "structured child result differs")
            require(load_json(child_path.with_suffix(".json")) == payload and strict_json(result["output"]) == payload, "native child artifacts differ")
            if role in ROLES:
                validate_report(payload, role, policy, evidence, observed, child)
                reports[role] = {"attempt_id": policy["run_id"], "child_id": child_id,
                                 "report": payload, "fingerprint": policy["fingerprints"][role]}
            else:
                require(set(payload) == set(REVIEW_PROPERTIES) and payload["role"] == "review" and payload["status"] in {"accepted", "hold"}, "malformed review")
                require(isinstance(payload["issues"], list) and all(isinstance(issue, str) and issue for issue in payload["issues"]), "invalid review findings")
                require(payload["candidate_sha256"] == file_hash(evidence / "candidate.json"), "review refers to another candidate")
                require(all(position < child["positions"][yield_id][0] for position in observed.values()), "review returned before reading candidate/sources")
                require(payload["status"] != "accepted" or not payload["issues"], "review accepted despite findings")
    actual_children = {path.resolve() for path in (evidence / "sessions").rglob("*.jsonl")} - {parent_path.resolve()}
    require(actual_children == expected_children, "unrequested/missing native child session")
    expected_agents = {"Main"} | {item["name"] for item in (policy.get("task_call") or {}).get("tasks", [])}
    require({row.get("agent", {}).get("id") for row in guard} <= expected_agents, "unrequested guard agent")
    require(set(reports) == set(ROLES), "required specialist outcome missing")
    issues = [f"{role}: blocked on {reports[role]['report']['source_path']}" for role in ROLES if reports[role]["report"]["status"] != "complete"]
    if stage in {"integrate", "review"}:
        require(not issues, "integration used blocked handoffs")
        require(load_json(evidence / "accepted-handoffs.json") == reports, "handoff bundle differs from original child results")
        scope = "review" if stage == "review" else "main"
        required_inputs = {"accepted-handoffs.json": file_hash(evidence / "accepted-handoffs.json")}
        required_inputs.update({policy["assignments"][role]["input"]: policy["fingerprints"][role]["source"] for role in ROLES})
        if stage == "review":
            required_inputs[CANDIDATE] = file_hash(evidence / "candidate.json")
        require({name: binding["sha256"] for name, binding in policy["reads"][scope].items()} == required_inputs, "dependent stage did not read the accepted inputs and actual candidate")
        candidate = load_json(evidence / "candidate.json")
        validate_candidate(candidate, reports)
        if stage == "integrate":
            if before.get(CANDIDATE):
                require(file_hash(evidence / "candidate-before.json") == before[CANDIDATE], "previous candidate was not preserved")
            writes = [(cid, call) for cid, call in parent["calls"].items() if call["name"] == "course_write"]
            require(len(writes) == 1 and strict_json(writes[0][1]["arguments"]["content"]) == candidate, "candidate is not the coordinator's single write")
            require(after.get(CANDIDATE) == file_hash(evidence / "candidate.json"), "candidate differs from observed output")
            write_position = parent["positions"][writes[0][0]][0]
            require(all(parent["positions"][cid][1] < write_position for cid, call in parent["calls"].items() if call["name"] == "course_read"), "coordinator wrote before accepting inputs")
        else:
            require(file_hash(evidence / "candidate.json") == file_hash(Path(policy["prior"]["path"]) / "candidate.json"), "review candidate differs from integrated candidate")
            if payload["status"] != "accepted":
                issues.extend(["review: " + issue for issue in payload["issues"]] or ["review: held without acceptance"])
        if current:
            require(file_hash(work_file(work, CANDIDATE)) == file_hash(evidence / "candidate.json"), "candidate changed after its producing/reviewing attempt")
    if sealed:
        require(load_json(evidence / "reports.json") == reports, "saved handoffs differ from native results")
    if current:
        for role in ROLES:
            if assignment(work, role)["fingerprint"] != reports[role]["fingerprint"]:
                issues.append(f"{role}: source, brief, role or control changed; dependent results are stale")
        if stage in {"integrate", "review"}:
            if file_hash(work_file(work, f"shared/prompts/{stage}.md")) != file_hash(evidence / "inputs/stage.md"):
                issues.append(f"{stage}: coordination brief changed; dependent results are stale")
        if stage == "review":
            if file_hash(work_file(work, "shared/agents/review.md")) != file_hash(evidence / "inputs/roles/review.md"):
                issues.append("review: role changed; candidate acceptance is stale")
    return {"run_id": policy["run_id"], "stage": stage, "reports": reports, "issues": issues,
            "dispatched": dispatch, "reused": reused, "omp_version": omp_ver}


def summary(audit):
    return {"status": "HOLD" if audit["issues"] else "PASS", "stage": audit["stage"],
            "run_id": audit["run_id"], "omp_version": audit["omp_version"], "issues": audit["issues"], "dispatched": audit["dispatched"],
            "reused": audit["reused"],
            "accepted_roles": [role for role in ROLES if audit["reports"].get(role, {}).get("report", {}).get("status") == "complete" and not any(issue.startswith(role + ":") for issue in audit["issues"])],
            "blocked_roles": [role for role in ROLES if audit["reports"].get(role, {}).get("report", {}).get("status") == "blocked"]}
