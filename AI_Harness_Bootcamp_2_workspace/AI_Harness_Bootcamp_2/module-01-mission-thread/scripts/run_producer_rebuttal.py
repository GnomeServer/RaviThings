#!/usr/bin/env python3
"""Write a producer rebuttal into a Module 1 work folder.

The positional work folder is unchanged. Without --fixture, this calls the
shared OMP launcher and allows only producer-rebuttal.md. A missing live
prerequisite exits 2 and does not create that file. A failed child is never
reported as success, even when a file remains. --fixture copies the sealed
practice fixture and is not live-model evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import uuid
from pathlib import Path

PRACTICE_WARNING = "PRACTICE: sealed rebuttal fixture; no live-model evidence"
TARGET_NAME = "producer-rebuttal.md"
PROVENANCE_NAME = "producer-rebuttal.practice.json"


def module_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        fixture = parent / "shared/case/fixtures" / TARGET_NAME
        prompt = parent / "shared/case/fixtures/PRODUCER_REBUTTAL_PROMPT.txt"
        if fixture.is_file() and prompt.is_file():
            return parent
    raise FileNotFoundError("Cold Lantern producer fixtures are missing from the checkout")


def shared_launcher() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "shared/run_omp.py"
        guard = parent / "shared/course_guard.mjs"
        if candidate.is_file() and guard.is_file():
            return candidate
    raise FileNotFoundError("shared OMP launcher is missing from the checkout")


def load_receipt_api():
    launcher = shared_launcher()
    shared = str(launcher.parent)
    if shared not in sys.path:
        sys.path.insert(0, shared)
    from run_omp import MODEL, PROVIDER, audit_evidence

    return PROVIDER, MODEL, audit_evidence


def confirm_output(target: Path, evidence: Path) -> list[str]:
    """Bind a live success claim to the child status and the receipted file."""
    errors: list[str] = []
    if not target.is_file():
        errors.append(f"{TARGET_NAME} is absent")
    try:
        provider, model, audit_evidence = load_receipt_api()
    except Exception as error:
        return errors + [f"cannot read shared receipt checker: {error}"]
    errors.extend(audit_evidence(evidence))
    result_path = evidence / "result.json"
    guard_path = evidence / "guard.jsonl"
    if not result_path.is_file() or not guard_path.is_file():
        return errors + ["live receipts are incomplete"]
    try:
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return errors + ["result.json is not readable"]
    if result.get("status") != "PASS" or result.get("exit_code") != 0:
        errors.append("child status is not a completed live run")
    if result.get("provider") != provider or result.get("model") != model:
        errors.append("live identity is not the pinned OpenRouter model")
    if not target.is_file():
        return errors
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    recorded = (result.get("output_sha256") or {}).get(TARGET_NAME)
    if recorded != digest:
        errors.append("disk rebuttal does not match the receipt")
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
        if row.get("output_sha256") != digest:
            continue
        resolved = row.get("resolved_path")
        if isinstance(resolved, str) and Path(resolved).resolve() == target.resolve():
            matched = True
    if not matched:
        errors.append(f"no course_write receipt for {TARGET_NAME}")
    return errors


def classify_live(returncode: int, target: Path, evidence: Path) -> int:
    """Return the live exit code. A remaining file cannot turn a failure into success."""
    if returncode == 2:
        return 2
    if returncode != 0:
        return 1
    return 1 if confirm_output(target, evidence) else 0


def write_fixture(work: Path, target: Path) -> int:
    provenance = work / PROVENANCE_NAME
    if target.exists() or target.is_symlink() or provenance.exists() or provenance.is_symlink():
        print(f"HOLD: {TARGET_NAME} or its provenance already exists", file=sys.stderr)
        return 1
    try:
        root = module_root()
    except FileNotFoundError as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 2
    fixture = root / "shared/case/fixtures" / TARGET_NAME
    raw = fixture.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    target.write_bytes(raw)
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        print("HOLD: practice copy does not match the sealed fixture", file=sys.stderr)
        return 1
    provenance_payload = {
        "mode": "practice",
        "live_model_evidence": False,
        "warning": PRACTICE_WARNING,
        "fixture_sha256": digest,
        "output_sha256": digest,
        "fixture_name": TARGET_NAME,
    }
    (work / PROVENANCE_NAME).write_text(
        json.dumps(provenance_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(PRACTICE_WARNING)
    print(f"Wrote practice rebuttal to {target}")
    return 0
def fresh_evidence(work: Path) -> Path:
    return work.parent / f"{work.name}-rebuttal-receipts" / uuid.uuid4().hex


def fresh_evidence(work: Path) -> Path:
    return work.parent / f"{work.name}-rebuttal-receipts" / uuid.uuid4().hex


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workdir", type=Path)
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="copy the sealed practice fixture; this is not a live-model run",
    )
    args = parser.parse_args(argv)
    work = args.workdir.expanduser().resolve()
    target = work / TARGET_NAME
    if not work.is_dir():
        print(f"HOLD: work folder does not exist: {work}", file=sys.stderr)
        return 2
    if args.fixture:
        return write_fixture(work, target)
    if target.exists() or target.is_symlink():
        print(f"HOLD: {TARGET_NAME} already exists", file=sys.stderr)
        return 1
    try:
        root = module_root()
        launcher = shared_launcher()
    except FileNotFoundError as error:
        print(f"HOLD: {error}", file=sys.stderr)
        return 2
    prompt = root / "shared/case/fixtures/PRODUCER_REBUTTAL_PROMPT.txt"
    evidence = fresh_evidence(work)
    completed = subprocess.run(
        [
            sys.executable,
            str(launcher),
            "--workdir",
            str(work),
            "--prompt",
            str(prompt),
            "--evidence",
            str(evidence),
            "--allow-write",
            TARGET_NAME,
        ]
    )
    code = classify_live(completed.returncode, target, evidence)
    if code == 0:
        print(f"PASS: live producer wrote {target}")
        print(f"Evidence: {evidence}")
        return 0
    if code == 2:
        return 2
    if target.exists():
        print(
            f"HOLD: live producer failed; a remaining {TARGET_NAME} is not a successful run",
            file=sys.stderr,
        )
    else:
        print("HOLD: live producer failed before a receipted rebuttal was saved", file=sys.stderr)
    if evidence.is_dir():
        print(f"Evidence: {evidence}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
