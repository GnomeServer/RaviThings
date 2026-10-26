#!/usr/bin/env python3
"""Build a synthetic, passing Module 4 attempt (work folder plus receipts) in a temporary directory.

The launcher's own receipt integrity is tested in tests/test_runtime_launcher.py. This builder stands in
for those receipts so the verifier's decisions can be tested without a model, a network, or the OMP binary:
tests patch the receipt auditor. Answers come from the staff key with fixed probabilities and confidences.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]
REPO = MODULE.parents[1]
sys.path.insert(0, str(MODULE / "scripts"))
import chalk  # noqa: E402

KEY = json.loads((MODULE / "tests" / "answer_key.json").read_text(encoding="utf-8"))
T0 = datetime(2026, 10, 8, 9, 0, 0, tzinfo=timezone.utc)
OWN_QUESTION = {"key": "names_a_place", "type": "yes_no", "answer": "p",
                "instructions": "Does the message name a ward, a theatre, or a pharmacy as the place the gloves are for? Answer with the probability that the answer is yes."}


def stamp(minutes: int) -> str:
    return (T0 + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def key_answers(state: dict, yes: float = 0.95, no: float = 0.05, confidence: float = 0.9, own: str | None = OWN_QUESTION["key"]) -> list[dict]:
    """The staff key rendered as typed answers, plus the learner's own yes-or-no question when given."""
    rows = []
    for message in state["messages"]:
        item = KEY["messages"][message["id"]]
        side = lambda value: yes if value == "yes" else no  # noqa: E731
        row = {"id": message["id"], "request": {"p": side(item["request"])}, "line": {"choice": item["line"], "confidence": confidence},
               "quantity": {"choice": item["quantity"], "confidence": confidence}, "urgency": {"score": item["urgency"], "confidence": confidence},
               "authority": {"p": side(item["authority"])}, "instructs_desk": {"p": side(item["instructs_desk"])},
               "replaces": {"choice": item["replaces"], "confidence": confidence}}
        if own:
            row[own] = {"p": yes if any(word in message["text"].lower() for word in ("ward", "theatre", "pharmacy")) else no}
        rows.append(row)
    return rows


def with_own_question(questions: dict) -> dict:
    return {**questions, "questions": [*questions["questions"], OWN_QUESTION]}


class Bundle:
    """A passing attempt. Tests change one thing, then call run()."""

    def __init__(self, base: Path):
        self.base = base
        self.work = base / "work"
        self.evidence = base / "evidence"
        self.audit_errors: dict[str, list[str]] = {}
        self.build()

    def write(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, (dict, list)):
            data = chalk.canonical(data)
        elif isinstance(data, str):
            data = data.encode("utf-8")
        path.write_bytes(data)

    def receipt(self, name: str, answers: list[dict], started_minutes: int, reads=("out/state.json", "shared/controls/questions.json"), profile="read") -> None:
        folder = self.evidence / name
        contract = self.work / "shared" / "controls" / "CONTRACT.md"
        policy = {"work_root": str(self.work), "profile": profile, "tools": ["course_read"] if profile == "read" else ["course_read", "course_write"],
                  "write_files": [], "write_root": None if profile == "read" else "artifacts",
                  "instruction": {"path": str(contract), "sha256": sha(contract.read_bytes())},
                  "prompt_sha256": sha((self.work / "shared" / "prompts" / "DECIDE.md").read_bytes())}
        self.write(folder / "policy.json", policy)
        inputs = {relative: sha((self.work / relative).read_bytes()) for relative in ("out/labels.json", "out/state.json", "shared/controls/questions.json", "shared/controls/CONTRACT.md", "shared/prompts/DECIDE.md")}
        self.write(folder / "result.json", {"started_at": stamp(started_minutes), "status": "PASS", "input_sha256": inputs})
        guard = [{"type": "executed", "tool": "course_read", "resolved_path": str(self.work / relative)} for relative in reads]
        self.write(folder / "guard.jsonl", "".join(json.dumps(row) + "\n" for row in guard))
        self.write(folder / "response.md", json.dumps({"schema": chalk.ANSWER_SCHEMA, "answers": answers}))

    def build(self) -> None:
        work, evidence = self.work, self.evidence
        shutil.copytree(MODULE / "shared", work / "shared", ignore=shutil.ignore_patterns("__pycache__", "figures", "verify"))
        shutil.copytree(MODULE / "scripts", work / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        self.write(work / "shared" / "controls" / "questions.json", with_own_question(chalk.load_json(MODULE / "shared" / "controls" / "questions.json")))
        self.state = chalk.build_state(work / "shared" / "case")
        self.write(work / "out" / "state.json", self.state)
        labels = {"schema": chalk.LABEL_SCHEMA, "labels": [{"id": identifier, **{key: KEY["messages"][identifier][key] for key in chalk.LABEL_KEYS}} for identifier in chalk.SAMPLE_IDS]}
        self.write(work / "out" / "labels.json", labels)
        raw = (work / "out" / "labels.json").read_bytes()
        self.write(evidence / "labels.sha256", {"schema": "chalk-line/labels-frozen/1", "sha256": sha(raw), "frozen_at_utc": stamp(10), "sample": list(chalk.SAMPLE_IDS)})
        self.answers = key_answers(self.state)
        self.receipt("decide-1", self.answers, 20)
        self.write(work / "out" / "answers-1.json", {"schema": chalk.ANSWER_SCHEMA, "receipt": "decide-1", "answers": self.answers})
        labels_checked = chalk.check_labels(labels, self.state)
        agreement = chalk.compare(labels_checked, self.answers, OWN_QUESTION["key"])
        agreement["answers"] = "answers-1.json"
        self.write(work / "out" / "agreement-1.json", agreement)
        self.route(1)
        self.write_handoff()

    def route(self, attempt: int) -> None:
        gates = chalk.load_gates(self.work / "shared" / "controls" / "gates.json")
        rows, summary = chalk.route(self.state, self.answers, gates)
        summary["answers"] = "answers-1.json"
        chalk.write_routing_csv(self.work / "out" / f"routing-{attempt}.csv", rows)
        self.write(self.work / "out" / f"requirement-{attempt}.json", summary)
        self.rows = rows

    def write_handoff(self, decision: str = "READY FOR SIGNATURE", omit: str | None = None) -> None:
        queue = [row["id"] for row in self.rows if row["route"] in ("REFER", "REVIEW", "CLARIFY") and row["id"] != omit]
        sections = {
            "Requirement line": "GL-65 12 boxes, GL-70 12 boxes, GL-75 28 boxes, GL-80 6 boxes, from the picked messages with the gates on disk; the delegated requisitions wait on the lead.",
            "Review queue decisions": "\n".join(f"- {identifier}: read in full; the desk lead decides." for identifier in queue),
            "Agreement and gates": "Four questions agreed on all ten sample messages; min_confidence stays at 0.7 because no wrong answer was observed. request isolates whether anything is asked for; line isolates the size; quantity isolates the number; authority isolates who approved.",
            "Limits": "Declared confidence is the model's claim about itself; ten messages cannot establish a rate.",
            "Decision": decision,
            "Next owner": "The desk lead signs the requirement line and reads the REFER queue first.",
        }
        text = "# Chalk Line handoff\n\n" + "\n\n".join(f"## {heading}\n\n{body}" for heading, body in sections.items()) + "\n"
        self.write(self.evidence / "handoff.md", text)

    def run(self) -> tuple[int, str]:
        """Return (hold count, printed report) from the real verifier with the receipt auditor patched."""
        spec = importlib.util.spec_from_file_location("verify_decisions_under_test", MODULE / "shared" / "verify" / "verify_decisions.py")
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(REPO))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path.remove(str(REPO))
        module.audit_evidence = lambda folder: self.audit_errors.get(Path(folder).name, [])
        buffer = StringIO()
        with redirect_stdout(buffer):
            holds = module.verify(self.work, self.evidence)
        return holds, buffer.getvalue()
