#!/usr/bin/env python3
"""Structural, semantic, and safety oracle for Module 1."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASS: list[str] = []
FAIL: list[str] = []


def check(cid: str, condition: bool, detail: str) -> None:
    (PASS if condition else FAIL).append(f"{cid}: {detail}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


# Frozen Reference
ref = ROOT / "reference/REFERENCE.md"
hash_file = ROOT / "reference/REFERENCE.sha256"
expected_hash = read(hash_file).split()[0] if hash_file.exists() else ""
actual_hash = hashlib.sha256(ref.read_bytes()).hexdigest() if ref.exists() else ""
check("M1-REF", bool(expected_hash) and expected_hash == actual_hash, f"reference hash {actual_hash}")

required = {
    "start": ROOT / "README.md",
    "lab": ROOT / "shared/MODULE_01_LAB.md",
    "orientation": ROOT / "shared/MISSION_THREAD.md",
    "troubleshooting": ROOT / "shared/WHEN_EVIDENCE_BREAKS.md",
    "request": ROOT / "shared/case/REQUEST.md",
    "brief": ROOT / "shared/case/AI_DISPATCH_BRIEF.md",
    "change": ROOT / "facilitator/fixtures/SEALED_CHANGE.md",
    "manifest": ROOT / "shared/case/SOURCE_MANIFEST.json",
    "calculator": ROOT / "scripts/compute_thread.py",
}
source_dir = ROOT / "shared/case/sources"
source_files = sorted(source_dir.glob("S*.md"))
check("M1-01", len(source_files) == 9, "exactly nine baseline source files")

# Manifest schema and exact source identity
manifest = {}
try:
    manifest = json.loads(read(required["manifest"]))
except Exception:
    pass
check("M1-02", manifest.get("case_id") == "COLD-LANTERN-PRACTICE", "practice case identity")
entries = manifest.get("sources", [])
check("M1-02", len(entries) == 9, "manifest has nine baseline entries")
for entry in entries:
    check("M1-02", all(k in entry for k in ("id", "file", "issuer", "version", "effective", "authorized_use", "sha256")), f"manifest fields for {entry.get('id','?')}")
    path = source_dir / entry.get("file", "")
    digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""
    check("M1-02", digest == entry.get("sha256"), f"manifest hash for {entry.get('id','?')}")

learner_files = [required[k] for k in ("start", "lab", "orientation", "troubleshooting", "request", "brief", "change")] + source_files

# Calculations via executable reference helper
if required["calculator"].exists():
    result = subprocess.run([sys.executable, str(required["calculator"]), "--json"], capture_output=True, text=True)
    check("M1-14", result.returncode == 0, "reference calculations execute")
    try:
        values = json.loads(result.stdout)
    except Exception:
        values = {}
    expected = {
        "scanned_kits": 216,
        "usable_kits": 180,
        "released_mass_kg": 1320,
        "mission_payload_kg": 1404,
        "payload_margin_kg": 246,
        "all_scanned_payload_kg": 1668,
        "all_scanned_overage_kg": 18,
        "v5_closure_local": "14:50 MDT",
        "earliest_departure": "14:25 MDT",
        "earliest_gate_arrival": "14:53 MDT",
        "v5_gate_margin_minutes": -3,
        "clinic_arrival_if_admitted": "15:33 MDT",
        "clinic_margin_if_admitted_minutes": 27,
        "v6_closure_local": "15:20 MDT",
        "v6_gate_margin_minutes": 27,
    }
    for key, wanted in expected.items():
        check("M1-14", values.get(key) == wanted, f"{key}={wanted!r}")

# No learner answer leakage (genuine no-spoiler protection)
for path in learner_files:
    text = read(path)
    check("M1-ANSWER", "246 kg" not in text and "1,404 kg" not in text and "3 minutes late" not in text, f"no protected conclusion leaked in {path.name}")

print(f"PASS {len(PASS)}")
for item in PASS:
    print("  PASS", item)
print(f"FAIL {len(FAIL)}")
for item in FAIL:
    print("  FAIL", item)
sys.exit(1 if FAIL else 0)
