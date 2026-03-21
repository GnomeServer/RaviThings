# tests/test_build_graph.py
import os
import tempfile
import pytest
from backend.build_graph import build_graph

def test_build_graph_creates_pickle(sample_db):
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        output_path = f.name
    try:
        stats = build_graph(sample_db, output_path)
        assert os.path.exists(output_path)
        assert stats["recipient_count"] > 0
        assert stats["psc_count"] > 0
        assert stats["naics_count"] > 0
        assert stats["edge_count"] > 0
        assert stats["community_count"] > 0
    finally:
        os.unlink(output_path)

def test_build_graph_correct_nodes(sample_db):
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        output_path = f.name
    try:
        stats = build_graph(sample_db, output_path)
        # sample_db has 4 unique recipients, 3 unique PSC, 3 unique NAICS
        assert stats["recipient_count"] == 4  # Sandia, ORNL, PNNL, LLNL
        assert stats["psc_count"] == 3  # R&D Physical, R&D Energy, Nuclear Reactor
        assert stats["naics_count"] == 3  # Physical Sciences, Biotech, Nuclear Energy
    finally:
        os.unlink(output_path)
