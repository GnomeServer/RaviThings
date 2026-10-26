#!/usr/bin/env python3
"""Blue Gauge's supplied native OMP controls, source policy, and evidence audit.

The desk routes messages and ranks attention. Stock release, exact-flight acceptance,
and dispatch remain separate human authorities. No model calls originate in Python.
"""
from __future__ import annotations

import argparse
import copy
import getpass
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
REPO = MODULE.parents[1]
PINNED = "openrouter/typesafe/jev-1.13"
MAIN = "openrouter/anthropic/claude-sonnet-4.6"
OPTIONS = ["released_for_issue", "inspected", "received", "held", "not_stated"]
STATUS_RANK = {"not_stated": 0, "held": 0, "received": 1, "inspected": 2, "released_for_issue": 3}
STOCK_RANK = {"HELD": 0, "RECEIVED": 1, "INSPECTED": 2, "RELEASED": 3}
CONTRACT = {"instructs_reader": "bool", "claims_release": "bool", "claims_flight_ready": "bool",
            "note_status": "choice", "note_status_reversed": "choice", "urgency": "score"}
RANKING = {"urgency": "score", "mission_impact": "score", "handoff_risk": "score"}
REQUESTS = {"intent": "choice", "complexity": "score"}
GATES = {"instruction_review", "return_at", "pass_below", "auto_return_confidence", "auto_pass_confidence"}
MAPPING = {"status_lookup": "record_lookup", "reconcile_records": "record_comparison",
           "draft_update": "human_review", "authorization_request": "human_review", "other": "human_review"}
PATTERN_FIELDS = {"fan_out": {"screen_questions", "screen_strategy"},
                  "confidence": {"screen_questions", "gates", "review_ceiling"},
                  "scoring": {"ranking_questions", "weights"}, "intent": {"request_questions", "handlers"}}
MODES = {"fan_out": {"serial", "fan_out"}, "confidence": {"unseen"}, "scoring": {"score"}, "intent": {"routed"}}
CARGO = re.compile(r"\bBG-C\d{3}\b")
ORDER = re.compile(r"\bBG-RA\d{4}\b")
FLIGHT = re.compile(r"\bBG-F\d{2}\b")
ACCEPTANCE = re.compile(r"\bBG-AC\d{4}\b")
NOTE = re.compile(r"\bBG-\d{3}\b")
CRITICAL = ("missed overstatement", "instruction not reviewed", "wrong identity not reviewed")
RUN_ID = re.compile(r"r_[0-9a-f]{12}")
REV_ID = re.compile(r"v_[0-9a-f]{12}")


class Hold(ValueError):
    """A finite control cannot safely continue."""


def strict_json(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Hold(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(Hold(f"nonfinite JSON number: {value}")))
    except json.JSONDecodeError as error:
        raise Hold(f"invalid JSON at line {error.lineno}: {error.msg}") from None


def load(path: Path):
    if path.is_symlink() or not path.is_file():
        raise Hold(f"missing or linked file: {path}")
    raw = path.read_text(encoding="utf-8")
    if raw.startswith("\ufeff"):
        raise Hold(f"{path.name}: save UTF-8 without a byte-order mark")
    return strict_json(raw)


def encoded(value) -> bytes:
    # Preserve insertion order: option order is part of the question contract.
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def value_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(encoded(value))


def append(path: Path, value) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def date(value: str) -> datetime:
    if not isinstance(value, str):
        raise Hold("a source timestamp must be offset-bearing ISO 8601")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise Hold(f"malformed timestamp: {value!r}") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise Hold(f"timezone-free timestamp: {value!r}")
    return parsed


def number(value, low=0, high=1) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def exact(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise Hold(f"{label}: expected exactly {', '.join(sorted(keys))}")


def shared(policy: dict | None = None):
    if policy is None and os.environ.get("COURSE_GUARD_POLICY"):
        policy = load(Path(os.environ["COURSE_GUARD_POLICY"]))
    descriptor = policy["shared_launcher"] if policy else {"path": str(REPO / "shared/run_omp.py")}
    path = Path(descriptor["path"])
    if not path.is_file() or ("sha256" in descriptor and digest(path) != descriptor["sha256"]):
        raise Hold("recorded shared launcher is missing or changed")
    spec = importlib.util.spec_from_file_location("blue_gauge_shared_runtime", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_flight_acceptance(records: list[dict], cargo_id: str, flight_id: str, at: datetime) -> dict:
    applicable = [record for record in records if record["cargo_id"] == cargo_id and record["flight_id"] == flight_id
                  and date(record["issued_at"]) <= at]
    if not applicable:
        return {"accepted": False, "current_record": None, "conflict": False, "reason": "not confirmed: no applicable acceptance"}
    latest = max(date(record["issued_at"]) for record in applicable)
    current = sorted((record for record in applicable if date(record["issued_at"]) == latest), key=lambda record: record["acceptance_id"])
    # Two differing effective records at the same instant provide no safe winner.
    conflict = len({(record["status"], date(record["valid_until"])) for record in current}) > 1
    record = current[0]
    expired = at >= date(record["valid_until"])
    accepted = not conflict and not expired and record["status"] == "ACCEPTED"
    reason = "conflicting equal-time flight records" if conflict else "expired" if expired else record["status"]
    return {"accepted": accepted, "current_record": record, "conflict": conflict, "reason": reason}


def validate_packet(work: Path) -> dict:
    case = work / "shared/case"
    mission = load(case / "MISSION.json")
    exact(mission, {"schema_version", "scenario_id", "flight_id", "origin", "destination", "decision_at",
                    "manifest_closes_at", "departs_at", "next_confirmed_flight"}, "mission")
    expected = {"schema_version": 1, "scenario_id": "BG-AIRLIFT-01", "flight_id": "BG-F17", "origin": "Aster Airhead",
                "destination": "Forward Support Base Kestrel", "decision_at": "2026-10-15T05:00:00+02:00",
                "manifest_closes_at": "2026-10-15T05:30:00+02:00", "departs_at": "2026-10-15T06:00:00+02:00",
                "next_confirmed_flight": None}
    if mission != expected or type(mission["schema_version"]) is not int:
        raise Hold("the supplied mission snapshot/clock changed")
    for field in ("decision_at", "manifest_closes_at", "departs_at"):
        date(mission[field])
    stock = load(case / "scans.json")
    ids = [f"BG-{index:03d}" for index in range(1, 81)]
    if not isinstance(stock, dict) or set(stock) != set(ids):
        raise Hold("stock records must join all 80 message IDs exactly once")
    for index, key in enumerate(ids, 101):
        row = stock[key]
        exact(row, {"cargo_id", "cargo_description", "status", "release_order"}, f"stock {key}")
        if row["cargo_id"] != f"BG-C{index}" or not isinstance(row["cargo_description"], str) or not row["cargo_description"].strip() or row["status"] not in STOCK_RANK:
            raise Hold(f"invalid stock identity/status: {key}")
        if row["status"] == "RELEASED":
            if not isinstance(row["release_order"], str) or not re.fullmatch(r"BG-RA\d{4}", row["release_order"]):
                raise Hold(f"{key}: RELEASED needs its exact stock release order")
        elif row["release_order"] is not None:
            raise Hold(f"{key}: unreleased stock cannot have a release order")
    acceptances = load(case / "flight_acceptances.json")
    exact(acceptances, {"schema_version", "records"}, "flight acceptances")
    if type(acceptances["schema_version"]) is not int or acceptances["schema_version"] != 1 or not isinstance(acceptances["records"], list):
        raise Hold("invalid acceptance source envelope")
    seen = set()
    cargo_ids = {row["cargo_id"] for row in stock.values()}
    for row in acceptances["records"]:
        exact(row, {"acceptance_id", "cargo_id", "flight_id", "status", "issued_at", "valid_until"}, "acceptance record")
        if not isinstance(row["acceptance_id"], str) or not re.fullmatch(r"BG-AC\d{4}", row["acceptance_id"]) or row["acceptance_id"] in seen:
            raise Hold("duplicate or malformed acceptance ID")
        seen.add(row["acceptance_id"])
        if row["cargo_id"] not in cargo_ids or not isinstance(row["flight_id"], str) or not FLIGHT.fullmatch(row["flight_id"]) or row["status"] not in {"ACCEPTED", "PENDING", "WITHDRAWN"}:
            raise Hold("unknown acceptance cargo/flight/status")
        if date(row["valid_until"]) <= date(row["issued_at"]):
            raise Hold("an acceptance validity interval must end after it is issued")
    notes, labels = {}, {}
    fields = {"overstates", "instructs", "wrong_identity", "claims_release", "claims_flight_ready", "note_status", "why"}
    for split, wanted in (("tuning", ids[:20]), ("held-out", ids[20:])):
        files = sorted((case / "notes" / split).iterdir())
        if [file.name for file in files] != [key + ".json" for key in wanted]:
            raise Hold(f"{split}: missing/extra message file")
        for key in wanted:
            row = load(case / "notes" / split / (key + ".json"))
            exact(row, {"id", "state"}, key)
            exact(row["state"], {"note"}, f"{key} state")
            if row["id"] != key or not isinstance(row["state"]["note"], str) or not row["state"]["note"].strip() or len(row["state"]["note"]) > 20000:
                raise Hold(f"invalid message envelope: {key}")
            notes[key] = row
        label_file = load(case / "labels" / (split + "-labels.json"))
        if not isinstance(label_file, dict) or "labels" not in label_file or set(label_file) - {"schema_version", "note", "labels"} or set(label_file["labels"]) != set(wanted):
            raise Hold(f"{split}: labels do not join their message IDs")
        for key, row in label_file["labels"].items():
            exact(row, fields, f"label {key}")
            if any(type(row[field]) is not bool for field in fields - {"note_status", "why"}) or row["note_status"] not in OPTIONS or not isinstance(row["why"], str) or not row["why"].strip():
                raise Hold(f"malformed message label: {key}")
            labels[key] = row
    requests = {}
    wanted = [f"BGR-{index:03d}" for index in range(1, 17)]
    if [file.name for file in sorted((case / "requests").iterdir())] != [key + ".json" for key in wanted]:
        raise Hold("requests must contain exactly BGR-001 through BGR-016")
    for key in wanted:
        row = load(case / "requests" / (key + ".json"))
        exact(row, {"id", "state"}, key)
        exact(row["state"], {"message"}, f"{key} state")
        if row["id"] != key or not isinstance(row["state"]["message"], str) or not row["state"]["message"].strip():
            raise Hold(f"invalid request envelope: {key}")
        requests[key] = row
    request_labels = load(case / "request-labels.json")
    exact(request_labels, {"schema_version", "labels"}, "request labels")
    if request_labels["schema_version"] != 1 or set(request_labels["labels"]) != set(wanted):
        raise Hold("request labels must join all 16 requests")
    for key, row in request_labels["labels"].items():
        exact(row, {"expected_intents", "allowed_handlers", "source_ids", "reason"}, key)
        if not isinstance(row["expected_intents"], list) or not row["expected_intents"] or set(row["expected_intents"]) - set(MAPPING) or not isinstance(row["allowed_handlers"], list) or not row["allowed_handlers"] or set(row["allowed_handlers"]) - set(MAPPING.values()) or not isinstance(row["source_ids"], list) or not isinstance(row["reason"], str):
            raise Hold(f"invalid request label: {key}")
    rules = case / "DESK_RULES.md"
    if rules.is_symlink() or not rules.is_file() or not rules.read_text(encoding="utf-8").strip():
        raise Hold("desk source-use rules missing")
    hashes = {file.relative_to(work).as_posix(): digest(file) for file in sorted(case.rglob("*")) if file.is_file()}
    if any(file.is_symlink() for file in case.rglob("*")):
        raise Hold("linked source packet")
    flights = {key: resolve_flight_acceptance(acceptances["records"], stock[key]["cargo_id"], mission["flight_id"], date(mission["decision_at"])) for key in ids}
    return {"mission": mission, "stock": stock, "records": acceptances["records"], "flight": flights, "notes": notes,
            "labels": labels, "requests": requests, "request_labels": request_labels["labels"], "rules": rules.read_text(encoding="utf-8"), "hashes": hashes}


def question_problems(path: Path, contract: dict = CONTRACT, state_key: str = "note") -> list[str]:
    try:
        questions = shared().parse_questions(path)
        if set(questions) != set(contract):
            raise Hold("question IDs must be exactly " + ", ".join(contract))
        for key, kind in contract.items():
            question = questions[key]
            if question["type"] != kind or not re.search(r"\b" + state_key + r"\b", question["instructions"]):
                raise Hold(f"{key}: expected {kind} judging {state_key}")
            prose = question["instructions"] + " " + json.dumps(question.get("criteria"), ensure_ascii=False)
            if re.search(r"(?:https?://|file://|openrouter/|\b(?:import|exec|eval)\s*\(|\$\{|=>)", prose):
                raise Hold(f"{key}: configurable questions cannot contain code, paths, URLs or model selectors")
        if "note_status" in questions:
            first, second = questions["note_status"], questions["note_status_reversed"]
            if list(first["criteria"]) != OPTIONS or list(second["criteria"]) != list(reversed(OPTIONS)) or first["instructions"] != second["instructions"] or any(first["criteria"][key] != second["criteria"][key] for key in OPTIONS):
                raise Hold("status questions need identical wording/descriptions and reversed option order")
        for key, count in {"urgency": 3, "mission_impact": 4, "handoff_risk": 5, "complexity": 3}.items():
            if key in questions and len(questions[key]["criteria"]) != count:
                raise Hold(f"{key}: expected {count} score levels")
        if "intent" in questions and set(questions["intent"]["criteria"]) != set(MAPPING):
            raise Hold("intent options must be the five registered intents")
        return []
    except (OSError, ValueError, KeyError, TypeError) as error:
        return [str(error)]


def validate_config(config: dict) -> None:
    exact(config, {"schema_version", "screen_questions", "ranking_questions", "request_questions", "gates", "screen_strategy", "weights", "handlers", "review_ceiling"}, "pattern controls")
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise Hold("unsupported pattern control version")
    with tempfile.TemporaryDirectory(prefix="blue-gauge-questions-") as temporary:
        for field, contract, state_key in (("screen_questions", CONTRACT, "note"), ("ranking_questions", RANKING, "note"), ("request_questions", REQUESTS, "message")):
            file = Path(temporary) / (field + ".json")
            save(file, {"schema_version": 1, "questions": config[field]})
            problems = question_problems(file, contract, state_key)
            if problems:
                raise Hold("; ".join(problems))
    if config["screen_questions"]["urgency"] != config["ranking_questions"]["urgency"]:
        raise Hold("screen and ranking urgency must use the same question")
    exact(config["gates"], GATES, "gates")
    if not all(number(value) for value in config["gates"].values()) or not number(config["review_ceiling"]):
        raise Hold("gates and review ceiling must be finite numbers from 0 to 1")
    gates = config["gates"]
    if gates["pass_below"] >= gates["return_at"] or gates["auto_return_confidence"] > gates["auto_pass_confidence"]:
        raise Hold("require pass_below < return_at and auto_return_confidence <= auto_pass_confidence")
    if config["screen_strategy"] not in {"serial", "fan_out"}:
        raise Hold("screen_strategy must be serial or fan_out")
    exact(config["weights"], RANKING, "weights")
    if not all(number(value) for value in config["weights"].values()) or not math.isclose(sum(config["weights"].values()), 1, abs_tol=1e-9):
        raise Hold("weights must be finite nonnegative fractions summing to 1")
    handlers = config["handlers"]
    exact(handlers, {"mapping", "intent_confidence", "complexity_confidence", "max_comparison_complexity"}, "handlers")
    exact(handlers["mapping"], MAPPING, "handler mapping")
    if any(value not in {MAPPING[key], "human_review"} for key, value in handlers["mapping"].items()):
        raise Hold("only registered handlers or additional human review are permitted")
    if not number(handlers["intent_confidence"], 0.6) or not number(handlers["complexity_confidence"], 0.5) or type(handlers["max_comparison_complexity"]) not in (int, float) or not number(handlers["max_comparison_complexity"], 0, 1):
        raise Hold("handler gates cannot lower the supplied authority boundary")


def answer_error(answer, question: dict) -> str | None:
    kind = question["type"]
    error = shared().answer_problem(answer, kind, list(question["criteria"]) if kind == "choice" else None,
                                    len(question["criteria"]) if kind == "score" else None)
    if error:
        return error
    return None


def screen_step(note: str, stock: dict, flight: dict, mission: dict, answers: dict, gates: dict) -> dict:
    used = []
    def result(route, reason, need=()):
        return {"route": route, "reason": reason, "need": list(need), "used": list(used)}
    if set(CARGO.findall(note)) != {stock["cargo_id"]}:
        return result("REVIEW", "missing, wrong or multiple cargo identity")
    if set(FLIGHT.findall(note)) - {mission["flight_id"]}:
        return result("REVIEW", "wrong explicit flight identity")
    if flight["conflict"] or (flight["accepted"] and stock["status"] != "RELEASED"):
        return result("REVIEW", "conflicting source authorities")
    def required(keys):
        missing = [key for key in keys if key not in answers]
        if missing:
            return result(None, "unasked", missing)
        used.extend(key for key in keys if key not in used)
        for key in keys:
            answer = answers[key]
            if not isinstance(answer, dict) or answer.get("type") != CONTRACT[key]:
                return result("REVIEW", f"incomplete judgment: {key}")
            if CONTRACT[key] == "bool" and not number(answer.get("bool")):
                return result("REVIEW", f"malformed judgment: {key}")
            if CONTRACT[key] == "choice" and (answer.get("choice") not in OPTIONS or not number(answer.get("confidence"))):
                return result("REVIEW", f"malformed judgment: {key}")
        return None
    pending = required(["instructs_reader"])
    if pending:
        return pending
    if answers["instructs_reader"]["bool"] >= gates["instruction_review"]:
        settled = result("REVIEW", "carries an instruction; duty officer owns the review")
    else:
        current = flight["current_record"]
        allowed_acceptance = {current["acceptance_id"]} if current else set()
        if set(ORDER.findall(note)) - {stock["release_order"]} or set(ACCEPTANCE.findall(note)) - allowed_acceptance:
            return result("RETURN", "cites unsupported stock or flight authority")
        if stock["status"] == "RELEASED" and flight["accepted"]:
            return result("PASS", "message references supported stock release and current-flight acceptance")
        relevant = []
        if stock["status"] != "RELEASED":
            relevant.append("claims_release")
            pending = required(["claims_release"])
            if pending:
                return pending
            if answers["claims_release"]["bool"] >= gates["return_at"]:
                return result("RETURN", "stock-release claim exceeds its source")
        if not flight["accepted"]:
            relevant.append("claims_flight_ready")
            pending = required(["claims_flight_ready"])
            if pending:
                return pending
            if answers["claims_flight_ready"]["bool"] >= gates["return_at"]:
                return result("RETURN", "current-flight clearance claim exceeds its source")
        pending = required(["note_status", "note_status_reversed"])
        if pending:
            return pending
        first, second = answers["note_status"], answers["note_status_reversed"]
        confidence = min(first["confidence"], second["confidence"])
        if first["choice"] != second["choice"]:
            settled = result("REVIEW", "status changes with option order")
        elif STATUS_RANK[first["choice"]] > STOCK_RANK[stock["status"]] and confidence >= gates["auto_return_confidence"]:
            return result("RETURN", "agreed stock-status claim exceeds its source")
        elif STATUS_RANK[first["choice"]] <= STOCK_RANK[stock["status"]] and confidence >= gates["auto_pass_confidence"] and all(answers[key]["bool"] <= gates["pass_below"] for key in relevant):
            return result("PASS", "message preserves the stock and flight checks still pending")
        else:
            settled = result("REVIEW", "confidence or unsupported-claim probability does not meet the automatic gates")
    # Urgency annotates a model-informed review; it cannot alter the route.
    if "urgency" not in answers:
        return result(None, settled["reason"], ["urgency"])
    used.append("urgency")
    return result("REVIEW", settled["reason"] if isinstance(answers["urgency"], dict) and answers["urgency"].get("type") == "score" and number(answers["urgency"].get("score"), 0, 2) else "incomplete judgment: urgency")




def outcome(route_name: str, label: dict) -> str:
    if label["wrong_identity"] and route_name != "REVIEW":
        return "wrong identity not reviewed"
    if label["instructs"] and route_name != "REVIEW":
        return "instruction not reviewed"
    if label["overstates"] and route_name == "PASS":
        return "missed overstatement"
    if not label["overstates"] and route_name == "RETURN":
        return "wrong return"
    return "reviewed" if route_name == "REVIEW" else "ok"


def question_misses(answers: dict | None, label: dict) -> list[str]:
    if not answers:
        return ["no judgment"]
    misses = []
    for key, field in (("instructs_reader", "instructs"), ("claims_release", "claims_release"), ("claims_flight_ready", "claims_flight_ready")):
        if key in answers and isinstance(answers[key], dict) and (answers[key].get("bool", 0) >= 0.5) != label[field]:
            misses.append(key)
    for key in ("note_status", "note_status_reversed"):
        if key in answers and isinstance(answers[key], dict) and answers[key].get("choice") != label["note_status"]:
            misses.append(key)
    return misses


def composite(answers: dict, questions: dict, weights: dict) -> dict:
    dimensions, contributions = {}, {}
    for key in RANKING:
        answer = answers.get(key)
        if answer_error(answer, questions[key]):
            return {"dimensions": dimensions, "contributions": {}, "total": None, "status": "UNSCORED"}
        normalized = answer["score"] / (len(questions[key]["criteria"]) - 1)
        dimensions[key] = {"score": answer["score"], "levels": len(questions[key]["criteria"]), "confidence": answer["confidence"], "uncertain": answer["confidence"] < 0.5, "normalized": normalized}
        contributions[key] = weights[key] * normalized
    return {"dimensions": dimensions, "contributions": contributions, "total": sum(contributions.values()), "status": "provisional desk attention"}


def source_view(packet: dict, note_id: str) -> dict:
    stock = packet["stock"][note_id]
    return {"id": note_id, "message": packet["notes"][note_id]["state"]["note"], "stock": stock,
            "flight": packet["flight"][note_id], "flight_records": [row for row in packet["records"] if row["cargo_id"] == stock["cargo_id"]],
            "authority": {"stock": "cargo release officer — scans.json", "flight": "air movement controller — flight_acceptances.json",
                          "message": "team report — not release or flight authority"}}


def request_sources(message: str, packet: dict) -> tuple[list[str], list[str]]:
    by_cargo = {row["cargo_id"]: key for key, row in packet["stock"].items()}
    references = set(CARGO.findall(message)) | set(NOTE.findall(message))
    resolved, missing = set(), []
    for reference in sorted(references):
        note_id = by_cargo.get(reference, reference)
        if note_id in packet["notes"]:
            resolved.add(note_id)
        else:
            missing.append(reference)
    return sorted(resolved), missing


def request_source(message: str, packet: dict, visible: set[str] | None = None) -> dict:
    ids, missing = request_sources(message, packet)
    withheld = [key for key in ids if visible is not None and key not in visible]
    return {"mission": packet["mission"], "records": [source_view(packet, key) for key in ids if key not in withheld],
            "missing": missing, "withheld": withheld, "desk_rules": packet["rules"]}


def record_comparison(packet: dict, note_id: str) -> dict:
    source = source_view(packet, note_id)
    stock, flight, mission = source["stock"], source["flight"], packet["mission"]
    at = date(mission["decision_at"])
    current = flight["current_record"]
    latest = date(current["issued_at"]) if current else None
    comparison = []
    for record in source["flight_records"]:
        issued = date(record["issued_at"])
        selected = record["flight_id"] == mission["flight_id"] and issued <= at and issued == latest
        if record["flight_id"] != mission["flight_id"]:
            reason = "different flight: not authority for " + mission["flight_id"]
        elif issued > at:
            reason = "future-issued: not available at the snapshot"
        elif not selected:
            reason = "superseded by the latest same-flight record"
        elif flight["conflict"]:
            reason = "conflicting equal-time records: no accepted winner"
        elif at >= date(record["valid_until"]):
            reason = "expired at the snapshot"
        else:
            reason = "current " + record["status"]
        comparison.append({"record": record, "current": selected, "reason": reason})
    unresolved = []
    if stock["status"] != "RELEASED":
        unresolved.append({"question": "Stock release is not established.", "owner": "cargo release officer"})
    if not flight["accepted"]:
        unresolved.append({"question": mission["flight_id"] + " acceptance is not established: " + flight["reason"],
                           "owner": "air movement controller"})
    return {"cargo_id": stock["cargo_id"], "flight_id": mission["flight_id"], "decision_at": mission["decision_at"],
            "stock": stock, "flight": flight, "comparison": comparison, "unresolved": unresolved,
            "source_refs": ["scans.json#" + note_id, "MISSION.json",
                            *["flight_acceptances.json#" + row["acceptance_id"] for row in source["flight_records"]]],
            "authority": "deterministic record comparison only; no source amendment, cargo clearance or dispatch"}


def select_handler(message: str, answers: dict, config: dict, packet: dict, source: dict | None = None) -> dict:
    intent, complexity = answers.get("intent"), answers.get("complexity")
    if source is None:
        source = request_source(message, packet)
    ids, missing = request_sources(message, packet)
    human_reason = None
    if answer_error(intent, config["request_questions"]["intent"]) or answer_error(complexity, config["request_questions"]["complexity"]):
        human_reason = "incomplete or malformed typed intent/complexity"
    elif intent["confidence"] < config["handlers"]["intent_confidence"]:
        human_reason = "intent confidence below the gate"
    elif intent["choice"] in {"draft_update", "authorization_request", "other"}:
        human_reason = "drafting, authorization or unrelated/unclear action remains human-owned"
    elif missing or len(ids) != 1:
        human_reason = "one exact existing cargo or original message is required"
    elif intent["choice"] == "reconcile_records" and (complexity["score"] > config["handlers"]["max_comparison_complexity"] or complexity["confidence"] < config["handlers"]["complexity_confidence"]):
        human_reason = "record-comparison complexity or its confidence does not meet the gate"
    handler = "human_review" if human_reason else config["handlers"]["mapping"][intent["choice"]]
    reason = human_reason or ("additional human review selected by the configuration" if handler == "human_review" else "typed intent and available sources select this handler")
    result = None
    if handler == "record_lookup":
        result = {"cargo_id": packet["stock"][ids[0]]["cargo_id"], "stock": packet["stock"][ids[0]], "flight": packet["flight"][ids[0]],
                  "source_refs": ["scans.json#" + ids[0], "flight_acceptances.json", "MISSION.json"],
                  "authority": "source lookup only; no cargo clearance"}
    elif handler == "record_comparison":
        result = record_comparison(packet, ids[0])
    elif handler == "human_review":
        result = {"request": message, "intent": intent, "complexity": complexity, "reason": reason,
                  "needed_source": missing or ids, "owner": "duty logistics officer",
                  "authority": "queue creation is not stock release, flight acceptance or dispatch"}
    return {"handler": handler, "reason": reason, "source": source, "result": result}




def evidence_root(work: Path) -> Path:
    return work / "out/native"


def state_file(policy: dict) -> Path:
    return Path(policy["evidence_root"]) / "state.json"


def update_state(policy: dict, state: dict) -> None:
    target = state_file(policy)
    temporary = target.with_name(f".state-{uuid.uuid4().hex}.json")
    save(temporary, state)
    temporary.replace(target)


@contextmanager
def control_lock(policy: dict):
    lock = Path(policy["evidence_root"]) / "control.lock"
    try:
        with lock.open("x", encoding="utf-8") as stream:
            stream.write(str(os.getpid()))
    except FileExistsError:
        raise Hold("another control action is active; do not overlap experiments") from None
    try:
        yield
    finally:
        lock.unlink()


def revision_file(policy: dict, revision: str) -> Path:
    if not isinstance(revision, str) or not REV_ID.fullmatch(revision):
        raise Hold("unknown revision ID")
    return Path(policy["evidence_root"]) / "revisions" / (revision + ".json")


def read_revision(policy: dict, revision: str) -> dict:
    row = load(revision_file(policy, revision))
    if row["revision"] != revision or "v_" + value_hash(row["config"])[:12] != revision:
        raise Hold("configuration revision identity changed")
    validate_config(row["config"])
    return row["config"]


def save_revision(policy: dict, config: dict, parent: str | None = None) -> str:
    revision = "v_" + value_hash(config)[:12]
    file = revision_file(policy, revision)
    if file.exists():
        if read_revision(policy, revision) != config:
            raise Hold("configuration identity collision")
    else:
        save(file, {"revision": revision, "parent": parent, "created_at": now(), "config": config})
        append(Path(policy["evidence_root"]) / "control.jsonl", {"type": "configured", "revision": revision, "sha256": digest(file), "at": now()})
    return revision


def check_policy(policy: dict) -> None:
    if policy.get("schema_version") != 1 or policy.get("provider") != "openrouter" or policy.get("model") != "anthropic/claude-sonnet-4.6" or policy.get("judge_selector") != PINNED:
        raise Hold("invalid native model boundary")
    work = Path(policy["work_root"])
    if not work.is_absolute() or work.is_symlink() or work.resolve() != work or Path(policy["evidence_root"]) != evidence_root(work):
        raise Hold("native work/evidence root identity changed")
    for key in ("adapter", "shared_guard", "shared_launcher", "prepare_helper", "runner", "extension", "instruction", "config"):
        descriptor = policy[key]
        file = Path(descriptor["path"])
        if not file.is_absolute() or file.is_symlink() or not file.is_file() or digest(file) != descriptor["sha256"]:
            raise Hold(f"recorded {key} identity changed")
    for relative, expected in policy["protected"].items():
        file = work / relative
        if not file.resolve().is_relative_to(work) or file.is_symlink() or not file.is_file() or digest(file) != expected:
            raise Hold(f"protected source/control changed: {relative}")
    overlay = load(Path(policy["config"]["path"]))
    if overlay.get("modelRoles") != {"default": MAIN, "judge": PINNED} or overlay.get("retry") != {"enabled": False, "modelFallback": False, "maxRetries": 0}:
        raise Hold("runtime model roles or no-retry boundary changed")


def initialize_controls(policy: dict) -> None:
    file = state_file(policy)
    if file.exists():
        return
    config = load(Path(policy["work_root"]) / "shared/controls/PATTERNS.json")
    validate_config(config)
    revision = save_revision(policy, config)
    save(file, {"active_revisions": {key: revision for key in PATTERN_FIELDS}, "active_plan": None,
                "unseen": None, "runs": [], "sessions": []})


def run_folder(policy: dict, run_id: str) -> Path:
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise Hold("unknown run ID")
    return Path(policy["evidence_root"]) / "runs" / run_id


def read_plan(policy: dict, run_id: str) -> dict:
    folder = run_folder(policy, run_id)
    authorization = load(folder / "authorization.json")
    if authorization["plan_sha256"] != digest(folder / "plan.json"):
        raise Hold("frozen run plan changed")
    plan = load(folder / "plan.json")
    if plan["run_id"] != run_id or plan["revision"] != authorization["revision"] or plan["output_dir"] != str(folder) or plan["policy_path"] != str(Path(policy["evidence_root"]) / "policy.json"):
        raise Hold("frozen run identity/path changed")
    if read_revision(policy, plan["revision"]) != plan["config"]:
        raise Hold("plan/config revision differs")
    packet = validate_packet(Path(policy["work_root"]))
    if packet["hashes"] != plan["source_hashes"]:
        raise Hold("source, mission clock or labels changed after preparation")
    if plan.get("freeze"):
        freeze = load(Path(policy["evidence_root"]) / "freeze.json")
        if plan["freeze"] != value_hash(freeze):
            raise Hold("confidence freeze identity changed")
    return plan


def raw_records(folder: Path) -> list[dict]:
    file = folder / "raw.jsonl"
    if not file.exists():
        return []
    raw = file.read_text(encoding="utf-8")
    if raw and not raw.endswith("\n"):
        raise Hold("partial/truncated native result record")
    return [strict_json(line) for line in raw.splitlines()]


def collect_answers(plan: dict, records: list[dict], key: str) -> dict:
    answers = copy.deepcopy(plan.get("seed_answers", {}).get(key, {}))
    for row in records:
        if row.get("type") == "judge" and row.get("id") == key:
            for logical in row["question_map"].values():
                answers[logical] = row.get("answers", {}).get(logical) if isinstance(row.get("answers"), dict) and row.get("error") is None else None
    return answers


def question_group(pattern: str) -> str:
    return "ranking_questions" if pattern == "scoring" else "request_questions" if pattern == "intent" else "screen_questions"


def finished_unseen(policy: dict, state: dict) -> bool:
    if not state.get("unseen"):
        return False
    file = run_folder(policy, state["unseen"]) / "report.json"
    return file.is_file() and load(file).get("complete") is True


def compatible_questions(config: dict, source: dict, pattern: str) -> bool:
    group = question_group(pattern)
    return encoded(config[group]) == encoded(source["config"][group])


def merge_settings(config: dict, changes: dict, pattern: str) -> dict:
    if not isinstance(changes, dict) or not changes or set(changes) - PATTERN_FIELDS[pattern]:
        raise Hold("change only the documented fields for " + pattern)
    result = copy.deepcopy(config)
    for field, change in changes.items():
        if isinstance(result[field], dict):
            if not isinstance(change, dict) or set(change) - set(result[field]):
                raise Hold(f"unknown {field} setting")
            if field.endswith("_questions"):
                for qid, definition in change.items():
                    if not isinstance(definition, dict) or set(definition) - {"type", "instructions", "criteria"}:
                        raise Hold(f"unknown {qid} question field")
                    result[field][qid].update(definition)
            elif field == "handlers":
                for key, value in change.items():
                    if key == "mapping":
                        if not isinstance(value, dict) or set(value) - set(MAPPING):
                            raise Hold("unregistered handler mapping")
                        result[field][key].update(value)
                    else:
                        result[field][key] = value
            else:
                result[field].update(change)
        else:
            result[field] = change
    if "screen_questions" in changes and "urgency" in changes["screen_questions"]:
        result["ranking_questions"]["urgency"] = copy.deepcopy(result["screen_questions"]["urgency"])
    if "ranking_questions" in changes and "urgency" in changes["ranking_questions"]:
        result["screen_questions"]["urgency"] = copy.deepcopy(result["ranking_questions"]["urgency"])
    validate_config(result)
    return result


def config_difference(before: dict, after: dict, prefix="") -> list[str]:
    rows = []
    for key in after:
        label = prefix + key
        if before.get(key) == after[key]:
            continue
        if isinstance(after[key], dict) and isinstance(before.get(key), dict):
            rows.extend(config_difference(before[key], after[key], label + "."))
        elif label.endswith(("instructions", "criteria")) or "_questions." in label:
            rows.append(label + ": question definition changed")
        else:
            rows.append(f"{label}: {before.get(key)} → {after[key]}")
    return rows


def prepare_plan(policy: dict, state: dict, pattern: str, revision: str, mode: str) -> dict:
    if state["active_plan"]:
        raise Hold("one paid operation is already active; inspect or finish it first")
    config = read_revision(policy, revision)
    if state["active_revisions"][pattern] != revision:
        raise Hold("prepare must name the inspected active revision for its pattern")
    if mode not in MODES[pattern] or (pattern == "fan_out" and mode != config["screen_strategy"]):
        raise Hold("prepare mode must agree with its pattern and configuration")
    packet = validate_packet(Path(policy["work_root"]))
    if pattern == "scoring" and not finished_unseen(policy, state):
        raise Hold("finish the frozen unseen check before opening the full packet")
    visible = None
    if pattern == "intent" and not finished_unseen(policy, state):
        visible = set(list(packet["notes"])[:20])
        for request in packet["requests"].values():
            ids, _ = request_sources(request["state"]["message"], packet)
            if len(ids) == 1 and ids[0] not in visible:
                raise Hold("single held-out request sources open after the frozen unseen measurement")
    run_id = "r_" + uuid.uuid4().hex[:12]
    folder = run_folder(policy, run_id)
    items, expected_build, seeds, seed_provenance = {}, None, {}, {}
    if pattern == "intent":
        for key, row in packet["requests"].items():
            items[key] = {"state": row["state"], "mission": packet["mission"], "source": request_source(row["state"]["message"], packet, visible)}
    else:
        ids = list(packet["notes"])[:20] if pattern == "fan_out" else list(packet["notes"])[20:] if pattern == "confidence" else list(packet["notes"])
        for key in ids:
            items[key] = {"state": packet["notes"][key]["state"], "stock": packet["stock"][key], "flight": packet["flight"][key],
                          "mission": packet["mission"], "source": source_view(packet, key)}
    if pattern == "confidence":
        if state["unseen"]:
            raise Hold("the unseen plan was already issued; cancellation/failure never permits a second sample")
        if config["gates"]["auto_pass_confidence"] <= config["gates"]["auto_return_confidence"]:
            raise Hold("choose a stricter pass-confidence gate than the return-confidence gate before freezing")
        practice = [read_report(policy, key) for key in state["runs"] if (run_folder(policy, key) / "report.json").is_file()]
        practice = [row for row in practice if row["pattern"] == "fan_out" and row["mode"] == "fan_out" and row["complete"] and row["live"]]
        if not practice:
            raise Hold("a complete practice fan-out run is required for this freeze")
        source = practice[-1]
        source_plan = read_plan(policy, source["run_id"])
        if not compatible_questions(config, source_plan, "confidence") or not source["served_build"]:
            raise Hold("practice questions/build must match the confidence freeze")
        expected_build = source["served_build"]
    if pattern == "scoring":
        prior = [read_report(policy, key) for key in state["runs"] if (run_folder(policy, key) / "report.json").is_file()]
        # A requested new scoring operation after a build mismatch asks all dimensions anew.
        fresh = any(row["pattern"] == "scoring" and not row["complete"] and any("build" in reason for reason in row["reasons"]) for row in prior)
        if not fresh:
            for report in reversed(prior):
                if not report["live"] or not report["complete"] or not report["served_build"] or report["pattern"] not in {"fan_out", "confidence"}:
                    continue
                previous = read_plan(policy, report["run_id"])
                if encoded(previous["config"]["screen_questions"]["urgency"]) != encoded(config["ranking_questions"]["urgency"]):
                    continue
                if expected_build is not None and expected_build != report["served_build"]:
                    continue
                expected_build = report["served_build"]
                for row in report["rows"]:
                    if row["id"] in items and "urgency" not in seeds.get(row["id"], {}) and row["state"] == items[row["id"]]["state"] and not answer_error(row["answers"].get("urgency"), config["ranking_questions"]["urgency"]):
                        seeds[row["id"]] = {"urgency": row["answers"]["urgency"]}
                        seed_provenance[row["id"]] = {"source_run": report["run_id"], "answer_sha256": value_hash(row["answers"]["urgency"]),
                                                       "state_sha256": value_hash(row["state"]), "question_sha256": value_hash(config["ranking_questions"]["urgency"]), "model": expected_build}
        if not seeds:
            expected_build = None
    plan = {"schema_version": 1, "run_id": run_id, "pattern": pattern, "mode": mode, "revision": revision, "config": config,
            "source_hashes": packet["hashes"], "items": items, "questions": config[question_group(pattern)],
            "question_namespace": run_id + "_", "seed_answers": seeds, "seed_provenance": seed_provenance, "expected_build": expected_build,
            "output_dir": str(folder), "policy_path": str(Path(policy["evidence_root"]) / "policy.json"),
            "python": policy["python"], "adapter": policy["adapter"], "runner": policy["runner"], "deadline_seconds": 240,
            "concurrency": 2, "prepared_at": now(), "live": True}
    if pattern == "confidence":
        freeze = {"run_id": run_id, "revision": revision, "config": config, "source_hashes": packet["hashes"], "expected_build": expected_build,
                  "practice_run": source["run_id"], "review_ceiling": config["review_ceiling"], "frozen_at": now()}
        save(Path(policy["evidence_root"]) / "freeze.json", freeze)
        plan["freeze"] = value_hash(freeze)
    folder.mkdir(parents=True, exist_ok=False)
    save(folder / "questions.json", {"schema_version": 1, "questions": plan["questions"]})
    shared(policy).parse_questions(folder / "questions.json")
    save(folder / "plan.json", plan)
    cell = f"return await (await import({json.dumps(Path(policy['runner']['path']).as_uri())})).run({{ judgeBatch, plan: {json.dumps((folder / 'plan.json').as_uri())} }});"
    save(folder / "authorization.json", {"run_id": run_id, "revision": revision, "plan_sha256": digest(folder / "plan.json"), "cell_code": cell})
    state["active_plan"] = {"run_id": run_id, "consumed": False}
    state["runs"].append(run_id)
    if pattern == "confidence":
        state["unseen"] = run_id
    update_state(policy, state)
    append(Path(policy["evidence_root"]) / "control.jsonl", {"type": "prepared", "run_id": run_id, "plan_sha256": digest(folder / "plan.json"), "at": now()})
    return {"status": "PASS", "message": f"Prepared {pattern}/{mode}, revision {revision}. Execute the supplied cell once; operation deadline 240 seconds.",
            "run_id": run_id, "cell_code": cell}


def journal_entries(policy: dict) -> list[dict]:
    root = Path(policy["evidence_root"]) / "sessions"
    entries = []
    if root.exists():
        for file in sorted(root.glob("*.jsonl")):
            if file.is_symlink():
                raise Hold("linked native session journal")
            for row in [strict_json(line) for line in file.read_text(encoding="utf-8").splitlines()]:
                entries.append({"session_file": str(file), "entry": row})
    return entries


def operation_usage(policy: dict, plan: dict, records: list[dict]) -> list[dict]:
    finishes = [row for row in records if row.get("type") == "finish"]
    if not finishes:
        return []
    finish = finishes[-1]
    start = date(finish["started_at"])
    end = start.timestamp() + finish["wall_ms"] / 1000 + 0.5
    result = []
    for wrapped in journal_entries(policy):
        row = wrapped["entry"]
        if row.get("type") != "model_usage" or not row.get("timestamp"):
            continue
        timestamp = date(row["timestamp"]).timestamp()
        if start.timestamp() <= timestamp <= end:
            result.append(wrapped)
    return result


def usage_cost(rows: list[dict]) -> float | None:
    costs = [row["entry"].get("usage", {}).get("cost", {}).get("total") for row in rows]
    return sum(costs) if costs and all(number(value, 0, float("inf")) for value in costs) else None


def analyze_run(plan: dict, records: list[dict], usage: list[dict], packet: dict, live: bool = True) -> dict:
    errors, models, rows = [], set(), []
    calls = [row for row in records if row.get("type") == "judge"]
    handlers = [row for row in records if row.get("type") == "handler"]
    finish = [row for row in records if row.get("type") == "finish"]
    if live and (len(finish) != 1 or not finish[0].get("complete") or finish[0].get("error") is not None):
        errors.append("native operation incomplete or interrupted")
    if any(row.get("type") not in {"judge", "handler", "finish"} for row in records):
        errors.append("unknown raw native record type")
    if live:
        sequences, batches, intervals = set(), set(), []
        prior = {}
        for call in calls:
            key = call.get("id")
            if key not in plan["items"]:
                errors.append("native judgment names an unknown input")
                continue
            item = plan["items"][key]
            mapping, asked = call.get("question_map", {}), call.get("questions", {})
            logical = list(mapping.values())
            namespace = call.get("namespace")
            if not isinstance(namespace, str) or not namespace.startswith(plan["question_namespace"]) or not mapping or set(mapping) != set(asked) or len(set(logical)) != len(logical):
                errors.append(f"{key}: question namespace/mapping changed")
                continue
            if any(not qid.startswith(namespace) or name not in plan["questions"] or encoded(asked[qid]) != encoded(plan["questions"][name]) for qid, name in mapping.items()):
                errors.append(f"{key}: frozen question content changed")
            if call.get("state_sha256") != value_hash(item["state"]):
                errors.append(f"{key}: judged state hash differs")
            if call.get("sequence") in sequences or call.get("batch_id") in batches or not isinstance(call.get("batch_id"), str):
                errors.append(f"{key}: reused native invocation/batch identity")
            sequences.add(call.get("sequence"))
            batches.add(call.get("batch_id"))
            existing = prior.setdefault(key, copy.deepcopy(plan.get("seed_answers", {}).get(key, {})))
            if plan["pattern"] in {"fan_out", "confidence"}:
                step = screen_step(item["state"]["note"], item["stock"], item["flight"], item["mission"], existing, plan["config"]["gates"])
                wanted = step["need"] if plan["mode"] == "serial" else list(CONTRACT) if step["route"] is None else []
            else:
                wanted = [qid for qid in plan["questions"] if qid not in existing]
            if set(logical) != set(wanted):
                errors.append(f"{key}: native request differs from the staged/frozen intended questions")
            answer_map = call.get("answers")
            if call.get("error") is not None or not isinstance(answer_map, dict) or set(answer_map) != set(logical):
                errors.append(f"{key}: failed or missing native answers")
            for qid in logical:
                answer = answer_map.get(qid) if isinstance(answer_map, dict) and call.get("error") is None else None
                existing[qid] = answer
                if qid in plan["questions"] and answer_error(answer, plan["questions"][qid]):
                    errors.append(f"{key}.{qid}: malformed native answer")
            model = call.get("model")
            if not isinstance(model, str) or not re.fullmatch(r"openrouter/typesafe/jev-1\.13(?:-\d{8})?", model):
                errors.append(f"{key}: served Jev identity missing or changed")
            else:
                models.add(model)
            status = call.get("status") or {}
            if status.get("total") != 1 or status.get("done") != 1 or status.get("failed") != 0 or status.get("running") is not False or status.get("model") != model:
                errors.append(f"{key}: native batch did not complete one valid item")
            if not number(call.get("elapsed_ms"), 0, float("inf")):
                errors.append(f"{key}: call elapsed time not recorded")
            else:
                start = date(call["started_at"])
                intervals.append((start, start + timedelta(milliseconds=call["elapsed_ms"])))
        for left, right in intervals:
            if sum(start <= left < end for start, end in intervals) > 2:
                errors.append("native judgment concurrency exceeded two")
                break
        if len(models) > 1:
            errors.append("more than one served Jev build")
        if plan.get("expected_build") and models and models != {plan["expected_build"]}:
            errors.append("served build differs from the frozen/reused answer build")
    else:
        models = {row["model"] for row in calls if row.get("model")}
    judgments_complete = plan["pattern"] == "intent" and plan["mode"] == "routed" and not errors and len(calls) == len(plan["items"])
    for key, item in plan["items"].items():
        answers = collect_answers(plan, records, key)
        row = {"id": key, "state": item["state"], "answers": answers, "stock": item.get("stock"), "flight": item.get("flight")}
        if plan["pattern"] in {"fan_out", "confidence"}:
            step = screen_step(item["state"]["note"], item["stock"], item["flight"], item["mission"], answers, plan["config"]["gates"])
            initial = screen_step(item["state"]["note"], item["stock"], item["flight"], item["mission"], {}, plan["config"]["gates"])
            settled = step["route"] or "REVIEW"
            reason = step["reason"] if step["route"] else "incomplete judgment: " + ", ".join(step["need"])
            if step["route"] is None:
                errors.append(f"{key}: required answers remain unasked")
            lower = None
            if all(isinstance(answers.get(qid), dict) and number(answers[qid].get("confidence")) for qid in ("note_status", "note_status_reversed")):
                lower = min(answers["note_status"]["confidence"], answers["note_status_reversed"]["confidence"])
            row.update({"route": settled, "reason": reason, "need": step["need"], "used": step["used"], "ignored": [qid for qid in answers if qid not in step["used"]],
                        "confidence": lower if not initial["route"] else None, "code_only": initial["route"] is not None,
                        "outcome": outcome(settled, packet["labels"][key]), "question_misses": question_misses(answers, packet["labels"][key])})
        elif plan["pattern"] == "scoring":
            row.update(composite(answers, plan["questions"], plan["config"]["weights"]))
            if row["total"] is None:
                errors.append(f"{key}: UNSCORED dimension missing or malformed")
        else:
            chosen = select_handler(item["state"]["message"], answers, plan["config"], packet, item["source"])
            actual = [entry for entry in handlers if entry.get("id") == key]
            executed = live and len(actual) == 1 and actual[0].get("executed") is True and actual[0].get("error") is None
            if live:
                if not executed or actual[0].get("handler") != chosen["handler"]:
                    errors.append(f"{key}: selected handler was not actually completed")
                elif actual[0].get("result") != chosen["result"]:
                    errors.append(f"{key}: deterministic handler result differs from its sources")
            label = packet["request_labels"][key]
            row.update({"handler": chosen["handler"], "reason": chosen["reason"], "executed": executed,
                        "result": actual[0].get("result") if executed else None, "source": chosen["source"],
                        "intent_mismatch": not isinstance(answers.get("intent"), dict) or answers["intent"].get("choice") not in label["expected_intents"],
                        "unsafe_handler": chosen["handler"] not in label["allowed_handlers"]})
        rows.append(row)
    if plan["pattern"] == "scoring":
        ranked = sorted((row for row in rows if row.get("total") is not None), key=lambda row: (-row["total"], row["id"]))
        for rank, row in enumerate(ranked, 1):
            row["rank"] = rank
        rows.sort(key=lambda row: (row.get("rank", 999), row["id"]))
    judge_usage = [row for row in usage if row["entry"].get("purpose") == "judge_batch" and row["entry"].get("provider") == "openrouter" and str(row["entry"].get("model", "")).startswith("typesafe/jev-1.13")]
    completion_usage = [row for row in usage if row["entry"].get("purpose") in {"eval_completion", "completion"}]
    uncached = live and bool(calls) and len(judge_usage) == len(calls) and all(row["entry"].get("stopReason") not in {"error", "aborted"} for row in judge_usage) and all(row.get("error") is None for row in calls)
    if uncached and any("openrouter/" + row["entry"]["model"] not in {PINNED, *models} for row in judge_usage):
        uncached = False
    reported_cost = usage_cost(judge_usage)
    batch_costs = [(row.get("status") or {}).get("cost") for row in calls]
    if uncached and (not all(number(cost, 0, float("inf")) for cost in batch_costs) or reported_cost is None or not math.isclose(sum(batch_costs), reported_cost, abs_tol=1e-8)):
        uncached = False
    if live and calls and not uncached:
        errors.append("Jev request/cost provenance not joined; native judge invocations only")
    if live and (completion_usage or any(row.get("completion_id") or row.get("model") for row in handlers)):
        errors.append("unexpected native completion: handler boundary changed")
    reviews = sum(row.get("route") == "REVIEW" for row in rows)
    critical = sum(row.get("outcome") in CRITICAL for row in rows)
    wrong = sum(row.get("outcome") in (*CRITICAL, "wrong return") and row.get("route") != "REVIEW" for row in rows)
    review_share = reviews / len(rows) if plan["pattern"] in {"fan_out", "confidence"} else None
    if plan["pattern"] == "confidence":
        if critical:
            errors.append("critical held-out message error" if plan["mode"] == "unseen" else "critical practice message error")
        if review_share > plan["config"]["review_ceiling"]:
            errors.append("review share exceeds the frozen ceiling")
    if plan["pattern"] == "intent" and plan["mode"] == "routed" and any(row["unsafe_handler"] for row in rows):
        errors.append("unsafe-handler mismatch against the request labels")
    # Completion/result errors hold completeness; measured decision errors do not erase a completed sample.
    incomplete = any(any(token in error for token in ("incomplete", "missing", "malformed", "unasked", "UNSCORED", "build", "did not complete", "not actually", "differs", "changed", "concurrency")) for error in errors)
    metrics = {"native_judge_invocations": len(calls) if live else 0, "jev_requests": len(judge_usage) if uncached else 0 if not live else None,
               "request_claim": "PASS" if uncached or not live or not calls else "HOLD", "reported_jev_cost_usd": reported_cost if live else 0,
               "completion_calls": len(completion_usage) if live else 0, "reported_completion_cost_usd": usage_cost(completion_usage) if completion_usage else 0,
               "chat_calls": None, "reported_chat_cost_usd": None, "wall_ms": finish[0].get("wall_ms") if live and len(finish) == 1 else None,
               "review_share": review_share, "wrong_automatic": wrong, "critical_errors": critical,
               "intent_mismatches": sum(row.get("intent_mismatch", False) for row in rows),
               "unsafe_handler_mismatches": sum(row.get("unsafe_handler", False) for row in rows),
               "handler_counts": {name: sum(row.get("handler") == name and row.get("executed") for row in rows) for name in sorted(set(MAPPING.values()))}}
    return {"run_id": plan["run_id"], "pattern": plan["pattern"], "mode": plan["mode"], "revision": plan["revision"], "config": plan["config"],
            "live": live, "complete": not incomplete and (not live or bool(finish) and finish[0].get("complete") is True),
            "judgments_complete": judgments_complete,
            "served_build": next(iter(models)) if len(models) == 1 else None, "rows": rows, "calls": calls if live else [], "handlers": handlers if live else [],
            "metrics": metrics, "decision": "HOLD" if errors else "PASS", "reasons": sorted(set(errors)),
            "answer_hashes": {row["id"]: value_hash(row["answers"]) for row in rows}, "source_run": plan.get("source_run")}


def read_report(policy: dict, run_id: str) -> dict:
    folder = run_folder(policy, run_id)
    seal = load(folder / "seal.json")
    for relative, expected in seal["files"].items():
        file = folder / relative
        if not file.resolve().is_relative_to(folder) or file.is_symlink() or digest(file) != expected:
            raise Hold(f"{run_id}: saved evidence changed: {relative}")
    plan = read_plan(policy, run_id)
    saved = load(folder / "report.json")
    if plan.get("live", True):
        raw, usage = raw_records(folder), load(folder / "usage.json")
    else:
        source_folder = run_folder(policy, plan["source_run"])
        read_report(policy, plan["source_run"])
        raw, usage = raw_records(source_folder), []
        if digest(source_folder / "raw.jsonl") != plan["source_raw_sha256"]:
            raise Hold("replay source answers changed")
    current = analyze_run(plan, raw, usage, validate_packet(Path(policy["work_root"])), plan.get("live", True))
    if encoded(saved) != encoded(current):
        raise Hold(f"{run_id}: report differs from deterministic recomputation")
    return saved


def seal_report(folder: Path, report: dict, usage: list[dict]) -> None:
    save(folder / "usage.json", usage)
    save(folder / "report.json", report)
    files = {file.relative_to(folder).as_posix(): digest(file) for file in sorted(folder.rglob("*")) if file.is_file()}
    save(folder / "seal.json", {"files": files, "sealed_at": now()})


def view_reports(packet: dict, reports: list[dict], policy: dict) -> dict:
    messages = [wrapped["entry"]["message"] for wrapped in journal_entries(policy)
                if wrapped["entry"].get("type") == "message" and wrapped["entry"].get("message", {}).get("role") == "assistant"]
    costs = [message.get("usage", {}).get("cost", {}).get("total") for message in messages]
    overhead = {"scope": "whole attempt as of inspection; excludes Jev calls", "chat_calls": len(messages),
                "reported_chat_cost_usd": sum(costs) if costs and all(number(cost, 0, float("inf")) for cost in costs) else None}
    return {"kind": reports[0]["pattern"] if reports else "inspection", "mission": packet["mission"], "runs": reports, "session_overhead": overhead}


def finalize_plan(policy: dict, state: dict, run_id: str) -> dict:
    plan = read_plan(policy, run_id)
    folder = run_folder(policy, run_id)
    if (folder / "report.json").exists():
        raise Hold("this operation already finalized; inspect its saved run")
    if not state["active_plan"] or state["active_plan"]["run_id"] != run_id or not state["active_plan"]["consumed"]:
        raise Hold("native operation lacks its one-use cell authorization")
    records = raw_records(folder)
    usage = operation_usage(policy, plan, records)
    report = analyze_run(plan, records, usage, validate_packet(Path(policy["work_root"])))
    seal_report(folder, report, usage)
    state["active_plan"] = None
    update_state(policy, state)
    append(Path(policy["evidence_root"]) / "control.jsonl", {"type": "finalized", "run_id": run_id, "seal_sha256": digest(folder / "seal.json"), "at": now()})
    return {"status": report["decision"], "message": f"{run_id}: {report['decision']}; " + ("; ".join(report["reasons"]) or "saved native results and deterministic policy agree"),
            "run_id": run_id, "view": view_reports(validate_packet(Path(policy["work_root"])), [report], policy)}


def replay_runs(policy: dict, state: dict, pattern: str, source_run: str, revisions: list[str]) -> dict:
    if pattern == "fan_out" or not isinstance(revisions, list) or not revisions or len(revisions) > 8 or len(set(revisions)) != len(revisions):
        raise Hold("replay needs one to eight distinct confidence/scoring/intent revisions")
    if state["active_plan"]:
        raise Hold("finish the active model operation before replay")
    source = read_report(policy, source_run)
    original = read_plan(policy, source_run)
    required = "fan_out" if pattern == "confidence" else pattern
    answered = source["judgments_complete"] if pattern == "intent" else source["complete"]
    if source["pattern"] != required or not answered or (pattern == "confidence" and source["mode"] != "fan_out") or (pattern == "intent" and source["mode"] != "routed"):
        raise Hold("replay requires a complete compatible answer run; missing answers never trigger a rerun")
    configs = [(revision, read_revision(policy, revision)) for revision in revisions]
    for revision, config in configs:
        if not compatible_questions(config, original, pattern):
            raise Hold("replay refused: question definition changed; only gates, weights or handler mapping may change")
        group = "gates" if pattern == "confidence" else "weights" if pattern == "scoring" else "handlers"
        if any(encoded(config[key]) != encoded(original["config"][key]) for key in PATTERN_FIELDS[pattern] - {group}):
            raise Hold("replay changes only " + group)
    raw_folder = run_folder(policy, original.get("source_run") or source_run)
    records = raw_records(raw_folder)
    packet = validate_packet(Path(policy["work_root"]))
    reports = []
    for revision, config in configs:
        run_id = "r_" + uuid.uuid4().hex[:12]
        folder = run_folder(policy, run_id)
        folder.mkdir(parents=True, exist_ok=False)
        plan = {**original, "run_id": run_id, "pattern": pattern, "revision": revision, "config": config, "live": False, "source_run": original.get("source_run") or source_run,
                "source_raw_sha256": digest(raw_folder / "raw.jsonl"), "output_dir": str(folder), "prepared_at": now()}
        plan.pop("freeze", None)
        save(folder / "plan.json", plan)
        save(folder / "authorization.json", {"run_id": run_id, "revision": revision, "plan_sha256": digest(folder / "plan.json"), "cell_code": None})
        report = analyze_run(plan, records, [], packet, False)
        seal_report(folder, report, [])
        reports.append(report)
        state["runs"].append(run_id)
        append(Path(policy["evidence_root"]) / "control.jsonl", {"type": "replayed", "run_id": run_id, "source_run": plan["source_run"], "seal_sha256": digest(folder / "seal.json"), "at": now()})
    update_state(policy, state)
    return {"status": "PASS", "message": "Replay saved; zero new Jev calls or handler executions. Intent preview: handlers not executed.",
            "run_id": reports[-1]["run_id"], "view": view_reports(packet, reports, policy)}




def log_records(file: Path) -> list[dict]:
    if not file.is_file() or file.is_symlink():
        return []
    return [strict_json(line) for line in file.read_text(encoding="utf-8").splitlines()]


def audit_evidence(policy: dict) -> list[str]:
    errors = []
    try:
        check_policy(policy)
        packet = validate_packet(Path(policy["work_root"]))
        state = load(state_file(policy))
        control = log_records(Path(policy["evidence_root"]) / "control.jsonl")
        guard = log_records(Path(policy["guard_log"]))
        native = journal_entries(policy)
        native_calls, native_results = {}, {}
        for wrapped in native:
            entry = wrapped["entry"]
            if entry.get("type") == "model_change":
                if entry.get("resolvedModelIsFallback") or entry.get("model") not in {MAIN, PINNED}:
                    errors.append("native journal model/fallback transition")
            message = entry.get("message", {})
            if message.get("role") == "assistant":
                for block in message.get("content", []):
                    if block.get("type") == "toolCall":
                        native_calls[block["id"]] = block
                if message.get("provider") != "openrouter" or message.get("model") != "anthropic/claude-sonnet-4.6":
                    errors.append("native main model identity differs")
            elif message.get("role") == "toolResult":
                native_results[message.get("toolCallId")] = message
        if not guard or not any(row.get("type") == "guard_ready" for row in guard):
            errors.append("native-session guard lifecycle not recorded")
        if any(row.get("type") == "guard_error" for row in guard):
            errors.append("native-session guard identity/runtime failure")
        for row in control:
            if row["type"] == "configured" and digest(revision_file(policy, row["revision"])) != row["sha256"]:
                errors.append("saved configuration revision changed")
            if row["type"] == "prepared" and digest(run_folder(policy, row["run_id"]) / "plan.json") != row["plan_sha256"]:
                errors.append("saved prepared plan changed")
            if row["type"] in {"finalized", "replayed"} and digest(run_folder(policy, row["run_id"]) / "seal.json") != row["seal_sha256"]:
                errors.append("saved immutable result seal changed")
        for revision in state["active_revisions"].values():
            read_revision(policy, revision)
        for run_id in state["runs"]:
            folder = run_folder(policy, run_id)
            if not (folder / "report.json").is_file():
                errors.append(f"{run_id}: native operation not finalized")
                continue
            report = read_report(policy, run_id)
            plan = read_plan(policy, run_id)
            if not report["live"]:
                if report["metrics"]["native_judge_invocations"] != 0 or report["metrics"]["completion_calls"] != 0 or any(row.get("executed") for row in report["rows"]):
                    errors.append(f"{run_id}: replay misrepresented as handler/model execution")
                continue
            auth = load(folder / "authorization.json")
            authorized = [row for row in guard if row.get("type") == "decision" and row.get("tool") == "eval" and row.get("allow") is True
                          and row.get("arguments", {}).get("code") == auth["cell_code"]]
            if len(authorized) != 1:
                errors.append(f"{run_id}: exact eval cell authorization missing/duplicated")
            else:
                call_id = authorized[0].get("call_id")
                requested = native_calls.get(call_id)
                result = native_results.get(call_id)
                if not requested or requested.get("name") != "eval" or requested.get("arguments", {}).get("code") != auth["cell_code"] or not result or result.get("isError"):
                    errors.append(f"{run_id}: native eval call/result join incomplete")
            for usage in load(folder / "usage.json"):
                matches = [wrapped for wrapped in native if wrapped["session_file"] == usage["session_file"] and wrapped["entry"].get("id") == usage["entry"].get("id")]
                if len(matches) != 1 or encoded(matches[0]) != encoded(usage):
                    errors.append(f"{run_id}: native usage record changed or missing")
            for row in report["rows"]:
                if plan["pattern"] == "intent" and row["executed"]:
                    if load(folder / "handlers" / (row["id"] + ".json")) != row["result"]:
                        errors.append(f"{run_id}.{row['id']}: handler disk effect differs")
            if report["decision"] == "HOLD":
                errors.extend(f"{run_id}: {reason}" for reason in report["reasons"])
        baseline = Path(policy["evidence_root"]) / "work-before.json"
        if baseline.is_file():
            actual = shared(policy).snapshot(Path(policy["work_root"]), [], ("out/native",))
            if load(baseline) != actual:
                errors.append("work changed outside supplied evidence outputs")
        if state["active_plan"]:
            errors.append("a paid operation is still active")
        if packet["hashes"] != {key: policy["protected"][key] for key in packet["hashes"]}:
            errors.append("initial source packet identity differs")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
        errors.append(f"incomplete native evidence: {error}")
    return sorted(set(errors))


def verification_result(policy: dict) -> dict:
    errors = audit_evidence(policy)
    state = load(state_file(policy))
    reports = []
    for key in state["runs"]:
        try:
            reports.append(read_report(policy, key))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    completed = {(row["pattern"], row["mode"], row["live"]) for row in reports if row["complete"]}
    required = {("fan_out", "serial", True), ("fan_out", "fan_out", True), ("confidence", "unseen", True),
                ("confidence", "fan_out", False), ("scoring", "score", True), ("scoring", "score", False),
                ("intent", "routed", True), ("intent", "routed", False)}
    for entry in sorted(required - completed):
        errors.append("not completed: " + "/".join(map(str, entry)))
    gates = {row["config"]["gates"]["auto_pass_confidence"] for row in reports if row["pattern"] == "confidence" and not row["live"] and row["complete"] and row["config"]["gates"]["auto_return_confidence"] == 0.4}
    if not {0.4, 0.6, 0.8}.issubset(gates):
        errors.append("not compared: pass-confidence gates 0.4/0.6/0.8 with return confidence 0.4")
    weights = {tuple(row["config"]["weights"][name] for name in RANKING) for row in reports if row["pattern"] == "scoring" and row["complete"]}
    if not {(0.5, 0.3, 0.2), (0.2, 0.6, 0.2)}.issubset(weights) or len(weights) < 3:
        errors.append("not compared: urgency-led, impact-led and learner-selected third weights")
    executed = {row["handler"] for report in reports if report["pattern"] == "intent" and report["mode"] == "routed" and report["live"] for row in report["rows"] if row["executed"]}
    for handler in sorted(set(MAPPING.values()) - executed):
        errors.append("not executed: " + handler)
    counts = {"runs": len(reports), "live_runs": sum(row["live"] for row in reports), "replays": sum(not row["live"] for row in reports),
              "native_judge_invocations": sum(row["metrics"]["native_judge_invocations"] for row in reports),
              "completion_calls": sum(row["metrics"]["completion_calls"] for row in reports)}
    return {"status": "HOLD" if errors else "PASS", "message": "; ".join(errors) if errors else "Sources, immutable revisions, native calls, usage, handler effects and recomputed comparisons agree.",
            "view": {"kind": "verification", "mission": validate_packet(Path(policy["work_root"]))["mission"], "counts": counts, "errors": errors,
                     "packet_label": "review packet — not a manifest or movement order"}}


def control_action(request: dict, policy: dict) -> dict:
    """Finite JSON adapter; public callers never supply code, paths, models or answers."""
    try:
        check_policy(policy)
        with control_lock(policy):
            initialize_controls(policy)
            state = load(state_file(policy))
            if not isinstance(request, dict) or not isinstance(request.get("action"), str):
                raise Hold("a control request must name its action")
            action = request["action"]
            shapes = {
                "configure": {"action", "pattern", "changes"}, "prepare": {"action", "pattern", "revision", "mode"},
                "replay": {"action", "pattern", "source_run", "revisions"}, "show": {"action", "runs"}, "verify": {"action"},
                "authorize_eval": {"action", "code"}, "screen_step": {"action", "plan_id", "id"}, "finalize": {"action", "plan_id"}}
            if action == "inspect":
                if set(request) - {"action", "target", "pattern", "id"} or request.get("target") not in {"controls", "source", "run"}:
                    raise Hold("inspect accepts only its declared target, pattern and ID")
            elif action in shapes:
                exact(request, shapes[action], action)
            else:
                raise Hold("unregistered control action")
            pattern = request.get("pattern")
            if pattern is not None and pattern not in PATTERN_FIELDS:
                raise Hold("unregistered pattern")
            if action in {"configure", "prepare", "replay"} and pattern is None:
                raise Hold("pattern is required")
            if action == "inspect":
                target, key = request["target"], request.get("id")
                packet = validate_packet(Path(policy["work_root"]))
                if target == "controls":
                    if key is not None:
                        raise Hold("controls inspect has no arbitrary ID or path")
                    selected = [pattern] if pattern else list(PATTERN_FIELDS)
                    controls = {name: {"revision": state["active_revisions"][name], "settings": {field: read_revision(policy, state["active_revisions"][name])[field] for field in PATTERN_FIELDS[name]}} for name in selected}
                    return {"status": "PASS", "message": "Inspect the supplied settings and question wording before preparing a model operation.",
                            "revision": state["active_revisions"][pattern] if pattern else None,
                            "view": {"kind": "inspection", "mission": packet["mission"], "controls": controls, "main_model": MAIN, "judge": PINNED, "omp_version": policy["omp_version"]}}
                if pattern is not None or not isinstance(key, str):
                    raise Hold("source/run inspect requires one known ID, not a pattern or path")
                if target == "run":
                    report = read_report(policy, key)
                    return {"status": report["decision"], "message": f"Saved {key}: {report['decision']}", "run_id": key, "view": view_reports(packet, [report], policy)}
                if key == "mission":
                    data = {"mission": packet["mission"], "authority": "fixed scenario snapshot; no next confirmed flight"}
                elif key in packet["requests"]:
                    message = packet["requests"][key]["state"]["message"]
                    ids, _ = request_sources(message, packet)
                    visible = None if finished_unseen(policy, state) else set(list(packet["notes"])[:20])
                    if visible is not None and len(ids) == 1 and ids[0] not in visible:
                        raise Hold("single held-out request sources open after the frozen unseen measurement")
                    data = {"request": packet["requests"][key], "source": request_source(message, packet, visible)}
                else:
                    by_cargo = {row["cargo_id"]: note_id for note_id, row in packet["stock"].items()}
                    note_id = by_cargo.get(key, key)
                    if note_id not in packet["notes"]:
                        raise Hold("unknown source ID; paths are never source IDs")
                    if int(note_id[3:]) > 20 and not finished_unseen(policy, state):
                        raise Hold("held-out worked sources open only after the frozen unseen run completes")
                    data = source_view(packet, note_id)
                    if int(note_id[3:]) <= 20 or finished_unseen(policy, state):
                        data["desk_label"] = packet["labels"][note_id]
                return {"status": "PASS", "message": f"Source {key}; stock release and exact-flight acceptance remain separate.", "view": {"kind": "inspection", "mission": packet["mission"], "data": data}}
            if action == "configure":
                if state["active_plan"]:
                    raise Hold("finish the active operation before changing configuration")
                if state["unseen"] and (pattern == "confidence" or "screen_questions" in request["changes"] or "ranking_questions" in request["changes"] and "urgency" in request["changes"]["ranking_questions"]):
                    raise Hold("confidence inputs are frozen; no label-guided retuning in this attempt")
                previous = state["active_revisions"][pattern]
                before = read_revision(policy, previous)
                config = merge_settings(before, request["changes"], pattern)
                if config == before:
                    raise Hold("configuration is unchanged; name one meaningful setting change")
                revision = save_revision(policy, config, previous)
                state["active_revisions"][pattern] = revision
                update_state(policy, state)
                return {"status": "PASS", "message": "Saved " + revision + ": " + "; ".join(config_difference(before, config)), "revision": revision}
            if action == "prepare":
                return prepare_plan(policy, state, pattern, request["revision"], request["mode"])
            if action == "authorize_eval":
                active = state["active_plan"]
                if not active or active["consumed"]:
                    raise Hold("no unused active plan; an old paid cell cannot run twice")
                run_id = active["run_id"]
                read_plan(policy, run_id)
                auth = load(run_folder(policy, run_id) / "authorization.json")
                if request["code"] != auth["cell_code"]:
                    raise Hold("eval code differs from the exact frozen native cell")
                active["consumed"], active["started_at"] = True, now()
                update_state(policy, state)
                append(Path(policy["evidence_root"]) / "control.jsonl", {"type": "eval_authorized", "run_id": run_id, "at": active["started_at"]})
                return {"status": "PASS", "message": "Exact frozen cell admitted once.", "run_id": run_id}
            if action == "screen_step":
                run_id, key = request["plan_id"], request["id"]
                active = state["active_plan"]
                if not active or active["run_id"] != run_id or not active["consumed"]:
                    raise Hold("screen step requires the active authorized native plan")
                plan = read_plan(policy, run_id)
                if key not in plan["items"]:
                    raise Hold("screen step input is not in the frozen plan")
                item = plan["items"][key]
                answers = collect_answers(plan, raw_records(run_folder(policy, run_id)), key)
                if plan["pattern"] in {"fan_out", "confidence"}:
                    step = screen_step(item["state"]["note"], item["stock"], item["flight"], item["mission"], answers, plan["config"]["gates"])
                    return {"status": "PASS", "message": step["reason"], "view": step}
                if plan["pattern"] != "intent" or plan["mode"] != "routed":
                    raise Hold("this plan has no staged screen/handler dispatch")
                selected = select_handler(item["state"]["message"], answers, plan["config"], validate_packet(Path(policy["work_root"])), item["source"])
                file = run_folder(policy, run_id) / "handlers" / (key + ".json")
                if file.exists():
                    raise Hold("this deterministic handler already executed")
                save(file, selected["result"])
                return {"status": "PASS", "message": selected["reason"], "view": selected}
            if action == "finalize":
                return finalize_plan(policy, state, request["plan_id"])
            if action == "replay":
                return replay_runs(policy, state, pattern, request["source_run"], request["revisions"])
            if action == "show":
                ids = request["runs"]
                if not isinstance(ids, list) or not 1 <= len(ids) <= 2 or len(set(ids)) != len(ids):
                    raise Hold("show names one run or one matching before/after pair")
                reports = [read_report(policy, key) for key in ids]
                if len(reports) == 2:
                    left, right = (read_plan(policy, key) for key in ids)
                    if left["source_hashes"] != right["source_hashes"] or left["items"] != right["items"] or encoded(left["questions"]) != encoded(right["questions"]):
                        raise Hold("show pair does not share identical sources, states and questions")
                    if reports[0]["served_build"] != reports[1]["served_build"]:
                        raise Hold("show pair served different Jev builds")
                return {"status": "PASS", "message": "Saved numeric evidence; not a benchmark or cargo clearance.", "view": view_reports(validate_packet(Path(policy["work_root"])), reports, policy)}
            return verification_result(policy)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
        return {"status": "HOLD", "message": str(error)}


def descriptor(file: Path) -> dict:
    if file.is_symlink() or not file.is_file():
        raise Hold(f"missing or linked supplied helper: {file}")
    return {"path": str(file.resolve()), "sha256": digest(file)}


def create_policy(work: Path, omp_version: str) -> dict:
    validate_packet(work)
    validate_config(load(work / "shared/controls/PATTERNS.json"))
    evidence = evidence_root(work)
    evidence.mkdir(parents=True, exist_ok=False)
    overlay = {"modelRoles": {"default": MAIN, "judge": PINNED}, "retry": {"enabled": False, "modelFallback": False, "maxRetries": 0},
               "startup": {"setupWizard": False}, "providers": {"cacheWarming": "off"},
               "tools": {"approval": {"blue_gauge": "allow", "eval": "allow"}, "intentTracing": False}}
    save(evidence / "runtime-config.yml", overlay)
    attempt_id = work.parent.name if work.parent.parent == attempts_root() and work.name == "work" else work.name + "-" + uuid.uuid4().hex[:12]
    policy = {"schema_version": 1, "attempt_id": attempt_id, "work_root": str(work), "evidence_root": str(evidence),
              "provider": "openrouter", "model": "anthropic/claude-sonnet-4.6", "judge_selector": PINNED, "omp_version": omp_version,
              "python": str(Path(sys.executable).resolve()), "adapter": descriptor(work / "scripts/blue_gauge.py"),
              "shared_guard": descriptor(REPO / "shared/course_guard.mjs"), "shared_launcher": descriptor(REPO / "shared/run_omp.py"),
              "prepare_helper": descriptor(REPO / "shared/prepare_work.py"), "runner": descriptor(work / "shared/controls/patterns.mjs"),
              "extension": descriptor(work / "shared/controls/patterns.extension.mjs"), "instruction": descriptor(work / "shared/controls/OMP_INSTRUCTIONS.md"),
              "config": descriptor(evidence / "runtime-config.yml"), "guard_log": str(evidence / "guard.jsonl"),
              "protected": {file.relative_to(work).as_posix(): digest(file) for tree in (work / "shared", work / "scripts") for file in sorted(tree.rglob("*")) if file.is_file()}}
    save(evidence / "policy.json", policy)
    save(evidence / "work-before.json", shared(policy).snapshot(work, [], ("out/native",)))
    (evidence / "sessions").mkdir()
    initialize_controls(policy)
    return policy


def attempts_root() -> Path:
    return Path.home() / "Documents/AIHB-work/module-06"


def register_attempt(policy: dict) -> None:
    root = attempts_root()
    root.mkdir(parents=True, exist_ok=True)
    folder = root / ("prepared-" + policy["attempt_id"])
    folder.mkdir(exist_ok=False)
    save(folder / "attempt.json", {"id": policy["attempt_id"], "policy_path": str(Path(policy["evidence_root"]) / "policy.json")})


def saved_attempts() -> dict[str, Path]:
    candidates = {}
    root = attempts_root()
    if not root.exists():
        return candidates
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.is_symlink():
            continue
        registration = folder / "attempt.json"
        if registration.is_file():
            entry = load(registration)
            key, file = entry["id"], Path(entry["policy_path"])
        else:
            key, file = folder.name, folder / "work/out/native/policy.json"
        if not file.is_file() or file.is_symlink():
            continue
        if key in candidates and candidates[key] != file:
            raise Hold("duplicate native Module 06 attempt ID: " + key)
        candidates[key] = file
    return candidates

def checkout_key() -> str:
    """Read only the named OpenRouter credential; no expansion or dotenv execution."""
    file = REPO / ".env"
    if not file.is_file() or file.is_symlink():
        return ""
    for line in file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key.strip() != "OPENROUTER_API_KEY":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value
    return ""



def terminal_key() -> str:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise Hold("native OMP requires an interactive terminal; credentials are never read from a pipe")
    key = os.environ.get("OPENROUTER_API_KEY", "").strip() or checkout_key()
    if not key:
        try:
            key = getpass.getpass("OpenRouter key (hidden; child-process environment only): ").strip()
        except (EOFError, KeyboardInterrupt):
            raise Hold("credential entry cancelled; no model call") from None
    if not key:
        raise Hold("blank key; no model call")
    return key


def omp_identity() -> tuple[str, str]:
    if sys.version_info < (3, 12):
        raise Hold("Python 3.12+ is required; return to your existing setup route")
    omp = shutil.which("omp")
    if not omp:
        raise Hold("omp is not on PATH; return to your existing setup route")
    result = subprocess.run([omp, "--version"], capture_output=True, text=True, timeout=15)
    version = result.stdout.strip()
    if result.returncode or not shared().valid_omp_version(version):
        raise Hold("omp --version did not return its actual omp/<semver> identity")
    return omp, version


def interrupt_plan(policy: dict, reason: str) -> None:
    state = load(state_file(policy))
    active = state["active_plan"]
    if not active:
        return
    folder = run_folder(policy, active["run_id"])
    records = raw_records(folder)
    if not any(row.get("type") == "finish" for row in records):
        append(folder / "raw.jsonl", {"type": "finish", "started_at": active.get("started_at", now()), "wall_ms": 0, "complete": False, "error": reason})
    active["consumed"] = True
    update_state(policy, state)
    finalize_plan(policy, state, active["run_id"])


def launch_session(policy: dict, omp: str, key: str, resume_file: Path | None = None) -> int:
    check_policy(policy)
    evidence = Path(policy["evidence_root"])
    runtime = evidence / "runtime"
    runtime.mkdir(exist_ok=True)
    environment = shared(policy).isolated_env(runtime, evidence / "policy.json", key)
    for name in ("TERM", "COLORTERM", "COLUMNS", "LINES"):
        if name in os.environ:
            environment[name] = os.environ[name]
    cwd = Path(environment["HOME"]) / "cwd"
    cwd.mkdir(exist_ok=True)
    listing = subprocess.run([omp, "models", "--kind", "judge", "--json", "--no-extensions"], cwd=cwd, env=environment,
                             capture_output=True, text=True, timeout=120)
    if key in listing.stdout or key in listing.stderr:
        raise Hold("credential appeared in runtime catalog output; output not saved")
    if listing.returncode:
        raise Hold("Jev catalog is unavailable through this key; no chat substitute or fixture fallback")
    catalog = strict_json(listing.stdout)
    if not any(row.get("selector") == PINNED for row in catalog.get("models", [])):
        raise Hold("the pinned Jev selector is not offered; live lane held")
    launch_id = uuid.uuid4().hex[:12]
    save(evidence / "launches" / (launch_id + "-catalog.json"), catalog)
    command = [omp, "--model", MAIN, "--no-title", "--no-skills", "--no-rules", "--no-extensions", "--no-lsp", "--no-prewalk", "--no-pty",
               "--approval-mode", "always-ask", "--no-tools", "--tools", "blue_gauge,eval",
               "--extension", policy["extension"]["path"], "--config", policy["config"]["path"],
               "--append-system-prompt", policy["instruction"]["path"], "--session-dir", str(evidence / "sessions")]
    if resume_file is not None:
        if resume_file.is_symlink() or not resume_file.resolve().is_relative_to(evidence / "sessions") or not resume_file.is_file():
            raise Hold("resume requires this attempt's explicitly selected native session")
        command += ["--resume", str(resume_file)]
    print(f"WORK: {policy['work_root']}\nEVIDENCE: {evidence}\nOMP: {policy['omp_version']}\nMAIN: {MAIN}\nJEV: {PINNED}", flush=True)
    print("planned movement: Aster Airhead → BG-F17 → Kestrel | snapshot 05:00 UTC+02 | cargo list closes 05:30 | departure 06:00", flush=True)
    save(evidence / "launches" / (launch_id + "-start.json"), {"command": command, "started_at": now(), "omp_version": policy["omp_version"], "resume": str(resume_file) if resume_file else None})
    child = subprocess.Popen(command, cwd=cwd, env=environment)
    interrupted = False
    try:
        code = child.wait()
    except KeyboardInterrupt:
        interrupted = True
        child.terminate()
        try:
            code = child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            code = child.wait()
    finally:
        interrupt_plan(policy, "native session interrupted" if interrupted else "native session closed with unfinished operation")
    session_files = []
    for file in sorted((evidence / "sessions").glob("*.jsonl")):
        headers = [row for row in log_records(file) if row.get("type") == "session"]
        if len(headers) == 1:
            session_files.append({"id": headers[0]["id"], "path": str(file)})
    state = load(state_file(policy))
    state["sessions"] = session_files
    update_state(policy, state)
    save(evidence / "launches" / (launch_id + "-end.json"), {"exit_code": code, "interrupted": interrupted, "sessions": session_files, "ended_at": now()})
    if code or interrupted or not session_files:
        print("HOLD: native session ended without complete proof; prior results preserved.")
        return 1
    print(f"Native session saved. Resume selects this attempt explicitly: {policy['attempt_id']}")
    return 0


def start(work: Path | None) -> int:
    omp, version = omp_identity()
    key = terminal_key()
    if work is None:
        helper_spec = importlib.util.spec_from_file_location("blue_gauge_prepare", REPO / "shared/prepare_work.py")
        helper = importlib.util.module_from_spec(helper_spec)
        helper_spec.loader.exec_module(helper)
        attempt = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
        work = helper.prepare("06", attempts_root() / attempt / "work")
    else:
        work = work.expanduser().absolute()
        if work.is_symlink() or not work.is_dir() or work.resolve() != work or work.is_relative_to(REPO):
            raise Hold("--work must name a previously prepared external Module 06 folder")
        if (evidence_root(work) / "policy.json").exists():
            raise Hold("this attempt already has a native session; use resume and explicitly select it")
    policy = create_policy(work, version)
    if work.parent.parent != attempts_root() or work.name != "work":
        register_attempt(policy)
    return launch_session(policy, omp, key)


def resume() -> int:
    omp, version = omp_identity()
    candidates = saved_attempts()
    root = attempts_root()
    if not candidates:
        raise Hold("no prepared native Module 06 attempts under " + str(root))
    if not sys.stdin.isatty():
        raise Hold("resume requires an explicit terminal selection")
    print("Existing Module 06 attempts:\n" + "\n".join(candidates))
    chosen = input("Attempt ID (no automatic latest): ").strip()
    if chosen not in candidates:
        raise Hold("select an exact listed attempt ID")
    policy = load(candidates[chosen])
    check_policy(policy)
    if version != policy["omp_version"]:
        raise Hold("OMP runtime changed; keep this evidence and start a fresh attempt")
    interrupt_plan(policy, "previous operation unfinished; resume never repeats a paid operation")
    sessions = load(state_file(policy))["sessions"]
    if not sessions:
        raise Hold("no native session ID recorded for this attempt")
    print("\n".join(row["id"] for row in sessions))
    session_id = input("Native session ID: ").strip()
    selected = [row for row in sessions if row["id"] == session_id]
    if len(selected) != 1:
        raise Hold("select an exact listed native session ID")
    return launch_session(policy, omp, terminal_key(), Path(selected[0]["path"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    launch = commands.add_parser("start", help="prepare and enter the actual native OMP terminal")
    launch.add_argument("--work", type=Path)
    commands.add_parser("resume", help="explicitly select an existing attempt and native session")
    audit = commands.add_parser("verify", help="staff audit of native saved evidence")
    audit.add_argument("--work", required=True, type=Path)
    audit.add_argument("--evidence", required=True, type=Path)
    control = commands.add_parser("control", help=argparse.SUPPRESS)
    control.add_argument("--policy", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "control":
            # A control HOLD is a protocol result, not a crashed subprocess.
            os.environ["COURSE_GUARD_POLICY"] = str(args.policy.absolute())
            result = control_action(strict_json(sys.stdin.read()), load(args.policy))
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
            return 0
        if args.command == "start":
            return start(args.work)
        if args.command == "resume":
            return resume()
        work, evidence = args.work.expanduser().resolve(), args.evidence.expanduser().resolve()
        if evidence != evidence_root(work):
            raise Hold("evidence must be the selected work folder's out/native directory")
        policy = load(evidence / "policy.json")
        os.environ["COURSE_GUARD_POLICY"] = str(evidence / "policy.json")
        result = verification_result(policy)
        print(result["status"] + ": " + result["message"])
        print(json.dumps(result["view"], ensure_ascii=False, indent=2))
        return 0 if result["status"] == "PASS" else 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired, EOFError) as error:
        if args.command == "control":
            print(json.dumps({"status": "HOLD", "message": str(error)}))
            return 0
        print("HOLD: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
