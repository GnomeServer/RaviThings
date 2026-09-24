"""LLM-based intent router for the OSINT Atlas command console.

Classifies a user query into one of {aggregate, entity_narrative, action, smalltalk}
so the chat handler can dispatch to the right tool:

- aggregate       → SQL GROUP BY over doe_contracts.db (Task 4)
- entity_narrative → 4-lane HybridRetriever (Task 2)
- action          → existing MAP_CMD path (no change)
- smalltalk       → no retrieval, just chat
"""
from typing import Literal
from pydantic import BaseModel, Field

from backend.glm_client import GLMClient


class IntentClassification(BaseModel):
    intent: Literal["aggregate", "entity_narrative", "action", "smalltalk"]
    confidence: float = Field(ge=0.0, le=1.0)
    search_terms: list[str] = Field(default_factory=list)
    filters: dict = Field(default_factory=dict)
    target_contractor: str | None = None


# Hand-written JSON Schema (strict-mode compatible — additionalProperties: False
# at every level, all properties in required).
INTENT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["intent", "confidence", "search_terms", "filters", "target_contractor"],
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["aggregate", "entity_narrative", "action", "smalltalk"],
            "description": (
                "aggregate: questions like 'who has contracts for X', 'how many contractors do Y', 'list all in state Z'. "
                "entity_narrative: questions about ONE specific contractor's posture, contracts, or details. "
                "action: 'show me X on the map', 'run kill chain on Y', 'open the panel for Z'. "
                "smalltalk: greetings, thanks, off-topic chat."
            ),
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Your confidence (0-1) in the intent classification.",
        },
        "search_terms": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Key terms to search the contract database for. Extract topical terms, "
                "not stopwords. For 'who has contracts for radiation hardening', return "
                "['radiation hardening']. Empty list if no searchable terms (e.g., smalltalk)."
            ),
        },
        "filters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["state", "fiscal_year", "min_obligation"],
            "properties": {
                "state": {"type": ["string", "null"], "description": "2-letter state code or full state name, or null"},
                "fiscal_year": {"type": ["integer", "null"], "description": "fiscal year (e.g. 2025), or null"},
                "min_obligation": {"type": ["number", "null"], "description": "minimum dollar threshold, or null"},
            },
        },
        "target_contractor": {
            "type": ["string", "null"],
            "description": (
                "If the user names a specific contractor (e.g. 'Honeywell', 'Lawrence Livermore'), "
                "return its name as a string. Otherwise null. Only set for entity_narrative intent."
            ),
        },
    },
}


_INTENT_SYSTEM_PROMPT = """\
You are an intent classifier for a contractor intelligence chat system. Your job is to \
classify the user's query into ONE of four intents and extract any search terms or filters.

INTENTS:
- aggregate: The user wants a list, count, or sum across MULTIPLE contractors. Examples:
  "who has contracts for cybersecurity", "how many contractors are in California",
  "list all DOE labs", "top contractors by obligation in 2025"
- entity_narrative: The user wants details about ONE specific contractor. Examples:
  "tell me about Lawrence Livermore", "what's Honeywell's cybersecurity posture",
  "show me Boeing's contracts"
- action: The user wants the system to DO something (visualize, analyze, run a workflow):
  "show this on the map", "run a kill chain on Honeywell", "filter to Texas"
- smalltalk: greetings, thanks, off-topic chat with no information request

Extract search_terms (the topical phrases the database should be searched for) and any \
explicit filters (state, fiscal_year, min_obligation). Set target_contractor only if the \
user names a specific contractor.

Return JSON matching the strict schema. Do not add fields. Use null for missing optionals.
"""


async def classify_intent(
    query: str,
    llm: GLMClient,
    recent_history: list[dict] | None = None,
) -> IntentClassification:
    """Classify a query into one of 4 intents using GLM-5.3 structured output.

    On any failure (network, malformed JSON, etc.), returns a safe default of
    intent='entity_narrative' with confidence 0.0 — this routes the query through
    the retrieval path, which is the most generally-useful fallback.
    """
    messages = [
        {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
    ]
    if recent_history:
        # Include the last 2 turns for context resolution ("the second one" → ?)
        for msg in recent_history[-2:]:
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": (msg.get("content") or "")[:500]})
    messages.append({"role": "user", "content": query})

    try:
        raw = await llm.chat_structured(messages, INTENT_SCHEMA, max_tokens=500)
        return IntentClassification(**raw)
    except Exception as e:
        print(f"[intent_router] classification failed, defaulting to entity_narrative: {e}")
        return IntentClassification(
            intent="entity_narrative",
            confidence=0.0,
            search_terms=[],
            filters={},
            target_contractor=None,
        )
