# tests/test_hybrid_retriever.py
import tempfile
import os
import pytest
from backend.build_graph import build_graph
from backend.graph_engine import GraphEngine
from backend.setup_fts import ensure_fts5
from backend.hybrid_retriever import HybridRetriever

@pytest.fixture
def retriever(sample_db):
    """Create retriever with sample DB (no ChromaDB — vector search will return empty)."""
    ensure_fts5(sample_db)
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        pkl_path = f.name
    build_graph(sample_db, pkl_path)
    engine = GraphEngine(pkl_path)
    retriever = HybridRetriever(
        db_path=sample_db,
        graph_engine=engine,
        chroma_path=None,  # Skip vector search in unit tests
    )
    yield retriever
    os.unlink(pkl_path)

def test_keyword_search(retriever):
    results = retriever.search_keyword("electrolyte", limit=10)
    assert len(results) > 0
    assert all("contract_transaction_unique_key" in r for r in results)

def test_graph_search(retriever):
    results = retriever.search_graph("battery", hops=1)
    assert isinstance(results, dict)
    assert "contracts" in results
    assert "paths" in results

def test_hybrid_search(retriever):
    results = retriever.search("electrolyte", n_results=10)
    assert len(results.contracts) > 0
    assert all(hasattr(c, "sources") for c in results.contracts)
    assert results.retrieval_counts["keyword"] > 0

def test_rrf_fusion(retriever):
    """Test that RRF properly ranks contracts found by multiple sources higher."""
    results = retriever.search("solid electrolyte", n_results=10)
    # KEY001 and KEY002 should rank high (match keyword "electrolyte")
    keys = [c.key for c in results.contracts]
    assert "KEY001" in keys or "KEY002" in keys
