#!/usr/bin/env python3
"""Offline validator and attempt-boundary regressions; no provider calls."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("hallucination", ROOT / "scripts/hallucination.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
SOURCES = M.load_sources_strict(ROOT / "shared/case")
ORIGINAL = M.validate_claims(M.load(ROOT / "shared/case/claims.json"), SOURCES)


def corrected_claims():
    claims = copy.deepcopy(ORIGINAL)
    claims[0].update(value="2233 kg", locator="SB-PC-03#payload")
    for row in claims[1:3]:
        row.update(value="13:05 MDT", locator="SB-PC-01#gate")
    claims[3].update(value=SOURCES["PC-03"]["SB-PC-03#payload"]["text"], locator="SB-PC-03#payload")
    claims[6].update(value=None, locator=None)
    return claims


def review_document(claims):
    answers = []
    for claim in claims:
        locator = None if claim["kind"] == "authority" else f"SB-{claim['case_id']}#" + ("payload" if claim["kind"] in ("mass", "citation") else "gate")
        answers.append({"id": claim["id"], "verdict": "unknown" if locator is None else "supported",
                        "locator": locator, "quote": None if locator is None else SOURCES[claim["case_id"]][locator]["text"],
                        "reason": "The original source establishes the fact." if locator else "The packet does not establish dispatch authorization."})
    return {"schema": "m08-review-v1", "answers": answers}


class ClaimChecks(unittest.TestCase):
    def test_repaired_clock_is_supported_and_zone_errors_are_held(self):
        for value, expected in (("13:05 MDT", "supported"), ("19:05 UTC", "supported"), ("13:05", "contradicted"), ("13:05 UTC", "contradicted"), ("19:05 MDT", "contradicted")):
            with self.subTest(value=value):
                claim = {**ORIGINAL[1], "value": value, "locator": "SB-PC-01#gate"}
                self.assertEqual(M.deterministic_check(claim, SOURCES)["verdict"], expected)

    def test_mass_requires_full_value_and_correct_case_locator(self):
        for value, locator in (("2222 kg; cleared for dispatch", "SB-PC-02#payload"), ("2222 kg", "SB-PC-01#payload"), ("2222 kg", None), ("2266 kg", "SB-PC-02#payload-s14")):
            with self.subTest(value=value, locator=locator):
                self.assertTrue(M.deterministic_check({**ORIGINAL[5], "value": value, "locator": locator}, SOURCES)["hold"])
        self.assertFalse(M.deterministic_check(ORIGINAL[5], SOURCES)["hold"])

    def test_extracts_cannot_drop_qualifications_or_change_vehicle(self):
        shortened = {**ORIGINAL[4], "value": "19:05 UTC"}
        self.assertTrue(M.deterministic_check(shortened, SOURCES)["hold"])
        self.assertTrue(M.deterministic_check(ORIGINAL[3], SOURCES)["hold"])
        self.assertFalse(M.deterministic_check(corrected_claims()[3], SOURCES)["hold"])

    def test_claim_coverage_types_and_identities_are_fixed(self):
        examples = []
        for field, value in (("case_id", "PC-02"), ("kind", "gate"), ("value", 2233), ("locator", "SB-PC-01#payload")):
            claims = corrected_claims()
            claims[0][field] = value
            examples.append(claims)
        duplicate = corrected_claims()
        duplicate[1] = copy.deepcopy(duplicate[0])
        examples.extend([duplicate, corrected_claims()[:-1]])
        extra = corrected_claims()
        extra[0]["released"] = True
        examples.append(extra)
        for claims in examples:
            with self.subTest(claims=claims), self.assertRaises(ValueError):
                M.validate_claims({"schema": "m08-correction-v1", "claims": claims}, SOURCES, "m08-correction-v1")
        self.assertEqual(len(M.validate_claims({"schema": "m08-correction-v1", "claims": corrected_claims()}, SOURCES, "m08-correction-v1")), 7)

    def test_review_requires_exact_per_case_evidence_and_full_coverage(self):
        valid = review_document(corrected_claims())
        M.validate_review(valid, corrected_claims(), SOURCES)
        modifications = [
            {"locator": "SB-PC-02#payload", "quote": SOURCES["PC-02"]["SB-PC-02#payload"]["text"]},
            {"quote": "This source authorizes dispatch."}, {"quote": None},
            {"locator": None, "quote": None}, {"reason": " "}, {"approved": True},
        ]
        for change in modifications:
            bad = copy.deepcopy(valid)
            bad["answers"][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                M.validate_review(bad, corrected_claims(), SOURCES)
        bad = copy.deepcopy(valid)
        bad["answers"][1] = copy.deepcopy(bad["answers"][0])
        with self.assertRaises(ValueError):
            M.validate_review(bad, corrected_claims(), SOURCES)

    def test_json_rejects_wrappers_duplicate_keys_and_nonfinite_numbers(self):
        for value in ('```json\n{}\n```', '{"schema":"a","schema":"b"}', '{"value":NaN}', '{} trailing'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                M.strict_json(value)

    def test_sources_reject_boolean_mass_false_authority_and_text_mismatch(self):
        for mutation in ("mass", "authority", "text", "empty"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                case = Path(temp) / "case"
                shutil.copytree(ROOT / "shared/case", case)
                path = case / "PC-01/sources.json"
                data = json.loads(path.read_text())
                record = data["sources"]["SB-PC-01#payload"]
                if mutation == "mass":
                    record["payload_kg"] = True
                elif mutation == "authority":
                    data["sources"]["SB-PC-01#near-clinic"]["authoritative"] = True
                elif mutation == "text":
                    record["text"] = "The load is 12211 kg, not the stated value."
                else:
                    record["text"] = ""
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    M.load_sources_strict(case)


class AttemptBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m08-offline-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.work, self.attempt = self.base / "work", self.base / "attempt"
        shutil.copytree(ROOT / "shared/case", self.work / "shared/case")
        shutil.copytree(ROOT / "shared/controls", self.work / "shared/controls")
        M.freeze(self.work, self.attempt)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts/hallucination.py"), *map(str, args)], capture_output=True, text=True,
                              env={**os.environ, "OPENROUTER_API_KEY": ""}, timeout=30)

    def test_no_key_creates_no_model_attempt(self):
        before = M.inventory(self.attempt)
        result = self.cli("review", "--attempt", self.attempt, "--reviewer", "source", "--phase", "before")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OPENROUTER_API_KEY unavailable", result.stderr)
        self.assertEqual(M.inventory(self.attempt), before)

    def test_existing_attempt_and_overlapping_paths_preserve_files(self):
        before = M.inventory(self.attempt)
        with self.assertRaises(ValueError):
            M.freeze(self.work, self.attempt)
        with self.assertRaises(ValueError):
            M.freeze(self.work, self.work / "nested-evidence")
        self.assertEqual(M.inventory(self.attempt), before)
        self.assertFalse((self.work / "nested-evidence").exists())

    def test_source_control_and_check_drift_are_rejected(self):
        for relative in ("frozen/case/PC-01/sources.json", "frozen/controls/review-source.txt", "initial-checks.json"):
            path = self.attempt / relative
            original = path.read_bytes()
            path.write_bytes(original + b" ")
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                M.frozen_attempt(self.attempt)
            path.write_bytes(original)

    def test_sparse_manifest_cannot_exclude_a_changed_source(self):
        manifest = self.attempt / "frozen/manifest.json"
        data = json.loads(manifest.read_text())
        del data["sha256"]["case/PC-03/sources.json"]
        manifest.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            M.frozen_attempt(self.attempt)

    def test_fabricated_parsed_results_cannot_establish_five_real_runs(self):
        review = review_document(corrected_claims())
        for phase in ("before", "after"):
            for role in ("source", "skeptic"):
                M.save(self.attempt / "reviews" / f"{phase}-{role}.json", M.encoded(review))
        M.save(self.attempt / "correction.json", M.encoded({"schema": "m08-correction-v1", "claims": corrected_claims()}))
        result = self.cli("report", "--attempt", self.attempt)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.attempt / "report.json").exists())
        self.assertFalse((self.attempt / "human-decision.json").exists())

    def test_report_does_not_overwrite_a_human_decision(self):
        decision = self.attempt / "human-decision.json"
        decision.write_text('human decision: retain the hold\n')
        result = self.cli("report", "--attempt", self.attempt)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(decision.read_text(), 'human decision: retain the hold\n')

    def test_blind_roots_exclude_other_reviews_and_findings(self):
        bundle = M.frozen_attempt(self.attempt)
        before = M.stage_inputs(bundle, "before-source", {})
        self.assertEqual(set(before), {"claims.json", "schema.json", "case/PC-01/sources.json", "case/PC-02/sources.json", "case/PC-03/sources.json"})
        after = M.stage_inputs(bundle, "after-source", {"correct": {"data": {"claims": corrected_claims()}}})
        self.assertEqual(set(after), set(before))
        self.assertEqual(json.loads(after["claims.json"])["claims"], corrected_claims())
        self.assertEqual(before["case/PC-03/sources.json"], after["case/PC-03/sources.json"])


if __name__ == "__main__":
    unittest.main()
