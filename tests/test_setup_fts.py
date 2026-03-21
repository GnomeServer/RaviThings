# tests/test_setup_fts.py
import sqlite3
import pytest
from backend.setup_fts import ensure_fts5, search_fts5

def test_ensure_fts5_creates_table(sample_db):
    result = ensure_fts5(sample_db)
    assert result is True
    conn = sqlite3.connect(sample_db)
    rows = conn.execute(
        "SELECT * FROM contracts_fts WHERE contracts_fts MATCH 'electrolyte'"
    ).fetchall()
    conn.close()
    assert len(rows) >= 2  # KEY001 and KEY002 mention electrolyte

def test_ensure_fts5_idempotent(sample_db):
    ensure_fts5(sample_db)
    ensure_fts5(sample_db)  # Should not raise
    conn = sqlite3.connect(sample_db)
    rows = conn.execute(
        "SELECT * FROM contracts_fts WHERE contracts_fts MATCH 'battery'"
    ).fetchall()
    conn.close()
    assert len(rows) >= 3  # KEY001, KEY002, KEY005 mention battery

def test_search_fts5_returns_keys(sample_db):
    ensure_fts5(sample_db)
    keys = search_fts5(sample_db, "nuclear reactor", limit=10)
    assert "KEY004" in keys
    assert "KEY001" not in keys  # Not about nuclear reactors
