#!/usr/bin/env python3
"""Run bounded native OMP stages; preserve and independently check their evidence."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import orchestration_evidence as evidence

ENV_KEYS = {"PATH", "LANG", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT",
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy",
            "all_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE",
            "CURL_CA_BUNDLE", "NODE_EXTRA_CA_CERTS"}
TIMEOUT_SECONDS = 300


def validate_work(path):
    original = Path(path).expanduser()
    evidence.require(not original.is_symlink(), "work root cannot be a link")
    work = original.resolve(strict=True)
    evidence.require(work.is_dir(), "work root must be a directory")
    evidence.require(not any((parent / ".git").exists() for parent in (work, *work.parents)), "work must be outside a Git checkout; use prepare_work.py")
    for name in ("scripts/orchestrate.py", "scripts/orchestration_evidence.py", evidence.GUARD):
        evidence.require(evidence.work_file(work, name).is_file(), f"required control missing: {name}")
    evidence.require(evidence.file_hash(work / "scripts/orchestrate.py") == evidence.file_hash(Path(__file__)), "run the launcher belonging to this work attempt")
    evidence.work_snapshot(work)
    return work


def inspect_work(work):
    assignments = {role: evidence.assignment(work, role) for role in evidence.ROLES}
    for role, assignment in assignments.items():
        if assignment["source_exists"]:
            source = evidence.load_json(evidence.work_file(work, assignment["input"]))
            evidence.current_record(source)
            evidence.require(source.get("role") == role, f"{role}: assigned source belongs to another specialist")
    evidence.role_body((work / "shared/agents/review.md").read_text(encoding="utf-8"), "review")
    for stage in evidence.STAGES:
        evidence.require((work / f"shared/prompts/{stage}.md").read_text(encoding="utf-8").strip(), f"{stage}: coordination brief is empty")
    return assignments


def isolated_environment(runtime, policy, key):
    environment = {name: value for name, value in os.environ.items() if name in ENV_KEYS or name.startswith("LC_")}
    environment["OPENROUTER_API_KEY"] = key
    environment["ORCHESTRATION_GUARD_POLICY"] = str(policy)
    for name, folder in {"HOME": "home", "USERPROFILE": "home", "APPDATA": "appdata", "LOCALAPPDATA": "localappdata",
                         "XDG_CONFIG_HOME": "config", "XDG_CACHE_HOME": "cache", "XDG_DATA_HOME": "data",
                         "XDG_STATE_HOME": "state", "XDG_RUNTIME_DIR": "xdg-runtime", "TMPDIR": "tmp", "TEMP": "tmp", "TMP": "tmp"}.items():
        target = runtime / folder
        target.mkdir(parents=True, exist_ok=True)
        environment[name] = str(target)
    return environment


def select_prior(work, stage, prior_path, assignments, omp_version):
    if stage == "fanout":
        evidence.require(prior_path is None, "fanout must not have --prior")
        evidence.require(not (work / evidence.CANDIDATE).exists(), "a first fanout needs a new work attempt without a candidate")
        return None, {}, [], list(evidence.ROLES)
    evidence.require(prior_path is not None, f"{stage} requires --prior")
    prior_path = Path(prior_path).expanduser().resolve(strict=True)
    prior = evidence.audit_attempt(work, prior_path, current=stage == "review")
    evidence.require(prior["omp_version"] == omp_version,
                     "OMP version changed since the prior attempt; start a fresh fanout chain")
    required_stages = {"integrate"} if stage == "review" else {"fanout", "repair"}
    evidence.require(prior["stage"] in required_stages, f"{stage}: incompatible prior stage")
    reports = prior["reports"]
    reusable = [role for role in evidence.ROLES if reports[role]["report"]["status"] == "complete"
                and reports[role]["fingerprint"] == assignments[role]["fingerprint"]]
    if stage == "repair":
        dispatched = [role for role in evidence.ROLES if role not in reusable]
        evidence.require(dispatched, "no invalidated specialist work to repair")
    else:
        evidence.require(reusable == list(evidence.ROLES), "all required handoffs must be accepted and unchanged before integration/review")
        evidence.require(not prior["issues"], "prior stage is held")
        dispatched = ["review"] if stage == "review" else []
    if stage == "review":
        evidence.require(evidence.file_hash(work / evidence.CANDIDATE) == evidence.file_hash(prior_path / "candidate.json"), "candidate changed since integration")
    reference = {"path": str(prior_path), "seal_sha256": evidence.file_hash(prior_path / "seal.json")}
    return reference, reports, reusable, dispatched


def native_binary(explicit):
    located = explicit or shutil.which("omp")
    evidence.require(located, "Oh My Pi is missing; complete platform setup for the latest stable release")
    binary = Path(located).expanduser().resolve(strict=True)
    result = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=20)
    version = result.stdout.strip()
    evidence.require(result.returncode == 0 and evidence.valid_omp_version(version),
                     f"invalid OMP version identity: {version or result.stderr.strip()}")
    return binary, version


def task_item(role, text):
    return {"name": role.title(), "agent": role, "task": text,
            "solutionSpace": "Read only assigned current sources; return the exact structured handoff or a source-specific blocked result.",
            "outputSchema": evidence.REVIEW_SCHEMA if role == "review" else evidence.REPORT_SCHEMA,
            "schemaMode": "strict"}


def copy_input(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())


def prepare_attempt(work, destination, stage, assignments, prior, reports, reused, dispatched, omp_version):
    original = Path(destination).expanduser()
    evidence.require(not original.exists() and not original.is_symlink(), "evidence destination already exists; choose a new path")
    output = original.resolve()
    evidence.require(not output.is_relative_to(work) and not work.is_relative_to(output), "evidence and work must be separate, non-overlapping roots")
    evidence.require(not any((parent / ".git").exists() for parent in output.parents), "evidence must be outside a Git checkout")
    if prior:
        old = Path(prior["path"])
        evidence.require(not output.is_relative_to(old) and not old.is_relative_to(output), "new evidence must not overlap prior evidence")
    output.mkdir(parents=True, exist_ok=False)
    runtime = output / ".runtime"
    cwd = runtime / "home/cwd"
    (cwd / ".omp/agents").mkdir(parents=True)
    for role in (*evidence.ROLES, "review"):
        copy_input(work / f"shared/agents/{role}.md", output / f"inputs/roles/{role}.md")
    for role in evidence.ROLES:
        copy_input(work / assignments[role]["brief"], output / f"inputs/briefs/{role}.md")
        if assignments[role]["source_exists"]:
            copy_input(work / assignments[role]["input"], output / f"inputs/sources/{role}.json")
    for name in ("orchestrate.py", "orchestration_evidence.py"):
        copy_input(work / "scripts" / name, output / "inputs/controls" / name)
    copy_input(work / evidence.GUARD, output / "inputs/controls/orchestration_guard.mjs")
    stage_text = (work / f"shared/prompts/{stage}.md").read_text(encoding="utf-8")
    copy_input(work / f"shared/prompts/{stage}.md", output / "inputs/stage.md")
    reads = {"main": {}}
    role_files = {}
    for role in dispatched:
        target = cwd / f".omp/agents/{role}.md"
        copy_input(work / f"shared/agents/{role}.md", target)
        role_files[role] = {"file": str(target), "sha256": evidence.file_hash(target)}
        reads[role] = {}
        if role in evidence.ROLES:
            assigned = assignments[role]
            reads[role][assigned["input"]] = {"file": str(work / assigned["input"]), "sha256": assigned["fingerprint"]["source"]}
    if stage in {"integrate", "review"}:
        evidence.write_json(output / "accepted-handoffs.json", reports)
        scope = "main" if stage == "integrate" else "review"
        reads[scope]["accepted-handoffs.json"] = {"file": str(output / "accepted-handoffs.json"), "sha256": evidence.file_hash(output / "accepted-handoffs.json")}
        for role in evidence.ROLES:
            assigned = assignments[role]
            reads[scope][assigned["input"]] = {"file": str(work / assigned["input"]), "sha256": assigned["fingerprint"]["source"]}
        if stage == "review":
            copy_input(work / evidence.CANDIDATE, output / "candidate.json")
            reads[scope][evidence.CANDIDATE] = {"file": str(work / evidence.CANDIDATE), "sha256": evidence.file_hash(output / "candidate.json")}
    candidate_before = evidence.file_hash(work / evidence.CANDIDATE) if (work / evidence.CANDIDATE).exists() else None
    if candidate_before and stage == "integrate":
        copy_input(work / evidence.CANDIDATE, output / "candidate-before.json")
    task_call = None
    if dispatched:
        tasks = [task_item(role, stage_text if role == "review" else assignments[role]["text"]) for role in dispatched]
        task_call = {"context": evidence.CONTEXT, "tasks": tasks}
    policy = {
        "schema_version": 1, "run_id": str(uuid.uuid4()), "stage": stage,
        "work_root": str(work), "evidence_root": str(output), "provider": evidence.PROVIDER,
        "model": evidence.MODEL, "omp_version": omp_version,
        "guard_source_sha256": evidence.file_hash(work / evidence.GUARD), "guard_log": str(output / "guard.jsonl"),
        "parent_tools": ["course_read", "course_write"] if stage == "integrate" else ["task"],
        "reads": reads, "write_file": evidence.CANDIDATE if stage == "integrate" else None,
        "output_before_sha256": candidate_before, "task_call": task_call, "role_files": role_files,
        "max_provider_requests": 12, "prior": prior, "reused": reused, "dispatched": dispatched,
        "fingerprints": {role: assignments[role]["fingerprint"] for role in evidence.ROLES},
        "assignments": {role: {key: value for key, value in assigned.items() if key != "text"} for role, assigned in assignments.items()},
    }
    evidence.write_json(output / "policy.json", policy)
    overlay = {"retry": {"enabled": False, "modelFallback": False}, "providers": {"cacheWarming": "off"},
               "async": {"enabled": False}, "task": {"batch": True, "maxConcurrency": 3, "maxRecursionDepth": 1},
               "tools": {"approval": {name: "allow" for name in ("course_read", "course_write", "task", "yield")}, "intentTracing": False}}
    evidence.write_json(output / "runtime-config.json", overlay)
    if task_call:
        prompt = (stage_text + "\n\nCall the native task tool exactly ONCE with the JSON below. Copy its context, task strings, "
                  "names, roles and schemas exactly; do not paraphrase the assignments. Do not schedule any other work. "
                  "After results return, briefly identify complete or blocked handoffs. A blocked child is not permission "
                  "to retry, supply an alternative file or integrate.\n\n" + evidence.json_bytes(task_call).decode())
    else:
        prompt = evidence.CONTEXT + "\n\n" + stage_text
    (output / "prompt.txt").write_text(prompt, encoding="utf-8")
    evidence.write_json(output / "work-before.json", evidence.work_snapshot(work))
    return output, policy, cwd, prompt


def execute_native(work, output, cwd, prompt, binary, omp_version, key):
    environment = isolated_environment(output / ".runtime", output / "policy.json", key)
    command = [str(binary), "--provider", evidence.PROVIDER, "--model", evidence.MODEL, "--thinking", "low",
               "--mode", "json", "-p", "--no-title", "--no-skills", "--no-rules", "--no-extensions", "--no-lsp",
               "--no-prewalk", "--no-pty", "--max-time", str(TIMEOUT_SECONDS), "--approval-mode", "always-ask", "--no-tools",
               "--tools", ",".join(evidence.load_json(output / "policy.json")["parent_tools"]),
               "--extension", str(work / evidence.GUARD), "--config", str(output / "runtime-config.json"),
               "--session-dir", str(output / "sessions")]
    outcome = {"command": command, "omp_version": omp_version, "binary_sha256": evidence.file_hash(binary),
               "returncode": None, "aborted": False, "timed_out": False}
    with (output / "stdout.jsonl").open("wb") as stdout, (output / "stderr.txt").open("wb") as stderr:
        child = subprocess.Popen(command, cwd=cwd, env=environment, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr)
        try:
            child.communicate(prompt.encode("utf-8"), timeout=TIMEOUT_SECONDS + 20)
        except (KeyboardInterrupt, subprocess.TimeoutExpired) as error:
            outcome["aborted"] = isinstance(error, KeyboardInterrupt)
            outcome["timed_out"] = isinstance(error, subprocess.TimeoutExpired)
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        outcome["returncode"] = child.returncode
    evidence.write_json(output / "process.json", outcome)
    evidence.write_json(output / "work-after.json", evidence.work_snapshot(work))
    return outcome


def run_stage(work, destination, stage, prior_path, explicit_omp):
    assignments = inspect_work(work)
    binary, omp_version = native_binary(explicit_omp)
    prior, reports, reused, dispatched = select_prior(work, stage, prior_path, assignments, omp_version)
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    evidence.require(key, "OPENROUTER_API_KEY is missing; load your current-process course credential")
    output, policy, cwd, prompt = prepare_attempt(work, destination, stage, assignments, prior, reports, reused, dispatched, omp_version)
    try:
        execute_native(work, output, cwd, prompt, binary, omp_version, key)
        if stage == "integrate" and (work / evidence.CANDIDATE).is_file():
            copy_input(work / evidence.CANDIDATE, output / "candidate.json")
        audit = evidence.audit_attempt(work, output, sealed=False)
        evidence.write_json(output / "reports.json", audit["reports"])
        result = evidence.summary(audit)
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {"status": "HOLD", "stage": stage, "run_id": policy["run_id"], "omp_version": omp_version,
                  "issues": [str(error)], "dispatched": dispatched, "reused": reused, "accepted_roles": [], "blocked_roles": []}
    evidence.write_json(output / "result.json", result)
    evidence.seal_attempt(output)
    print(evidence.json_bytes(result).decode(), end="")
    return 0 if result["status"] == "PASS" else 1


def check_stage(work, path):
    output = Path(path).expanduser().resolve()
    try:
        audit = evidence.audit_attempt(work, output)
        evidence.require(evidence.load_json(output / "reports.json") == audit["reports"], "saved handoffs differ from native results")
        result = evidence.summary(audit)
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {"status": "HOLD", "issues": [str(error)]}
    print(evidence.json_bytes(result).decode(), end="")
    return 0 if result["status"] == "PASS" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="inspect assignments without a model call")
    inspect.add_argument("--work", required=True)
    run = commands.add_parser("run", help="run one bounded native OMP stage")
    run.add_argument("--work", required=True)
    run.add_argument("--evidence", required=True)
    run.add_argument("--stage", required=True, choices=evidence.STAGES)
    run.add_argument("--prior")
    run.add_argument("--omp", help="explicit path to a verified OMP executable")
    check = commands.add_parser("check", help="independently verify saved evidence without a model call")
    check.add_argument("--work", required=True)
    check.add_argument("--evidence", required=True)
    arguments = parser.parse_args(argv)
    try:
        evidence.require(sys.version_info >= (3, 12), "Python 3.12 or newer is required")
        work = validate_work(arguments.work)
        if arguments.command == "inspect":
            assignments = inspect_work(work)
            result = {"status": "PASS", "omp_release_policy": "latest", "model": evidence.SELECTOR,
                      "graph": [list(evidence.ROLES), ["integrate"], ["review"], ["human decision"]],
                      "assignments": {role: {key: value for key, value in value.items() if key != "text"} for role, value in assignments.items()}}
            print(evidence.json_bytes(result).decode(), end="")
            return 0
        if arguments.command == "run":
            return run_stage(work, arguments.evidence, arguments.stage, arguments.prior, arguments.omp)
        return check_stage(work, arguments.evidence)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
