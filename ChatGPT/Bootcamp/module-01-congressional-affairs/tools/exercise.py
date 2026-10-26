#!/usr/bin/env python3
"""Manage a local attempt for the fictional Module 01 congressional affairs case.

Only packet identity, work-file structure, and freeze order are checked here.
The learner must still judge whether the evidence supports the verdict.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "case"
SOURCES = CASE / "sources"
TEMPLATES = ROOT / "templates"
CHANGE = ROOT / "facilitator" / "S10_CA27_PORTAL_NOTICE_v6.md"
MANIFEST = CASE / "manifest.json"

STEPS = (
    "Inquiry defined",
    "Records received",
    "Cases validated",
    "Brief assembled",
    "Release approved",
    "Submission window met",
    "Packet transmitted",
    "Committee receipt confirmed",
)
STATEMENT_TYPES = {
    "SOURCE FACT", "CALCULATION", "INFERENCE", "DECISION", "UNSUPPORTED"
}
BASELINE_FILES = (
    "source-register.csv",
    "thread-ledger.csv",
    "challenge-matrix.md",
    "corrected-brief.md",
    "baseline-verdict.md",
    "change-prediction.md",
)
SCRATCH_FILES = (
    "challenge-matrix.md",
    "corrected-brief.md",
    "baseline-verdict.md",
    "change-prediction.md",
    "changed-brief.md",
    "changed-verdict.md",
    "handoff.md",
    "handoff-scrutiny.md",
    "handoff-scrutiny-decision.md",
)


class Hold(Exception):
    """An attempt should be preserved for inspection."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest() -> dict[str, object]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("case_id") != "CA-27-PRACTICE":
        raise Hold("case manifest has the wrong identity")
    sources = data.get("sources")
    if not isinstance(sources, dict) or len(sources) != 9:
        raise Hold("case manifest must list nine sources")
    if data.get("change", {}).get("file") != CHANGE.name:
        raise Hold("change manifest has the wrong identity")
    return data


def verify_case_source_files(data: dict[str, object]) -> None:
    for name, expected in data["sources"].items():
        path = SOURCES / name
        if not path.is_file() or digest(path) != expected:
            raise Hold(f"course source missing or changed: {path}")
    if not CHANGE.is_file() or digest(CHANGE) != data["change"]["sha256"]:
        raise Hold(f"course change missing or changed: {CHANGE}")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise Hold(f"missing {path.name}")
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        if not reader.fieldnames or any(row.get(None) for row in rows):
            raise Hold(f"malformed CSV: {path.name}")
        return rows


def require_baseline_structure(work: Path, data: dict[str, object]) -> None:
    for name in BASELINE_FILES:
        path = work / name
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            raise Hold(f"missing or empty baseline file: {name}")

    register = read_csv(work / "source-register.csv")
    if len(register) != 9:
        raise Hold("source-register.csv needs one row for each of the nine sources")
    listed = set()
    for row in register:
        name = row.get("file", "").strip()
        if name not in data["sources"] or name in listed:
            raise Hold("source register has a missing, duplicate, or unknown file")
        listed.add(name)
        if row.get("sha256", "").strip() != data["sources"][name]:
            raise Hold(f"source register hash does not match: {name}")
        expected_id = name.split("_", 1)[0]
        if row.get("source_id", "").strip() != expected_id:
            raise Hold(f"source register ID does not match: {name}")
        for field in ("issuer", "version_or_status", "effective_time", "exact_entities",
                      "allowed_use", "not_allowed_to_prove", "status"):
            if not row.get(field, "").strip():
                raise Hold(f"source register {name} is missing {field}")

    ledger = read_csv(work / "thread-ledger.csv")
    if not ledger or not set(STEPS).issubset({row.get("step", "").strip() for row in ledger}):
        raise Hold("thread ledger must cover all eight named steps")
    for row in ledger:
        if row.get("step", "").strip() not in STEPS:
            raise Hold("thread ledger contains an unknown step name")
        if row.get("statement_type", "").strip() not in STATEMENT_TYPES:
            raise Hold("thread ledger contains an unknown statement type")
        if not row.get("claim_id", "").strip() or not row.get("claim", "").strip():
            raise Hold("thread ledger contains an empty claim")

    verdict = (work / "baseline-verdict.md").read_text(encoding="utf-8")
    if not any(f"Verdict: {value}" in verdict for value in ("ACCEPT", "REVISE", "REJECT", "HOLD")):
        raise Hold("baseline-verdict.md needs an explicit verdict")


def verify_work(work: Path, data: dict[str, object]) -> None:
    inbox = work / "inbox"
    if not inbox.is_dir():
        raise Hold(f"missing inbox: {inbox}")
    expected_names = set(data["sources"])
    change_path = inbox / CHANGE.name
    if change_path.exists():
        expected_names.add(CHANGE.name)
    actual_names = {path.name for path in inbox.iterdir() if path.is_file()}
    if actual_names != expected_names:
        raise Hold("inbox file set differs from the original packet and optional reveal")
    for name, expected in data["sources"].items():
        path = inbox / name
        if digest(path) != expected:
            raise Hold(f"inbox hash mismatch: {name}")
        print(f"{expected}  {name}")
    if change_path.exists():
        expected = data["change"]["sha256"]
        if digest(change_path) != expected:
            raise Hold("revealed notice hash mismatch")
        print(f"{expected}  {CHANGE.name}")

    freeze = work / "baseline-freeze.json"
    if freeze.exists():
        record = json.loads(freeze.read_text(encoding="utf-8"))
        if record.get("case_id") != "CA-27-PRACTICE":
            raise Hold("freeze has the wrong case identity")
        files = record.get("files")
        if not isinstance(files, dict) or set(files) != set(BASELINE_FILES):
            raise Hold("freeze file set is incomplete")
        for name, expected in files.items():
            path = work / name
            if not path.is_file() or digest(path) != expected:
                raise Hold(f"frozen baseline changed: {name}")
        print("PASS: frozen baseline hashes match")
    else:
        print("INFO: baseline not frozen yet")

    release = work / "change-release.json"
    if change_path.exists() != release.exists():
        raise Hold("change notice and release record must exist together")
    if release.exists():
        if not freeze.exists():
            raise Hold("change was released without a baseline freeze")
        record = json.loads(release.read_text(encoding="utf-8"))
        if record.get("sha256") != data["change"]["sha256"]:
            raise Hold("release record does not match the notice")
        print("PASS: change release record matches")


def start(work: Path, data: dict[str, object]) -> None:
    verify_case_source_files(data)
    if work.exists():
        raise Hold(f"destination already exists: {work}")
    work.mkdir(parents=True)
    shutil.copyfile(ROOT / "LAB.md", work / "LAB.md")
    shutil.copyfile(CASE / "REQUEST.md", work / "REQUEST.md")
    inbox = work / "inbox"
    inbox.mkdir()
    for name in data["sources"]:
        shutil.copyfile(SOURCES / name, inbox / name)
    for name in ("source-register.csv", "thread-ledger.csv"):
        shutil.copyfile(TEMPLATES / name, work / name)
    shutil.copyfile(TEMPLATES / "thread-ledger.csv", work / "changed-thread-ledger.csv")
    for name in SCRATCH_FILES:
        (work / name).write_text("", encoding="utf-8")
    (work / "desk.md").write_text(
        "# CA-27 desk · 14:05 EDT\n\nRead [REQUEST.md](REQUEST.md), then every "
        "source in [inbox/](inbox/). The AI draft is output to verify.\n",
        encoding="utf-8",
    )
    print(f"PASS: created {work}")


def freeze(work: Path, data: dict[str, object]) -> None:
    if (work / "baseline-freeze.json").exists():
        raise Hold("baseline already frozen; preserve this attempt")
    if (work / "inbox" / CHANGE.name).exists():
        raise Hold("change already revealed; baseline cannot be frozen afterward")
    verify_work(work, data)
    require_baseline_structure(work, data)
    record = {
        "case_id": "CA-27-PRACTICE",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": {name: digest(work / name) for name in BASELINE_FILES},
    }
    with (work / "baseline-freeze.json").open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(f"PASS: baseline frozen at {work / 'baseline-freeze.json'}")


def reveal(work: Path, data: dict[str, object]) -> None:
    if not (work / "baseline-freeze.json").exists():
        raise Hold("freeze the baseline before revealing the change")
    if (work / "inbox" / CHANGE.name).exists() or (work / "change-release.json").exists():
        raise Hold("change already released; preserve this attempt")
    verify_work(work, data)
    target = work / "inbox" / CHANGE.name
    with target.open("xb") as stream:
        stream.write(CHANGE.read_bytes())
    record = {
        "case_id": "CA-27-PRACTICE",
        "released_at_utc": datetime.now(timezone.utc).isoformat(),
        "file": CHANGE.name,
        "sha256": data["change"]["sha256"],
    }
    with (work / "change-release.json").open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(f"PASS: practice change copied to {target}")


def prepare_review(work: Path, data: dict[str, object]) -> None:
    verify_work(work, data)
    if not (work / "change-release.json").exists():
        raise Hold("reveal the change and write the changed verdict first")
    changed_ledger = read_csv(work / "changed-thread-ledger.csv")
    if not set(STEPS).issubset({row.get("step", "").strip() for row in changed_ledger}):
        raise Hold("changed thread ledger must cover all eight named steps")
    for name in ("changed-brief.md", "changed-verdict.md"):
        path = work / name
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            raise Hold(f"missing or empty changed file: {name}")
    handoff = work / "handoff.md"
    if not handoff.is_file() or not handoff.read_text(encoding="utf-8").strip():
        raise Hold("handoff.md is empty")
    target = work / "scrutiny-packet"
    if target.exists():
        raise Hold("scrutiny packet already exists; preserve it")
    target.mkdir()
    shutil.copyfile(work / "REQUEST.md", target / "REQUEST.md")
    shutil.copyfile(handoff, target / "handoff.md")
    shutil.copytree(work / "inbox", target / "inbox")
    (target / "REVIEW_TASK.md").write_text(
        "# Fresh-session scrutiny\n\nRead `handoff.md`, `REQUEST.md`, and every "
        "source in `inbox/`. Test the handoff's claims against the exact "
        "inquiry, version, time, authority, arithmetic, and later notice. "
        "Return `STOOD`, `DID NOT STAND`, or `HOLD`, with exact source "
        "citations and any missing evidence. Do not infer an upload or "
        "committee receipt.\n",
        encoding="utf-8",
    )
    print(f"PASS: isolated review packet at {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "verify", "freeze", "reveal", "prepare-review"))
    parser.add_argument("workdir", type=Path)
    args = parser.parse_args()
    work = args.workdir.expanduser().resolve()
    try:
        data = manifest()
        if args.action == "start":
            start(work, data)
        elif args.action == "verify":
            verify_work(work, data)
        elif args.action == "freeze":
            freeze(work, data)
        elif args.action == "reveal":
            reveal(work, data)
        else:
            prepare_review(work, data)
    except (Hold, OSError, ValueError, KeyError, UnicodeError) as exc:
        print(f"HOLD: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
