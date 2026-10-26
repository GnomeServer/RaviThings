#!/usr/bin/env python3
"""Run OMP with course-only tools and independently checked receipts.

This is an OMP tool boundary, not an operating-system sandbox. Exit 2 means
invalid invocation/prerequisites; exit 1 preserves an attempted but held run.

The `mcp` profile (--mcp-config and --authority) connects one declared MCP server and
joins the harness events, the guard decisions, the server's own audit log, and the
files on disk.

The `judge` profile (--judge-config, --judge-questions, --judge-states, --judge-output)
sets OMP's judge model role to the pinned OpenRouter decision model and lets the model
call `eval` once, with the frozen cell that runs shared/judge_runner.mjs. The launcher
then checks every saved judgment, the build that answered it, and the work folder.
`--list-judges` saves the judge models OMP offers through the course key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

PROVIDER = "openrouter"
MODEL = "anthropic/claude-sonnet-4.6"
SELECTOR = f"{PROVIDER}/{MODEL}"
GUARD = Path(__file__).with_name("course_guard.mjs")
JUDGE_RUNNER = Path(__file__).with_name("judge_runner.mjs")
JUDGE_SELECTOR = "openrouter/typesafe/jev-1.13"
JUDGE_MODEL = re.compile(r"openrouter/typesafe/jev-1\.13(?:-\d{8})?")
EVAL_KEYS = {"language", "code", "title", "timeout", "reset"}
DECLARATION = {"schema_version": 1, "yolo": False, "read_root": ".", "write_root": "artifacts", "tools": ["course_read", "course_write"], "skills": False, "gateway": False}
POLICY_KEYS = {"schema_version", "run_id", "work_root", "profile", "tools", "write_files", "write_root", "provider", "model", "omp_version", "prompt_sha256", "instruction", "declaration", "python", "guard_source_sha256", "runtime_config_sha256", "guard_log", "watch_paths"}
OPTIONAL_POLICY_KEYS = {"mcp", "snapshot_exclude", "judge", "thinking"}
MODULE_03_MCP = Path(__file__).resolve().parents[1] / "AI_Harness_Bootcamp_2" / "module-03-mcp-research" / "shared" / "mcp"
MCP_SERVER = "vault"
MCP_ENV = {"OMP_MCP_REQUIRE_READY": "1", "OMP_MCP_TIMEOUT_MS": "30000"}
ENV_KEYS = {"PATH", "LANG", "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "NODE_EXTRA_CA_CERTS"}


def valid_omp_version(version) -> bool:
    return isinstance(version, str) and bool(re.fullmatch(r"omp/[0-9]+\.[0-9]+\.[0-9]+", version))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def strict_json(text: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON number: {value}")))


def descriptor(value: str | None, label: str, nonempty: bool = True) -> dict | None:
    if value is None:
        return None
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"missing {label}: {path}")
    raw = path.read_bytes()
    if nonempty and not raw.decode("utf-8").strip():
        raise ValueError(f"empty {label}: {path}")
    return {"path": str(path), "sha256": sha256(raw)}


def overlap(left: Path, right: Path) -> bool:
    return left.is_relative_to(right) or right.is_relative_to(left)


def permission_path(value: str, work: Path) -> str:
    if not value or value in {".", ".."} or "\0" in value or any(char in value for char in ":?#") or Path(value).is_absolute() or PureWindowsPath(value).drive or value.startswith(("\\", "/")):
        raise ValueError(f"permission must be a relative output path: {value!r}")
    pieces = re.split(r"[\\/]", value)
    if any(piece in {"", ".", ".."} for piece in pieces):
        raise ValueError(f"invalid permission path: {value!r}")
    if any(re.fullmatch(r"(?:con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", piece, re.I) for piece in pieces):
        raise ValueError("device output paths are not allowed")
    relative = "/".join(pieces)
    target = (work / relative).resolve()
    if not target.is_relative_to(work):
        raise ValueError("permission path escapes through a link")
    return relative


def parse_declaration(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    blocks = re.findall(r"^```json\s*\n(.*?)^```\s*$", text, re.M | re.S)
    if len(blocks) != 1:
        raise ValueError("AGENT_POLICY.md must contain exactly one JSON block")
    declaration = strict_json(blocks[0])
    if declaration != DECLARATION or set(declaration) != set(DECLARATION) or type(declaration.get("schema_version")) is not int:
        raise ValueError("AGENT_POLICY.md must use the fixed class policy without extra keys or broader permissions")
    return declaration


SNAKE = re.compile(r"[a-z][a-z0-9_]{0,63}")


def learner_text(path: Path) -> str:
    """Read a file the learner edits; a byte-order mark is refused by name rather than misread."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        raise ValueError(f"{path.name} starts with a byte-order mark; save it as UTF-8 without one")
    return text


def parse_judge_config(path: Path) -> str:
    """Return the judge selector from the two-line OMP setting, refusing anything else."""
    lines = [line.rstrip() for line in learner_text(path).splitlines() if line.strip() and not line.lstrip().startswith("#")]
    match = re.fullmatch(r" +judge: *(['\"]?)([A-Za-z0-9._~/:@+-]+)\1", lines[1]) if len(lines) == 2 and lines[0] == "modelRoles:" else None
    if not match:
        raise ValueError("JUDGE.yml must hold exactly two setting lines: 'modelRoles:' and an indented 'judge: <selector>'")
    selector = match.group(2)
    if selector != JUDGE_SELECTOR:
        if "~" in selector:
            raise ValueError(f"judge selector {selector} is an alias that follows the newest release; pin {JUDGE_SELECTOR}")
        raise ValueError(f"judge selector {selector} is not the pinned decision model {JUDGE_SELECTOR}")
    return selector


def parse_questions(path: Path) -> dict:
    """Check a question file against the supported OMP judge bridge shapes."""
    data = strict_json(learner_text(path))
    if not isinstance(data, dict) or set(data) != {"schema_version", "questions"} or data["schema_version"] != 1 or type(data["schema_version"]) is not int:
        raise ValueError('the question file must be {"schema_version": 1, "questions": {...}}')
    questions = data["questions"]
    if not isinstance(questions, dict) or not 1 <= len(questions) <= 40:
        raise ValueError("the question file must define 1 to 40 questions")
    text = lambda value: isinstance(value, str) and bool(value.strip())
    for qid, question in questions.items():
        where = f"question {qid!r}"
        if not SNAKE.fullmatch(qid):
            raise ValueError(f"{where}: ids use lowercase letters, digits, and underscores")
        if not isinstance(question, dict) or question.get("type") not in {"bool", "choice", "score"} or set(question) - {"type", "instructions", "criteria"} or not text(question.get("instructions")):
            raise ValueError(f"{where}: needs type bool, choice, or score, text instructions, and no field other than criteria")
        criteria = question.get("criteria")
        if question["type"] == "bool":
            fits = criteria is None or (isinstance(criteria, dict) and bool(criteria) and set(criteria) <= {"true", "false"} and all(text(value) for value in criteria.values()))
        elif question["type"] == "choice":
            fits = isinstance(criteria, dict) and 2 <= len(criteria) <= 255 and all(SNAKE.fullmatch(label) and text(value) for label, value in criteria.items())
        else:
            fits = isinstance(criteria, list) and 2 <= len(criteria) <= 11 and all(text(value) for value in criteria)
        if not fits:
            raise ValueError(f"{where}: criteria do not fit a {question['type']} question; option and level descriptions must be text")
    return questions


def parse_states(directory: Path, work: Path) -> dict:
    folder = directory.expanduser().resolve()
    if not folder.is_dir() or not folder.is_relative_to(work):
        raise ValueError(f"the states folder must be inside the work folder: {folder}")
    files = sorted(folder.iterdir())
    if not 1 <= len(files) <= 200 or any(item.is_symlink() or not item.is_file() or item.suffix != ".json" for item in files):
        raise ValueError("the states folder must hold 1 to 200 regular .json files and nothing else")
    states = {}
    for item in files:
        record = strict_json(item.read_text(encoding="utf-8"))
        if not isinstance(record, dict) or set(record) != {"id", "state"} or record["id"] != item.stem or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", item.stem) or not isinstance(record["state"], (dict, str)) or len(json.dumps(record["state"])) > 20000:
            raise ValueError(f'state file {item.name} must be {{"id": <file name>, "state": <text or object>}} under 20,000 characters')
        states[item.stem] = {"path": str(item), "sha256": file_hash(item)}
    return states


def prepare_judge(args, work: Path) -> dict:
    """Check the judge setting, questions, states, and output before anything runs."""
    config = descriptor(args.judge_config, "JUDGE.yml")
    selector = parse_judge_config(Path(config["path"]))
    questions = descriptor(args.judge_questions, "question file")
    if not Path(questions["path"]).is_relative_to(work):
        raise ValueError("the question file must be inside the work folder")
    parsed = parse_questions(Path(questions["path"]))
    states_dir = Path(args.judge_states).expanduser().resolve()
    states = parse_states(states_dir, work)
    output = permission_path(args.judge_output, work)
    target = work / output
    if target.exists() or target.is_symlink():
        raise ValueError(f"judge output already exists: {output}; keep it and choose a new name")
    if not target.parent.is_dir():
        raise ValueError(f"the folder that holds the judge output is missing: {target.parent}")
    if not JUDGE_RUNNER.is_file():
        raise ValueError("judge_runner.mjs is missing; restore the published shared helper")
    return {"selector": selector, "config": config, "questions": questions, "parsed": parsed, "states": states, "states_dir": states_dir.relative_to(work).as_posix(), "output": output}


def judge_launch_files(prep: dict, work: Path, evidence: Path) -> tuple[str, dict]:
    """Freeze the exact question and setting bytes, write the plan, and return the prompt and policy.judge."""
    frozen_questions = evidence / "questions.json"
    frozen_questions.write_bytes(Path(prep["questions"]["path"]).read_bytes())
    (evidence / "judge-config.yml").write_bytes(Path(prep["config"]["path"]).read_bytes())
    plan = {"questions": str(frozen_questions), "states": {key: value["path"] for key, value in prep["states"].items()}, "output_dir": str(work / prep["output"]),
            "intent": f"Judging {len(prep['states'])} states", "concurrency": 8, "retries": 0, "deadline_seconds": 240}
    plan_file = evidence / "judge-plan.json"
    plan_file.write_bytes(json_bytes(plan))
    cell = f"return await (await import({json.dumps(JUDGE_RUNNER.resolve().as_uri())})).run({{ judgeBatch, plan: {json.dumps(plan_file.as_uri())} }});"
    prompt = ("Call the eval tool exactly once, with language \"js\" and this code, character for character:\n\n"
              f"```js\n{cell}\n```\n\nDo not call any other tool, and do not call eval a second time. When the result arrives, reply with the result text only.\n")
    parsed = prep["parsed"]
    judge = {"selector": prep["selector"], "config": prep["config"], "questions": prep["questions"],
             "frozen_questions": {"path": str(frozen_questions), "sha256": file_hash(frozen_questions)},
             "question_types": {qid: question["type"] for qid, question in parsed.items()},
             "choice_options": {qid: list(question["criteria"]) for qid, question in parsed.items() if question["type"] == "choice"},
             "score_levels": {qid: len(question["criteria"]) for qid, question in parsed.items() if question["type"] == "score"},
             "states": prep["states"], "states_dir": prep["states_dir"], "output": prep["output"],
             "runner": {"path": str(JUDGE_RUNNER.resolve()), "sha256": file_hash(JUDGE_RUNNER)},
             "plan": {"path": str(plan_file), "sha256": file_hash(plan_file)}, "cell_code": cell}
    return prompt, judge


def _unit(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1


def answer_problem(answer, kind: str, options: list | None, levels: int | None) -> str | None:
    if not isinstance(answer, dict) or answer.get("type") != kind:
        return f"expected a {kind} answer"
    if kind == "bool":
        return None if set(answer) == {"type", "bool"} and _unit(answer["bool"]) else "malformed yes probability"
    probabilities = answer.get("probabilities")
    if not isinstance(probabilities, dict) or not all(_unit(value) for value in probabilities.values()) or not _unit(answer.get("confidence")):
        return "malformed probabilities or confidence"
    if kind == "choice":
        return None if answer.get("choice") in options and set(probabilities) == set(options) else "choice outside the frozen options"
    score = answer.get("score")
    fits = set(probabilities) == {str(level) for level in range(levels)} and isinstance(score, (int, float)) and not isinstance(score, bool) and 0 <= score <= levels - 1
    return None if fits else "score outside the frozen levels"


def judge_output_errors(policy: dict) -> tuple[list[str], dict]:
    """Check saved judgments against the frozen questions and the pinned build; return errors and a summary."""
    judge = policy["judge"]
    folder = Path(policy["work_root"]) / judge["output"]
    try:
        rows = [strict_json(line) for line in (folder / "judgments.jsonl").read_text(encoding="utf-8").splitlines()]
        status = strict_json((folder / "batch-status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as error:
        return [f"judge output missing or malformed: {error}"], {}
    errors, models, expected = [], set(), list(judge["states"])
    if [row.get("key") if isinstance(row, dict) else None for row in rows] != expected:
        errors.append("judgments do not list every state exactly once, in order")
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"key", "answers", "error", "model"}:
            errors.append("malformed judgment row")
            continue
        key = row["key"]
        if row["error"] is not None or not isinstance(row["answers"], dict):
            errors.append(f"{key}: no judgment ({row['error']})")
            continue
        if not isinstance(row["model"], str) or not JUDGE_MODEL.fullmatch(row["model"]):
            errors.append(f"{key}: answered by {row['model']!r}, not the pinned judge")
        models.add(row["model"])
        if set(row["answers"]) != set(judge["question_types"]):
            errors.append(f"{key}: answers do not match the frozen question ids")
            continue
        for qid, kind in judge["question_types"].items():
            problem = answer_problem(row["answers"][qid], kind, judge["choice_options"].get(qid), judge["score_levels"].get(qid))
            if problem:
                errors.append(f"{key}.{qid}: {problem}")
    if len(models) > 1:
        errors.append(f"more than one judge build answered: {sorted(map(str, models))}")
    finished = isinstance(status, dict) and status.get("total") == len(expected) == status.get("done") and status.get("failed") == 0 and status.get("running") is False
    if not finished:
        errors.append("batch status does not show every state judged without failure")
    cost = status.get("cost") if isinstance(status, dict) else None
    if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
        errors.append("batch status lacks a cost")
    if isinstance(status, dict) and status.get("model") not in models:
        errors.append("batch status names a different judge build")
    summary = {"selector": judge["selector"], "served_model": next(iter(models)) if len(models) == 1 else None, "items": len(rows), "cost_usd": cost,
               "judgments_sha256": file_hash(folder / "judgments.jsonl"), "status_sha256": file_hash(folder / "batch-status.json")}
    return errors, summary


def judge_files(policy: dict) -> list[dict]:
    judge = policy.get("judge")
    return [judge["frozen_questions"], judge["runner"], judge["plan"], *judge["states"].values()] if judge else []


def isolated_env(runtime: Path, policy: Path, key: str) -> dict[str, str]:
    environment = {name: value for name, value in os.environ.items() if name in ENV_KEYS or name.startswith("LC_")}
    environment["OPENROUTER_API_KEY"] = key
    environment["COURSE_GUARD_POLICY"] = str(policy)
    for name, folder in {"HOME": "home", "USERPROFILE": "home", "APPDATA": "appdata", "LOCALAPPDATA": "localappdata", "XDG_CONFIG_HOME": "config", "XDG_CACHE_HOME": "cache", "XDG_DATA_HOME": "data", "XDG_STATE_HOME": "state", "XDG_RUNTIME_DIR": "xdg-runtime", "TMPDIR": "tmp", "TEMP": "tmp", "TMP": "tmp"}.items():
        target = runtime / folder
        target.mkdir(exist_ok=True)
        environment[name] = str(target)
    return environment


def path_state(path: Path) -> dict:
    if path.is_symlink():
        return {"type": "link", "target": os.readlink(path)}
    if not path.exists():
        return {"type": "missing", "sha256": None}
    if path.is_file():
        return {"type": "file", "sha256": file_hash(path)}
    if path.is_dir():
        return {"type": "directory"}
    raise ValueError(f"unsupported filesystem object: {path}")


def work_snapshot(root: Path, exclude: tuple[str, ...] = ()) -> dict:
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if (Path(directory) / name).relative_to(root).as_posix() not in exclude]
        for name in sorted(dirs + files):
            path = Path(directory) / name
            result[path.relative_to(root).as_posix()] = path_state(path)
    return dict(sorted(result.items()))


def snapshot(work: Path, watches: list[Path], exclude: tuple[str, ...] = ()) -> dict:
    return {"work": work_snapshot(work, exclude), "watch": {str(path): path_state(path) for path in watches}}


def read_jsonl(path: Path) -> list[dict]:
    raw = path.read_bytes()
    if not raw or not raw.endswith(b"\n"):
        raise ValueError(f"missing or truncated JSONL: {path.name}")
    rows = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            raise ValueError(f"blank JSONL record: {path.name}")
        row = strict_json(line)
        if not isinstance(row, dict) or not isinstance(row.get("type"), str):
            raise ValueError(f"invalid event record: {path.name}")
        rows.append(row)
    return rows


def mcp_support():
    """Import the connection helpers and server constants that Module 03 ships."""
    if str(MODULE_03_MCP) not in sys.path:
        sys.path.insert(0, str(MODULE_03_MCP))
    import authority
    import vault_mcp
    return authority, vault_mcp


def mcp_tool_name(tool: str) -> str:
    return f"mcp__{MCP_SERVER}_{tool}"


def prepare_mcp(config: dict, authority_file: dict, work: Path) -> dict:
    """Check the two connection files and describe the connection. Raises ValueError with the reason."""
    auth, vault = mcp_support()
    for item in (config, authority_file):
        if not Path(item["path"]).resolve().is_relative_to(work):
            raise ValueError("mcp.json and AUTHORITY.md must be inside the work copy")
    try:
        declaration = auth.parse_authority(Path(authority_file["path"]).read_text(encoding="utf-8"))
        servers = auth.parse_config(Path(config["path"]).read_text(encoding="utf-8"))["mcpServers"]
        parsed = None
        if declaration["phase"] == "revoked":
            if servers:
                raise auth.AuthorityError("a revoked phase needs an empty mcpServers map in mcp.json")
        else:
            if set(servers) != {MCP_SERVER}:
                raise auth.AuthorityError(f"mcp.json must define exactly one server named {MCP_SERVER}")
            parsed = auth.validate_entry(servers[MCP_SERVER], work)
            problems = auth.consistency(declaration, parsed)
            if problems:
                raise auth.AuthorityError("; ".join(problems))
            if file_hash(parsed["script"]) != file_hash(MODULE_03_MCP / "vault_mcp.py"):
                raise auth.AuthorityError("the work copy's vault_mcp.py differs from the course's; prepare a new work copy instead of editing the server")
    except auth.AuthorityError as error:
        raise ValueError(str(error)) from None
    return {"declaration": declaration, "parsed": parsed, "vault": vault}


def mcp_launch_files(prep: dict, work: Path, evidence: Path) -> tuple[bytes, bytes, dict]:
    """Return (hermetic mcp.json bytes, authority.json bytes, policy.mcp) for one run."""
    declaration, parsed, vault = prep["declaration"], prep["parsed"], prep["vault"]
    audit = str(evidence / "mcp-audit.jsonl")
    if parsed is None:
        document = {"mcpServers": {}}
        flags, offered, script = None, [], None
    else:
        flag_args = []
        if parsed["read_only"]:
            flag_args.append("--read-only")
        if parsed["no_overwrite"]:
            flag_args.append("--no-overwrite")
        for prefix in parsed["read_prefixes"]:
            flag_args += ["--read-prefix", prefix]
        for prefix in parsed["write_prefixes"]:
            flag_args += ["--write-prefix", prefix]
        if parsed["max_results"]:
            flag_args += ["--max-results", str(parsed["max_results"])]
        entry = {"type": "stdio", "command": str(Path(sys.executable).resolve()), "args": [str(parsed["script"]), "--root", str(work / "vault"), *flag_args, "--audit-log", audit],
                 "instructions": parsed["instructions"], "timeout": 30000}
        document = {"mcpServers": {MCP_SERVER: entry}}
        flags = {"read_only": parsed["read_only"], "read_prefixes": sorted(parsed["read_prefixes"]), "write_prefixes": sorted(parsed["write_prefixes"]),
                 "no_overwrite": parsed["no_overwrite"], "max_results": parsed["max_results"] or 20}
        offered = [name for name in vault.TOOL_NAMES if not (parsed["read_only"] and name in vault.MUTATING_TOOLS)]
        script = {"path": str(parsed["script"]), "sha256": file_hash(parsed["script"])}
    hermetic = json_bytes(document)
    declared = json_bytes(declaration)
    allowed = list(declaration["allow_tools"])
    policy_mcp = {"server": MCP_SERVER if parsed else None, "script": script, "phase": declaration["phase"], "allow_tools": allowed,
                  "allow_names": [mcp_tool_name(name) for name in allowed], "known_names": [mcp_tool_name(name) for name in vault.TOOL_NAMES] if parsed else [],
                  "read_scope": list(declaration["read_scope"]), "write_scope": list(declaration["write_scope"]), "create_only": declaration["create_only"],
                  "instructions": parsed["instructions"] if parsed else None, "flags": flags, "tools_offered": offered, "audit_log": audit,
                  "hermetic_config_sha256": sha256(hermetic), "declaration_sha256": sha256(declared)}
    return hermetic, declared, policy_mcp


def expected_approval(policy: dict) -> dict:
    mcp = policy.get("mcp")
    if not mcp:
        return {name: "allow" for name in policy["tools"]}
    return {name: ("allow" if name in mcp["allow_names"] else "deny") for name in mcp["known_names"]}


def normalize_arguments(arguments) -> dict:
    """Drop what OMP drops before a call: the intent field and empty optional values."""
    if not isinstance(arguments, dict):
        return {}
    return {key: value for key, value in arguments.items() if key != "i" and value not in ("", None, {})}


def redact_arguments(arguments: dict) -> dict:
    shown = {}
    for key, value in arguments.items():
        if key in ("content", "oldString", "newString") and isinstance(value, str):
            data = value.encode("utf-8")
            shown[f"{key}_sha256"] = sha256(data)
            shown[f"{key}_bytes"] = len(data)
        else:
            shown[key] = value
    return shown


def under(path: str, prefixes) -> bool:
    return any(path.startswith(prefix) for prefix in prefixes)


def join_mcp(policy: dict, calls: dict, results: dict, ends: dict, decisions: dict, audit: list[dict] | None) -> tuple[list[dict], list[str]]:
    """Match each assistant call to its guard decision and to the server's own audit row."""
    mcp, errors, records = policy["mcp"], [], []
    rows = [row for row in (audit or []) if row.get("type") == "tool_call"]
    unused = list(rows)
    for order, (identifier, call) in enumerate(calls.items(), 1):
        name = str(call.get("name", ""))
        result, end, decision = results.get(identifier, {}), ends.get(identifier, {}), decisions.get(identifier)
        record = {"order": order, "call_id": identifier, "tool": name, "arguments": call.get("arguments"), "result_is_error": bool(result.get("isError")),
                  "result_text": "".join(block.get("text", "") for block in result.get("content", []) if isinstance(block, dict)), "audit": None, "effect": None}
        if decision is None:
            record["classification"] = "DENIED_BY_RUNTIME"
        elif not decision.get("allow"):
            record["classification"] = "DENIED_BY_GUARD"
        else:
            tool = (result.get("details") or {}).get("mcpToolName") or name.removeprefix(f"mcp__{MCP_SERVER}_")
            wanted = normalize_arguments(redact_arguments(normalize_arguments(call.get("arguments"))))
            row = next((candidate for candidate in unused if candidate.get("tool") == tool and normalize_arguments(candidate.get("arguments")) == wanted), None)
            if row is None:
                record["classification"] = "ERROR"
                if not result.get("isError"):
                    errors.append(f"successful MCP call {identifier} has no matching server audit row")
            else:
                unused.remove(row)
                record["audit"], record["effect"] = row, row.get("effect")
                if not row.get("allowed"):
                    record["classification"] = "DENIED_BY_SERVER"
                elif row.get("is_error"):
                    record["classification"] = "ERROR"
                else:
                    record["classification"] = "EXECUTED"
                if bool(row.get("is_error")) != bool(result.get("isError")):
                    errors.append(f"MCP call {identifier}: server and harness disagree about whether it failed")
                for read in row.get("reads") or []:
                    if not under(read, mcp["read_scope"]):
                        errors.append(f"server returned a note outside read_scope: {read}")
        records.append(record)
    if unused:
        errors.append(f"server audit holds {len(unused)} call(s) the harness never made")
    start = next((row for row in (audit or []) if row.get("type") == "server_start"), None)
    if mcp["server"]:
        if start is None:
            errors.append("server audit has no server_start row")
        else:
            if start.get("flags") != mcp["flags"]:
                errors.append("server started with limits that differ from the frozen policy")
            if start.get("script_sha256") != mcp["script"]["sha256"]:
                errors.append("server script differs from the frozen policy")
            if start.get("tools_offered") != mcp["tools_offered"]:
                errors.append("server offered a different tool set than the frozen policy")
    elif audit:
        errors.append("a revoked phase started a server")
    return records, errors


def mcp_disk_errors(policy: dict, records: list[dict], before: dict, after: dict) -> list[str]:
    mcp, errors, effects = policy["mcp"], [], {}
    for record in records:
        effect = record.get("effect")
        if not effect:
            continue
        effects[effect["path"]] = effect
        if effect["op"] not in ("create", "append", "overwrite"):
            errors.append(f"a tool outside the live-run ceiling changed the vault: {effect['op']} {effect['path']}")
        if mcp["write_scope"] and not under(effect["path"], mcp["write_scope"]):
            errors.append(f"server changed a note outside write_scope: {effect['path']}")
        if mcp["create_only"] and effect["op"] != "create":
            errors.append(f"create_only is declared but the server performed {effect['op']} on {effect['path']}")
    for relative in before:
        if relative not in after:
            errors.append(f"existing file or folder was removed: {relative}")
    for relative, state in after.items():
        old = before.get(relative)
        if old == state:
            continue
        if not relative.startswith("vault/"):
            errors.append(f"change outside the vault: {relative}")
            continue
        inside = relative[len("vault/"):]
        if state.get("type") == "directory":
            if not any(path == inside or path.startswith(inside + "/") for path in effects):
                errors.append(f"unexplained new folder: {relative}")
            continue
        effect = effects.get(inside)
        if not effect or effect.get("sha256_after") != state.get("sha256"):
            errors.append(f"unreceipted vault change: {relative}")
        elif old is not None and mcp["create_only"]:
            errors.append(f"an existing note changed although create_only is declared: {relative}")
    return errors


def validate_run(policy: dict, events: list[dict], guard: list[dict], snapshots: dict, child_exit: int, audit: list[dict] | None = None) -> list[str]:
    errors = []
    def require(condition, reason):
        if not condition:
            errors.append(reason)
    require(child_exit == 0, f"OMP exited {child_exit}")
    mcp, judge = policy.get("mcp"), policy.get("judge")
    require(set(policy) - OPTIONAL_POLICY_KEYS == POLICY_KEYS and set(policy) & OPTIONAL_POLICY_KEYS <= OPTIONAL_POLICY_KEYS and (mcp is not None) == (policy.get("profile") == "mcp")
            and (judge is not None) == (policy.get("profile") == "judge") and (not judge or policy.get("tools") == ["eval"]) and policy.get("schema_version") == 1, "resolved policy schema differs")
    require(policy.get("provider") == PROVIDER and policy.get("model") == MODEL, "pinned provider/model differs")
    require("thinking" not in policy or policy["thinking"] == "low", "unsupported explicit thinking level")
    require(valid_omp_version(policy.get("omp_version")), "omp_version is not a recorded valid OMP identity")
    terminal = [row for row in events if row.get("type") == "agent_end" and row.get("isTerminal") is not False]
    require(len(terminal) == 1, "expected exactly one terminal agent_end")
    require(not any(re.search(r"retry|fallback", row.get("type", "")) or row.get("type") in {"model_changed", "extension_error"} for row in events), "retry, fallback, model drift, or extension error observed")
    require(bool(guard) and guard[0].get("type") == "guard_ready" and guard[-1].get("type") == "guard_end", "guard lifecycle missing or out of order")
    require(sum(row.get("type") == "guard_ready" for row in guard) == 1 and sum(row.get("type") == "guard_end" for row in guard) == 1, "guard lifecycle duplicated or incomplete")
    require(all(row.get("run_id") == policy.get("run_id") for row in guard), "guard run identity differs")
    require(not any(row.get("type") == "guard_error" for row in guard), "guard initialization or identity failed")
    ready = next((row for row in guard if row.get("type") == "guard_ready"), {})
    require(sorted(ready.get("active_tools", [])) == sorted(list(policy.get("tools", [])) + (mcp["allow_names"] if mcp else [])), "active tools differ from frozen policy")
    requests = [row for row in guard if row.get("type") == "provider_request"]
    require(bool(requests), "no observed provider request")
    if mcp:
        require(all(row.get("tools") == sorted(mcp["allow_names"]) for row in requests), "a provider request offered tools outside the declaration")
    require(all((row.get("provider"), row.get("model")) == (PROVIDER, MODEL) for row in [ready, *requests]), "guard provider/model drift")
    ending = next((row for row in guard if row.get("type") == "guard_end"), {})
    require(ending.get("ready") is True and ending.get("failed") is False, "guard did not finish in a ready, unfailed state")
    require(ending.get("provider_requests") == len(requests), "provider-request count differs")
    if policy.get("instruction"):
        loads = [i for i, row in enumerate(guard) if row.get("type") == "instruction_loaded"]
        first_request = next((i for i, row in enumerate(guard) if row.get("type") == "provider_request"), -1)
        require(bool(loads) and loads[0] < first_request, "saved instruction was not observed before the first request")
        for i in loads:
            row = guard[i]
            require(row.get("file_sha256") == policy["instruction"]["sha256"] and row.get("loaded_text_sha256") == sha256(Path(policy["instruction"]["path"]).read_bytes().decode("utf-8").strip().encode("utf-8")), "loaded instruction identity differs")
    messages = [row.get("message", {}) for row in events if row.get("type") == "message_end"]
    assistants = [message for message in messages if message.get("role") == "assistant"]
    require(bool(assistants) and assistants[-1].get("stopReason") == "stop", "final assistant did not complete normally")
    require(all((message.get("provider"), message.get("model")) == (PROVIDER, MODEL) for message in assistants), "assistant identity drift")
    if terminal and assistants:
        final = [message for message in terminal[0].get("messages", []) if message.get("role") == "assistant"]
        # The streamed OMP message can carry completedAt without it appearing
        # in the terminal agent-loop message. All other fields must match.
        streamed = dict(assistants[-1])
        if final and "completedAt" not in final[-1]:
            streamed.pop("completedAt", None)
        require(bool(final) and final[-1] == streamed, "terminal and streamed assistant records disagree")
    calls, results, starts, ends, decisions, checks, executed, positions = {}, {}, {}, {}, {}, {}, {}, {}
    for message in messages:
        if message.get("role") == "assistant":
            for block in message.get("content", []):
                if block.get("type") == "toolCall":
                    identifier = block.get("id")
                    require(isinstance(identifier, str) and identifier not in calls, "missing or duplicated assistant call ID")
                    calls[identifier] = block
        elif message.get("role") == "toolResult":
            identifier = message.get("toolCallId")
            require(identifier not in results, "duplicated tool result")
            results[identifier] = message
    for row in events:
        if row.get("type") in {"tool_execution_start", "tool_execution_end"}:
            destination = starts if row["type"] == "tool_execution_start" else ends
            identifier = row.get("toolCallId")
            require(identifier not in destination, "duplicated execution event")
            destination[identifier] = row
    for position, row in enumerate(guard):
        if row.get("type") in {"decision", "execution_check", "executed"}:
            destination = {"decision": decisions, "execution_check": checks, "executed": executed}[row["type"]]
            identifier = row.get("call_id")
            require(identifier not in destination, "duplicated guard call record")
            destination[identifier] = row
            positions[(row["type"], identifier)] = position
    require(set(calls) == set(results) == set(starts) == set(ends), "unmatched assistant calls, executions, or results")
    require(set(decisions).issubset(calls) and set(checks).issubset(calls) and set(executed).issubset(calls), "guard record has no actual assistant call")
    writes = {}
    for identifier, call in calls.items():
        start, end, result = starts.get(identifier, {}), ends.get(identifier, {}), results.get(identifier, {})
        require(start.get("toolName") == end.get("toolName") == result.get("toolName") == call.get("name"), "tool name mismatch")
        # OMP drops empty optional eval arguments (for example "reset": null) before it executes the call.
        arguments = normalize_arguments(call.get("arguments")) if judge and call.get("name") == "eval" else call.get("arguments")
        require(start.get("args") == arguments, "tool arguments differ from assistant call")
        require(end.get("isError") == result.get("isError") and end.get("result", {}).get("content") == result.get("content"), "execution/result mismatch")
        decision = decisions.get(identifier)
        if decision:
            require(decision.get("tool") == call.get("name") and decision.get("arguments") == arguments, "guard decision does not match call")
            if not decision.get("allow"):
                require(end.get("isError") is True and identifier not in executed, "denied call executed successfully")
        else:
            # Unknown tools are rejected before the extension hook is entered.
            require(call.get("name") not in policy.get("tools", []) and end.get("isError") is True and "not found" in json.dumps(end.get("result", {})).lower(), "call lacks a guard decision or observed runtime rejection")
        if end.get("isError") is False:
            if mcp and str(call.get("name", "")).startswith("mcp__"):
                require(bool(decision and decision.get("allow")) and call.get("name") in mcp["allow_names"], "successful MCP call lacks a guard decision for a declared tool")
            elif judge and call.get("name") == "eval":
                arguments = call.get("arguments", {})
                require(bool(decision and decision.get("allow")), "successful eval lacks an allowing guard decision")
                require(set(arguments) <= EVAL_KEYS and arguments.get("language") == "js" and arguments.get("code") == judge["cell_code"], "eval ran code other than the frozen judge cell")
            else:
                require(identifier in executed and bool(decision and decision.get("allow")), "successful call lacks actual guarded execution")
        if identifier in executed:
            check = checks.get(identifier, {})
            effect = executed[identifier]
            target = Path(effect.get("resolved_path", ""))
            require(call.get("name") in policy["tools"], "executed tool was not declared")
            require(target.is_absolute() and target.is_relative_to(Path(policy["work_root"])), "executed path exceeded the work root")
            require(check.get("allow") is True and check.get("arguments") == call.get("arguments") and check.get("tool") == call.get("name"), "successful execution lacks its independent authorization")
            require(effect.get("tool") == call.get("name") and effect.get("resolved_path") == check.get("resolved_path") == (decision or {}).get("resolved_path"), "executed tool/path differs from its authorization")
            require(positions.get(("decision", identifier), -1) < positions.get(("execution_check", identifier), -1) < positions[("executed", identifier)], "execution preceded its authorization")
            require(end.get("isError") is False, "guard claims execution but runtime reports error")
            if call.get("name") == "course_write":
                writes[executed[identifier].get("resolved_path")] = executed[identifier].get("output_sha256")
    before, after = snapshots["before"], snapshots["after"]
    require(before["watch"] == after["watch"], "watched target changed")
    work = Path(policy["work_root"])
    if mcp:
        records, joined = join_mcp(policy, calls, results, ends, decisions, audit)
        errors.extend(joined)
        errors.extend(mcp_disk_errors(policy, records, before["work"], after["work"]))
        if mcp["phase"] == "revoked":
            require(all(record["classification"] == "DENIED_BY_RUNTIME" for record in records), "a revoked phase executed or reached a tool")
    elif judge:
        ran = [identifier for identifier, call in calls.items() if call.get("name") == "eval" and ends.get(identifier, {}).get("isError") is False]
        require(len(ran) == 1, f"expected exactly one completed judge cell, observed {len(ran)}")
        for relative, old in before["work"].items():
            require(after["work"].get(relative) == old, f"existing input/control changed: {relative}")
        declared = {judge["output"], f"{judge['output']}/judgments.jsonl", f"{judge['output']}/batch-status.json"}
        added = set(after["work"]) - set(before["work"])
        require(added == declared and after["work"].get(judge["output"], {}).get("type") == "directory", f"judge run changed the work folder beyond its declared output: {sorted(added ^ declared)}")
        if added == declared:
            errors.extend(judge_output_errors(policy)[0])
    else:
        for relative, old in before["work"].items():
            require(after["work"].get(relative) == old, f"existing input/control changed: {relative}")
        for relative, current in after["work"].items():
            if relative in before["work"]:
                continue
            absolute = str(work / relative)
            if current.get("type") == "directory":
                require(any(Path(output).is_relative_to(work / relative) for output in writes), f"unexplained new directory: {relative}")
            else:
                require(current.get("type") == "file" and writes.get(absolute) == current.get("sha256"), f"unreceipted output or forbidden effect: {relative}")
        for absolute, digest in writes.items():
            target = Path(absolute)
            permitted = target.is_relative_to(work) and (target.relative_to(work).as_posix() in policy["write_files"] or bool(policy["write_root"] and target.is_relative_to(work / policy["write_root"])))
            require(permitted, f"write exceeded policy: {absolute}")
            if target.is_relative_to(work):
                require(after["work"].get(target.relative_to(work).as_posix(), {}).get("sha256") == digest, "tool-written output differs from disk snapshot")
    return errors


def mcp_call_records(evidence: Path) -> list[dict]:
    """One record per assistant tool call in a saved MCP run: tool, arguments, classification, audit row, effect."""
    policy = strict_json((evidence / "policy.json").read_text(encoding="utf-8"))
    events = read_jsonl(evidence / "events.jsonl")
    guard = read_jsonl(evidence / "guard.jsonl")
    audit = read_jsonl(evidence / "mcp-audit.jsonl") if (evidence / "mcp-audit.jsonl").is_file() else []
    calls, results, ends, decisions = {}, {}, {}, {}
    for row in events:
        if row.get("type") == "message_end":
            message = row.get("message", {})
            if message.get("role") == "assistant":
                for block in message.get("content", []):
                    if block.get("type") == "toolCall":
                        calls[block["id"]] = block
            elif message.get("role") == "toolResult":
                results[message.get("toolCallId")] = message
        elif row.get("type") == "tool_execution_end":
            ends[row.get("toolCallId")] = row
    for row in guard:
        if row.get("type") == "decision":
            decisions[row.get("call_id")] = row
    records, _ = join_mcp(policy, calls, results, ends, decisions, audit)
    return records


def _response_text(events: list[dict]) -> str:
    assistants = [row.get("message", {}) for row in events if row.get("type") == "message_end" and row.get("message", {}).get("role") == "assistant"]
    return "".join(block.get("text", "") for block in (assistants[-1].get("content", []) if assistants else []) if block.get("type") == "text")


def audit_evidence(evidence: Path) -> list[str]:
    """Recheck saved receipts without trusting an assistant's description."""
    try:
        policy = strict_json((evidence / "policy.json").read_text(encoding="utf-8"))
        result = strict_json((evidence / "result.json").read_text(encoding="utf-8"))
        snapshots = strict_json((evidence / "snapshots.json").read_text(encoding="utf-8"))
        events = read_jsonl(evidence / "events.jsonl")
        guard = read_jsonl(evidence / "guard.jsonl")
        audit = read_jsonl(evidence / "mcp-audit.jsonl") if policy.get("mcp") and (evidence / "mcp-audit.jsonl").is_file() else None
        errors = validate_run(policy, events, guard, snapshots, result["exit_code"], audit)
        if (evidence / "response.md").read_text(encoding="utf-8") != _response_text(events):
            errors.append("saved response differs from final assistant event")
        expected = {
            "policy_sha256": file_hash(evidence / "policy.json"),
            "guard_sha256": file_hash(evidence / "guard.jsonl"),
            "declared_policy_sha256": policy["declaration"]["sha256"] if policy.get("declaration") else None,
            "instruction_sha256": policy["instruction"]["sha256"] if policy.get("instruction") else None,
            "input_sha256": {name: value["sha256"] for name, value in snapshots["before"]["work"].items() if value["type"] == "file"},
            "output_sha256": {name: value.get("sha256") for name, value in snapshots["after"]["work"].items() if value["type"] == "file" and value != snapshots["before"]["work"].get(name)},
        }
        if policy.get("mcp"):
            expected["mcp"] = {"config_sha256": policy["mcp"]["config"]["sha256"] if policy["mcp"].get("config") else None,
                               "authority_sha256": policy["mcp"]["authority"]["sha256"] if policy["mcp"].get("authority") else None,
                               "audit_sha256": file_hash(evidence / "mcp-audit.jsonl") if (evidence / "mcp-audit.jsonl").is_file() else None, "calls": len(mcp_call_records(evidence))}
            if file_hash(evidence / "mcp.json") != policy["mcp"]["hermetic_config_sha256"] or file_hash(evidence / "authority.json") != policy["mcp"]["declaration_sha256"]:
                errors.append("saved connection files differ from the frozen policy")
        elif "mcp" in result:
            errors.append("a non-MCP run carries MCP evidence")
        if policy.get("judge"):
            expected["judge"] = judge_output_errors(policy)[1]
            saved = {"questions.json": policy["judge"]["frozen_questions"]["sha256"], "judge-config.yml": policy["judge"]["config"]["sha256"], "judge-plan.json": policy["judge"]["plan"]["sha256"]}
            if any(file_hash(evidence / name) != digest for name, digest in saved.items()):
                errors.append("saved judge files differ from the frozen policy")
        elif "judge" in result:
            errors.append("a non-judge run carries judge evidence")
        for key, value in expected.items():
            if result.get(key) != value:
                errors.append(f"{key} differs")
        if result.get("provider") != PROVIDER or result.get("model") != MODEL:
            errors.append("result provider/model differs")
        if result.get("omp_version") != policy.get("omp_version"):
            errors.append("result omp_version differs from policy")
        if result.get("run_id") != policy.get("run_id") or result.get("status") != "PASS":
            errors.append("run identity or completion status differs")
        for row in guard:
            if row.get("type") in {"guard_ready", "guard_end", "instruction_loaded"} and row.get("policy_sha256") != expected["policy_sha256"]:
                errors.append("guard resolved-policy hash differs")
        frozen = [("instruction", policy.get("instruction")), ("declaration", policy.get("declaration"))]
        if policy.get("mcp"):
            # mcp.json and AUTHORITY.md legitimately change between phases; the evidence folder keeps the exact bytes each run used.
            frozen += [("server script", policy["mcp"].get("script"))]
        if policy.get("judge"):
            # JUDGE.yml and the question file legitimately change between runs; the evidence folder keeps the exact bytes each run used.
            frozen += [("judge runner", policy["judge"]["runner"])] + [(f"state {key}", item) for key, item in policy["judge"]["states"].items()]
        for key, item in frozen:
            if item and file_hash(Path(item["path"])) != item["sha256"]:
                errors.append(f"{key} file changed")
        if file_hash(evidence / "runtime-config.yml") != policy["runtime_config_sha256"]:
            errors.append("runtime overlay changed")
        overlay = strict_json((evidence / "runtime-config.yml").read_text(encoding="utf-8"))
        if overlay.get("retry") != {"enabled": False, "modelFallback": False} or overlay.get("providers", {}).get("cacheWarming") != "off" or overlay.get("tools", {}).get("approval") != expected_approval(policy):
            errors.append("runtime overlay does not disable retries/fallback/warming and authorize only declared tools")
        if overlay.get("modelRoles") != ({"judge": policy["judge"]["selector"]} if policy.get("judge") else None):
            errors.append("runtime overlay judge role differs from the frozen policy")
        for path, observed in snapshots["after"]["watch"].items():
            if path_state(Path(path)) != observed:
                errors.append(f"watched target changed after the run: {path}")
        return errors
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
        return [f"incomplete or malformed evidence: {error}"]


def list_judges(evidence_arg: Path) -> int:
    """Save and print the judge models OMP offers through the course key. No model is called."""
    try:
        evidence = evidence_arg.expanduser().absolute()
        if evidence.exists() or evidence.is_symlink():
            raise ValueError(f"evidence attempt already exists: {evidence}; choose a new directory")
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            raise ValueError("OPENROUTER_API_KEY unavailable; enter and export the key in this terminal")
        omp = shutil.which("omp")
        if not omp:
            raise ValueError("omp is not on PATH; install and verify the latest stable release")
    except (OSError, ValueError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="course-omp-runtime-") as temp:
        runtime = Path(temp).resolve()
        environment = isolated_env(runtime, runtime / "no-policy.json", key)
        cwd = Path(environment["HOME"]) / "cwd"
        cwd.mkdir()
        try:
            version = subprocess.run([omp, "--version"], cwd=cwd, env=environment, capture_output=True, text=True, timeout=15)
            omp_version = version.stdout.strip()
            if version.returncode or not valid_omp_version(omp_version):
                raise ValueError("omp --version did not return a valid omp/<semver> identity")
            listing = subprocess.run([omp, "models", "--kind", "judge", "--json"], cwd=cwd, env=environment, capture_output=True, text=True, timeout=120)
            if key in listing.stdout or key in listing.stderr:
                raise ValueError("the provider key appeared in the model listing; nothing was saved")
            if listing.returncode:
                raise ValueError(f"omp models exited {listing.returncode}: {listing.stderr.strip()[:300]}")
            catalog = strict_json(listing.stdout)
            models = catalog["models"]
            if not isinstance(models, list) or any(not isinstance(row, dict) or not isinstance(row.get("selector"), str) for row in models):
                raise ValueError("omp models returned an unexpected listing")
        except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
            print(f"HOLD: {error}", file=sys.stderr)
            return 2
    evidence.mkdir(parents=True)
    (evidence / "candidates.json").write_bytes(json_bytes(catalog))
    pinned = any(row["selector"] == JUDGE_SELECTOR for row in models)
    (evidence / "result.json").write_bytes(json_bytes({"omp_version": omp_version, "fetched_at": datetime.now(timezone.utc).isoformat(), "candidates": len(models), "pinned": JUDGE_SELECTOR, "pinned_offered": pinned, "candidates_sha256": file_hash(evidence / "candidates.json")}))
    price = lambda value: f"{value:.3f}" if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else "varies"
    print(f"{'judge model selector':50} {'context':>9} {'$/M input':>10} {'$/M output':>11}")
    for row in sorted(models, key=lambda row: row["selector"]):
        cost = row.get("cost") if isinstance(row.get("cost"), dict) else {}
        marker = "  <- course pin" if row["selector"] == JUDGE_SELECTOR else ""
        print(f"{row['selector']:50} {str(row.get('contextWindow', '?')):>9} {price(cost.get('input')):>10} {price(cost.get('output')):>11}{marker}")
    if not pinned:
        print(f"HOLD: {JUDGE_SELECTOR} is not offered through this key; saved {len(models)} candidates to {evidence / 'candidates.json'}")
        return 1
    print(f"PASS: saved {len(models)} judge candidates to {evidence / 'candidates.json'}; {JUDGE_SELECTOR} is offered")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path)
    parser.add_argument("--prompt")
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--instruction")
    parser.add_argument("--thinking", choices=("low",), help="Use bounded low thinking for this run; omission retains OMP's default")
    access = parser.add_mutually_exclusive_group()
    access.add_argument("--policy")
    access.add_argument("--allow-write", action="append", default=[])
    access.add_argument("--write-root")
    parser.add_argument("--mcp-config")
    parser.add_argument("--authority")
    parser.add_argument("--judge-config")
    parser.add_argument("--judge-questions")
    parser.add_argument("--judge-states")
    parser.add_argument("--judge-output")
    parser.add_argument("--list-judges", action="store_true")
    parser.add_argument("--watch-path", action="append", default=[])
    args = parser.parse_args(argv)
    judge_args = (args.judge_config, args.judge_questions, args.judge_states, args.judge_output)
    others = (args.instruction, args.policy, args.allow_write, args.write_root, args.mcp_config, args.authority, args.thinking)
    if args.list_judges:
        if args.workdir or args.prompt or args.watch_path or any(judge_args) or any(others):
            print("HOLD: --list-judges takes only --evidence", file=sys.stderr)
            return 2
        return list_judges(args.evidence)
    try:
        judging = any(value is not None for value in judge_args)
        if judging and not all(value is not None for value in judge_args):
            raise ValueError("--judge-config, --judge-questions, --judge-states, and --judge-output go together")
        if judging and (args.prompt or any(others)):
            raise ValueError("a judge run takes no --prompt, --instruction, --policy, --allow-write, --write-root, --mcp-config, --authority, or --thinking; the launcher writes its own prompt")
        if args.workdir is None or (not judging and args.prompt is None):
            raise ValueError("--workdir and --prompt are required")
        work = args.workdir.expanduser().resolve()
        if not work.is_dir():
            raise ValueError(f"missing work directory: {work}")
        evidence_input = args.evidence.expanduser().absolute()
        if evidence_input.exists() or evidence_input.is_symlink():
            raise ValueError(f"evidence attempt already exists: {evidence_input}; choose a new directory")
        evidence = evidence_input.resolve()
        if overlap(work, evidence):
            raise ValueError("work and evidence directories must not overlap")
        prompt = None if judging else descriptor(args.prompt, "prompt")
        judge_prep = prepare_judge(args, work) if judging else None
        instruction = descriptor(args.instruction, "saved instruction")
        declaration = descriptor(args.policy, "AGENT_POLICY.md")
        mcp_config = descriptor(args.mcp_config, "mcp.json")
        authority_file = descriptor(args.authority, "AUTHORITY.md")
        mcp_prep = None
        write_files = [permission_path(value, work) for value in args.allow_write]
        if len(write_files) != len(set(write_files)):
            raise ValueError("duplicate authorized output")
        if any((work / value).exists() or (work / value).is_symlink() for value in write_files):
            raise ValueError("authorized output already exists; preserve it and choose a new output")
        write_root = permission_path(args.write_root, work) if args.write_root else None
        profile, tools = "read", ["course_read"]
        if bool(mcp_config) != bool(authority_file):
            raise ValueError("--mcp-config and --authority go together")
        if mcp_config and (declaration or write_files or write_root):
            raise ValueError("--mcp-config and --authority cannot be combined with --policy, --allow-write, or --write-root")
        if mcp_config:
            mcp_prep = prepare_mcp(mcp_config, authority_file, work)
            profile, tools = "mcp", []
        elif judge_prep:
            profile, tools = "judge", ["eval"]
        elif declaration:
            parse_declaration(Path(declaration["path"]))
            profile, tools, write_root = "declared", DECLARATION["tools"], "artifacts"
        elif write_root or write_files:
            profile, tools = ("write_root" if write_root else "write_files"), ["course_read", "course_write"]
        if write_root:
            permission_path(write_root, work)
            if (work / write_root).exists() and not (work / write_root).is_dir():
                raise ValueError("write root must be a directory")
        watches = [Path(value).expanduser().absolute() for value in args.watch_path]
        if len(watches) != len(set(watches)) or any(path.is_dir() for path in watches):
            raise ValueError("watch paths must be distinct files or missing targets")
        if any(overlap(path.resolve(), evidence) for path in watches):
            raise ValueError("watched targets cannot overlap evidence")
        if not GUARD.is_file():
            raise ValueError("course_guard.mjs is missing; restore the published shared helper")
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            raise ValueError("OPENROUTER_API_KEY unavailable; enter and export the key in this terminal")
        omp = shutil.which("omp")
        if not omp:
            raise ValueError("omp is not on PATH; install and verify the latest stable release")
    except (OSError, ValueError, UnicodeError) as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="course-omp-runtime-") as temp:
        runtime = Path(temp).resolve()
        if overlap(runtime, work) or overlap(runtime, evidence):
            print("HOLD: OS temporary directory overlaps work/evidence", file=sys.stderr)
            return 2
        environment = isolated_env(runtime, evidence / "policy.json", key)
        if mcp_prep:
            environment.update(MCP_ENV)
        # OMP walks ancestor context files up to HOME even with --no-rules.
        cwd = Path(environment["HOME"]) / "cwd"
        cwd.mkdir()
        try:
            version = subprocess.run([omp, "--version"], cwd=cwd, env=environment, capture_output=True, text=True, timeout=15)
            omp_version = version.stdout.strip()
            if version.returncode or not valid_omp_version(omp_version):
                raise ValueError("omp --version did not return a valid omp/<semver> identity")
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            print(f"HOLD: {error}", file=sys.stderr)
            return 2
        evidence.mkdir(parents=True, exist_ok=False)
        policy_mcp = policy_judge = None
        if judge_prep:
            prompt_text, policy_judge = judge_launch_files(judge_prep, work, evidence)
            (evidence / "prompt.md").write_text(prompt_text, encoding="utf-8")
            prompt = {"path": str(evidence / "prompt.md"), "sha256": file_hash(evidence / "prompt.md")}
        if mcp_prep:
            hermetic, declared_json, policy_mcp = mcp_launch_files(mcp_prep, work, evidence)
            policy_mcp["config"], policy_mcp["authority"] = mcp_config, authority_file
            (evidence / "mcp.json").write_bytes(hermetic)
            (evidence / "authority.json").write_bytes(declared_json)
            (cwd / ".omp").mkdir()
            (cwd / ".omp" / "mcp.json").write_bytes(hermetic)
        overlay = {"retry": {"enabled": False, "modelFallback": False}, "providers": {"cacheWarming": "off"}, "tools": {"approval": expected_approval({"tools": tools, "mcp": policy_mcp}), "intentTracing": False}}
        if policy_judge:
            overlay["modelRoles"] = {"judge": policy_judge["selector"]}
        overlay_file = evidence / "runtime-config.yml"
        overlay_file.write_bytes(json_bytes(overlay))
        policy = {"schema_version": 1, "run_id": str(uuid.uuid4()), "work_root": str(work), "profile": profile, "tools": tools, "write_files": write_files, "write_root": write_root, "provider": PROVIDER, "model": MODEL, "omp_version": omp_version, "prompt_sha256": prompt["sha256"], "instruction": instruction, "declaration": declaration, "python": str(Path(sys.executable).resolve()), "guard_source_sha256": file_hash(GUARD), "runtime_config_sha256": file_hash(overlay_file), "guard_log": str(evidence / "guard.jsonl"), "watch_paths": list(map(str, watches))}
        if policy_mcp:
            policy["mcp"], policy["snapshot_exclude"] = policy_mcp, ["vault/.obsidian"]
        if policy_judge:
            policy["judge"] = policy_judge
        if args.thinking is not None:
            policy["thinking"] = args.thinking
        policy_file = evidence / "policy.json"
        policy_file.write_bytes(json_bytes(policy))
        frozen_policy_hash = file_hash(policy_file)
        exclude = tuple(policy.get("snapshot_exclude", []))
        before = snapshot(work, watches, exclude)
        command = [omp, "--model", SELECTOR, "-p", "--mode", "json", "--no-session", "--no-title", "--no-skills", "--no-rules", "--no-extensions", "--no-lsp", "--no-prewalk", "--no-pty", "--max-time", "300", "--approval-mode", "always-ask", "--no-tools"]
        if args.thinking is not None:
            command += ["--thinking", args.thinking]
        if not mcp_prep:
            command += ["--tools", ",".join(tools)]
        command += ["--extension", str(GUARD.resolve()), "--config", str(overlay_file)]
        if instruction:
            command.extend(["--append-system-prompt", instruction["path"]])
        started = datetime.now(timezone.utc).isoformat()
        errors = []
        stdout, stderr, child_exit = b"", b"", 1
        try:
            process = subprocess.Popen(command, cwd=cwd, env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                stdout, stderr = process.communicate(Path(prompt["path"]).read_bytes(), timeout=330)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                errors.append("OMP exceeded the 330-second outer deadline")
            child_exit = process.returncode
        except OSError as error:
            errors.append(f"OMP launch failed: {error}")
        if key.encode() in stdout:
            stdout = stdout.replace(key.encode(), b"[REDACTED]")
            errors.append("provider key appeared in stdout; raw stream redacted and held")
        (evidence / "events.jsonl").write_bytes(stdout)
        (evidence / "stderr.txt").write_text(stderr.decode("utf-8", errors="replace").replace(key, "[REDACTED]"), encoding="utf-8")
        after = snapshot(work, watches, exclude)
        snapshots = {"before": before, "after": after}
        (evidence / "snapshots.json").write_bytes(json_bytes(snapshots))
        events, mcp_calls = [], []
        try:
            events = read_jsonl(evidence / "events.jsonl")
            guard = read_jsonl(evidence / "guard.jsonl")
            audit = read_jsonl(evidence / "mcp-audit.jsonl") if mcp_prep and (evidence / "mcp-audit.jsonl").is_file() else None
            errors.extend(validate_run(policy, events, guard, snapshots, child_exit, audit))
            if mcp_prep:
                mcp_calls = mcp_call_records(evidence)
            if any(row.get("policy_sha256") != frozen_policy_hash for row in guard if row.get("type") in {"guard_ready", "guard_end", "instruction_loaded"}):
                errors.append("guard resolved-policy identity differs")
        except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
            errors.append(f"incomplete or malformed receipts: {error}")
        try:
            if file_hash(policy_file) != frozen_policy_hash or file_hash(GUARD) != policy["guard_source_sha256"] or file_hash(overlay_file) != policy["runtime_config_sha256"]:
                errors.append("frozen policy, guard, or configuration changed")
            for item in (prompt, instruction, declaration, mcp_config, authority_file, (policy_mcp or {}).get("script"), *judge_files(policy), *([policy_judge["config"], policy_judge["questions"]] if policy_judge else [])):
                if item and (not Path(item["path"]).is_file() or file_hash(Path(item["path"])) != item["sha256"]):
                    errors.append("frozen prompt/instruction/declaration/hash capability changed")
        except OSError as error:
            errors.append(f"frozen input could not be rechecked: {error}")
        try:
            response = _response_text(events)
        except (TypeError, AttributeError) as error:
            response = ""
            errors.append(f"malformed final assistant content: {error}")
        (evidence / "response.md").write_text(response, encoding="utf-8")
        result = {"run_id": policy["run_id"], "provider": PROVIDER, "model": MODEL, "omp_version": omp_version, "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(), "exit_code": child_exit, "policy_sha256": frozen_policy_hash, "guard_sha256": file_hash(evidence / "guard.jsonl") if (evidence / "guard.jsonl").is_file() else None, "declared_policy_sha256": declaration["sha256"] if declaration else None, "instruction_sha256": instruction["sha256"] if instruction else None, "input_sha256": {relative: value["sha256"] for relative, value in before["work"].items() if value["type"] == "file"}, "output_sha256": {relative: value.get("sha256") for relative, value in after["work"].items() if value["type"] == "file" and value != before["work"].get(relative)}, "status": "PASS" if child_exit == 0 and not errors else "HOLD", "reason": "all checks passed" if child_exit == 0 and not errors else "; ".join(errors) or "OMP exited non-zero"}
        if policy_mcp:
            result["mcp"] = {
                "config_sha256": mcp_config["sha256"] if mcp_config else None,
                "authority_sha256": authority_file["sha256"] if authority_file else None,
                "audit_sha256": file_hash(evidence / "mcp-audit.jsonl") if (evidence / "mcp-audit.jsonl").is_file() else None,
                "calls": len(mcp_calls),
            }
        if policy_judge:
            result["judge"] = judge_output_errors(policy)[1]
            if result["judge"]:
                cost = result["judge"]["cost_usd"]
                shown = f"{cost:.6f}" if isinstance(cost, (int, float)) and not isinstance(cost, bool) else "unknown"
                print(f"JUDGE: {result['judge']['items']} judged by {result['judge']['served_model']}; cost USD {shown}")
        (evidence / "result.json").write_bytes(json_bytes(result))
        print(f"{result['status']}: {result['reason']}")
        return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
