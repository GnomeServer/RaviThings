#!/usr/bin/env python3
"""Shared Chalk Line logic: build the state, validate typed answers, and route messages.

Everything here is deterministic and inspectable. The model answers questions; this code
owns the control flow, the unit arithmetic, supersession, and the routes.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ANSWER_SCHEMA = "chalk-line/answers/1"
QUESTION_SCHEMA = "chalk-line/questions/1"
LABEL_SCHEMA = "chalk-line/labels/1"
GATES_SCHEMA = "chalk-line/gates/1"
ROUTES = ("PICK", "CLARIFY", "REFER", "REVIEW", "SUPERSEDED", "IGNORE")
SAMPLE_IDS = ("CL-003", "CL-007", "CL-011", "CL-014", "CL-018", "CL-022", "CL-026", "CL-031", "CL-035", "CL-039")
LABEL_KEYS = ("request", "line", "quantity", "authority")
CORE_QUESTIONS = {"request": "yes_no", "line": "choice", "quantity": "choice", "urgency": "score", "authority": "yes_no", "instructs_desk": "yes_no", "replaces": "choice"}
OWN_KEY = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
NUMBER = re.compile(r"(?<![\w:.-])(\d+(?:\.\d+)?)(?![\w:.-])|(?<![\w-])(" + "|".join(WORD_NUMBERS) + r")(?=\s+\w)", re.IGNORECASE)


class Hold(ValueError):
    """A violation the caller reports and stops on."""


def strict_json(text: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Hold(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        return json.loads(text, object_pairs_hook=pairs)
    except json.JSONDecodeError as error:
        raise Hold(f"not valid JSON: {error.msg} at line {error.lineno}") from None


def load_json(path: Path):
    return strict_json(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def write_new(path: Path, data: bytes) -> None:
    """Create a file; never overwrite an earlier attempt."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


# ---------------------------------------------------------------- state

def read_messages(case: Path) -> list[dict]:
    rows = []
    for line in (case / "messages.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(strict_json(line))
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise Hold("duplicate message id in messages.jsonl")
    return rows


def candidates_for(text: str) -> list[dict]:
    """Every number in the message, with up to two following words of the same sentence. Software finds spans; the model picks."""
    found = []
    for match in NUMBER.finditer(text):
        start = match.start()
        span = match.group(0)
        if re.search(r"[.?!]$", text[match.end():match.end() + 1]):
            following = []
        else:
            following = re.findall(r"\s+([^\s]+)", text[match.end():])[:2]
        for word in following:
            span += " " + word
            if re.search(r"[.?!]$", word):
                break
        span = re.sub(r"[.,;:!?]+$", "", span)
        found.append({"id": f"q{len(found) + 1}", "text": span, "offset": start})
    return found


def build_state(case: Path) -> dict:
    catalog = load_json(case / "catalog.json")
    messages = []
    for row in read_messages(case):
        messages.append({"id": row["id"], "time": row["time"], "from": row["from"], "channel": row["channel"], "text": row["text"],
                         "candidates": [{"id": item["id"], "text": item["text"]} for item in candidates_for(row["text"])]})
    rules = {
        "requisition_authority": catalog["requisition_authority"],
        "requisition_reference": catalog["requisition_reference"],
        "unit_of_issue": catalog["unit_of_issue"],
        "case_means": catalog["case_means"],
        "later_messages_win": "A message that corrects, cancels, resends, or confirms an earlier message replaces it.",
    }
    return {"schema": "chalk-line/state/1", "movement": {key: catalog[key] for key in ("movement", "commodity", "origin", "destination", "vehicle", "run", "intake_closes")},
            "catalog": catalog["lines"], "desk_rules": rules, "messages": messages}


# ---------------------------------------------------------------- answers

def questions_by_key(questions: dict) -> dict[str, dict]:
    if not isinstance(questions, dict) or questions.get("schema") != QUESTION_SCHEMA or not isinstance(questions.get("questions"), list):
        raise Hold("questions.json has an unexpected schema")
    keys = [item.get("key") for item in questions["questions"]]
    if len(keys) != len(set(keys)):
        raise Hold("questions.json repeats a key")
    return {item["key"]: item for item in questions["questions"]}


def check_questions(questions: dict, pristine: dict | None = None) -> str:
    """The seven supplied questions must be intact; exactly one yes-or-no question of your own may follow them."""
    by_key = questions_by_key(questions)
    for key, kind in CORE_QUESTIONS.items():
        if key not in by_key:
            raise Hold(f"the supplied question {key!r} is missing")
        if by_key[key].get("type") != kind:
            raise Hold(f"the supplied question {key!r} must keep type {kind!r}")
        if pristine is not None and by_key[key] != questions_by_key(pristine)[key]:
            raise Hold(f"the supplied question {key!r} was changed; only your own question may differ")
    if list(by_key)[: len(CORE_QUESTIONS)] != list(CORE_QUESTIONS):
        raise Hold("keep the seven supplied questions first, in their original order")
    own = [key for key in by_key if key not in CORE_QUESTIONS]
    if len(own) != 1:
        raise Hold(f"add exactly one question of your own after the seven supplied ones; found {len(own)}")
    key = own[0]
    item = by_key[key]
    if not OWN_KEY.match(key):
        raise Hold(f"your question's key {key!r} must be 3 to 32 lowercase letters, digits, or underscores, starting with a letter")
    if item.get("type") != "yes_no" or item.get("answer") != "p":
        raise Hold("your question must have type yes_no and answer p")
    if set(item) != {"key", "type", "answer", "instructions"}:
        raise Hold("your question must hold exactly key, type, answer, and instructions")
    if not isinstance(item["instructions"], str) or len(item["instructions"].split()) < 8 or "?" not in item["instructions"]:
        raise Hold("your question's instructions must be a question of at least eight words")
    return key


def _number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Hold(f"{label}: not a number")
    if not 0 <= value <= 1:
        raise Hold(f"{label}: {value} is outside 0 to 1")
    return float(value)


def validate_answers(document, state: dict, questions: dict) -> list[dict]:
    """Return normalized answers in state order, or raise Hold at the first group of violations."""
    if not isinstance(document, dict):
        raise Hold("the reply is not one JSON object")
    if set(document) != {"schema", "answers"} or document.get("schema") != ANSWER_SCHEMA:
        raise Hold("the reply must hold exactly schema and answers, with schema chalk-line/answers/1")
    if not isinstance(document["answers"], list):
        raise Hold("answers is not a list")
    by_key = questions_by_key(questions)
    expected_ids = [message["id"] for message in state["messages"]]
    got_ids = [item.get("id") if isinstance(item, dict) else None for item in document["answers"]]
    if got_ids != expected_ids:
        missing = [item for item in expected_ids if item not in got_ids]
        extra = [item for item in got_ids if item not in expected_ids]
        duplicated = sorted({item for item in got_ids if got_ids.count(item) > 1})
        detail = f"missing {missing[:3]}, unexpected {extra[:3]}, duplicated {duplicated[:3]}"
        if not missing and not extra and not duplicated:
            detail = "all forty present but out of state order"
        raise Hold(f"answers must cover exactly the forty messages in state order; {detail}")
    violations: list[str] = []
    normalized = []
    for message, item in zip(state["messages"], document["answers"]):
        label = message["id"]
        keys = set(item) - {"id"}
        if keys != set(by_key):
            violations.append(f"{label}: keys differ from the question set (missing {sorted(set(by_key) - keys)}, extra {sorted(keys - set(by_key))})")
            continue
        row = {"id": label}
        for key, question in by_key.items():
            value = item[key]
            try:
                if not isinstance(value, dict):
                    raise Hold(f"{label}.{key}: not an object")
                if question["type"] == "yes_no":
                    if set(value) != {"p"}:
                        raise Hold(f"{label}.{key}: must hold only p")
                    row[key] = {"p": _number(value["p"], f"{label}.{key}.p")}
                elif question["type"] == "choice":
                    if set(value) != {"choice", "confidence"}:
                        raise Hold(f"{label}.{key}: must hold only choice and confidence")
                    options = choice_options(question, message, expected_ids)
                    if value["choice"] not in options:
                        raise Hold(f"{label}.{key}: {value['choice']!r} is not one of {options}")
                    row[key] = {"choice": value["choice"], "confidence": _number(value["confidence"], f"{label}.{key}.confidence")}
                else:
                    if set(value) != {"score", "confidence"}:
                        raise Hold(f"{label}.{key}: must hold only score and confidence")
                    score = value["score"]
                    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score < len(question["levels"]):
                        raise Hold(f"{label}.{key}: score must be an integer level from 0 to {len(question['levels']) - 1}")
                    row[key] = {"score": score, "confidence": _number(value["confidence"], f"{label}.{key}.confidence")}
            except Hold as error:
                violations.append(str(error))
        normalized.append(row)
    if violations:
        raise Hold("; ".join(violations[:10]) + (f"; and {len(violations) - 10} more" if len(violations) > 10 else ""))
    return normalized


def choice_options(question: dict, message: dict, ids: list[str]) -> list[str]:
    source = question.get("options_from")
    if source == "candidates":
        return [item["id"] for item in message["candidates"]] + ["NONE"]
    if source == "earlier_ids":
        return ids[: ids.index(message["id"])] + ["NONE"]
    return list(question["options"])


def parse_reply(text: str) -> tuple[object, bool]:
    """Accept the bare document or one fenced block; anything else is prose."""
    stripped = text.strip()
    fenced = False
    match = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", stripped, re.S | re.I)
    if match:
        stripped, fenced = match.group(1).strip(), True
    if not stripped.startswith("{"):
        raise Hold("the reply does not start with a JSON object; prose around the document is a violation")
    return strict_json(stripped), fenced


# ---------------------------------------------------------------- labels

def yes_no_side(p: float) -> str:
    return "yes" if p >= 0.5 else "no"


def noul_confidence(p: float) -> float:
    return abs(2 * p - 1)


def check_labels(labels, state: dict) -> dict[str, dict]:
    if not isinstance(labels, dict) or labels.get("schema") != LABEL_SCHEMA or not isinstance(labels.get("labels"), list):
        raise Hold("labels.json must hold schema chalk-line/labels/1 and a labels list")
    messages = {message["id"]: message for message in state["messages"]}
    ids = [item.get("id") for item in labels["labels"]]
    if ids != list(SAMPLE_IDS):
        raise Hold(f"labels must cover exactly the sample {list(SAMPLE_IDS)} in order")
    result = {}
    for item in labels["labels"]:
        message = messages[item["id"]]
        row = {}
        for key in LABEL_KEYS:
            value = item.get(key)
            if value in (None, "", "?"):
                raise Hold(f"{item['id']}.{key} is not filled in")
            if key in ("request", "authority"):
                if value not in ("yes", "no"):
                    raise Hold(f"{item['id']}.{key} must be yes or no")
            elif key == "line":
                if value not in ("GL-65", "GL-70", "GL-75", "GL-80", "UNSTATED", "MIXED", "NONE"):
                    raise Hold(f"{item['id']}.line must be a catalog line, UNSTATED, MIXED, or NONE")
            else:
                options = [candidate["id"] for candidate in message["candidates"]] + ["NONE"]
                if value not in options:
                    raise Hold(f"{item['id']}.quantity must be one of {options}")
            row[key] = value
        result[item["id"]] = row
    return result


def compare(labels: dict[str, dict], answers: list[dict], own: str | None = None) -> dict:
    by_id = {row["id"]: row for row in answers}
    report = {"sample": list(SAMPLE_IDS), "questions": {}, "disagreements": []}
    if own:
        report["own_question"] = {"key": own, "sample": {identifier: {"p": by_id[identifier][own]["p"], "side": yes_no_side(by_id[identifier][own]["p"])} for identifier in SAMPLE_IDS}}
    for key in LABEL_KEYS:
        agree = 0
        for identifier in SAMPLE_IDS:
            answer = by_id[identifier][key]
            if key in ("request", "authority"):
                model, declared = yes_no_side(answer["p"]), noul_confidence(answer["p"])
            else:
                model, declared = answer["choice"], answer["confidence"]
            mine = labels[identifier][key]
            if model == mine:
                agree += 1
            else:
                report["disagreements"].append({"id": identifier, "question": key, "mine": mine, "model": model, "declared_confidence": round(declared, 3)})
        report["questions"][key] = {"agree": agree, "disagree": len(SAMPLE_IDS) - agree}
    report["highest_confidence_among_disagreements"] = max((item["declared_confidence"] for item in report["disagreements"]), default=None)
    return report


# ---------------------------------------------------------------- routing

def load_gates(path: Path) -> dict:
    gates = load_json(path)
    if not isinstance(gates, dict) or gates.get("schema") != GATES_SCHEMA:
        raise Hold("gates.json must hold schema chalk-line/gates/1")
    for key in ("request", "authority", "instructs_desk", "min_confidence"):
        _number(gates.get(key), f"gates.{key}")
    if set(gates) != {"schema", "request", "authority", "instructs_desk", "min_confidence"}:
        raise Hold("gates.json holds an unexpected key")
    return gates


def boxes_from_candidate(text: str) -> tuple[float | None, str]:
    """Deterministic unit arithmetic. Returns (boxes, unit); unit is boxes, cases, or unknown."""
    head = text.split()[0].lower()
    value = WORD_NUMBERS.get(head)
    if value is None:
        try:
            value = float(head)
        except ValueError:
            return None, "unknown"
    tail = text.split()[1:]
    unit = re.sub(r"[^a-z]", "", tail[0].lower()) if tail else ""
    if unit in ("box", "boxes"):
        return float(value), "boxes"
    if unit in ("case", "cases"):
        return float(value) * 10, "cases"
    return None, "unknown"


def referred(row: dict, gates: dict) -> bool:
    """A message that instructs the desk, or a request without authority, goes to a person and cannot replace anything."""
    if row["instructs_desk"]["p"] >= gates["instructs_desk"]:
        return True
    return row["request"]["p"] >= gates["request"] and row["authority"]["p"] < gates["authority"]


def route(state: dict, answers: list[dict], gates: dict) -> tuple[list[dict], dict]:
    messages = {message["id"]: message for message in state["messages"]}
    replaced_by: dict[str, list[str]] = {}
    uncertain_link: dict[str, str] = {}
    for row in answers:
        target = row["replaces"]["choice"]
        if target == "NONE" or referred(row, gates):
            continue
        if row["replaces"]["confidence"] < gates["min_confidence"]:
            uncertain_link.setdefault(target, f"{row['id']} may replace it (declared confidence {row['replaces']['confidence']:.2f})")
            uncertain_link.setdefault(row["id"], f"may replace {target} (declared confidence {row['replaces']['confidence']:.2f})")
            continue
        replaced_by.setdefault(target, []).append(row["id"])
    rows = []
    for row in answers:
        identifier = row["id"]
        decision, reason, boxes, line = None, "", None, None
        if identifier in replaced_by:
            decision, reason = "SUPERSEDED", "replaced by " + ", ".join(replaced_by[identifier])
        elif row["instructs_desk"]["p"] >= gates["instructs_desk"]:
            decision, reason = "REFER", f"instruction to the desk (p={row['instructs_desk']['p']:.2f})"
        elif identifier in uncertain_link:
            decision, reason = "REVIEW", "uncertain supersession: " + uncertain_link[identifier]
        elif row["request"]["p"] < gates["request"]:
            decision, reason = "IGNORE", f"not a request (p={row['request']['p']:.2f})"
        else:
            chosen_line = row["line"]["choice"]
            chosen_quantity = row["quantity"]["choice"]
            if chosen_line == "MIXED":
                decision, reason = "REVIEW", "two sizes in one message"
            elif chosen_line in ("UNSTATED", "NONE") or chosen_quantity == "NONE":
                decision, reason = "CLARIFY", f"size {chosen_line}, quantity {chosen_quantity}"
            else:
                candidate = next(item for item in messages[identifier]["candidates"] if item["id"] == chosen_quantity)
                amount, unit = boxes_from_candidate(candidate["text"])
                if amount is None or amount != int(amount) or amount <= 0:
                    decision, reason = "CLARIFY", f"quantity unit unclear in {candidate['text']!r}"
                elif row["authority"]["p"] < gates["authority"]:
                    decision, reason = "REFER", f"no authority cited (p={row['authority']['p']:.2f})"
                else:
                    declared = {"line": row["line"]["confidence"], "quantity": row["quantity"]["confidence"], "request": noul_confidence(row["request"]["p"]),
                                "authority": noul_confidence(row["authority"]["p"]), "instructs_desk": noul_confidence(row["instructs_desk"]["p"])}
                    weakest = min(declared, key=declared.get)
                    if declared[weakest] < gates["min_confidence"]:
                        decision, reason = "REVIEW", f"declared confidence {declared[weakest]:.2f} on {weakest} is below the gate"
                    else:
                        decision, reason, boxes, line = "PICK", f"{int(amount)} boxes of {chosen_line} from {candidate['text']!r} ({unit})", int(amount), chosen_line
        rows.append({"id": identifier, "route": decision, "reason": reason, "line": line or "", "boxes": boxes if boxes is not None else ""})
    requirement = {item["line"]: {"boxes": 0, "from": []} for item in state["catalog"]}
    for item in rows:
        if item["route"] == "PICK":
            requirement[item["line"]]["boxes"] += item["boxes"]
            requirement[item["line"]]["from"].append(item["id"])
    summary = {"schema": "chalk-line/requirement/1", "gates": {key: gates[key] for key in ("request", "authority", "instructs_desk", "min_confidence")},
               "routes": {name: sum(1 for item in rows if item["route"] == name) for name in ROUTES}, "requirement": requirement,
               "total_boxes": sum(value["boxes"] for value in requirement.values())}
    return rows, summary


def write_routing_csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "route", "line", "boxes", "reason"], lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in writer.fieldnames})


def read_routing_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["boxes"] = int(row["boxes"]) if row["boxes"] else ""
    return rows
