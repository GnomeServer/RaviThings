# backend/setup_fts.py
"""Create and populate FTS5 virtual table for keyword search."""
import sqlite3
import argparse

def ensure_fts5(db_path: str) -> bool:
    """Create FTS5 virtual table if it doesn't exist. Returns True when ready."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if FTS5 table already exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='contracts_fts'"
    )
    if cursor.fetchone():
        conn.close()
        return True

    # Create FTS5 virtual table (porter tokenizer enables stemming: battery matches batteries)
    cursor.execute("""
        CREATE VIRTUAL TABLE contracts_fts USING fts5(
            contract_transaction_unique_key,
            transaction_description,
            content=contracts,
            content_rowid=rowid,
            tokenize='porter unicode61'
        )
    """)

    # Populate from contracts table
    cursor.execute("""
        INSERT INTO contracts_fts(rowid, contract_transaction_unique_key, transaction_description)
        SELECT rowid, contract_transaction_unique_key, transaction_description
        FROM contracts
        WHERE transaction_description IS NOT NULL
    """)

    conn.commit()
    conn.close()
    return True


def _sanitize_fts5_query(query: str) -> str:
    """Sanitize user input for FTS5 MATCH: strip operators, quote each term."""
    import re
    # Remove FTS5 special characters: * ? - : ^ ( ) { } " AND OR NOT NEAR
    cleaned = re.sub(r'[*?\-:^(){}"\[\]]', ' ', query)
    # Split into words, filter empties, quote each term to prevent operator interpretation
    terms = [f'"{t}"' for t in cleaned.split() if t and len(t) > 1]
    if not terms:
        return ""
    # Join with OR for broad matching
    return " OR ".join(terms)


def search_fts5(db_path: str, query: str, limit: int = 20) -> list[str]:
    """Search FTS5 and return matching contract_transaction_unique_keys."""
    sanitized = _sanitize_fts5_query(query)
    if not sanitized:
        return []
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT contract_transaction_unique_key FROM contracts_fts "
            "WHERE contracts_fts MATCH ? LIMIT ?",
            (sanitized, limit),
        ).fetchall()
    except Exception:
        # Fallback: if FTS5 still fails, return empty rather than crash
        rows = []
    conn.close()
    return [r[0] for r in rows]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up FTS5 for DOE contracts")
    parser.add_argument("--db", default="doe_contracts.db", help="Path to SQLite DB")
    args = parser.parse_args()
    print(f"Setting up FTS5 on {args.db}...")
    ensure_fts5(args.db)
    print("FTS5 ready.")
