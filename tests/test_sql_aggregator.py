import os
import sqlite3
import tempfile
import pytest

from backend.sql_aggregator import aggregate_contracts, ContractorRollup


@pytest.fixture
def fixture_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE contracts (
            contract_transaction_unique_key TEXT PRIMARY KEY,
            recipient_name TEXT,
            recipient_state_name TEXT,
            transaction_description TEXT,
            federal_action_obligation REAL,
            action_date_fiscal_year INTEGER,
            product_or_service_code_description TEXT,
            naics_description TEXT
        )
    """)
    rows = [
        ("K1", "HONEYWELL FED MFG", "MO", "Nuclear waste cleanup project", 5_000_000, 2024, "R&D", "RESEARCH"),
        ("K2", "HONEYWELL FED MFG", "MO", "Nuclear materials handling", 3_000_000, 2025, "R&D", "RESEARCH"),
        ("K3", "LOCKHEED MARTIN", "CA", "Nuclear cleanup support", 8_000_000, 2024, "ENG", "ENGINEERING"),
        ("K4", "BOEING", "WA", "Aircraft maintenance", 1_000_000, 2024, "MFG", "MANUFACTURING"),
        ("K5", "LOCKHEED MARTIN", "CA", "Nuclear waste containment", 2_000_000, 2025, "ENG", "ENGINEERING"),
    ]
    conn.executemany("INSERT INTO contracts VALUES (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    yield path
    os.unlink(path)


def test_aggregate_basic_search(fixture_db):
    rollups = aggregate_contracts(fixture_db, ["nuclear"], {}, limit=10)
    assert len(rollups) == 2  # Honeywell + Lockheed (Boeing has no nuclear contracts)
    # Sorted by total_obligation DESC
    assert rollups[0].recipient_name == "LOCKHEED MARTIN"
    assert rollups[0].contract_count == 2
    assert rollups[0].total_obligation == 10_000_000
    assert rollups[1].recipient_name == "HONEYWELL FED MFG"
    assert rollups[1].contract_count == 2
    assert rollups[1].total_obligation == 8_000_000


def test_aggregate_with_state_filter(fixture_db):
    rollups = aggregate_contracts(fixture_db, ["nuclear"], {"state": "CA"}, limit=10)
    assert len(rollups) == 1
    assert rollups[0].recipient_name == "LOCKHEED MARTIN"


def test_aggregate_with_fiscal_year_filter(fixture_db):
    rollups = aggregate_contracts(fixture_db, ["nuclear"], {"fiscal_year": 2024}, limit=10)
    # Only the 2024 nuclear contracts: HONEYWELL K1 ($5M), LOCKHEED K3 ($8M)
    assert len(rollups) == 2
    by_name = {r.recipient_name: r for r in rollups}
    assert by_name["LOCKHEED MARTIN"].total_obligation == 8_000_000
    assert by_name["HONEYWELL FED MFG"].total_obligation == 5_000_000


def test_aggregate_sql_injection_safe(fixture_db):
    # Even with hostile input, the LIKE pattern should be parameterized
    malicious = ["x'; DROP TABLE contracts; --"]
    rollups = aggregate_contracts(fixture_db, malicious, {}, limit=10)
    # Should return zero rows, not crash, and the table should still exist
    assert rollups == []
    conn = sqlite3.connect(fixture_db)
    cnt = conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
    assert cnt == 5  # table not dropped
    conn.close()


def test_aggregate_returns_sample_descriptions(fixture_db):
    rollups = aggregate_contracts(fixture_db, ["nuclear"], {}, limit=10)
    lockheed = next(r for r in rollups if r.recipient_name == "LOCKHEED MARTIN")
    assert len(lockheed.sample_descriptions) >= 1
    assert any("Nuclear" in s for s in lockheed.sample_descriptions)
