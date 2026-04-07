import asyncio
import json
import os
import pathlib
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def clean_log(tmp_path, monkeypatch):
    """Redirect _ATLAS_CHAT_LOG to a temp file for the test."""
    import test_atlas_server as srv
    log_path = tmp_path / "atlas_chat.jsonl"
    monkeypatch.setattr(srv, "_ATLAS_CHAT_LOG", log_path)
    yield log_path


async def _fake_stream(messages, *args, **kwargs):
    for tok in ["Hello", " ", "world"]:
        yield tok


@pytest.mark.asyncio
async def test_chat_turn_is_logged(clean_log, monkeypatch):
    import test_atlas_server as srv
    monkeypatch.setattr(srv.hermes, "is_available", lambda: True)
    monkeypatch.setattr(srv.hermes, "chat_stream", _fake_stream)

    # Mock the intent router (added in Task 3) so this test doesn't hit
    # the real Hermes API for classification — keeps the test fast and
    # CI-runnable without NOUS_API_KEY.
    from backend.intent_router import IntentClassification
    async def fake_classify(query, hermes, recent_history=None):
        return IntentClassification(
            intent="smalltalk", confidence=1.0,
            search_terms=[], filters={}, target_contractor=None,
        )
    monkeypatch.setattr("backend.intent_router.classify_intent", fake_classify)

    payload = {
        "query": "what's up",
        "messages": [],
        "contractor_count": 2214,
        "data_context": "",
        "session_id": "test-session-123",
    }

    transport = ASGITransport(app=srv.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Bypass auth
        srv.SITE_PASSWORD = ""
        resp = await client.post("/api/atlas-chat", json=payload)
        assert resp.status_code == 200
        # Drain the SSE stream
        _ = resp.text

    assert clean_log.exists(), "log file should be created"
    lines = clean_log.read_text().strip().splitlines()
    assert len(lines) == 1, f"expected 1 log line, got {len(lines)}"
    record = json.loads(lines[0])
    assert record["session_id"] == "test-session-123"
    assert record["query"] == "what's up"
    assert "Hello world" in record["response_text"]
    assert record["response_time_ms"] >= 0
    assert "full_messages" in record
    assert isinstance(record["full_messages"], list)
