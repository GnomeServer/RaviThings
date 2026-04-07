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


@pytest.fixture
def fake_aggregate_chat(tmp_path, monkeypatch):
    import test_atlas_server as srv
    from backend.intent_router import IntentClassification
    from backend.sql_aggregator import ContractorRollup

    monkeypatch.setattr(srv, "_ATLAS_CHAT_LOG", tmp_path / "atlas_chat.jsonl")
    srv.SITE_PASSWORD = ""

    async def fake_classify(query, hermes, recent_history=None):
        return IntentClassification(
            intent="aggregate",
            confidence=0.95,
            search_terms=["nuclear waste"],
            filters={},
            target_contractor=None,
        )
    monkeypatch.setattr("backend.intent_router.classify_intent", fake_classify)

    fake_rollups = [
        ContractorRollup(recipient_name="HONEYWELL FED MFG", contract_count=12,
                         total_obligation=50_000_000, fiscal_years=[2024, 2025],
                         top_psc=["R&D"], top_naics=["RESEARCH"],
                         sample_descriptions=["Nuclear waste cleanup"]),
        ContractorRollup(recipient_name="LOCKHEED MARTIN", contract_count=8,
                         total_obligation=30_000_000, fiscal_years=[2024],
                         top_psc=["ENG"], top_naics=["ENGINEERING"],
                         sample_descriptions=["Nuclear cleanup support"]),
    ]
    def fake_agg(db_path, terms, filters, limit=20):
        return fake_rollups
    monkeypatch.setattr("backend.sql_aggregator.aggregate_contracts", fake_agg)

    async def fake_stream(messages, *args, **kwargs):
        for tok in ["Honeywell", " has", " 12 contracts"]:
            yield tok
    monkeypatch.setattr(srv.hermes, "is_available", lambda: True)
    monkeypatch.setattr(srv.hermes, "chat_stream", fake_stream)
    return tmp_path / "atlas_chat.jsonl"


@pytest.mark.asyncio
async def test_chat_aggregate_path_injects_rollups(fake_aggregate_chat):
    import test_atlas_server as srv
    payload = {"query": "who has contracts for nuclear waste",
               "session_id": "s2", "messages": [], "contractor_count": 2214, "data_context": ""}

    transport = ASGITransport(app=srv.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/atlas-chat", json=payload)
        assert resp.status_code == 200
        _ = resp.text

    record = json.loads(fake_aggregate_chat.read_text().strip().splitlines()[-1])
    assert record["retrieval_path"] == "sql_aggregate"
    assert record["retrieval_results_count"] == 2

    system_msg = record["full_messages"][0]
    assert "CONTRACTOR ROLLUPS" in system_msg["content"]
    assert "HONEYWELL FED MFG" in system_msg["content"]
    assert "12 contracts" in system_msg["content"]
    assert "$50,000,000" in system_msg["content"]
