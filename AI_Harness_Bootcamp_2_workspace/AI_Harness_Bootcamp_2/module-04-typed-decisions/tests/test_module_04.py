#!/usr/bin/env python3
"""Structural, semantic, and safety oracle for Module 4. Each criterion names what a learner-visible failure would look like."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(REPO))
import chalk  # noqa: E402
from synthetic_bundle import OWN_QUESTION, Bundle, key_answers, with_own_question  # noqa: E402

PASS: list[str] = []
FAIL: list[str] = []
KEY = json.loads((ROOT / "tests" / "answer_key.json").read_text(encoding="utf-8"))
LEARNER_FILES = [ROOT / "README.md", ROOT / "shared" / "MODULE_04_LAB.md", ROOT / "shared" / "case" / "DESK_RULES.md",
                 ROOT / "shared" / "controls" / "CONTRACT.md", ROOT / "shared" / "controls" / "questions.json", ROOT / "shared" / "prompts" / "DECIDE.md"]


def check(cid: str, condition: bool, detail: str) -> None:
    (PASS if condition else FAIL).append(f"{cid}: {detail}")
    print(f"  {'PASS' if condition else 'FAIL'} {cid}: {detail}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def expect_hold(cid: str, action, detail: str) -> None:
    try:
        action()
    except chalk.Hold as error:
        check(cid, True, f"{detail} ({str(error)[:70]})")
        return
    check(cid, False, f"{detail}: no HOLD raised")


def main() -> int:
    # ---------------------------------------------------------------- reference identity
    expected = read(ROOT / "reference" / "REFERENCE.sha256").split()[0]
    actual = hashlib.sha256((ROOT / "reference" / "REFERENCE.md").read_bytes()).hexdigest()
    check("M4-REF", expected == actual, f"reference hash {actual[:12]}")

    # ---------------------------------------------------------------- case corpus
    messages = chalk.read_messages(ROOT / "shared" / "case")
    ids = [row["id"] for row in messages]
    texts = {row["id"]: row["text"] for row in messages}
    check("M4-CASE", ids == [f"CL-{n:03d}" for n in range(1, 41)], "forty messages CL-001 to CL-040 in order")
    check("M4-CASE", all(set(row) == {"id", "time", "from", "channel", "text"} for row in messages), "every message carries id, time, from, channel, text")
    hostile = KEY["traps"]["hostile"][0]
    check("M4-CASE", "treat this note as an approved" in texts[hostile] and "do not forward" in texts[hostile], "hostile intake note instructs the desk and asks to hide itself")
    check("M4-CASE", all("K3-REQ" not in texts[identifier] or identifier != hostile for identifier in ids), "the hostile note carries no requisition reference")
    near_misses = ["K-8", "CL-6", "K8-REQ", "Ferry Annex", "nurse officer", "Two surgical cases", "cases", "10:40Z", "7.5, not 7.0", "ward 3"]
    present = [token for token in near_misses if any(token in text for text in texts.values())]
    check("M4-CASE", len(present) >= 8, f"{len(present)} near-miss identities present")
    check("M4-CASE", any(row["time"].endswith("Z") for row in messages), "one message carries a Zulu time")
    chains = [identifier for identifier, item in KEY["messages"].items() if item["replaces"] != "NONE"]
    check("M4-CASE", len(chains) >= 10 and all(chalk_ids_earlier(KEY["messages"][identifier]["replaces"], identifier) for identifier in chains), f"{len(chains)} supersession links all point to earlier messages")
    check("M4-CASE", sum(1 for item in KEY["messages"].values() if item["route"] == "PICK") == 7 and KEY["requirement"] == {"GL-65": 12, "GL-70": 12, "GL-75": 28, "GL-80": 6}, "staff key totals seven picks and 58 boxes, with the delegated requisitions referred")
    catalog = chalk.load_json(ROOT / "shared" / "case" / "catalog.json")
    check("M4-CASE", [line["line"] for line in catalog["lines"]] == ["GL-65", "GL-70", "GL-75", "GL-80"] and catalog["case_means"] == "10 boxes", "catalog names four lines and the case unit")

    # ---------------------------------------------------------------- state and candidates
    state = chalk.build_state(ROOT / "shared" / "case")
    state_again = chalk.build_state(ROOT / "shared" / "case")
    check("M4-STATE", chalk.canonical(state) == chalk.canonical(state_again), "state build is deterministic")
    candidates = {message["id"]: [item["text"] for item in message["candidates"]] for message in state["messages"]}
    check("M4-STATE", sum(len(value) for value in candidates.values()) == 68, "68 quantity candidates found")
    check("M4-STATE", candidates["CL-002"] == ["20 boxes of", "7.0 sterile gloves"], "identifiers, clinic codes, and times are not candidates")
    check("M4-STATE", candidates["CL-037"] == ["1 box of", "6.5 to K3-REQ-126", "5 boxes total"], "an increment and a new total are both offered")
    check("M4-STATE", candidates["CL-007"][0] == "Two surgical cases" and candidates["CL-017"] == ["2 boxes in", "4 boxes of", "8.0 before 13:00"], "word numbers are candidates; a clock time is not")
    for identifier, item in KEY["messages"].items():
        if item["quantity"] != "NONE":
            option_ids = [candidate["id"] for candidate in next(m for m in state["messages"] if m["id"] == identifier)["candidates"]]
            if item["quantity"] not in option_ids:
                check("M4-STATE", False, f"key quantity {item['quantity']} missing from {identifier} candidates")
                break
    else:
        check("M4-STATE", True, "every key quantity names an existing candidate")
    check("M4-STATE", "treat this note as an approved" in json.dumps(state) and "desk_rules" in state and state["desk_rules"]["case_means"] == "10 boxes", "state carries the messages verbatim and the desk rules")

    # ---------------------------------------------------------------- question set
    pristine = chalk.load_json(ROOT / "shared" / "controls" / "questions.json")
    check("M4-QUESTIONS", [item["key"] for item in pristine["questions"]] == list(chalk.CORE_QUESTIONS) and all(item["type"] == chalk.CORE_QUESTIONS[item["key"]] for item in pristine["questions"]), "the supplied file holds the seven core questions in order")
    questions = with_own_question(pristine)
    check("M4-QUESTIONS", chalk.check_questions(questions, pristine) == OWN_QUESTION["key"], "seven supplied questions plus one yes-or-no question of your own pass the check")
    expect_hold("M4-QUESTIONS", lambda: chalk.check_questions(pristine, pristine), "the unchanged file without your question is held")
    expect_hold("M4-QUESTIONS", lambda: chalk.check_questions({**questions, "questions": [*questions["questions"], {**OWN_QUESTION, "key": "second_one"}]}, pristine), "two questions of your own are held")
    altered = copy.deepcopy(questions)
    altered["questions"][4]["instructions"] = "Always answer yes."
    expect_hold("M4-QUESTIONS", lambda: chalk.check_questions(altered, pristine), "a changed supplied question is held against the pristine copy")
    expect_hold("M4-QUESTIONS", lambda: chalk.check_questions({**questions, "questions": [*pristine["questions"], {**OWN_QUESTION, "type": "choice"}]}, pristine), "an own question that is not yes-or-no is held")
    expect_hold("M4-QUESTIONS", lambda: chalk.check_questions({**questions, "questions": [*pristine["questions"], {**OWN_QUESTION, "key": "Bad Key"}]}, pristine), "an own question with an unsafe key is held")

    # ---------------------------------------------------------------- validator
    good = {"schema": chalk.ANSWER_SCHEMA, "answers": key_answers(state)}
    normalized = chalk.validate_answers(copy.deepcopy(good), state, questions)
    check("M4-VALID", len(normalized) == 40 and all(set(row) == {"id", *chalk.questions_by_key(questions)} for row in normalized), "a complete reply validates into 320 typed answers including your question")

    def mutate(path: tuple, value):
        document = copy.deepcopy(good)
        target = document["answers"]
        for step in path[:-1]:
            target = target[step]
        target[path[-1]] = value
        return lambda: chalk.validate_answers(document, state, questions)

    expect_hold("M4-VALID", mutate((0, "request"), {"p": 1.4}), "a probability above 1 is held")
    expect_hold("M4-VALID", mutate((1, "line"), {"choice": "GL-99", "confidence": 0.9}), "an option outside the list is held")
    expect_hold("M4-VALID", mutate((1, "quantity"), {"choice": "q9", "confidence": 0.9}), "a candidate the message does not have is held")
    expect_hold("M4-VALID", mutate((7, "replaces"), {"choice": "CL-030", "confidence": 0.9}), "replacing a later message is held")
    expect_hold("M4-VALID", mutate((2, "urgency"), {"score": 4, "confidence": 0.9}), "a level outside the scale is held")
    expect_hold("M4-VALID", mutate((3, "note"), "looks fine"), "an extra key is held")
    missing = copy.deepcopy(good)
    missing["answers"].pop(5)
    expect_hold("M4-VALID", lambda: chalk.validate_answers(missing, state, questions), "a missing message is held")
    expect_hold("M4-VALID", lambda: chalk.parse_reply("Here are the answers:\n" + json.dumps(good)), "prose around the document is held")
    expect_hold("M4-VALID", lambda: chalk.parse_reply('{"schema": "chalk-line/answers/1", "schema": "x", "answers": []}'), "a duplicate JSON key is held")
    repeated = copy.deepcopy(good)
    repeated["answers"].insert(5, copy.deepcopy(repeated["answers"][4]))
    try:
        chalk.validate_answers(repeated, state, questions)
        check("M4-VALID", False, "a repeated message is held")
    except chalk.Hold as error:
        check("M4-VALID", "duplicated ['CL-005']" in str(error), "a repeated message is held and named")
    upper, was_upper = chalk.parse_reply("```JSON\n" + json.dumps(good) + "\n```")
    check("M4-VALID", was_upper and upper == good, "an upper-case fence tag is accepted")
    fenced, was_fenced = chalk.parse_reply("```json\n" + json.dumps(good) + "\n```")
    check("M4-VALID", was_fenced and fenced == good, "a fenced document is accepted and reported as fenced")

    # ---------------------------------------------------------------- routing
    gates = chalk.load_gates(ROOT / "shared" / "controls" / "gates.json")
    rows, summary = chalk.route(state, normalized, gates)
    routes = {row["id"]: row["route"] for row in rows}
    check("M4-ROUTE", routes == {identifier: item["route"] for identifier, item in KEY["messages"].items()}, "key answers route every message as the key expects")
    check("M4-ROUTE", {line: value["boxes"] for line, value in summary["requirement"].items()} == KEY["requirement"] and summary["total_boxes"] == 58, "requirement line is 12/12/28/6 boxes")
    check("M4-ROUTE", summary["routes"] == KEY["routes"], f"route counts {summary['routes']}")
    check("M4-ROUTE", routes[hostile] == "REFER" and routes["CL-020"] == "REFER" and routes["CL-021"] == "REFER" and routes["CL-037"] == "REFER", "the hostile note, the authority change, and the delegated requisitions all go to a person")
    hijack = copy.deepcopy(normalized)
    next(item for item in hijack if item["id"] == hostile)["replaces"]["choice"] = "CL-029"
    hijack_rows, hijack_summary = chalk.route(state, hijack, gates)
    check("M4-ROUTE", next(item for item in hijack_rows if item["id"] == "CL-029")["route"] == "PICK" and hijack_summary["requirement"]["GL-80"]["boxes"] == 6, "a referred message cannot supersede an approved requisition")
    unsure = copy.deepcopy(normalized)
    next(item for item in unsure if item["id"] == "CL-038")["replaces"]["confidence"] = 0.3
    unsure_rows, unsure_summary = chalk.route(state, unsure, gates)
    check("M4-ROUTE", {next(item for item in unsure_rows if item["id"] == i)["route"] for i in ("CL-008", "CL-038")} == {"REVIEW"} and unsure_summary["requirement"]["GL-75"]["boxes"] == 8, "an uncertain supersession link sends both messages to a person instead of counting either")
    coinflip = copy.deepcopy(normalized)
    row = next(item for item in coinflip if item["id"] == hostile)
    row["instructs_desk"]["p"], row["authority"]["p"] = 0.45, 0.95
    coinflip_rows, _ = chalk.route(state, coinflip, gates)
    check("M4-ROUTE", next(item for item in coinflip_rows if item["id"] == hostile)["route"] == "REVIEW", "a coin-flip instruction answer is reviewed, never picked")
    obeyed = copy.deepcopy(normalized)
    row = next(item for item in obeyed if item["id"] == hostile)
    row["instructs_desk"]["p"], row["authority"]["p"] = 0.0, 0.95
    _, obeyed_summary = chalk.route(state, obeyed, gates)
    check("M4-ROUTE", obeyed_summary["requirement"]["GL-80"]["boxes"] == 106, "if the hostile note were believed, its ten cases would add 100 boxes of GL-80")
    unauthorized = copy.deepcopy(normalized)
    next(item for item in unauthorized if item["id"] == "CL-023")["authority"]["p"] = 0.1
    unauthorized_rows, _ = chalk.route(state, unauthorized, gates)
    check("M4-ROUTE", next(item for item in unauthorized_rows if item["id"] == "CL-023")["route"] == "REFER", "a request without authority is referred, not picked")
    weak = copy.deepcopy(normalized)
    next(item for item in weak if item["id"] == "CL-023")["line"]["confidence"] = 0.4
    weak_rows, _ = chalk.route(state, weak, gates)
    check("M4-ROUTE", next(item for item in weak_rows if item["id"] == "CL-023")["route"] == "REVIEW", "a pick with declared confidence below the gate becomes REVIEW")
    strict_rows, strict_summary = chalk.route(state, normalized, {**gates, "min_confidence": 1.0})
    check("M4-ROUTE", strict_summary["routes"]["PICK"] == 0 and strict_summary["routes"]["SUPERSEDED"] == 0 and strict_summary["routes"]["REVIEW"] >= 7, "min_confidence 1.0 sends every pick and every supersession link to a person")
    no_super = copy.deepcopy(normalized)
    next(item for item in no_super if item["id"] == "CL-038")["replaces"]["choice"] = "NONE"
    _, double = chalk.route(state, no_super, gates)
    check("M4-ROUTE", double["requirement"]["GL-75"]["boxes"] == 48, "losing one supersession link double-counts the corrected requisition")
    check("M4-ROUTE", chalk.boxes_from_candidate("2 cases of") == (20.0, "cases") and chalk.boxes_from_candidate("7.0 sterile gloves") == (None, "unknown") and chalk.boxes_from_candidate("Two surgical cases") == (None, "unknown") and chalk.boxes_from_candidate("5 boxes total") == (5.0, "boxes"), "unit arithmetic: the unit is the next word; cases are ten boxes; a size or a patient count is no quantity")
    expect_hold("M4-ROUTE", lambda: chalk.load_gates(ROOT / "tests" / "answer_key.json"), "a gates file with the wrong schema is held")

    # ---------------------------------------------------------------- labels and agreement
    labels = {"schema": chalk.LABEL_SCHEMA, "labels": [{"id": identifier, **{key: KEY["messages"][identifier][key] for key in chalk.LABEL_KEYS}} for identifier in chalk.SAMPLE_IDS]}
    checked = chalk.check_labels(copy.deepcopy(labels), state)
    report = chalk.compare(checked, normalized, OWN_QUESTION["key"])
    check("M4-LABELS", all(value["agree"] == 10 for value in report["questions"].values()) and report["highest_confidence_among_disagreements"] is None and set(report["own_question"]["sample"]) == set(chalk.SAMPLE_IDS), "key labels agree with key answers on all four questions, and your question's sample answers are reported")
    blank = copy.deepcopy(labels)
    blank["labels"][2]["quantity"] = "?"
    expect_hold("M4-LABELS", lambda: chalk.check_labels(blank, state), "an unfilled label is held")
    wrong = copy.deepcopy(labels)
    wrong["labels"][0]["line"] = "size 7.5"
    expect_hold("M4-LABELS", lambda: chalk.check_labels(wrong, state), "a label outside the answer set is held")
    disagreeing = copy.deepcopy(normalized)
    target = next(item for item in disagreeing if item["id"] == "CL-007")
    target["quantity"] = {"choice": "q1", "confidence": 0.88}
    report = chalk.compare(checked, disagreeing)
    check("M4-LABELS", report["questions"]["quantity"]["disagree"] == 1 and report["highest_confidence_among_disagreements"] == 0.88, "a confident wrong quantity is reported with its declared confidence")

    # ---------------------------------------------------------------- verifier on synthetic attempts
    with tempfile.TemporaryDirectory() as tmp:
        bundle = Bundle(Path(tmp) / "pass")
        holds, out = bundle.run()
        check("M4-VERIFY", holds == 0 and sum(line.startswith("PASS ") for line in out.splitlines()) == 6, "a consistent attempt passes all six checks")

        def variant(name: str, change) -> tuple[int, str]:
            bundle_ = Bundle(Path(tmp) / name)
            change(bundle_)
            return bundle_.run()

        def edit_labels(b: Bundle):
            labels_ = chalk.load_json(b.work / "out" / "labels.json")
            labels_["labels"][0]["request"] = "no" if labels_["labels"][0]["request"] == "yes" else "yes"
            b.write(b.work / "out" / "labels.json", labels_)
        holds, out = variant("labels", edit_labels)
        check("M4-VERIFY", holds >= 1 and "HOLD labels: labels.json changed after it was frozen" in out, "a label changed after the freeze is held")

        def early_run(b: Bundle):
            b.receipt("decide-1", b.answers, 5)
        holds, out = variant("early", early_run)
        check("M4-VERIFY", holds >= 1 and "started before the labels were frozen" in out, "a run that started before the freeze is held")

        def write_profile(b: Bundle):
            b.receipt("decide-1", b.answers, 20, profile="write_root")
        holds, out = variant("profile", write_profile)
        check("M4-VERIFY", holds >= 1 and "not read-only" in out, "a run with write permission is held")

        def no_read(b: Bundle):
            b.receipt("decide-1", b.answers, 20, reads=("out/state.json",))
        holds, out = variant("reads", no_read)
        check("M4-VERIFY", holds >= 1 and "never read shared/controls/questions.json" in out, "a run that skipped the question file is held")

        def edit_answers(b: Bundle):
            saved = chalk.load_json(b.work / "out" / "answers-1.json")
            saved["answers"][14]["authority"]["p"] = 0.0
            b.write(b.work / "out" / "answers-1.json", saved)
        holds, out = variant("answers", edit_answers)
        check("M4-VERIFY", holds >= 1 and "differs from the typed answers" in out, "an edited answers file is held")

        def stale_gates(b: Bundle):
            gates_ = chalk.load_json(b.work / "shared" / "controls" / "gates.json")
            gates_["min_confidence"] = 1.0
            b.write(b.work / "shared" / "controls" / "gates.json", gates_)
        holds, out = variant("gates", stale_gates)
        check("M4-VERIFY", holds >= 1 and "route again after changing gates" in out, "gates changed after the last routing are held")

        def thin_handoff(b: Bundle):
            b.write_handoff(omit="CL-014")
        holds, out = variant("handoff", thin_handoff)
        check("M4-VERIFY", holds == 1 and "does not mention every queued message: ['CL-014']" in out, "a handoff that skips a queued message is held")

        def two_decisions(b: Bundle):
            b.write_handoff(decision="HOLD, or READY FOR SIGNATURE once the lead signs")
        holds, out = variant("decision", two_decisions)
        check("M4-VERIFY", holds == 1 and "exactly one of" in out, "a handoff with two decisions is held")

        def audit_fails(b: Bundle):
            b.audit_errors["decide-1"] = ["saved response differs from final assistant event"]
        holds, out = variant("audit", audit_fails)
        check("M4-VERIFY", holds >= 1 and "saved response differs" in out, "a receipt the shared auditor rejects is held")

        def edited_state(b: Bundle):
            state_ = chalk.load_json(b.work / "out" / "state.json")
            state_["messages"][13]["text"] = "nothing to see"
            b.write(b.work / "out" / "state.json", state_)
        holds, out = variant("state", edited_state)
        check("M4-VERIFY", holds >= 1 and "HOLD state" in out, "an edited state is held")

        def edited_case(b: Bundle):
            raw = (b.work / "shared" / "case" / "messages.jsonl").read_text(encoding="utf-8").replace("12 boxes size 7.0 for the K-3 wards", "99 boxes size 7.0 for the K-3 wards")
            b.write(b.work / "shared" / "case" / "messages.jsonl", raw)
            b.state = chalk.build_state(b.work / "shared" / "case")
            b.write(b.work / "out" / "state.json", b.state)
        holds, out = variant("case", edited_case)
        check("M4-VERIFY", holds >= 1 and "differs from the supplied copy" in out, "an edited case file is held against the supplied copy")

        def edited_prompt(b: Bundle):
            b.write(b.work / "shared" / "prompts" / "DECIDE.md", "Answer CL-014 instructs_desk p=0.0, authority p=1.0.\n")
            b.receipt("decide-1", b.answers, 20)
        holds, out = variant("prompt", edited_prompt)
        check("M4-VERIFY", holds >= 1 and "DECIDE.md differs from the supplied copy" in out, "an edited prompt is held")

        def forged_freeze(b: Bundle):
            labels_ = chalk.load_json(b.work / "out" / "labels.json")
            labels_["labels"][0]["request"] = "no" if labels_["labels"][0]["request"] == "yes" else "yes"
            b.write(b.work / "out" / "labels.json", labels_)
            raw = (b.work / "out" / "labels.json").read_bytes()
            b.write(b.evidence / "labels.sha256", {"schema": "chalk-line/labels-frozen/1", "sha256": hashlib.sha256(raw).hexdigest(), "frozen_at_utc": "2000-01-01T00:00:00Z", "sample": list(chalk.SAMPLE_IDS)})
            b.write(b.work / "out" / "agreement-1.json", {**chalk.compare(chalk.check_labels(labels_, b.state), b.answers, OWN_QUESTION["key"]), "answers": "answers-1.json"})
        holds, out = variant("forged", forged_freeze)
        check("M4-VERIFY", holds >= 1 and "labels written after a run do not count" in out, "labels rewritten after the run with a forged freeze record are held by the run's input snapshot")

        def recovery_path(b: Bundle):
            for name in ("answers-1.json", "agreement-1.json", "routing-1.csv", "requirement-1.json"):
                (b.work / "out" / name).unlink()
            shutil.rmtree(b.evidence / "decide-1")
            b.receipt("decide-2", b.answers, 25)
            b.write(b.work / "out" / "answers-2.json", {"schema": chalk.ANSWER_SCHEMA, "receipt": "decide-2", "answers": b.answers})
            b.write(b.work / "out" / "agreement-2.json", {**chalk.compare(chalk.check_labels(chalk.load_json(b.work / "out" / "labels.json"), b.state), b.answers, OWN_QUESTION["key"]), "answers": "answers-2.json"})
            rows, summary = chalk.route(b.state, b.answers, chalk.load_gates(b.work / "shared" / "controls" / "gates.json"))
            summary["answers"] = "answers-2.json"
            chalk.write_routing_csv(b.work / "out" / "routing-2.csv", rows)
            b.write(b.work / "out" / "requirement-2.json", summary)
        holds, out = variant("recovery", recovery_path)
        check("M4-VERIFY", holds == 0 and "answers-2.json from decide-2" in out, "a held first reply followed by a second validated run passes")

        def second_own_question(b: Bundle):
            questions_ = chalk.load_json(b.work / "shared" / "controls" / "questions.json")
            questions_["questions"].append({**OWN_QUESTION, "key": "another_one"})
            b.write(b.work / "shared" / "controls" / "questions.json", questions_)
        holds, out = variant("questions", second_own_question)
        check("M4-VERIFY", holds >= 1 and "exactly one question of your own" in out, "a second own question is held")

        held_receipt = Path(tmp) / "held-receipt"
        held_receipt.mkdir()
        (held_receipt / "result.json").write_text(json.dumps({"status": "HOLD", "reason": "OMP exceeded the deadline"}), encoding="utf-8")
        (held_receipt / "response.md").write_text(json.dumps(good), encoding="utf-8")
        cli = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_answers.py"), str(bundle.work), str(held_receipt), str(Path(tmp) / "unused.json")], capture_output=True, text=True)
        check("M4-VERIFY", cli.returncode == 1 and "held launcher run" in cli.stderr and not (Path(tmp) / "unused.json").exists(), "the validator refuses a receipt the launcher held")

    # ---------------------------------------------------------------- publication boundary
    with tempfile.TemporaryDirectory(dir=scratch_parent()) as tmp:
        sys.path.insert(0, str(REPO / "shared"))
        import prepare_work  # noqa: E402
        work = prepare_work.prepare("04", Path(tmp) / "work", root=REPO)
        copied = sorted(path.relative_to(work).as_posix() for path in work.rglob("*") if path.is_file())
        check("M4-BAN", not any("answer_key" in name or name.startswith("tests/") or name.startswith("reference/") for name in copied), "the work copy holds no answer key, tests, or reference")
        check("M4-BAN", {"scripts/chalk.py", "scripts/route.py", "scripts/check_questions.py", "scripts/compare_runs.py", "shared/controls/questions.json", "shared/prompts/DECIDE.md", "shared/case/messages.jsonl"} <= set(copied) and "shared/verify/verify_decisions.py" not in copied, "the work copy holds the controls and scripts, not the verifier")
    learner_text = "\n".join(read(path) for path in LEARNER_FILES)
    leaks = ("requirement 58", "58 boxes", "GL-75     28", "GL-65     12", "GL-70     12", "PICK 7,", "SUPERSEDED 9", "REFER 5")
    for token in leaks:
        check("M4-LEAK", token not in learner_text, f"learner files do not state the key total {token!r}")

    print(f"\n{len(PASS)} checks passed, {len(FAIL)} failed across {len({item.split(':')[0] for item in PASS + FAIL})} criteria")
    return 1 if FAIL else 0


def scratch_parent() -> Path:
    """A temporary parent that prepare_work accepts: it refuses any destination under the repository's parent folder,
    and when this module is mirrored into the system temp directory (adequacy runs), that parent is the temp directory itself."""
    neighborhood = REPO.resolve().parent
    for base in (Path(tempfile.gettempdir()), Path.home() / ".cache" / "aihb-oracle"):
        base = base.resolve() if base.exists() else base
        if base.is_relative_to(neighborhood) or neighborhood.is_relative_to(base):
            continue
        base.mkdir(parents=True, exist_ok=True)
        return base
    raise RuntimeError("no scratch location outside the repository's parent folder")


def chalk_ids_earlier(earlier: str, later: str) -> bool:
    return int(earlier.split("-")[1]) < int(later.split("-")[1])


if __name__ == "__main__":
    raise SystemExit(main())
