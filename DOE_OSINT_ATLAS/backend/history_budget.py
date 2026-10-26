# backend/history_budget.py
"""Token-budgeted conversation history.

Replaces the legacy 6-turn / 500-char cap with a budget that keeps the most
recent messages whose total estimated tokens fit under target_tokens.

Token estimation is intentionally rough — we use len(content) // 4 + 10 per
message, which slightly overestimates for English (good — we want to under-fill
rather than overflow).
"""


def _est_tokens(msg: dict) -> int:
    content = msg.get("content", "") or ""
    return len(content) // 4 + 10


def budget_history(messages: list[dict], target_tokens: int = 8000) -> list[dict]:
    """Return the longest tail of `messages` whose total tokens fit under target.

    Walks backwards from the newest message, including each one until adding
    the next would exceed target_tokens. The returned list preserves the
    original message order (oldest of the kept slice first).

    Args:
        messages: list of {"role": ..., "content": ...} dicts
        target_tokens: budget in estimated tokens (default 8000)

    Returns:
        Subset of messages, in original order, with content UNCHANGED.
    """
    if not messages:
        return []

    kept_reversed: list[dict] = []
    used = 0
    for msg in reversed(messages):
        est = _est_tokens(msg)
        if kept_reversed and used + est > target_tokens:
            break
        kept_reversed.append(msg)
        used += est

    return list(reversed(kept_reversed))
