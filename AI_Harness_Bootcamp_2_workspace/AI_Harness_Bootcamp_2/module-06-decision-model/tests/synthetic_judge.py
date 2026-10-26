#!/usr/bin/env python3
"""TEST ONLY: native-artifact vectors; never a provider or learner execution option."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(REPO / "shared")]
import blue_gauge as bg
import prepare_work

MODEL = "openrouter/typesafe/jev-1.13-20000101"
COST = 0.0001


def prepared(folder: Path) -> tuple[Path, dict]:
    work = prepare_work.prepare("06", folder / "work", root=REPO)
    return work, bg.create_policy(work, "omp/18.6.0")


def boolean(value: float) -> dict:
    return {"type": "bool", "bool": value}


def choice(question: dict, selected: str, confidence: float = 1, top: float = 1) -> dict:
    options = list(question["criteria"])
    return {"type": "choice", "choice": selected, "confidence": confidence,
            "probabilities": {option: top if option == selected else (1 - top) / (len(options) - 1) for option in options}}


def score(question: dict, value: float, confidence: float = 1) -> dict:
    levels = len(question["criteria"])
    low, high = int(value), min(levels - 1, int(value) + 1)
    probabilities = {str(level): 0.0 for level in range(levels)}
    probabilities[str(low)] = 1 - (value - low)
    probabilities[str(high)] += value - low
    return {"type": "score", "score": value, "confidence": confidence, "probabilities": probabilities}


def screen_answers(questions: dict, label: dict) -> dict:
    return {"instructs_reader": boolean(float(label["instructs"])),
            "claims_release": boolean(float(label["claims_release"])),
            "claims_flight_ready": boolean(float(label["claims_flight_ready"])),
            "note_status": choice(questions["note_status"], label["note_status"]),
            "note_status_reversed": choice(questions["note_status_reversed"], label["note_status"]),
            "urgency": score(questions["urgency"], 1)}


def revision(policy: dict, pattern: str) -> str:
    return bg.load(bg.state_file(policy))["active_revisions"][pattern]


def configure(policy: dict, pattern: str, changes: dict) -> str:
    result = bg.control_action({"action": "configure", "pattern": pattern, "changes": changes}, policy)
    assert result["status"] == "PASS", result
    return result["revision"]


def prepare(policy: dict, pattern: str, mode: str) -> dict:
    result = bg.control_action({"action": "prepare", "pattern": pattern, "mode": mode, "revision": revision(policy, pattern)}, policy)
    assert result["status"] == "PASS", result
    return result


def judgment(plan: dict, key: str, names: list[str], answers: dict, sequence: int, start: datetime) -> dict:
    namespace = plan["question_namespace"] + str(sequence) + "_"
    mapping = {namespace + name: name for name in names}
    return {"type": "judge", "id": key, "sequence": sequence, "batch_id": "fixture_batch_" + str(sequence),
            "namespace": namespace, "question_map": mapping,
            "questions": {native: plan["questions"][logical] for native, logical in mapping.items()},
            "state_sha256": bg.value_hash(plan["items"][key]["state"]), "started_at": start.isoformat(),
            "elapsed_ms": 1, "answers": {name: answers[name] for name in names}, "error": None, "model": MODEL,
            "status": {"id": "fixture_batch_" + str(sequence), "total": 1, "done": 1, "failed": 0, "running": False, "model": MODEL, "cost": COST}}


def finish(start: datetime, wall_ms: int, complete: bool = True) -> dict:
    return {"type": "finish", "started_at": start.isoformat(), "wall_ms": wall_ms,
            "complete": complete, "error": None if complete else "fixture interruption"}


def record_run(policy: dict, issued: dict, *, join_usage: bool = True, complete: bool = True, override: dict | None = None, failed_handlers: set[str] | None = None) -> dict:
    """Exercise the real plan/finalizer/seals using explicitly fabricated test receipts."""
    run_id = issued["run_id"]
    plan = bg.read_plan(policy, run_id)
    assert bg.control_action({"action": "authorize_eval", "code": issued["cell_code"]}, policy)["status"] == "PASS"
    folder = bg.run_folder(policy, run_id)
    packet = bg.validate_packet(Path(policy["work_root"]))
    stream = folder / "raw.jsonl"
    stream.write_text("", encoding="utf-8")
    native = Path(policy["evidence_root"]) / "sessions" / "fixture-only.jsonl"
    guard = Path(policy["guard_log"])
    call_id = "fixture_eval_" + run_id
    args = {"language": "js", "timeout": 250, "reset": False, "code": issued["cell_code"]}
    bg.append(guard, {"type": "guard_ready", "fixture_only": True})
    bg.append(guard, {"type": "decision", "tool": "eval", "allow": True, "arguments": args, "call_id": call_id})
    bg.append(native, {"type": "message", "message": {"role": "assistant", "provider": "openrouter", "model": "anthropic/claude-sonnet-4.6",
               "content": [{"type": "toolCall", "id": call_id, "name": "eval", "arguments": args}]}})
    start = datetime.now(timezone.utc)
    sequence = 0
    if complete:
        for key, item in plan["items"].items():
            if plan["pattern"] in {"fan_out", "confidence"}:
                answers = screen_answers(plan["questions"], packet["labels"][key])
            elif plan["pattern"] == "scoring":
                answers = {name: score(question, int(key[3:]) % len(question["criteria"])) for name, question in plan["questions"].items()}
            else:
                label = packet["request_labels"][key]
                answers = {"intent": choice(plan["questions"]["intent"], label["expected_intents"][0]),
                           "complexity": score(plan["questions"]["complexity"], 1)}
            answers.update((override or {}).get(key, {}))
            prior = dict(plan.get("seed_answers", {}).get(key, {}))
            if plan["pattern"] == "intent":
                # intent asks both once in runner; fabricate one-shot then handler record
                names = [name for name in plan["questions"] if name not in prior]
                if names:
                    sequence += 1
                    at = start + timedelta(milliseconds=sequence * 2)
                    row = judgment(plan, key, names, answers, sequence, at)
                    bg.append(stream, row)
                    if join_usage:
                        bg.append(native, {"type": "model_usage", "id": f"fixture_usage_{run_id}_{sequence}", "timestamp": at.isoformat(),
                                  "purpose": "judge_batch", "api": "test-only", "provider": "openrouter", "model": "typesafe/jev-1.13",
                                  "usage": {"cost": {"total": COST}}, "stopReason": "stop"})
                    prior.update(row["answers"])
            else:
                while True:
                    if plan["pattern"] in {"fan_out", "confidence"}:
                        step = bg.screen_step(item["state"]["note"], item["stock"], item["flight"], item["mission"], prior, plan["config"]["gates"])
                        names = step["need"] if plan["mode"] == "serial" else list(plan["questions"]) if step["route"] is None else []
                    else:
                        names = [name for name in plan["questions"] if name not in prior]
                    if not names:
                        break
                    sequence += 1
                    at = start + timedelta(milliseconds=sequence * 2)
                    row = judgment(plan, key, names, answers, sequence, at)
                    bg.append(stream, row)
                    if join_usage:
                        bg.append(native, {"type": "model_usage", "id": f"fixture_usage_{run_id}_{sequence}", "timestamp": at.isoformat(),
                                  "purpose": "judge_batch", "api": "test-only", "provider": "openrouter", "model": "typesafe/jev-1.13",
                                  "usage": {"cost": {"total": COST}}, "stopReason": "stop"})
                    prior.update(row["answers"])
            if plan["pattern"] == "intent":
                selected = bg.select_handler(item["state"]["message"], prior, plan["config"], packet, item["source"])
                handler = selected["handler"]
                deterministic = handler in {"record_lookup", "record_comparison", "human_review"}
                result = selected.get("result")
                failed = key in (failed_handlers or set())
                if deterministic and result is not None:
                    bg.save(folder / "handlers" / (key + ".json"), result)
                bg.append(stream, {"type": "handler", "id": key, "handler": handler, "executed": not failed, "result": None if failed else result,
                                  "completion_id": None, "requested_model": None, "error": "fixture provider refusal" if failed else None,
                                  "started_at": start.isoformat(), "elapsed_ms": 1})
    bg.append(stream, finish(start, sequence * 2 + 10, complete))
    result = bg.control_action({"action": "finalize", "plan_id": run_id}, policy)
    assert "run_id" in result, result
    bg.append(native, {"type": "message", "message": {"role": "toolResult", "toolCallId": call_id, "isError": False,
                                                      "content": [{"type": "text", "text": "fixture-only eval receipt"}]}})
    return bg.read_report(policy, run_id)


def fan_run(policy: dict, **kwargs) -> dict:
    configure(policy, "fan_out", {"screen_strategy": "fan_out"})
    return record_run(policy, prepare(policy, "fan_out", "fan_out"), **kwargs)


def unlock_full_packet(policy: dict) -> tuple[dict, dict]:
    practice = fan_run(policy)
    configure(policy, "confidence", {"gates": {"auto_pass_confidence": 0.6}})
    unseen = record_run(policy, prepare(policy, "confidence", "unseen"))
    return practice, unseen
