# tests/test_history_budget.py
from backend.history_budget import budget_history


def test_budget_returns_all_when_under_budget():
    messages = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    out = budget_history(messages, target_tokens=1000)
    assert out == messages


def test_budget_drops_oldest_when_over():
    # 30 messages × ~100 chars each = ~750 tokens. Budget 200 → should keep ~6.
    messages = [
        {"role": "user" if i % 2 == 0 else "assistant",
         "content": f"This is message number {i:03d} " * 4}  # ~100 chars
        for i in range(30)
    ]
    out = budget_history(messages, target_tokens=200)
    assert len(out) < len(messages)
    assert len(out) > 0
    # Most recent message must always be included
    assert out[-1] == messages[-1]
    # Order must be preserved (oldest dropped, not interleaved)
    for i in range(len(out) - 1):
        original_idx = messages.index(out[i])
        next_idx = messages.index(out[i + 1])
        assert next_idx == original_idx + 1


def test_budget_preserves_content_unchanged():
    """Message content must NOT be truncated by budget_history."""
    long_msg = {"role": "user", "content": "x" * 5000}
    out = budget_history([long_msg], target_tokens=10000)
    assert out[0]["content"] == "x" * 5000


def test_budget_handles_empty_messages():
    assert budget_history([], target_tokens=1000) == []
