import os
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.intent_router import (
    classify_intent,
    IntentClassification,
    INTENT_SCHEMA,
)


def test_intent_schema_is_strict_compatible():
    """The schema must satisfy OpenAI strict-mode requirements:
    - top-level type=object
    - additionalProperties: False at every object level
    - all properties listed in 'required'
    """
    assert INTENT_SCHEMA["type"] == "object"
    assert INTENT_SCHEMA.get("additionalProperties") is False
    assert set(INTENT_SCHEMA["required"]) == set(INTENT_SCHEMA["properties"].keys())


@pytest.mark.asyncio
async def test_classify_intent_aggregate():
    fake_llm = MagicMock()
    fake_llm.chat_structured = AsyncMock(return_value={
        "intent": "aggregate",
        "confidence": 0.95,
        "search_terms": ["nuclear waste"],
        "filters": {},
        "target_contractor": None,
    })
    result = await classify_intent("who has contracts for nuclear waste", fake_llm)
    assert isinstance(result, IntentClassification)
    assert result.intent == "aggregate"
    assert result.search_terms == ["nuclear waste"]
    assert result.target_contractor is None


@pytest.mark.asyncio
async def test_classify_intent_entity_narrative():
    fake_llm = MagicMock()
    fake_llm.chat_structured = AsyncMock(return_value={
        "intent": "entity_narrative",
        "confidence": 0.88,
        "search_terms": ["cybersecurity", "posture"],
        "filters": {},
        "target_contractor": "Honeywell Federal Manufacturing",
    })
    result = await classify_intent("tell me about honeywell's cybersecurity posture", fake_llm)
    assert result.intent == "entity_narrative"
    assert result.target_contractor == "Honeywell Federal Manufacturing"


@pytest.mark.asyncio
async def test_classify_intent_handles_malformed_response():
    """If the LLM returns garbage, we default to entity_narrative (the safe path
    that uses retrieval) rather than crashing."""
    fake_llm = MagicMock()
    fake_llm.chat_structured = AsyncMock(side_effect=ValueError("bad json"))
    result = await classify_intent("anything", fake_llm)
    assert result.intent == "entity_narrative"
    assert result.confidence == 0.0
