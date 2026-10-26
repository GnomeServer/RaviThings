# tests/test_reranker.py
import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.hybrid_retriever import ContractResult
from backend.reranker import rerank


def _make_result(key, description, recipient, psc="R420", naics="541715",
                 obligation=100000.0, fiscal_year=2024, rrf_score=0.0):
    r = ContractResult(
        key=key,
        description=description,
        recipient=recipient,
        obligation=obligation,
        fiscal_year=fiscal_year,
        psc=psc,
        naics=naics,
        sources=["keyword"],
        rrf_score=rrf_score,
    )
    return r


class TestReranker(unittest.TestCase):

    def test_reranks_by_similarity(self):
        """Result most similar to query should be ranked first."""
        results = [
            _make_result("K1", "nuclear fuel rod cladding", "ACME Corp", rrf_score=0.5),
            _make_result("K2", "solar panel efficiency research", "SunTech", rrf_score=0.5),
            _make_result("K3", "wind turbine blade composites", "WindCo", rrf_score=0.5),
        ]

        # Query is about solar panels. We craft embeddings so result[1] (solar)
        # is closest to the query vector.
        query_vec = [1.0, 0.0, 0.0]
        result_vecs = [
            [0.0, 1.0, 0.0],   # K1 — orthogonal to query
            [0.9, 0.1, 0.0],   # K2 — very similar to query
            [0.0, 0.0, 1.0],   # K3 — orthogonal to query
        ]

        def mock_embed(texts):
            # First text is the query, rest are results
            return [query_vec] + result_vecs

        ranked = rerank("solar panel research", results, mock_embed, limit=10)
        self.assertEqual(ranked[0].key, "K2")
        self.assertTrue(hasattr(ranked[0], "rerank_score"))

    def test_respects_limit(self):
        """Only `limit` results should be returned."""
        results = [
            _make_result(f"K{i}", f"description {i}", f"Company{i}", rrf_score=0.1 * (i + 1))
            for i in range(5)
        ]

        dim = 4
        query_vec = [1.0, 0.0, 0.0, 0.0]
        result_vecs = [
            [float(i == j) for j in range(dim)]
            for i in range(5)
        ]

        def mock_embed(texts):
            return [query_vec] + result_vecs[:len(texts) - 1]

        ranked = rerank("test query", results, mock_embed, limit=2)
        self.assertEqual(len(ranked), 2)

    def test_handles_empty_results(self):
        """Empty input should return empty output."""
        def mock_embed(texts):
            return [[0.0, 0.0, 0.0]]

        ranked = rerank("anything", [], mock_embed, limit=10)
        self.assertEqual(ranked, [])

    def test_combines_rrf_and_similarity(self):
        """Verify the 0.4 * normalized_rrf + 0.6 * cosine_similarity weighting."""
        # Result A: high RRF (1.0), low similarity
        # Result B: low RRF (0.1), high similarity
        results = [
            _make_result("A", "unrelated topic alpha", "CorpA", rrf_score=1.0),
            _make_result("B", "exact match topic beta", "CorpB", rrf_score=0.1),
        ]

        query_vec = [1.0, 0.0]
        result_vecs = [
            [0.0, 1.0],   # A — orthogonal (cosine sim ~0)
            [1.0, 0.0],   # B — identical direction (cosine sim ~1)
        ]

        def mock_embed(texts):
            return [query_vec] + result_vecs

        ranked = rerank("exact match topic", results, mock_embed, limit=10)

        # Result A: final = 0.4 * 1.0 + 0.6 * 0.0 = 0.4
        # Result B: final = 0.4 * 0.1 + 0.6 * 1.0 = 0.64
        # So B should come first
        self.assertEqual(ranked[0].key, "B")
        self.assertEqual(ranked[1].key, "A")

        # Check approximate scores
        self.assertAlmostEqual(ranked[0].rerank_score, 0.64, places=2)
        self.assertAlmostEqual(ranked[1].rerank_score, 0.4, places=2)

    def test_preserves_contract_data(self):
        """All original ContractResult fields must survive reranking."""
        results = [
            _make_result(
                "PRESERVE1",
                "advanced battery electrolyte",
                "BattCorp",
                psc="R420",
                naics="541715",
                obligation=250000.0,
                fiscal_year=2025,
                rrf_score=0.7,
            ),
        ]

        query_vec = [1.0, 0.0, 0.0]
        result_vecs = [[0.8, 0.2, 0.0]]

        def mock_embed(texts):
            return [query_vec] + result_vecs

        ranked = rerank("battery research", results, mock_embed, limit=10)
        self.assertEqual(len(ranked), 1)
        r = ranked[0]
        self.assertEqual(r.key, "PRESERVE1")
        self.assertEqual(r.description, "advanced battery electrolyte")
        self.assertEqual(r.recipient, "BattCorp")
        self.assertEqual(r.psc, "R420")
        self.assertEqual(r.naics, "541715")
        self.assertAlmostEqual(r.obligation, 250000.0)
        self.assertEqual(r.fiscal_year, 2025)
        self.assertEqual(r.sources, ["keyword"])
        self.assertAlmostEqual(r.rrf_score, 0.7)
        self.assertTrue(hasattr(r, "rerank_score"))


if __name__ == "__main__":
    unittest.main()
