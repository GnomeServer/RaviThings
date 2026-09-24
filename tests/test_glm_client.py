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
