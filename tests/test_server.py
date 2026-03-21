# tests/test_server.py
import tempfile
import os
import pytest
from fastapi.testclient import TestClient
from backend.build_graph import build_graph
from backend.setup_fts import ensure_fts5

@pytest.fixture
def app_client(sample_db):
    """Create test FastAPI app with sample data."""
    ensure_fts5(sample_db)
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        pkl_path = f.name
    build_graph(sample_db, pkl_path)

    os.environ["DB_PATH"] = sample_db
    os.environ["GRAPH_PATH"] = pkl_path
    os.environ["CHROMA_PATH"] = ""  # Skip in tests
    os.environ["STATIC_DIR"] = ""  # Skip in tests

    from backend.server import create_app
    app = create_app()
    with TestClient(app) as client:
        yield client

    os.unlink(pkl_path)
    meta_path = pkl_path.replace(".pkl", "_meta.json")
    if os.path.exists(meta_path):
        os.unlink(meta_path)

def test_health(app_client):
    resp = app_client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ready", "starting")

def test_graph_endpoint(app_client):
    resp = app_client.get("/api/graph?entity=recipient:Sandia National Labs&hops=1")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0

def test_search_endpoint(app_client):
    resp = app_client.get("/api/search?q=electrolyte&mode=keyword")
    assert resp.status_code == 200
    data = resp.json()
    assert "contracts" in data

def test_communities_endpoint(app_client):
    resp = app_client.get("/api/communities")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

def test_stats_endpoint(app_client):
    resp = app_client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "node_count" in data
