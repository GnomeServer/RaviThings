# tests/test_recipe_engine.py
import pytest
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from backend.recipe_engine import RecipeEngine
from backend.hybrid_retriever import HybridResults, ContractResult


async def _fake_chat_stream(messages):
    """Async generator that yields fake tokens for testing."""
    for token in ["1. Electrolyte ", "fabrication ", "by Sandia\n", "2. Electrode ", "assembly"]:
        yield token


@pytest.fixture
def mock_retriever():
    """Mock retriever that returns canned results."""
    mock = MagicMock()
    mock.search.return_value = HybridResults(
        contracts=[
            ContractResult(
                key="KEY001", description="Solid electrolyte fabrication",
                recipient="Sandia", obligation=1000000, fiscal_year=2024,
                psc="R&D", naics="Physical Sciences", sources=["keyword"],
            ),
        ],
        retrieval_counts={"vector": 0, "keyword": 1, "graph": 0},
        graph_paths={"nodes": [], "edges": []},
    )
    return mock


@pytest.fixture
def mock_ollama():
    """Mock Ollama client."""
    mock = AsyncMock()
    mock.generate.return_value = '["solid electrolyte fabrication", "electrode manufacturing"]'
    mock.chat_stream = _fake_chat_stream
    return mock


@pytest.mark.asyncio
async def test_decompose_generates_sub_queries(mock_ollama, mock_retriever):
    engine = RecipeEngine(ollama=mock_ollama, retriever=mock_retriever)
    events = []
    async for event in engine.synthesize("How do you make batteries?"):
        events.append(event)
    phase_events = [e for e in events if e["event"] == "phase"]
    assert len(phase_events) >= 1
    assert phase_events[0]["data"]["phase"] == "decompose"


@pytest.mark.asyncio
async def test_synthesize_emits_done(mock_ollama, mock_retriever):
    engine = RecipeEngine(ollama=mock_ollama, retriever=mock_retriever)
    events = []
    async for event in engine.synthesize("How do you make batteries?"):
        events.append(event)
    done_events = [e for e in events if e["event"] == "done"]
    assert len(done_events) == 1


@pytest.mark.asyncio
async def test_synthesize_emits_round_events(mock_ollama, mock_retriever):
    engine = RecipeEngine(ollama=mock_ollama, retriever=mock_retriever)
    events = []
    async for event in engine.synthesize("How do you make batteries?"):
        events.append(event)
    round_events = [e for e in events if e["event"] == "round"]
    assert len(round_events) >= 1
    assert round_events[0]["data"]["round"] == 1


@pytest.mark.asyncio
async def test_synthesize_emits_token_events(mock_ollama, mock_retriever):
    engine = RecipeEngine(ollama=mock_ollama, retriever=mock_retriever)
    events = []
    async for event in engine.synthesize("How do you make batteries?"):
        events.append(event)
    token_events = [e for e in events if e["event"] == "token"]
    assert len(token_events) >= 1
    # Verify tokens contain content
    for te in token_events:
        assert "content" in te["data"]


@pytest.mark.asyncio
async def test_synthesize_emits_recipe_steps(mock_ollama, mock_retriever):
    engine = RecipeEngine(ollama=mock_ollama, retriever=mock_retriever)
    events = []
    async for event in engine.synthesize("How do you make batteries?"):
        events.append(event)
    step_events = [e for e in events if e["event"] == "recipe_step"]
    assert len(step_events) >= 1
    # Each step should have the expected keys
    for se in step_events:
        assert "step" in se["data"]
        assert "name" in se["data"]
        assert "who" in se["data"]


@pytest.mark.asyncio
async def test_done_event_has_steps_and_confidence(mock_ollama, mock_retriever):
    engine = RecipeEngine(ollama=mock_ollama, retriever=mock_retriever)
    events = []
    async for event in engine.synthesize("How do you make batteries?"):
        events.append(event)
    done_events = [e for e in events if e["event"] == "done"]
    assert len(done_events) == 1
    done_data = done_events[0]["data"]
    assert "steps" in done_data
    assert "confidence" in done_data
    assert done_data["confidence"] in ("low", "medium", "high")
    assert "total_contracts" in done_data
    assert "total_dollars" in done_data


@pytest.mark.asyncio
async def test_converged_event_emitted(mock_ollama, mock_retriever):
    engine = RecipeEngine(ollama=mock_ollama, retriever=mock_retriever)
    events = []
    async for event in engine.synthesize("How do you make batteries?"):
        events.append(event)
    converged_events = [e for e in events if e["event"] == "converged"]
    assert len(converged_events) == 1
    assert "total_contracts" in converged_events[0]["data"]


@pytest.mark.asyncio
async def test_fallback_when_llm_returns_invalid_json(mock_retriever):
    """When LLM returns non-JSON, engine should fall back to original query."""
    mock_ollama = AsyncMock()
    mock_ollama.generate.return_value = "I cannot generate a JSON array."
    mock_ollama.chat_stream = _fake_chat_stream
    engine = RecipeEngine(ollama=mock_ollama, retriever=mock_retriever)
    events = []
    async for event in engine.synthesize("How do you make batteries?"):
        events.append(event)
    # Should still complete successfully
    done_events = [e for e in events if e["event"] == "done"]
    assert len(done_events) == 1
