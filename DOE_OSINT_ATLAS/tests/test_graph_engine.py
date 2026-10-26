# tests/test_graph_engine.py
import tempfile
import os
import pytest
from backend.build_graph import build_graph
from backend.graph_engine import GraphEngine

@pytest.fixture
def graph_engine(sample_db):
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        pkl_path = f.name
    build_graph(sample_db, pkl_path)
    engine = GraphEngine(pkl_path)
    yield engine
    os.unlink(pkl_path)
    meta_path = pkl_path.replace(".pkl", "_meta.json")
    if os.path.exists(meta_path):
        os.unlink(meta_path)

def test_load_graph(graph_engine):
    assert graph_engine.node_count > 0
    assert graph_engine.edge_count > 0

def test_get_subgraph(graph_engine):
    subgraph = graph_engine.get_subgraph("recipient:Sandia National Labs", hops=1)
    assert len(subgraph["nodes"]) > 1  # Sandia + connected nodes
    assert len(subgraph["edges"]) > 0
    node_names = [n["name"] for n in subgraph["nodes"]]
    assert "recipient:Sandia National Labs" in node_names

def test_search_nodes(graph_engine):
    results = graph_engine.search_nodes("Sandia")
    assert len(results) > 0
    assert any("Sandia" in r["label"] for r in results)

def test_get_communities(graph_engine):
    communities = graph_engine.get_communities()
    assert len(communities) > 0
    assert all("id" in c and "node_count" in c for c in communities)

def test_get_neighbors(graph_engine):
    neighbors = graph_engine.get_neighbors("recipient:Sandia National Labs")
    assert len(neighbors) > 0
    # Should include PSC and NAICS nodes connected to Sandia
    types = {n["type"] for n in neighbors}
    assert "psc" in types or "naics" in types
