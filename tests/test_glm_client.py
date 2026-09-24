import json

import pytest

from backend.glm_client import parse_structured_message


def test_parse_structured_message_rejects_null_content():
    """GLM-5.3 returns content=null when reasoning consumes max_tokens.

    json.loads(None) is the production TypeError. Fail with a clear error
    instead of letting that leak into the intent router.
    """
    with pytest.raises(ValueError, match="content empty"):
        parse_structured_message({"role": "assistant", "content": None, "reasoning": "..."})


def test_parse_structured_message_parses_json_object():
    payload = {"intent": "aggregate", "confidence": 0.9}
    assert parse_structured_message({"content": json.dumps(payload)}) == payload


def test_message_text_rejects_null_content():
    from backend.glm_client import message_text

    with pytest.raises(ValueError, match="empty content"):
        message_text({"content": None}, finish_reason="length")


def test_completion_body_omits_token_cap():
    from backend.glm_client import GLMClient

    body = GLMClient(api_key="test")._completion_body(
        [{"role": "user", "content": "analyze"}],
        None,
        stream=False,
        reasoning_effort="low",
    )
    assert "max_tokens" not in body
    assert body["reasoning"] == {"effort": "low"}


def test_completion_body_keeps_explicit_cap():
    from backend.glm_client import GLMClient

    body = GLMClient(api_key="test")._completion_body(
        [{"role": "user", "content": "hi"}],
        4096,
        stream=False,
    )
    assert body["max_tokens"] == 4096
