#!/usr/bin/env python3
"""Verify the Cold Lantern practice packet and source hashes."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "shared/case"
MANIFEST = CASE / "SOURCE_MANIFEST.json"

required = [
    ROOT / "README.md",
    ROOT / "shared/MODULE_01_LAB.md",
    ROOT / "shared/MISSION_THREAD.md",
    ROOT / "shared/WHEN_EVIDENCE_BREAKS.md",
    ROOT / "facilitator/RUNBOOK.md",
    CASE / "REQUEST.md",
    CASE / "AI_DISPATCH_BRIEF.md",
    ROOT / "facilitator/fixtures/SEALED_CHANGE.md",
    ROOT / "shared/templates/source-register.csv",
    ROOT / "shared/templates/thread-ledger.csv",
    ROOT / "scripts/start_work.py",
    ROOT / "scripts/freeze_baseline.py",
    ROOT / "scripts/reveal_change.py",
    ROOT / "scripts/render_review.py",
    ROOT / "scripts/compute_thread.py",
    ROOT / "scripts/check_work.py",
    ROOT / "scripts/hash_inbox.py",
    ROOT / "scripts/run_producer_rebuttal.py",
    ROOT / "scripts/run_handoff.py",
    CASE / "fixtures/HANDOFF_PROMPT.txt",
    CASE / "fixtures/HANDOFF_SCRUTINY_PROMPT.txt",
    CASE / "INBOX_MAP.json",
    MANIFEST,
]

errors: list[str] = []
for path in required:
    if not path.exists():
        errors.append(f"missing: {path.relative_to(ROOT)}")

manifest = {}
if MANIFEST.exists():
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid manifest JSON: {exc}")

if manifest.get("case_id") != "COLD-LANTERN-PRACTICE":
    errors.append("wrong or missing case_id")

sources = manifest.get("sources", [])
if len(sources) != 9:
    errors.append(f"expected 9 sources, observed {len(sources)}")

observed_ids: set[str] = set()
for entry in sources:
    sid = entry.get("id", "?")
    observed_ids.add(sid)
    path = CASE / "sources" / entry.get("file", "")
    if not path.exists():
        errors.append(f"{sid}: file missing")
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != entry.get("sha256"):
        errors.append(f"{sid}: hash mismatch")

expected_ids = {f"S{i:02d}" for i in range(1, 10)}
if observed_ids != expected_ids:
    errors.append(f"source IDs mismatch: {sorted(observed_ids)}")

result = {
    "state": "PASS" if not errors else "HOLD",
    "case_id": manifest.get("case_id"),
    "source_count": len(sources),
    "errors": errors,
}
print(json.dumps(result, indent=2))
sys.exit(0 if not errors else 1)
