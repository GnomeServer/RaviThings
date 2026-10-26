#!/usr/bin/env python3
"""Have the learner's own model write a handoff, then test it in a new session.

There is no practice fixture. A missing key or a failed child is a hold.
The scrutiny session receives the handoff and the source files only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

STARTER = "# Handoff\n\n"
HANDOFF_NAME = "handoff.md"
SCRUTINY_NAME = "handoff-scrutiny.md"
DECISION_NAME = "handoff-scrutiny-decision.md"
WRITER_SESSION = "handoff-session.json"
SCRUTINY_SESSION = "handoff-scrutiny-session.json"
KEY_HOLD = "HOLD: OPENROUTER_API_KEY unavailable; enter and export the key in this terminal"
EXCLUDED_NAMES = {
    "thread-ledger.csv",
    "changed-thread-ledger.csv",
    "corrected-brief.md",
    "changed-brief.md",
    "baseline-verdict.md",
    "changed-verdict.md",
    "challenge-matrix.md",
    "source-register.csv",
    "producer-rebuttal.md",
    "review.html",
    "handoff-session.json",
    "handoff-scrutiny-session.json",
    "handoff-scrutiny-decision.md",
    "desk.md",
}
HANDOFF_LABELS = (
    "Question reviewed:",
    "Exact entities and as-of time:",
    "Current verdict:",
    "Eight-step thread location:",
    "Material traced claim:",
    "Sources of record:",
    "Rejected sources and reasons:",
    "Baseline-to-change delta:",
    "Current unresolved condition:",
    "Standing rule:",
    "What the next person should inspect first:",
)
CONCLUSIONS = ("STOOD", "DID NOT STAND", "HOLD")
VERDICTS = ("ACCEPT", "REVISE", "REJECT", "HOLD")


def module_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "shared/case/fixtures/HANDOFF_PROMPT.txt").is_file():
            return parent
    raise FileNotFoundError("Cold Lantern handoff prompts are missing from the checkout")


def shared_launcher() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "shared/run_omp.py"
        guard = parent / "shared/course_guard.mjs"
        if candidate.is_file() and guard.is_file():
            return candidate
    raise FileNotFoundError("shared OMP launcher is missing from the checkout")


def pinned_selector() -> str:
    launcher = shared_launcher()
    shared = str(launcher.parent)
    if shared not in sys.path:
        sys.path.insert(0, shared)
    from run_omp import MODEL, PROVIDER

    return f"{PROVIDER}/{MODEL}"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_starter(path: Path) -> bool:
    return path.is_file() and not path.is_symlink() and path.read_text(encoding="utf-8") == STARTER


def fresh_dir(work: Path, kind: str) -> Path:
    return work.parent / f"{work.name}-{kind}" / uuid.uuid4().hex


def hold(message: str, code: int = 1) -> int:
    print(f"HOLD: {message}", file=sys.stderr)
    return code


def precheck(work: Path) -> int | None:
    if not work.is_dir():
        return hold(f"work folder does not exist: {work}", 2)
    if not os.environ.get("OPENROUTER_API_KEY"):
        print(KEY_HOLD, file=sys.stderr)
        return 2
    if not shutil.which("omp"):
        return hold("omp is not on PATH; install the verified OMP binary", 2)
    try:
        shared_launcher()
        module_root()
    except FileNotFoundError as error:
        return hold(str(error), 2)
    return None


def required_inputs(work: Path) -> int | None:
    missing = [name for name in ("changed-verdict.md", "REVEALED_CHANGE.md", "inbox") if not (work / name).exists()]
    if missing:
        return hold("changed verdict, revealed change, or inbox is missing: " + ", ".join(missing), 2)
    inbox = work / "inbox"
    if not inbox.is_dir() or inbox.is_symlink():
        return hold("inbox is not a real directory", 2)
    return None


def confirm_output(target: Path, evidence: Path, name: str) -> list[str]:
    errors: list[str] = []
    if not target.is_file() or target.is_symlink():
        return [f"{name} is absent"]
    result_path = evidence / "result.json"
    guard_path = evidence / "guard.jsonl"
    if not result_path.is_file() or not guard_path.is_file():
        return ["live receipts are incomplete"]
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
        selector = pinned_selector()
    except (OSError, json.JSONDecodeError, FileNotFoundError, ImportError) as error:
        return [f"cannot read live receipt: {error}"]
    if result.get("status") != "PASS" or result.get("exit_code") != 0:
        errors.append("child status is not a completed live run")
    provider, model = selector.split("/", 1)
    if result.get("provider") != provider or result.get("model") != model:
        errors.append("live identity is not the pinned OpenRouter model")
    file_digest = digest(target)
    recorded = (result.get("output_sha256") or {}).get(name)
    if recorded != file_digest:
        errors.append(f"disk {name} does not match the receipt")
    matched = False
    try:
        lines = guard_path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        return errors + [f"guard.jsonl is not readable: {error}"]
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            return errors + ["guard.jsonl is not readable"]
        if row.get("type") != "executed" or row.get("tool") != "course_write":
            continue
        if row.get("output_sha256") != file_digest:
            continue
        resolved = row.get("resolved_path")
        if isinstance(resolved, str) and Path(resolved).resolve() == target.resolve():
            matched = True
    if not matched:
        errors.append(f"no course_write receipt for {name}")
    return errors


def launch(work: Path, prompt: Path, evidence: Path, allow_write: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            str(shared_launcher()),
            "--workdir",
            str(work),
            "--prompt",
            str(prompt),
            "--evidence",
            str(evidence),
            "--allow-write",
            allow_write,
        ]
    )


def write_session(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_handoff(work: Path) -> int:
    if not work.is_dir():
        return hold(f"work folder does not exist: {work}", 2)
    target = work / HANDOFF_NAME
    if target.is_symlink():
        return hold(f"{HANDOFF_NAME} is a link; keep it", 1)
    if target.exists() and not is_starter(target):
        return hold(f"{HANDOFF_NAME} already has work in it; keep it", 1)
    blocked = precheck(work)
    if blocked:
        return blocked
    blocked = required_inputs(work)
    if blocked:
        return blocked
    starter = target.read_bytes() if target.exists() else None
    if target.exists():
        target.unlink()
    evidence = fresh_dir(work, "handoff-receipts")
    prompt = module_root() / "shared/case/fixtures/HANDOFF_PROMPT.txt"
    completed = launch(work, prompt, evidence, HANDOFF_NAME)
    errors = [] if completed.returncode == 0 else [f"child exit {completed.returncode}"]
    if completed.returncode == 0:
        errors = confirm_output(target, evidence, HANDOFF_NAME)
    if completed.returncode == 2:
        if not target.exists() and starter is not None:
            target.write_bytes(starter)
        return 2
    if errors:
        if target.exists():
            print(f"HOLD: live handoff failed; a remaining {HANDOFF_NAME} is not a successful run", file=sys.stderr)
        else:
            if starter is not None:
                target.write_bytes(starter)
            print("HOLD: live handoff failed before a receipted handoff was saved", file=sys.stderr)
        if evidence.is_dir():
            print(f"Evidence: {evidence}", file=sys.stderr)
        return 1
    write_session(
        work / WRITER_SESSION,
        {
            "role": "handoff-writer",
            "live_model_evidence": True,
            "model": pinned_selector(),
            "output": HANDOFF_NAME,
            "output_sha256": digest(target),
            "evidence": str(evidence),
            "prompt_sha256": digest(prompt),
        },
    )
    print(f"PASS: your AI wrote {target}")
    print(f"Evidence: {evidence}")
    return 0


def build_packet(work: Path, packet: Path) -> None:
    """Copy the handoff and source files only. Working notes stay out."""
    packet.mkdir(parents=True)
    shutil.copyfile(work / HANDOFF_NAME, packet / HANDOFF_NAME)
    inbox = packet / "inbox"
    inbox.mkdir()
    for source in sorted((work / "inbox").iterdir(), key=lambda item: item.name):
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"inbox entry is not a regular file: {source.name}")
        shutil.copyfile(source, inbox / source.name)
    revealed = work / "REVEALED_CHANGE.md"
    if revealed.is_symlink() or not revealed.is_file():
        raise ValueError("REVEALED_CHANGE.md is not a regular file")
    shutil.copyfile(revealed, packet / "REVEALED_CHANGE.md")
    mapping = json.loads((module_root() / "shared/case/INBOX_MAP.json").read_text(encoding="utf-8"))
    lines = [f"{entry['id']}\tinbox/{entry['inbox']}" for entry in mapping["sources"]]
    lines.append("S10\tREVEALED_CHANGE.md")
    (packet / "SOURCE_INDEX.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def scrutinize(work: Path) -> int:
    blocked = precheck(work)
    if blocked:
        return blocked
    blocked = required_inputs(work)
    if blocked:
        return blocked
    handoff = work / HANDOFF_NAME
    session_path = work / WRITER_SESSION
    if not handoff.is_file() or handoff.is_symlink() or is_starter(handoff) or not session_path.is_file():
        return hold(f"{HANDOFF_NAME} is not a receipted AI handoff", 1)
    try:
        writer = json.loads(session_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return hold("handoff session record is not readable", 1)
    if writer.get("output_sha256") != digest(handoff) or not writer.get("live_model_evidence"):
        return hold(f"{HANDOFF_NAME} does not match the writer receipt", 1)
    scrutiny = work / SCRUTINY_NAME
    if scrutiny.exists() or scrutiny.is_symlink() or (work / SCRUTINY_SESSION).exists():
        return hold(f"{SCRUTINY_NAME} already exists; keep it", 1)
    packet = fresh_dir(work, "scrutiny-packet")
    evidence = fresh_dir(work, "scrutiny-receipts")
    try:
        build_packet(work, packet)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        return hold(f"could not build the scrutiny packet: {error}", 2)
    prompt = module_root() / "shared/case/fixtures/HANDOFF_SCRUTINY_PROMPT.txt"
    completed = launch(packet, prompt, evidence, SCRUTINY_NAME)
    produced = packet / SCRUTINY_NAME
    if completed.returncode == 2:
        return 2
    errors = confirm_output(produced, evidence, SCRUTINY_NAME) if completed.returncode == 0 else [f"child exit {completed.returncode}"]
    if errors:
        if produced.exists():
            print(f"HOLD: scrutiny failed; a remaining {SCRUTINY_NAME} is not a successful run", file=sys.stderr)
        else:
            print("HOLD: scrutiny failed before a receipted file was saved", file=sys.stderr)
        if evidence.is_dir():
            print(f"Evidence: {evidence}", file=sys.stderr)
        return 1
    shutil.copyfile(produced, scrutiny)
    if digest(scrutiny) != digest(produced):
        return hold("copied scrutiny does not match the receipted file", 1)
    write_session(
        work / SCRUTINY_SESSION,
        {
            "role": "handoff-scrutiny",
            "live_model_evidence": True,
            "model": pinned_selector(),
            "tested_handoff_sha256": digest(handoff),
            "output": SCRUTINY_NAME,
            "output_sha256": digest(scrutiny),
            "evidence": str(evidence),
            "writer_evidence": writer.get("evidence"),
            "packet": str(packet),
            "prompt_sha256": digest(prompt),
            "excluded": sorted(EXCLUDED_NAMES),
        },
    )
    print(f"PASS: a new session wrote {scrutiny}")
    print(f"Evidence: {evidence}")
    return 0


def retire(work: Path) -> int:
    if not work.is_dir():
        return hold(f"work folder does not exist: {work}", 2)
    target = work / HANDOFF_NAME
    if not target.is_file() or target.is_symlink() or is_starter(target):
        return hold("there is no AI handoff to retire", 1)
    names = (HANDOFF_NAME, WRITER_SESSION, SCRUTINY_NAME, SCRUTINY_SESSION, DECISION_NAME)
    for name in names:
        if (work / name).is_symlink():
            return hold(f"{name} is a link; keep it", 1)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = work / "handoff-retired" / stamp
    folder.mkdir(parents=True)
    moved = []
    for name in names:
        path = work / name
        if path.exists():
            path.replace(folder / name)
            moved.append(name)
    (work / HANDOFF_NAME).write_text(STARTER, encoding="utf-8")
    print(f"PASS: retired handoff kept at {folder}")
    print("Kept: " + ", ".join(moved))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("write", "scrutinize", "retire"))
    parser.add_argument("workdir", type=Path)
    args = parser.parse_args(argv)
    work = args.workdir.expanduser().resolve()
    if args.action == "write":
        return write_handoff(work)
    if args.action == "scrutinize":
        return scrutinize(work)
    return retire(work)


if __name__ == "__main__":
    raise SystemExit(main())
