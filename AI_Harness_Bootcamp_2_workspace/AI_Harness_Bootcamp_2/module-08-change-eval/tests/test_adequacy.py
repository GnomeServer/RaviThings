#!/usr/bin/env python3
"""Adversarial aggregation tests; authored judgments are not live evidence."""
import copy
import unittest

from test_module_08 import M, ORIGINAL, SOURCES, corrected_claims, review_document


def reviews_for(claims):
    return {label: review_document(claims) for label in M.STAGES if label != "correct"}


class EnsembleDecisions(unittest.TestCase):
    def test_unanimous_false_approval_cannot_defeat_a_source_fact(self):
        correction = corrected_claims()
        correction[0]["value"] = "2040 kg"
        rows = M.claim_findings(ORIGINAL, correction, SOURCES, reviews_for(correction))
        self.assertEqual(rows[0]["after"]["source"]["verdict"], "supported")
        self.assertEqual(rows[0]["after"]["skeptic"]["verdict"], "supported")
        self.assertTrue(rows[0]["content_hold"])
        self.assertEqual(rows[0]["final_deterministic"]["verdict"], "contradicted")

    def test_repair_rechecks_supported_controls_and_reports_regression(self):
        correction = corrected_claims()
        correction[5]["value"] = "9999 kg"
        rows = M.claim_findings(ORIGINAL, correction, SOURCES, reviews_for(correction))
        self.assertFalse(rows[0]["content_hold"])
        self.assertTrue(rows[5]["regression"])
        self.assertTrue(rows[5]["content_hold"])
        self.assertFalse(rows[4]["regression"])

    def test_unknown_is_usable_only_when_the_assertion_is_withdrawn(self):
        correction = corrected_claims()
        reviews = reviews_for(correction)
        retained = M.claim_findings(ORIGINAL, correction, SOURCES, reviews)[6]
        self.assertEqual(retained["final_deterministic"]["verdict"], "unknown")
        self.assertFalse(retained["content_hold"])
        correction[6]["value"] = "The shipment is released for dispatch."
        invented = M.claim_findings(ORIGINAL, correction, SOURCES, reviews)[6]
        self.assertTrue(invented["content_hold"])
        self.assertEqual(invented["final_deterministic"]["verdict"], "unknown")

    def test_disagreement_survives_a_successful_deterministic_repair(self):
        correction = corrected_claims()
        reviews = reviews_for(correction)
        reviews["after-skeptic"]["answers"][0]["verdict"] = "unknown"
        rows = M.claim_findings(ORIGINAL, correction, SOURCES, reviews)
        self.assertEqual(rows[0]["final_deterministic"]["verdict"], "supported")
        self.assertTrue(rows[0]["review_disagreement"])
        self.assertTrue(rows[0]["content_hold"])
        self.assertEqual(rows[0]["reviewers_disagreeing_with_check"], ["skeptic"])


if __name__ == "__main__":
    unittest.main()
