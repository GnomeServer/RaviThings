import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.conversation_state import ConversationState, ConversationStore


def test_conversation_store_round_trips_turns():
    store = ConversationStore()
    store.append_turn("s1", "user", "hello")
    store.append_turn("s1", "assistant", "hi there")
    state = store.get_or_create("s1")
    assert state.session_id == "s1"
    assert len(state.verbatim_turns) == 2
    assert state.verbatim_turns[0]["role"] == "user"
    assert state.verbatim_turns[0]["content"] == "hello"
    assert state.verbatim_turns[1]["content"] == "hi there"
    assert state.turn_count == 2


def test_conversation_store_isolates_sessions():
    store = ConversationStore()
    store.append_turn("s1", "user", "alpha")
    store.append_turn("s2", "user", "beta")
    s1 = store.get_or_create("s1")
    s2 = store.get_or_create("s2")
    assert s1.verbatim_turns[0]["content"] == "alpha"
    assert s2.verbatim_turns[0]["content"] == "beta"


def test_conversation_store_ttl_eviction():
    store = ConversationStore(ttl_seconds=0.1)
    store.append_turn("s1", "user", "hello")
    assert "s1" in store._sessions
    time.sleep(0.15)
    store.evict_expired()
    assert "s1" not in store._sessions


def test_conversation_store_max_sessions_eviction():
    store = ConversationStore(max_sessions=2)
    store.append_turn("s1", "user", "a")
    time.sleep(0.01)
    store.append_turn("s2", "user", "b")
    time.sleep(0.01)
    store.append_turn("s3", "user", "c")  # should evict s1 (oldest)
    assert "s1" not in store._sessions
    assert "s2" in store._sessions
    assert "s3" in store._sessions


def test_get_or_create_resets_last_used():
    store = ConversationStore()
    store.append_turn("s1", "user", "hi")
    t0 = store._sessions["s1"].last_used_at
    time.sleep(0.05)
    store.get_or_create("s1")
    assert store._sessions["s1"].last_used_at > t0


# ── Task 7: rolling summary + entity tracker ─────────────────────────────

def test_extract_entities_finds_known_names():
    from backend.conversation_state import _extract_entities
    names = ["HONEYWELL FED MFG", "LOCKHEED MARTIN", "BOEING"]
    text = "I want to know about Honeywell and lockheed martin."
    found = _extract_entities(text, names)
    assert "HONEYWELL FED MFG" in found
    assert "LOCKHEED MARTIN" in found
    assert "BOEING" not in found


def test_update_entities_dedupes_and_orders_by_recency():
    store = ConversationStore()
    names = ["HONEYWELL", "LOCKHEED", "BOEING"]
    store.update_entities("s1", "user", "tell me about Honeywell", names)
    store.update_entities("s1", "user", "now lockheed", names)
    store.update_entities("s1", "user", "back to honeywell", names)
    state = store.get_or_create("s1")
    # Honeywell should be most recent (re-mentioned), Lockheed before
    assert state.entity_tracker[-1] == "HONEYWELL"
    assert "LOCKHEED" in state.entity_tracker
    # Each name appears at most once
    assert len(state.entity_tracker) == len(set(state.entity_tracker))


@pytest.mark.asyncio
async def test_maybe_summarize_triggers_above_budget():
    store = ConversationStore()
    # 30 turns × ~500 chars = ~3700 tokens — under default 8K budget, won't trigger
    # 30 turns × ~2000 chars = ~15000 tokens — over default 8K, should trigger
    long_content = "x" * 2000
    for i in range(30):
        store.append_turn("s1", "user" if i % 2 == 0 else "assistant", long_content)

    fake_llm = MagicMock()
    fake_llm.chat = AsyncMock(return_value="The user has been discussing X, Y, Z.")
    fake_llm.is_available = lambda: True

    summarized = await store.maybe_summarize("s1", fake_llm, target_tokens=8000)
    assert summarized is True

    state = store.get_or_create("s1")
    assert state.rolling_summary == "The user has been discussing X, Y, Z."
    # Older verbatim turns should be trimmed (we keep only the tail that fits)
    assert len(state.verbatim_turns) < 30


@pytest.mark.asyncio
async def test_maybe_summarize_skips_when_under_budget():
    store = ConversationStore()
    store.append_turn("s1", "user", "short")
    store.append_turn("s1", "assistant", "short")
    fake_llm = MagicMock()
    fake_llm.chat = AsyncMock()
    fake_llm.is_available = lambda: True
    summarized = await store.maybe_summarize("s1", fake_llm, target_tokens=8000)
    assert summarized is False
    fake_llm.chat.assert_not_called()
