# tests/conftest.py
import pytest
import sqlite3
import tempfile
import os

@pytest.fixture
def sample_db():
    """Create a small test SQLite DB with contract data."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.execute("""
        CREATE TABLE contracts (
            contract_transaction_unique_key TEXT PRIMARY KEY,
            award_id_piid TEXT,
            action_date TEXT,
            action_date_fiscal_year INTEGER,
            federal_action_obligation REAL,
            total_dollars_obligated REAL,
            awarding_agency_name TEXT,
            awarding_sub_agency_name TEXT,
            recipient_name TEXT,
            recipient_city_name TEXT,
            recipient_state_name TEXT,
            primary_place_of_performance_city_name TEXT,
            primary_place_of_performance_state_name TEXT,
            transaction_description TEXT,
            product_or_service_code_description TEXT,
            naics_description TEXT,
            award_type TEXT,
            extent_competed TEXT
        )
    """)
    rows = [
        ("KEY001", "AWD001", "2024-01-15", 2024, 1000000.0, 5000000.0,
         "Department of Energy", "NNSA", "Sandia National Labs",
         "Albuquerque", "New Mexico", "Albuquerque", "New Mexico",
         "Fabrication of solid electrolyte thin films for lithium-ion battery applications",
         "R&D- PHYSICAL SCIENCES", "Research and Development in Physical Sciences",
         "DELIVERY ORDER", "FULL AND OPEN COMPETITION"),
        ("KEY002", "AWD001", "2024-03-20", 2024, 2000000.0, 5000000.0,
         "Department of Energy", "NNSA", "Sandia National Labs",
         "Albuquerque", "New Mexico", "Albuquerque", "New Mexico",
         "Characterization of garnet-type ceramic electrolytes for solid state batteries",
         "R&D- PHYSICAL SCIENCES", "Research and Development in Physical Sciences",
         "DELIVERY ORDER", "FULL AND OPEN COMPETITION"),
        ("KEY003", "AWD002", "2024-06-01", 2024, 3000000.0, 3000000.0,
         "Department of Energy", "Office of Science", "Oak Ridge National Lab",
         "Oak Ridge", "Tennessee", "Oak Ridge", "Tennessee",
         "Scale-up of dry electrode manufacturing process for advanced batteries",
         "R&D- ENERGY", "Research and Development in Biotechnology",
         "CONTRACT", "FULL AND OPEN COMPETITION"),
        ("KEY004", "AWD003", "2023-09-15", 2023, 500000.0, 500000.0,
         "Department of Energy", "Office of Science", "Pacific NW National Lab",
         "Richland", "Washington", "Richland", "Washington",
         "Nuclear reactor component testing and safety analysis",
         "NUCLEAR REACTOR COMPONENTS", "Nuclear Energy Research",
         "BPA CALL", "NOT COMPETED"),
        ("KEY005", "AWD004", "2024-02-10", 2024, 1500000.0, 1500000.0,
         "Department of Energy", "NNSA", "Lawrence Livermore National Lab",
         "Livermore", "California", "Livermore", "California",
         "Sulfide glass electrolyte synthesis for next-generation batteries",
         "R&D- PHYSICAL SCIENCES", "Research and Development in Physical Sciences",
         "DELIVERY ORDER", "FULL AND OPEN COMPETITION"),
    ]
    conn.executemany(
        "INSERT INTO contracts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows
    )
    conn.commit()
    conn.close()
    yield tmp.name
    os.unlink(tmp.name)

@pytest.fixture
def ollama_base_url():
    """Return Ollama base URL from env or default."""
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434")
