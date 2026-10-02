"""Provider progress contracts: real SSE boundaries, privacy and fallback identity."""
import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.glm_client import GLMClient
from backend.kill_chain import generate_kill_chain, generate_step_detail


def event(value):
    return "data:" + json.dumps(value, ensure_ascii=False) + "\r\n\r\n"


def delta(text=None, **fields):
    return event({"choices": [{"delta": {"content": text, **fields}}]})


def ending(reason="stop"):
    return event({"choices": [{"delta": {}, "finish_reason": reason}]}) + "data: [DONE]\n\n"


class FragmentedStream(httpx.AsyncByteStream):
    """Split UTF-8 and SSE delimiters across transport reads."""
    def __init__(self, text):
        self.data = text.encode("utf-8")
        self.closed = False

    async def __aiter__(self):
        for offset in range(0, len(self.data), 3):
            yield self.data[offset:offset + 3]

    async def aclose(self):
        self.closed = True


@pytest.fixture
def provider(monkeypatch):
    original = httpx.AsyncClient
    requests = []
    streams = []
    replies = []

    def respond(request):
        requests.append(json.loads(request.content))
        reply = replies.pop(0)
        if isinstance(reply, dict):
            return httpx.Response(200, json=reply)
        stream = FragmentedStream(reply)
        streams.append(stream)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=stream)

    monkeypatch.setattr(
        "backend.glm_client.httpx.AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs),
    )
    return replies, requests, streams


def test_structured_progress_preserves_body_and_only_exposes_visible_text(provider, monkeypatch):
    replies, requests, streams = provider
    events = []
    monkeypatch.setattr("backend.glm_client.time.monotonic", lambda: 1.0)
    raw = '{"answer":"é🛰"}'
    replies.append(
        ": keepalive private text\n\n"
        + delta(reasoning="PRIVATE", reasoning_details=[{"text": "SECRET"}])
        + delta(raw[:2]) + delta(raw[2:7]) + delta(raw[7:])
        + event({"choices": [], "usage": {"completion_tokens": 900}})
        + ending()
    )
    client = GLMClient("credential", on_progress=events.append)
    schema = {"type": "object", "properties": {"answer": {"type": "string"}}}
    messages = [{"role": "user", "content": "PRIVATE PROMPT"}]
    result = asyncio.run(client.chat_structured(messages, schema, max_tokens=123, reasoning_effort="low"))
    assert result == {"answer": "é🛰"}
    assert requests == [{
        "model": client.model, "messages": messages, "stream": True, "max_tokens": 123,
        "reasoning": {"effort": "low"},
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "structured_output", "strict": True, "schema": schema,
        }},
    }]
    updates = [e for e in events if e["type"] == "delta"]
    assert "".join(e["text"] for e in updates) == raw
    assert [e["characters"] for e in updates] == [2, len(raw)]
    assert len([e for e in events if e["type"] == "activity"]) == 2
    assert [e["stage"] for e in events if e["type"] == "stage"] == [
        "connecting", "waiting", "streaming", "parsing",
    ]
    serialized = json.dumps(events)
    for private in ("PRIVATE", "SECRET", "credential", "completion_tokens", "reasoning"):
        assert private not in serialized
    assert all(e["type"] in {"stage", "activity", "delta"} for e in events)
    assert streams[0].closed


@pytest.mark.parametrize("tail", [
    "",  # EOF after valid-looking JSON
    "data: [DONE]\n\n",  # No finish choice
    event({"choices": [{"delta": {}, "finish_reason": "stop"}]}),  # Missing DONE
    ending("length"),
    ending("content_filter"),
    event({"error": {"message": "PRIVATE provider error", "code": 500}}) + ending(),
    event({"choices": [{"error": {"message": "PRIVATE"}}]}) + ending(),
    "data: broken PRIVATE JSON\n\n" + ending(),
    "data: []\n\n" + ending(),
    "event: error\ndata: {\"message\":\"PRIVATE\"}\n\n" + ending(),
    event({"unexpected": "PRIVATE"}) + ending(),
])
def test_stream_errors_and_truncation_cannot_become_success(provider, tail):
    replies, _, streams = provider
    events = []
    replies.append(delta('{"complete":true}') + tail)
    with pytest.raises(ValueError) as exc:
        asyncio.run(GLMClient("key", on_progress=events.append).chat_structured([], {}))
    assert "PRIVATE" not in str(exc.value)
    assert "PRIVATE" not in json.dumps(events)
    assert streams[0].closed


def test_reasoning_only_is_activity_but_empty_answer_fails(provider):
    replies, _, _ = provider
    events = []
    replies.append(": keepalive\n\n" + delta(reasoning="PRIVATE") + ending())
    with pytest.raises(ValueError, match="empty content"):
        asyncio.run(GLMClient("key", on_progress=events.append).chat([]))
    assert any(e["type"] == "activity" for e in events)
    assert not any(e["type"] == "delta" for e in events)
    assert "PRIVATE" not in json.dumps(events)


def test_multiline_sse_and_uncapped_chat_settings(provider):
    replies, requests, _ = provider
    replies.append('data: {"choices":\n' + 'data: [{"delta":{"content":"answer"}}]}\n\n' + ending())
    result = asyncio.run(GLMClient("key", on_progress=lambda _: None).chat([], max_tokens=None))
    assert result == "answer"
    assert "max_tokens" not in requests[0]
    assert requests[0]["reasoning"] == {"effort": "low"}


def test_no_progress_callers_keep_nonstreaming_contract(provider):
    replies, requests, _ = provider
    replies.extend([
        {"choices": [{"message": {"content": "answer"}, "finish_reason": "stop"}]},
        {"choices": [{"message": {"content": '{"answer":true}'}, "finish_reason": "stop"}]},
    ])
    client = GLMClient("key")
    assert asyncio.run(client.chat([])) == "answer"
    assert asyncio.run(client.chat_structured([], {})) == {"answer": True}
    assert all(body["stream"] is False for body in requests)


def intel():
    return {
        "name": "Example", "city": "", "state": "", "domain": "", "category": "",
        "obligation": 0, "dmarc": "", "web_score": 100, "onprem_count": 0,
        "services_count": 0, "vulns_count": 0, "ssl_issues_count": 0, "os_list": [],
        "vectors": [], "all_services": [], "all_vulns": [],
    }


@pytest.mark.parametrize("first_finish", ["length", "stop"])
def test_fallback_starts_new_attempt_resets_count_and_retains_verification(provider, monkeypatch, first_finish):
    replies, requests, _ = provider
    events = []
    answer = {"summary": "done", "risk_level": "low", "steps": [], "remediation": []}
    raw = json.dumps(answer)
    replies.extend([
        delta("discard this incomplete attempt") + ending(first_finish),
        delta(raw) + ending(),
    ])
    verified = {**answer, "jev": {"unavailable": True}}
    verify = AsyncMock(return_value=verified)
    monkeypatch.setattr("backend.kill_chain.verify_kill_chain", verify)
    client = GLMClient("key", on_progress=events.append)
    result = asyncio.run(generate_kill_chain(client, intel(), on_progress=events.append))
    assert result == verified
    verify.assert_awaited_once_with(answer, intel())
    starts = [e for e in events if e.get("stage") == "connecting"]
    assert [e["attempt"] for e in starts] == [1, 2]
    assert [e["characters"] for e in events if e["type"] == "delta"] == [
        len("discard this incomplete attempt"), len(raw),
    ]
    assert events[0]["stage"] == "preparing"
    assert events[-1]["stage"] == "verifying"
    assert "response_format" in requests[0] and "response_format" not in requests[1]


def test_step_detail_stream_keeps_salvage_and_reports_parsing(provider):
    replies, requests, _ = provider
    events = []
    answer = {"vulnerability": {"description": "defensive analysis"}}
    replies.append(delta("```json\n" + json.dumps(answer) + "\n```") + ending())
    result = asyncio.run(generate_step_detail(
        GLMClient("key", on_progress=events.append), intel(), {}, on_progress=events.append,
    ))
    assert result == answer
    assert events[0]["stage"] == "preparing"
    assert events[-1]["stage"] == "parsing"
    assert "max_tokens" not in requests[0]
    assert requests[0]["reasoning"] == {"effort": "low"}


def test_step_detail_truncated_json_is_error_not_salvaged_success(provider):
    replies, _, _ = provider
    replies.append(delta('{"vulnerability":{"description":"looks complete"}}'))
    result = asyncio.run(generate_step_detail(GLMClient("key", on_progress=lambda _: None), intel(), {}))
    assert "error" in result
    assert "ended before completion" in result["error"]


def test_buffered_output_flushes_while_provider_pauses(monkeypatch):
    """Provider deliberately waits for the buffered progress to reach the UI."""
    original = httpx.AsyncClient
    events = []

    async def scenario():
        flushed = asyncio.Event()

        def progress(frame):
            events.append(frame)
            if frame["type"] == "delta" and frame["characters"] == 2:
                flushed.set()

        class PausedStream(httpx.AsyncByteStream):
            async def __aiter__(self):
                yield delta("a").encode()
                yield delta("b").encode()
                await asyncio.wait_for(flushed.wait(), timeout=1.0)
                yield ending().encode()

        def respond(request):
            return httpx.Response(200, stream=PausedStream())

        monkeypatch.setattr(
            "backend.glm_client.httpx.AsyncClient",
            lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs),
        )
        assert await GLMClient("key", on_progress=progress).chat([]) == "ab"

    asyncio.run(scenario())
    assert [e["text"] for e in events if e["type"] == "delta"] == ["a", "b"]


@pytest.mark.parametrize("failure", ["provider", "length", "transport", "cancel"])
@pytest.mark.parametrize("callback_raises", [False, True])
def test_buffered_progress_flushes_on_failure_preserving_original_error(monkeypatch, failure, callback_raises):
    original = httpx.AsyncClient
    events = []
    monkeypatch.setattr("backend.glm_client.time.monotonic", lambda: 1.0)
    transport_error = httpx.ReadError("transport interrupted")

    async def scenario():
        received = asyncio.Event()

        def progress(frame):
            events.append(frame)
            if callback_raises and frame["type"] == "delta" and frame["characters"] == 2:
                raise RuntimeError("cleanup callback failed")

        class FailingStream(httpx.AsyncByteStream):
            closed = False

            async def __aiter__(self):
                yield delta("a").encode()
                yield delta("b", reasoning="PRIVATE").encode()
                # Both frames have been consumed, but the throttle still holds b.
                assert [e["text"] for e in events if e["type"] == "delta"] == ["a"]
                received.set()
                if failure == "provider":
                    yield event({"error": {"message": "PRIVATE"}}).encode()
                elif failure == "length":
                    yield ending("length").encode()
                elif failure == "transport":
                    raise transport_error
                else:
                    await asyncio.Future()

            async def aclose(self):
                self.closed = True

        stream = FailingStream()
        monkeypatch.setattr(
            "backend.glm_client.httpx.AsyncClient",
            lambda **kwargs: original(
                transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=stream)),
                **kwargs,
            ),
        )
        task = asyncio.create_task(GLMClient("key", on_progress=progress).chat_structured([], {}))
        if failure == "cancel":
            await received.wait()
            task.cancel()
        error_type, message = {
            "provider": (ValueError, "Model stream reported an error"),
            "length": (ValueError, "Model stream did not finish normally"),
            "transport": (httpx.ReadError, "transport interrupted"),
            "cancel": (asyncio.CancelledError, None),
        }[failure]
        with pytest.raises(error_type, match=message) as exc:
            await task
        if failure == "transport":
            assert exc.value is transport_error
        assert stream.closed

    asyncio.run(scenario())
    updates = [e for e in events if e["type"] == "delta"]
    assert [e["text"] for e in updates] == ["a", "b"]
    assert [e["characters"] for e in updates] == [1, 2]
    assert len([e for e in events if e["type"] == "activity"]) == 2
    assert [e["stage"] for e in events if e["type"] == "stage"] == [
        "connecting", "waiting", "streaming",
    ]
    assert all(e["type"] in {"stage", "activity", "delta"} for e in events)
    assert "PRIVATE" not in json.dumps(events)
