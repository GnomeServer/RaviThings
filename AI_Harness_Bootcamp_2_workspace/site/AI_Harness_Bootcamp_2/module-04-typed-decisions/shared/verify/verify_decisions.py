#!/usr/bin/env python3
"""Final check for a Chalk Line attempt: receipts, typed answers, frozen labels, gates, routing, and handoff must agree.

Usage: verify_decisions.py <workdir> <evidence-dir>
This is a public practice check. It confirms that the files were produced in the stated order and still agree with
each other; it does not judge whether the model's answers are right. Your labels and your reading do that.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2]
REFORMATION = MODULE.parents[1]
sys.path.insert(0, str(REFORMATION))
sys.path.insert(0, str(MODULE / "scripts"))
from shared.run_omp import audit_evidence, file_hash, overlap, read_jsonl  # noqa: E402

import chalk  # noqa: E402

HEADINGS = ("Requirement line", "Review queue decisions", "Agreement and gates", "Limits", "Decision", "Next owner")
READS = ("out/state.json", "shared/controls/questions.json")
PINNED = ("shared/case/messages.jsonl", "shared/case/catalog.json", "shared/case/DESK_RULES.md", "shared/controls/CONTRACT.md", "shared/prompts/DECIDE.md")


def iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check_receipt(work: Path, evidence: Path, receipt: Path, frozen_at: datetime, state: dict, questions: dict, labels_digest: str) -> list[dict]:
    errors = audit_evidence(receipt)
    if errors:
        raise chalk.Hold(f"{receipt.name}: " + "; ".join(errors))
    policy = chalk.load_json(receipt / "policy.json")
    result = chalk.load_json(receipt / "result.json")
    if policy["work_root"] != str(work):
        raise chalk.Hold(f"{receipt.name}: the receipt belongs to a different work folder")
    if policy["profile"] != "read" or policy["tools"] != ["course_read"] or policy["write_files"] or policy["write_root"]:
        raise chalk.Hold(f"{receipt.name}: the run was not read-only; a decision function writes nothing")
    contract = work / "shared" / "controls" / "CONTRACT.md"
    if not policy.get("instruction") or policy["instruction"]["path"] != str(contract) or policy["instruction"]["sha256"] != file_hash(contract):
        raise chalk.Hold(f"{receipt.name}: the contract was not the saved instruction, or it changed afterwards")
    if policy["prompt_sha256"] != file_hash(work / "shared" / "prompts" / "DECIDE.md"):
        raise chalk.Hold(f"{receipt.name}: the prompt is not the unchanged DECIDE.md")
    if iso(result["started_at"]) <= frozen_at:
        raise chalk.Hold(f"{receipt.name}: the run started before the labels were frozen")
    inputs = result.get("input_sha256", {})
    if inputs.get("out/labels.json") != labels_digest:
        raise chalk.Hold(f"{receipt.name}: the labels the run saw on disk differ from the labels now frozen; labels written after a run do not count")
    if inputs.get("out/state.json") != chalk.sha256_bytes(chalk.canonical(state)):
        raise chalk.Hold(f"{receipt.name}: the state the run saw on disk differs from the state built from the supplied case")
    for relative in ("shared/controls/questions.json", "shared/controls/CONTRACT.md", "shared/prompts/DECIDE.md"):
        if inputs.get(relative) != file_hash(work / relative):
            raise chalk.Hold(f"{receipt.name}: {relative} changed after the run")
    guard = read_jsonl(receipt / "guard.jsonl")
    read_paths = {row.get("resolved_path") for row in guard if row.get("type") == "executed" and row.get("tool") == "course_read"}
    for relative in READS:
        if str(work / relative) not in read_paths:
            raise chalk.Hold(f"{receipt.name}: the model never read {relative} through course_read")
    document, _ = chalk.parse_reply((receipt / "response.md").read_text(encoding="utf-8"))
    return chalk.validate_answers(document, state, questions)


def verify(work: Path, evidence: Path) -> int:
    holds = 0

    def report(name: str, action):
        nonlocal holds
        try:
            detail = action()
            print(f"PASS {name}: {detail}")
        except KeyError as error:
            holds += 1
            if str(error).strip("'") in ("state", "questions", "own", "labels", "labels_digest", "frozen_at", "answers", "agreements", "rows", "final"):
                print(f"HOLD {name}: not checked because an earlier check held")
            else:
                print(f"HOLD {name}: missing field {error}")
        except (chalk.Hold, OSError, TypeError, ValueError, StopIteration) as error:
            holds += 1
            print(f"HOLD {name}: {error}")
    if not work.is_dir() or not evidence.is_dir() or overlap(work, evidence):
        print("HOLD setup: work and evidence must be separate existing folders")
        return 1
    shared = {}

    def state_unchanged():
        for relative in PINNED:
            if (work / relative).read_bytes() != (MODULE / relative).read_bytes():
                raise chalk.Hold(f"{relative} differs from the supplied copy; the case, contract, and prompt are not yours to edit")
        questions = chalk.load_json(work / "shared" / "controls" / "questions.json")
        own = chalk.check_questions(questions, chalk.load_json(MODULE / "shared" / "controls" / "questions.json"))
        expected = chalk.canonical(chalk.build_state(work / "shared" / "case"))
        if (work / "out" / "state.json").read_bytes() != expected:
            raise chalk.Hold("out/state.json differs from the state built from the supplied case")
        shared["state"] = chalk.strict_json(expected.decode("utf-8"))
        shared["questions"] = questions
        shared["own"] = own
        return f"{len(shared['state']['messages'])} messages as built from the case; seven supplied questions intact plus your question {own}"
    report("state", state_unchanged)

    def labels_frozen():
        raw = (work / "out" / "labels.json").read_bytes()
        shared["labels"] = chalk.check_labels(chalk.strict_json(raw.decode("utf-8")), shared["state"])
        record = chalk.load_json(evidence / "labels.sha256")
        if record.get("sha256") != chalk.sha256_bytes(raw):
            raise chalk.Hold("labels.json changed after it was frozen")
        shared["frozen_at"] = iso(record["frozen_at_utc"])
        shared["labels_digest"] = record["sha256"]
        return f"{len(chalk.SAMPLE_IDS)} sample labels frozen at {record['frozen_at_utc']}"
    report("labels", labels_frozen)

    def answers_from_receipts():
        saved = sorted((work / "out").glob("answers-*.json"))
        if not saved:
            raise chalk.Hold("no out/answers-*.json; validate a receipt first")
        verified = {}
        for path in saved:
            document = chalk.load_json(path)
            receipt = evidence / str(document.get("receipt", ""))
            if not receipt.is_dir() or receipt.parent != evidence:
                raise chalk.Hold(f"{path.name} names a receipt that is not under the evidence folder")
            answers = check_receipt(work, evidence, receipt, shared["frozen_at"], shared["state"], shared["questions"], shared["labels_digest"])
            if document["answers"] != answers:
                raise chalk.Hold(f"{path.name} differs from the typed answers in {receipt.name}/response.md")
            verified[path.name] = (answers, receipt.name)
        shared["answers"] = {name: value[0] for name, value in verified.items()}
        return ", ".join(f"{name} from {verified[name][1]}" for name in sorted(verified))
    report("answers", answers_from_receipts)

    def agreement():
        files = sorted((work / "out").glob("agreement-*.json"))
        if not files:
            raise chalk.Hold("no out/agreement-*.json; compare the labels with a validated answers file first")
        shared["agreements"] = {}
        for path in files:
            saved = chalk.load_json(path)
            source = saved.get("answers") if isinstance(saved, dict) else None
            if source not in shared["answers"]:
                raise chalk.Hold(f"{path.name} names an answers file that was not verified: {source}")
            expected = chalk.compare(shared["labels"], shared["answers"][source], shared["own"])
            expected["answers"] = source
            if saved != expected:
                raise chalk.Hold(f"{path.name} differs from the comparison of the frozen labels with {source}")
            shared["agreements"][source] = len(expected["disagreements"])
        return "; ".join(f"{source}: {count} disagreements on the sample" for source, count in shared["agreements"].items())
    report("agreement", agreement)

    def routing():
        gates = chalk.load_gates(work / "shared" / "controls" / "gates.json")
        attempts = sorted(int(path.stem.split("-")[1]) for path in (work / "out").glob("requirement-*.json"))
        if not attempts:
            raise chalk.Hold("no out/requirement-*.json; route the answers first")
        final = attempts[-1]
        summary = chalk.load_json(work / "out" / f"requirement-{final}.json")
        answers = shared["answers"].get(summary.get("answers"))
        if answers is None:
            raise chalk.Hold(f"requirement-{final}.json names an answers file that was not verified")
        if summary.get("answers") not in shared["agreements"]:
            raise chalk.Hold(f"requirement-{final}.json routes {summary.get('answers')}, which was never compared with the frozen labels")
        rows, expected = chalk.route(shared["state"], answers, gates)
        expected["answers"] = summary["answers"]
        if summary != expected:
            raise chalk.Hold(f"requirement-{final}.json differs from a fresh routing with the current gates; route again after changing gates")
        if chalk.read_routing_csv(work / "out" / f"routing-{final}.csv") != rows:
            raise chalk.Hold(f"routing-{final}.csv differs from a fresh routing")
        shared["rows"] = rows
        shared["final"] = final
        return f"attempt {final}: {summary['total_boxes']} boxes across {len(rows)} routed messages"
    report("routing", routing)

    def handoff():
        text = (evidence / "handoff.md").read_text(encoding="utf-8")
        for heading in HEADINGS:
            if not re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.M):
                raise chalk.Hold(f"handoff.md lacks the heading '{heading}'")
        decision = re.split(r"^##\s+Decision\s*$", text, flags=re.M)[1].split("\n## ")[0]
        found = [token for token in ("READY FOR SIGNATURE", "HOLD") if token in decision]
        if len(found) != 1:
            raise chalk.Hold("the Decision section must state exactly one of READY FOR SIGNATURE or HOLD")
        queue = [row["id"] for row in shared["rows"] if row["route"] in ("REFER", "REVIEW", "CLARIFY")]
        missing = [identifier for identifier in queue if identifier not in text]
        if missing:
            raise chalk.Hold(f"handoff.md does not mention every queued message: {missing}")
        return f"decision {found[0]}; {len(queue)} queued messages addressed"
    report("handoff", handoff)
    return holds


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: verify_decisions.py <workdir> <evidence-dir>", file=sys.stderr)
        return 2
    work, evidence = (Path(value).expanduser().resolve() for value in argv[1:])
    holds = verify(work, evidence)
    if holds:
        print(f"HOLD: {holds} checks held; preserve the attempt and repair the named cause")
        return 1
    print("PASS: receipts, typed answers, frozen labels, gates, routing, and handoff agree; the answers' meaning is yours to judge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
