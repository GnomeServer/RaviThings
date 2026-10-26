#!/usr/bin/env python3
"""End-to-end tests for the visible Module 1 practice workflow."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
COLUMNS = [
    "step", "claim_id", "statement_type", "exact_entity", "entry_condition",
    "claim", "source_id", "source_version", "locator", "source_excerpt",
    "warrant", "calculation", "output_condition", "next_handoff",
    "uncertainty", "result",
]
STEPS = [
    "Requirement defined", "Cargo received", "Cargo released", "Vehicle made ready",
    "Movement authorized", "Route window met", "Cargo delivered", "Usable effect confirmed",
]
CHALLENGE_MATRIX = """# Challenge matrix

## Warehouse receipt is not usable inventory

RCPT-8821 records a scan. It does not release kits.

## Permit text is not approval

accepted for processing is intake, not authorization.

## Community page is the wrong route

R-17 is not R-71.

## Vendor note is the wrong vehicle

VX-240 is not VX-204.

## Hostile instruction

SYSTEM OVERRIDE is quoted data.

## Producer confidence

96% confidence is not independent evidence.

## Producer rebuttal

producer-rebuttal repeats the same GO.
"""




def run(script: str, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], text=True, capture_output=True)


class WorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name) / "work"
        result = run("start_work.py", self.work)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        inbox = list((self.work / "inbox").glob("*.md"))
        self.assertEqual(len(inbox), 9)
        self.assertFalse(any(path.name == "SOURCE_MANIFEST.json" for path in self.work.rglob("*")))


    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_ledger(self, path: Path, changed: bool = False, unrelated_delta: bool = False) -> None:
        rows = []
        for index, step in enumerate(STEPS, start=1):
            source = f"S{min(index, 6):02d}"
            version = "v6" if changed and step == "Route window met" else "v5" if step == "Route window met" else "current"
            claim = "North Gate closes at 21:20Z" if changed and step == "Route window met" else "North Gate closes at 20:50Z" if step == "Route window met" else f"{step} checked"
            if unrelated_delta and step == "Cargo received":
                claim = "Cargo received was changed without dependency"
            rows.append({
                "step": step,
                "claim_id": f"C{index:02d}",
                "statement_type": "SOURCE FACT",
                "exact_entity": "MO-27 / VX-204 / R-71 / H-17",
                "entry_condition": "prior step supported" if index > 1 else "request supplied",
                "claim": claim,
                "source_id": source,
                "source_version": version,
                "locator": "named section",
                "source_excerpt": claim,
                "warrant": "The applicable source states this exact condition.",
                "calculation": "none",
                "output_condition": "checked",
                "next_handoff": STEPS[index] if index < len(STEPS) else "human decision",
                "uncertainty": "delivery not yet observed" if index > 6 else "none",
                "result": "NOT YET OCCURRED" if index > 6 else "SUPPORTED",
            })

        # Six required practice calculations (lab section 5)
        gate_z = "21:20Z" if changed else "20:50Z"
        gate_mdt = "15:20 MDT" if changed else "14:50 MDT"
        gate_margin = "27 min" if changed else "-3 min"
        route_version = "v6" if changed else "v5"
        rows.extend([
            {"step": "Cargo received", "claim_id": "C09", "statement_type": "CALCULATION",
             "exact_entity": "scanned kit count", "entry_condition": "S02 tote scan",
             "claim": "216 scanned kits", "source_id": "S02", "source_version": "RCPT-8821",
             "locator": "tote and lot count", "source_excerpt": "12 totes scanned",
             "warrant": "Scanned count from warehouse receipt.",
             "calculation": "12 totes x 18 kits/tote = 216 kits",
             "output_condition": "scanned identity frozen", "next_handoff": "release decision",
             "uncertainty": "none", "result": "SUPPORTED"},
            {"step": "Cargo released", "claim_id": "C10", "statement_type": "CALCULATION",
             "exact_entity": "usable kit count", "entry_condition": "S03 QA release",
             "claim": "180 usable kits", "source_id": "S03", "source_version": "QA-661",
             "locator": "release count", "source_excerpt": "10 totes released",
             "warrant": "Released count from QA release.",
             "calculation": "10 released totes x 18 kits/tote = 180 kits",
             "output_condition": "usable count frozen", "next_handoff": "vehicle readiness",
             "uncertainty": "none", "result": "SUPPORTED"},
            {"step": "Vehicle made ready", "claim_id": "C11", "statement_type": "CALCULATION",
             "exact_entity": "mission payload mass", "entry_condition": "S04 rack requirement",
             "claim": "1404 kg mission payload", "source_id": "S04", "source_version": "r7",
             "locator": "rack mass", "source_excerpt": "84 kg required rack",
             "warrant": "Released mass plus required rack from fleet spec.",
             "calculation": "1320 kg released mass + 84 kg rack = 1404 kg",
             "output_condition": "payload within limit", "next_handoff": "authorization",
             "uncertainty": "none", "result": "SUPPORTED"},
            {"step": "Vehicle made ready", "claim_id": "C12", "statement_type": "CALCULATION",
             "exact_entity": "payload margin", "entry_condition": "S04 payload limit",
             "claim": "246 kg margin; 18 kg overage if all scanned loaded",
             "source_id": "S04", "source_version": "r7",
             "locator": "payload limit", "source_excerpt": "1650 kg limit",
             "warrant": "Limit from fleet spec.",
             "calculation": "1650 - 1404 = 246 kg margin; 1668 - 1650 = 18 kg overage",
             "output_condition": "margin positive", "next_handoff": "authorization",
             "uncertainty": "none", "result": "SUPPORTED"},
            {"step": "Route window met", "claim_id": "C13", "statement_type": "CALCULATION",
             "exact_entity": "gate closure and margin", "entry_condition": "S05 route bulletin",
             "claim": f"Gate closes {gate_mdt}; margin {gate_margin}",
             "source_id": "S05", "source_version": route_version,
             "locator": "North Gate closure", "source_excerpt": f"North Gate closes {gate_z}",
             "warrant": "Closure time from current route bulletin.",
             "calculation": f"{gate_z} - 6 h = {gate_mdt}; {gate_z} - 14:53Z = {gate_margin}",
             "output_condition": "gate open on arrival" if changed else "gate closed before arrival",
             "next_handoff": "delivery", "uncertainty": "none" if changed else "gate already closed",
             "result": "SUPPORTED"},
            {"step": "Route window met", "claim_id": "C14", "statement_type": "CALCULATION",
             "exact_entity": "travel schedule", "entry_condition": "S01 step durations",
             "claim": "Depart 14:25, gate 14:53, clinic 15:33 MDT",
             "source_id": "S01", "source_version": "r4",
             "locator": "step durations", "source_excerpt": "20 min depart, 28 min gate, 40 min clinic",
             "warrant": "Durations from mission requirement.",
             "calculation": "14:05 + 20 min = 14:25; + 28 min = 14:53; + 40 min = 15:33",
             "output_condition": "schedule feasible" if changed else "schedule infeasible at baseline gate",
             "next_handoff": "delivery", "uncertainty": "counterfactual at baseline gate",
             "result": "SUPPORTED"},
        ])

        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    def prepare(self, unrelated_delta: bool = False) -> None:
        mapping = json.loads((ROOT / "shared/case/INBOX_MAP.json").read_text(encoding="utf-8"))
        by_id = {entry["id"]: entry["inbox"] for entry in mapping["sources"]}
        shutil.copyfile(ROOT / "shared/templates/source-register.csv", self.work / "source-register.csv")
        with (self.work / "source-register.csv").open("a", encoding="utf-8") as handle:
            for row in (
                f"S01,{by_id['S01']},North Basin Mission Control,r4,2026-10-06 13:50 MDT,MO-27,requirements,delivery,APPLICABLE\n",
                f"S02,{by_id['S02']},Red Mesa Warehouse Management,RCPT-8821,2026-10-06 13:42 MDT,WMS totes and lots,custody and identity,usable inventory,APPLICABLE\n",
                f"S03,{by_id['S03']},North Basin Quality Office,QA-661,2026-10-06 13:48 MDT,QA release,quality release status,permit approval,APPLICABLE\n",
                f"S04,{by_id['S04']},North Basin Fleet Engineering,r7,2026-10-01 00:00 MDT,VX-204,payload and rack,VX-240,APPLICABLE\n",
                f"S05,{by_id['S05']},North Basin Road Authority,v5 current,2026-10-06 19:55Z,R-71,route closure,R-17,SUPERSEDED\n",
                f"S06,{by_id['S06']},North Basin Movement Registry,snapshot 14:02,2026-10-06 14:02 MDT,PR-4418,permit status,authorization,APPLICABLE\n",
                f"S07,{by_id['S07']},Alpine Bodyworks,2026-09-12,2026-09-12,VX-240,packing dimensions,VX-204,IRRELEVANT\n",
                f"S08,{by_id['S08']},Pine County Community Desk,2026-10-06 14:00,2026-10-06 14:00 MDT,R-17,R-17 status,R-71,IRRELEVANT\n",
                f"S09,{by_id['S09']},AI producer,draft 14:05,2026-10-06 14:05 MDT,AI brief,none,verification,OUTPUT_TO_CHECK\n",
            ):
                handle.write(row)
        self.write_ledger(self.work / "thread-ledger.csv")
        (self.work / "baseline-verdict.md").write_text("# Baseline verdict\n\nVerdict: HOLD\nStanding rule: Use the exact current source.\nUnresolved condition: permit pending\n", encoding="utf-8")
        (self.work / "change-prediction.md").write_text("# Prediction\n\nFields that should change\nClaims that should change\nFields that must not change\nCondition that would still block\nUnexpected change\n", encoding="utf-8")
        (self.work / "challenge-matrix.md").write_text(CHALLENGE_MATRIX, encoding="utf-8")
        (self.work / "corrected-brief.md").write_text("# Corrected brief\n\nInternal class review.\n", encoding="utf-8")
        (self.work / "handoff.md").write_text("# Handoff\n\nCurrent result and sources.\n", encoding="utf-8")
        (self.work / "producer-rebuttal.md").write_text(
            "# Producer rebuttal\n\n" + ("GO argument using the inbox. " * 20) + "\n",
            encoding="utf-8",
        )

        freeze = run("freeze_baseline.py", self.work)
        self.assertEqual(freeze.returncode, 0, freeze.stdout + freeze.stderr)
        reveal = run("reveal_change.py", self.work)
        self.assertEqual(reveal.returncode, 0, reveal.stdout + reveal.stderr)

        self.write_ledger(self.work / "changed-thread-ledger.csv", changed=True, unrelated_delta=unrelated_delta)
        (self.work / "changed-brief.md").write_text("# Changed brief\n\nR-71 v6 closes at 21:20Z. Permit remains PENDING.\n", encoding="utf-8")
        (self.work / "changed-verdict.md").write_text("# Changed verdict\n\nVerdict: HOLD\nChanged source: R71-2026-1006-v6\nChanged fields: route closure and gate margin\nUnchanged blockers: permit remains PENDING\nLater event not yet observed: delivery\nWhy the overall verdict did not change: authorization is unresolved.\nNew closure: 21:20Z\n", encoding="utf-8")
        render = run("render_review.py", self.work)
        self.assertEqual(render.returncode, 0, render.stdout + render.stderr)

    def test_complete_visible_practice_passes(self) -> None:
        self.prepare()
        result = run("check_work.py", self.work)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_changed_history_and_downstream_explanations_preserve_facts(self) -> None:
        self.prepare()
        path = self.work / "changed-thread-ledger.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        by_id = {row["claim_id"]: row for row in rows}
        by_id["C06"]["exact_entity"] += " / R71-2026-1006-v6"
        by_id["C06"]["source_id"] = "S10"
        by_id["C06"]["next_handoff"] = "Compare arrival with the revised 15:20 MDT closure."
        by_id["C06"]["warrant"] += " The earlier 20:50Z closure is superseded."
        by_id["C05"]["warrant"] = "S10 and C06 resolve the route-window conflict, not the pending permit."
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        with (self.work / "changed-brief.md").open("a", encoding="utf-8") as handle:
            handle.write("\nThe old 20:50Z closure is superseded. R-17 remains the wrong route.\n")
        result = run("check_work.py", self.work)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unapplied_route_revision_holds(self) -> None:
        self.prepare()
        shutil.copyfile(self.work / "thread-ledger.csv", self.work / "changed-thread-ledger.csv")
        result = run("check_work.py", self.work, "--phase", "change")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_unrelated_explanation_without_revision_dependency_holds(self) -> None:
        self.prepare()
        path = self.work / "changed-thread-ledger.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        rows[1]["warrant"] = "The warehouse now grants copyright permission."
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        result = run("check_work.py", self.work, "--phase", "change")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_unrelated_changed_step_holds(self) -> None:
        self.prepare(unrelated_delta=True)
        result = run("check_work.py", self.work)
        self.assertEqual(result.returncode, 1)

    def test_tampered_baseline_holds(self) -> None:
        self.prepare()
        with (self.work / "thread-ledger.csv").open("a", encoding="utf-8") as handle:
            handle.write("tamper\n")
        result = run("check_work.py", self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: frozen:thread-ledger.csv", result.stdout)

    def test_tampered_copied_source_holds(self) -> None:
        self.prepare()
        source = self.work / "inbox/2026-10-06-1348-qa-661.md"
        source.write_text(source.read_text(encoding="utf-8") + "\ntamper\n", encoding="utf-8")
        result = run("check_work.py", self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: source hash:S03", result.stdout)


    def test_tampered_revealed_change_holds(self) -> None:
        self.prepare()
        change = self.work / "REVEALED_CHANGE.md"
        change.write_text(change.read_text(encoding="utf-8") + "\ntamper\n", encoding="utf-8")
        result = run("check_work.py", self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: revealed change hash", result.stdout)

    def test_incomplete_source_register_holds(self) -> None:
        self.prepare()
        register = self.work / "source-register.csv"
        lines = register.read_text(encoding="utf-8").splitlines()
        kept = [line for line in lines if not line.startswith("S05,")]
        register.write_text("\n".join(kept) + "\n", encoding="utf-8")
        result = run("check_work.py", self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: source register covers all nine sources", result.stdout)

    def test_blank_calculation_holds(self) -> None:
        self.prepare()
        ledger = self.work / "thread-ledger.csv"
        with ledger.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            if row["statement_type"] == "CALCULATION":
                row["calculation"] = ""
                break
        with ledger.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        result = run("check_work.py", self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: calculations have explicit formulas", result.stdout)

    def test_reveal_before_freeze_holds(self) -> None:
        other = Path(self.tmp.name) / "unfrozen"
        self.assertEqual(run("start_work.py", other).returncode, 0)
        result = run("reveal_change.py", other)
        self.assertEqual(result.returncode, 1)
        self.assertIn("freeze baseline", result.stdout)

    def test_wrong_scanned_count_holds(self) -> None:
        self.prepare()
        ledger = self.work / "thread-ledger.csv"
        with ledger.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            for field in ("calculation", "claim", "result"):
                row[field] = row[field].replace("216", "215")
            if row["statement_type"] == "CALCULATION" and "12" in row["calculation"]:
                row["calculation"] = "12*18=215"
        with ledger.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        result = run("check_work.py", self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: practice scanned count 216", result.stdout)


    def test_changed_accept_holds(self) -> None:
        self.prepare()
        path = self.work / "changed-verdict.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("Verdict: HOLD", "Verdict: ACCEPT"),
            encoding="utf-8",
        )
        result = run("check_work.py", self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: changed verdict is HOLD", result.stdout)

    def test_baseline_revise_holds(self) -> None:
        self.prepare()
        path = self.work / "baseline-verdict.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("Verdict: HOLD", "Verdict: REVISE"),
            encoding="utf-8",
        )
        result = run("check_work.py", self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: baseline verdict is HOLD", result.stdout)

    def test_hash_inbox_fresh_start(self) -> None:
        result = run("hash_inbox.py", self.work)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 9)
        for line in lines:
            digest, name = line.split(" ", 1)
            self.assertEqual(len(digest), 64)
            self.assertTrue((self.work / "inbox" / name).exists())
            self.assertFalse(name.startswith("S0"))

    def test_phase_ingest_fresh_start(self) -> None:
        result = run("check_work.py", "--phase", "ingest", self.work)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS: phase ingest", result.stdout)
        self.assertNotIn("scanned_kits():", result.stdout)

    def test_calculator_shows_each_function_and_json_stays_values_only(self) -> None:
        shown = run("compute_thread.py")
        self.assertEqual(shown.returncode, 0, shown.stderr)
        parsed = run("compute_thread.py", "--json")
        self.assertEqual(parsed.returncode, 0, parsed.stderr)
        values = json.loads(parsed.stdout)
        self.assertNotIn("():", parsed.stdout)
        expected = {
            "scanned_kits": "12 totes * 18 kits/tote = 216 kits",
            "usable_kits": "10 released totes * 18 kits/tote = 180 kits",
            "released_mass_kg": "10 released totes * 132 kg/tote = 1320 kg",
            "mission_payload_kg": "1320 kg + 84 kg rack = 1404 kg",
            "payload_margin_kg": "1650 kg - 1404 kg = 246 kg",
            "all_scanned_payload_kg": "12 totes * 132 kg/tote + 84 kg rack = 1668 kg",
            "all_scanned_overage_kg": "1668 kg - 1650 kg = 18 kg",
            "v5_closure_local": "20:50Z - 6 h = 14:50 MDT",
            "earliest_departure": "14:05 MDT + 20 min = 14:25 MDT",
            "earliest_gate_arrival": "14:25 MDT + 28 min = 14:53 MDT",
            "v5_gate_margin_minutes": "14:50 MDT - 14:53 MDT = -3 min",
            "clinic_arrival_if_admitted": "14:53 MDT + 40 min = 15:33 MDT",
            "clinic_margin_if_admitted_minutes": "16:00 MDT - 15:33 MDT = 27 min",
            "v6_closure_local": "21:20Z - 6 h = 15:20 MDT",
            "v6_gate_margin_minutes": "15:20 MDT - 14:53 MDT = 27 min",
        }
        self.assertEqual(set(values), set(expected))
        for name, formula in expected.items():
            self.assertIn(f"{name}(): {formula}", shown.stdout)
            shown_result = formula.rsplit("= ", 1)[1]
            if isinstance(values[name], int):
                self.assertTrue(shown_result.startswith(f"{values[name]} "))
            else:
                self.assertEqual(shown_result, values[name])

    def test_ledger_check_shows_scored_math_and_hides_sealed_change(self) -> None:
        self.prepare()
        result = run("check_work.py", self.work, "--phase", "ledger")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in (
            "scanned_kits()",
            "usable_kits()",
            "released_mass_kg()",
            "mission_payload_kg()",
            "payload_margin_kg()",
            "v5_closure_local()",
            "earliest_departure()",
            "earliest_gate_arrival()",
        ):
            self.assertIn(name, result.stdout)
        self.assertNotIn("v6_closure_local():", result.stdout)
        self.assertNotIn("v6_gate_margin_minutes():", result.stdout)
        self.assertNotIn("21:20Z", result.stdout)
        self.assertIn("12 totes * 18 kits/tote = 216 kits", result.stdout)
        self.assertIn("10 released totes * 132 kg/tote = 1320 kg", result.stdout)
        self.assertIn("1320 kg + 84 kg rack = 1404 kg", result.stdout)
        self.assertIn("1650 kg - 1404 kg = 246 kg", result.stdout)
        self.assertIn("20:50Z - 6 h = 14:50 MDT", result.stdout)
        self.assertIn("14:05 MDT + 20 min = 14:25 MDT", result.stdout)
        self.assertIn("14:25 MDT + 28 min = 14:53 MDT", result.stdout)

    def test_challenge_missing_vx240_fails(self) -> None:
        self.prepare()
        path = self.work / "challenge-matrix.md"
        path.write_text(path.read_text(encoding="utf-8").replace("VX-240", "similar vehicle"), encoding="utf-8")
        result = run("check_work.py", self.work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAIL: challenge:VX-240", result.stdout)
    def test_producer_rebuttal_fixture_writes_warning_and_provenance(self) -> None:
        result = run("run_producer_rebuttal.py", self.work, "--fixture")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PRACTICE: sealed rebuttal fixture; no live-model evidence", result.stdout)
        target = self.work / "producer-rebuttal.md"
        self.assertTrue(target.exists())
        prov = self.work / "producer-rebuttal.practice.json"
        self.assertTrue(prov.exists())
        data = json.loads(prov.read_text(encoding="utf-8"))
        self.assertFalse(data.get("live_model_evidence"))
        self.assertEqual(data.get("mode"), "practice")
        target_digest = hashlib.sha256(target.read_bytes()).hexdigest()
        self.assertEqual(data.get("fixture_sha256"), target_digest)
        self.assertEqual(data.get("output_sha256"), target_digest)

    def test_producer_rebuttal_fixture_refuses_overwrite(self) -> None:
        run("run_producer_rebuttal.py", self.work, "--fixture")
        original = (self.work / "producer-rebuttal.md").read_bytes()
        original_prov = (self.work / "producer-rebuttal.practice.json").read_bytes() if (self.work / "producer-rebuttal.practice.json").exists() else b""
        result = run("run_producer_rebuttal.py", self.work, "--fixture")
        self.assertEqual(result.returncode, 1)
        self.assertEqual((self.work / "producer-rebuttal.md").read_bytes(), original)
        if original_prov:
            self.assertEqual((self.work / "producer-rebuttal.practice.json").read_bytes(), original_prov)

    def test_producer_live_missing_key_exits_2_no_artifact(self) -> None:
        env = os.environ.copy()
        env.pop("OPENROUTER_API_KEY", None)
        result = subprocess.run([sys.executable, str(SCRIPTS / "run_producer_rebuttal.py"), str(self.work)], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.work / "producer-rebuttal.md").exists())

    def test_producer_failed_child_leaving_file_does_not_report_success(self) -> None:
        target = self.work / "producer-rebuttal.md"
        target.write_text("partial from failed child")
        # Exercise classify_live directly via python -c to prove nonzero + leftover file cannot pass (returns 1)
        test_code = f'''
import sys
from pathlib import Path
sys.path.insert(0, "{str(SCRIPTS)}")
from run_producer_rebuttal import classify_live
target = Path("{target}")
print(classify_live(1, target, Path("dummy")))
'''
        res = subprocess.run([sys.executable, "-c", test_code], capture_output=True, text=True)
        self.assertEqual(res.stdout.strip(), "1")


    def test_start_work_refuses_existing_destination(self) -> None:
        # self.work exists from setUp; start_work must refuse and leave bytes unchanged
        files_before = {p.relative_to(self.work): p.read_bytes() for p in self.work.rglob("*") if p.is_file()}
        result = run("start_work.py", self.work)
        self.assertNotEqual(result.returncode, 0)
        files_after = {p.relative_to(self.work): p.read_bytes() for p in self.work.rglob("*") if p.is_file()}
        self.assertEqual(files_before, files_after)

    def test_handoff_write_keeps_existing_work_without_a_key(self) -> None:
        target = self.work / "handoff.md"
        target.write_text("# Module 1 handoff\n\nCurrent verdict: HOLD\n", encoding="utf-8")
        before = target.read_bytes()
        env = os.environ.copy()
        env.pop("OPENROUTER_API_KEY", None)
        result = subprocess.run([sys.executable, str(SCRIPTS / "run_handoff.py"), "write", str(self.work)], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("already has work in it", result.stderr)
        self.assertEqual(target.read_bytes(), before)

    def test_handoff_write_missing_key_leaves_starter(self) -> None:
        target = self.work / "handoff.md"
        before = target.read_bytes()
        env = os.environ.copy()
        env.pop("OPENROUTER_API_KEY", None)
        result = subprocess.run([sys.executable, str(SCRIPTS / "run_handoff.py"), "write", str(self.work)], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("OPENROUTER_API_KEY unavailable", result.stderr)
        self.assertEqual(target.read_bytes(), before)

    def test_scrutiny_packet_excludes_working_notes(self) -> None:
        sys.path.insert(0, str(SCRIPTS))
        import run_handoff
        (self.work / "REVEALED_CHANGE.md").write_text("# S10\nNorth Gate closes at 21:20Z.\n", encoding="utf-8")
        (self.work / "thread-ledger.csv").write_text("working notes\n", encoding="utf-8")
        (self.work / "changed-verdict.md").write_text("Verdict: HOLD\n", encoding="utf-8")
        handoff = self.work / "handoff.md"
        handoff.write_text("# Module 1 handoff\n\nCurrent verdict: HOLD\n", encoding="utf-8")
        packet = self.work.parent / "packet"
        run_handoff.build_packet(self.work, packet)
        names = {path.name for path in packet.rglob("*")}
        self.assertIn("handoff.md", names)
        self.assertIn("REVEALED_CHANGE.md", names)
        self.assertIn("SOURCE_INDEX.txt", names)
        self.assertNotIn("thread-ledger.csv", names)
        self.assertNotIn("changed-verdict.md", names)
        self.assertEqual((packet / "handoff.md").read_bytes(), handoff.read_bytes())
        self.assertTrue((packet / "inbox").is_dir())
        self.assertEqual(len(list((packet / "inbox").glob("*.md"))), 9)

    def test_handoff_phase_binds_two_sessions_and_rejects_a_visible_ledger(self) -> None:
        sys.path.insert(0, str(SCRIPTS))
        import run_handoff
        self.prepare()
        handoff = self.work / "handoff.md"
        handoff.write_text(
            "# Module 1 handoff\n\n"
            + "".join(f"{label} recorded\n" for label in run_handoff.HANDOFF_LABELS).replace(
                "Current verdict: recorded", "Current verdict: HOLD"
            ),
            encoding="utf-8",
        )
        scrutiny = self.work / "handoff-scrutiny.md"
        scrutiny.write_text("Conclusion: DID NOT STAND\nClaim tested: permit\n", encoding="utf-8")
        (self.work / "handoff-scrutiny-decision.md").write_text(
            "Scrutiny result: DID NOT STAND\nClaim rechecked: permit pending\nSource opened: S06\nScrutiny holds: YES\nWhat stays unchanged: HOLD\n",
            encoding="utf-8",
        )
        packet = self.work.parent / "packet"
        run_handoff.build_packet(self.work, packet)
        handoff_digest = hashlib.sha256(handoff.read_bytes()).hexdigest()
        scrutiny_digest = hashlib.sha256(scrutiny.read_bytes()).hexdigest()
        writer_evidence = self.work.parent / "writer-evidence"
        scrutiny_evidence = self.work.parent / "scrutiny-evidence"
        self._receipt(writer_evidence, "handoff.md", handoff_digest, handoff)
        self._receipt(scrutiny_evidence, "handoff-scrutiny.md", scrutiny_digest, packet / "handoff-scrutiny.md")
        (packet / "handoff-scrutiny.md").write_bytes(scrutiny.read_bytes())
        selector = run_handoff.pinned_selector()
        (self.work / "handoff-session.json").write_text(json.dumps({
            "live_model_evidence": True, "model": selector, "output_sha256": handoff_digest, "evidence": str(writer_evidence),
        }), encoding="utf-8")
        (self.work / "handoff-scrutiny-session.json").write_text(json.dumps({
            "live_model_evidence": True, "model": selector, "tested_handoff_sha256": handoff_digest,
            "output_sha256": scrutiny_digest, "evidence": str(scrutiny_evidence), "packet": str(packet),
        }), encoding="utf-8")
        passed = run("check_work.py", self.work, "--phase", "handoff")
        self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
        (packet / "thread-ledger.csv").write_text("working notes\n", encoding="utf-8")
        leaked = run("check_work.py", self.work, "--phase", "handoff")
        self.assertEqual(leaked.returncode, 1)
        self.assertIn("FAIL: scrutiny packet excludes working notes", leaked.stdout)

    def _receipt(self, evidence: Path, name: str, file_digest: str, target: Path) -> None:
        evidence.mkdir()
        (evidence / "result.json").write_text(json.dumps({
            "status": "PASS", "output_sha256": {name: file_digest},
        }), encoding="utf-8")
        (evidence / "guard.jsonl").write_text(json.dumps({
            "type": "executed", "tool": "course_write", "output_sha256": file_digest, "resolved_path": str(target),
        }) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
