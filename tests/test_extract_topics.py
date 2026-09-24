# tests/test_extract_topics.py
import tempfile
import os
import sqlite3
import json
import pytest
from unittest.mock import AsyncMock
from backend.extract_topics import create_topics_db, extract_topics_batch

def test_create_topics_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    try:
        create_topics_db(path)
        conn = sqlite3.connect(path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "topics" in table_names
        assert "topic_contracts" in table_names
        conn.close()
    finally:
        os.unlink(path)

@pytest.mark.asyncio
async def test_extract_topics_batch(sample_db):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        topics_path = f.name
    try:
        create_topics_db(topics_path)
        mock_ollama = AsyncMock()
        mock_ollama.generate.return_value = json.dumps([
            {"topic": "solid electrolyte fabrication", "description": "Making solid electrolytes"},
            {"topic": "ceramic characterization", "description": "Testing ceramics"}
        ])
        stats = await extract_topics_batch(
            db_path=sample_db,
            topics_db_path=topics_path,
            llm=mock_ollama,
            batch_size=5,
            limit=5,
        )
        assert stats["processed"] > 0
        assert stats["topics_created"] > 0
        conn = sqlite3.connect(topics_path)
        topics = conn.execute("SELECT * FROM topics").fetchall()
        assert len(topics) > 0
        conn.close()
    finally:
        os.unlink(topics_path)
