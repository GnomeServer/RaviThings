import time
import pytest

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
