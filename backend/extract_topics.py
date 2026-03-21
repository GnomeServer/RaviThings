# backend/extract_topics.py
"""Extract topics from contract descriptions using Dolphin3 via Ollama."""
import argparse
import asyncio
import json
import sqlite3
from typing import AsyncGenerator
from backend.ollama_client import OllamaClient

EXTRACT_PROMPT = """Extract 1-3 specific technical topics from this DOE contract description.
Return ONLY a JSON array of objects with "topic" (short name) and "description" (one sentence).

Description: "{description}"

Example output: [{{"topic": "garnet ceramic sintering", "description": "High-temperature sintering of LLZO garnet ceramics for solid electrolytes"}}]"""


def create_topics_db(path: str):
    """Create topics.db schema if not exists."""
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS topics (
            topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_name TEXT NOT NULL UNIQUE,
            topic_description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS topic_contracts (
            topic_id INTEGER REFERENCES topics(topic_id),
            contract_key TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            PRIMARY KEY (topic_id, contract_key)
        );
        CREATE TABLE IF NOT EXISTS extraction_log (
            contract_key TEXT PRIMARY KEY,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_topic_name ON topics(topic_name);
        CREATE INDEX IF NOT EXISTS idx_topic_contract ON topic_contracts(contract_key);
    """)
    conn.commit()
    conn.close()


async def extract_topics_batch(
    db_path: str,
    topics_db_path: str,
    ollama: OllamaClient,
    batch_size: int = 100,
    limit: int | None = None,
) -> dict:
    """Extract topics from unprocessed contract descriptions. Returns stats."""
    create_topics_db(topics_db_path)

    conn = sqlite3.connect(db_path)
    topics_conn = sqlite3.connect(topics_db_path)

    # Get already-processed keys
    processed = set(
        r[0] for r in topics_conn.execute("SELECT contract_key FROM extraction_log").fetchall()
    )

    # Get unprocessed descriptions
    rows = conn.execute(
        "SELECT contract_transaction_unique_key, transaction_description "
        "FROM contracts WHERE transaction_description IS NOT NULL"
    ).fetchall()
    conn.close()

    unprocessed = [(k, d) for k, d in rows if k not in processed]
    if limit:
        unprocessed = unprocessed[:limit]

    total_processed = 0
    total_topics = 0

    for i in range(0, len(unprocessed), batch_size):
        batch = unprocessed[i:i + batch_size]
        for key, description in batch:
            try:
                prompt = EXTRACT_PROMPT.format(description=description[:500])
                response = await ollama.generate(prompt)
                topics = json.loads(response)
                if not isinstance(topics, list):
                    topics = []
            except (json.JSONDecodeError, Exception):
                topics = []

            for t in topics:
                topic_name = t.get("topic", "").strip().lower()
                topic_desc = t.get("description", "")
                if not topic_name:
                    continue

                # Upsert topic
                topics_conn.execute(
                    "INSERT OR IGNORE INTO topics (topic_name, topic_description) VALUES (?, ?)",
                    (topic_name, topic_desc),
                )
                topic_id = topics_conn.execute(
                    "SELECT topic_id FROM topics WHERE topic_name = ?", (topic_name,)
                ).fetchone()[0]

                # Link to contract
                topics_conn.execute(
                    "INSERT OR IGNORE INTO topic_contracts (topic_id, contract_key) VALUES (?, ?)",
                    (topic_id, key),
                )
                total_topics += 1

            # Mark as processed
            topics_conn.execute(
                "INSERT OR IGNORE INTO extraction_log (contract_key) VALUES (?)", (key,)
            )
            total_processed += 1

        topics_conn.commit()

    topics_conn.close()
    return {"processed": total_processed, "topics_created": total_topics}


async def extract_topics_stream(
    db_path: str, topics_db_path: str, ollama: OllamaClient,
    batch_size: int = 100, limit: int | None = None,
) -> AsyncGenerator[dict, None]:
    """Streaming version for SSE endpoint."""
    yield {"event": "phase", "data": {"phase": "extracting"}}
    stats = await extract_topics_batch(db_path, topics_db_path, ollama, batch_size, limit)
    yield {"event": "done", "data": stats}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract topics from DOE contracts")
    parser.add_argument("--db", default="doe_contracts.db")
    parser.add_argument("--topics-db", default="topics.db")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--ollama-host", default="http://localhost:11434")
    parser.add_argument("--model", default="dolphin3")
    args = parser.parse_args()

    ollama = OllamaClient(base_url=args.ollama_host, model=args.model)
    stats = asyncio.run(extract_topics_batch(
        args.db, args.topics_db, ollama, args.batch_size, args.limit
    ))
    print(f"Extraction complete: {stats}")
