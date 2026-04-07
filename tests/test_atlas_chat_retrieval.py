import json
import pytest
from dataclasses import dataclass
from httpx import ASGITransport, AsyncClient
from unittest.mock import MagicMock


@dataclass
class StubContract:
    key: str
    description: str
    recipient: str
    obligation: float
    fiscal_year: int = 2025
    psc: str = ""
    naics: str = ""
    sources: list = None
    rrf_score: float = 0.5


@dataclass
class StubResults:
    contracts: list
    retrieval_counts: dict = None
    graph_paths: dict = None


@pytest.fixture
def fake_retriever_chat(tmp_path, monkeypatch):
    import test_atlas_server as srv
    monkeypatch.setattr(srv, "_ATLAS_CHAT_LOG", tmp_path / "atlas_chat.jsonl")
    srv.SITE_PASSWORD = ""

    fake_results = StubResults(
        contracts=[
            StubContract(key="K1", description="Cybersecurity assessment for NNSA",
                         recipient="HONEYWELL FEDERAL MFG & TECH", obligation=12345678),
            StubContract(key="K2", description="Penetration testing services",
                         recipient="LOCKHEED MARTIN", obligation=987654),
            StubContract(key="K3", description="Network monitoring",
                         recipient="RAYTHEON", obligation=55555),
        ],
        retrieval_counts={"vector": 3, "keyword": 0, "graph": 0, "relationship": 0, "fused": 3},
        graph_paths={"nodes": [], "edges": []},
    )
    fake = MagicMock()
    fake.search.return_value = fake_results
    monkeypatch.setattr(srv, "_retriever_singleton", fake)
    monkeypatch.setattr(srv, "get_retriever", lambda: fake)

    async def fake_stream(messages, *args, **kwargs):
        for tok in ["Honeywell", " has", " contracts"]:
            yield tok

    monkeypatch.setattr(srv.hermes, "is_available", lambda: True)
    monkeypatch.setattr(srv.hermes, "chat_stream", fake_stream)

    # Mock the intent router to skip the LLM call. atlas_chat imports
    # classify_intent inside the function from backend.intent_router, so
    # monkeypatching the source module is sufficient (no aliasing).
    from backend.intent_router import IntentClassification

    async def fake_classify(query, hermes, recent_history=None):
        return IntentClassification(
            intent="entity_narrative",
            confidence=0.95,
            search_terms=["honeywell", "cybersecurity"],
            filters={},
            target_contractor="Honeywell",
        )

    monkeypatch.setattr("backend.intent_router.classify_intent", fake_classify)
    return tmp_path / "atlas_chat.jsonl"


@pytest.mark.asyncio
async def test_chat_includes_retrieval_context_in_prompt(fake_retriever_chat):
    import test_atlas_server as srv
    payload = {"query": "tell me about Honeywell's cybersecurity",
               "session_id": "s1", "messages": [], "contractor_count": 2214, "data_context": ""}

    transport = ASGITransport(app=srv.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/atlas-chat", json=payload)
        assert resp.status_code == 200
        _ = resp.text  # drain

    log_path = fake_retriever_chat
    record = json.loads(log_path.read_text().strip().splitlines()[-1])
    assert record["retrieval_path"] == "hybrid_4lane"
    assert record["retrieval_results_count"] == 3

    # The system message should contain the retrieval context
    system_msg = record["full_messages"][0]
    assert system_msg["role"] == "system"
    assert "RELEVANT CONTRACT DATA" in system_msg["content"]
    assert "HONEYWELL" in system_msg["content"]
    assert "LOCKHEED" in system_msg["content"]
    assert "Cybersecurity assessment" in system_msg["content"]
