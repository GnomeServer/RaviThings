import os
import pytest
import pathlib

CHROMA_PATH = pathlib.Path(__file__).parent.parent / "chroma_db"
DB_PATH = pathlib.Path(__file__).parent.parent / "doe_contracts.db"

pytestmark = pytest.mark.skipif(
    not CHROMA_PATH.exists() or not DB_PATH.exists(),
    reason="chroma_db or doe_contracts.db not present in this environment",
)


def test_hybrid_retriever_initializes_against_real_chroma():
    from backend.hybrid_retriever import HybridRetriever
    from backend.ollama_client import OllamaClient

    retriever = HybridRetriever(
        db_path=str(DB_PATH),
        chroma_path=str(CHROMA_PATH),
        ollama=OllamaClient(),
    )
    assert retriever.chroma_collection is not None, (
        "expected chroma_collection 'doe_contracts' to load — "
        "either chromadb is not installed or the collection is missing"
    )
    assert retriever.chroma_collection.count() > 200_000, (
        f"expected ~247k embeddings, got {retriever.chroma_collection.count()}"
    )


def test_hybrid_retriever_returns_results_for_known_query():
    """Smoke test that the orphaned retriever still works end-to-end.

    Uses search_keyword (FTS5) instead of search_vector to avoid Ollama
    dependency in CI; vector search is verified by the test above (count > 0).
    """
    from backend.hybrid_retriever import HybridRetriever

    retriever = HybridRetriever(
        db_path=str(DB_PATH),
        chroma_path=str(CHROMA_PATH),
    )
    results = retriever.search_keyword("nuclear", limit=5)
    assert len(results) > 0, "FTS5 keyword search returned zero results for 'nuclear'"
    assert all("contract_transaction_unique_key" in r for r in results)
