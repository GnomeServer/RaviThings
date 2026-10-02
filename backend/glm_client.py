# backend/glm_client.py
"""Client for GLM-5.3 (Z.ai) via the OpenRouter OpenAI-compatible API."""
import asyncio
from contextlib import aclosing, suppress
import json
import os
import time
from typing import AsyncGenerator, Callable

import httpx


async def _lines_with_flush(response, pending_delay, flush) -> AsyncGenerator[str, None]:
    """Flush buffered *actual* output on deadline without cancelling a read."""
    lines = response.aiter_lines()
    read = None
    try:
        while True:
            if read is None:
                read = asyncio.create_task(anext(lines))
            ready, _ = await asyncio.wait({read}, timeout=pending_delay())
            if not ready:
                flush()
                continue
            completed, read = read, None
            try:
                yield completed.result()
            except StopAsyncIteration:
                break
    finally:
        if read is not None:
            read.cancel()
            with suppress(asyncio.CancelledError, StopAsyncIteration):
                await read
        await lines.aclose()


def parse_structured_message(message: dict) -> dict:
    """Return the JSON object in a completion message.

    GLM-5.3 spends output tokens on reasoning before ``content``. If that
    budget is exhausted, ``content`` is null and ``json.loads`` raises
    TypeError. Treat that as a failed structured call.
    """
    raw = message.get("content") if isinstance(message, dict) else None
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode()
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(
            "structured output content empty "
            f"(got {type(raw).__name__}); reasoning likely consumed max_tokens"
        )
    return json.loads(raw)

def message_text(message: dict, *, finish_reason: str | None = None) -> str:
    """Return visible completion text.

    GLM-5.3 can spend the whole output budget on reasoning and return
    ``content: null``. Callers must not treat that as a string.
    """
    raw = message.get("content") if isinstance(message, dict) else None
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode()
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(
            "model returned empty content "
            f"(got {type(raw).__name__}, finish_reason={finish_reason}); "
            "reasoning likely consumed max_tokens"
        )
    return raw



class GLMClient:
    """Async client for the GLM-5.3 reasoning model.

    GLM-5.3 is accessed via OpenRouter's OpenAI-compatible API at
    https://openrouter.ai/api/v1.  The API key is read from the
    ``OPENROUTER_API_KEY`` environment variable when not supplied
    explicitly.  The model slug defaults to ``z-ai/glm-5.3`` and can be
    overridden with ``OPENROUTER_MODEL``.

    GLM-5.3 is an always-on reasoning model.  Reasoning tokens arrive in
    a separate ``reasoning`` field (streamed ``delta.reasoning`` /
    non-streamed ``message.reasoning``) and are ignored here — only the
    final ``content`` is returned, so callers never see reasoning traces.
    """

    def __init__(self, api_key: str | None = None, *, on_progress: Callable[[dict], None] | None = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = os.environ.get("OPENROUTER_MODEL", "z-ai/glm-5.3")
        self.on_progress = on_progress
        self._progress_attempt = 0

    def _stage(self, stage: str, message: str, **fields) -> None:
        if self.on_progress is not None:
            self.on_progress({"type": "stage", "stage": stage, "message": message,
                              "model": self.model, **fields})

    async def _stream_completion(self, body: dict, *, timeout: float) -> str:
        """Collect visible SSE content; progress never contains provider metadata.

        A stop choice AND the SSE terminator are required. A complete-looking
        JSON prefix is not proof that a response finished successfully.
        """
        self._progress_attempt += 1
        self._stage("connecting", "Connecting to model", attempt=self._progress_attempt)
        parts: list[str] = []
        pending: list[str] = []
        characters = 0
        last_delta: float | None = None
        last_activity: float | None = None
        activity_pending = False
        streaming = False
        finish_reason = None
        done = False

        def flush_delta() -> None:
            nonlocal last_delta
            if pending and self.on_progress is not None:
                self.on_progress({"type": "delta", "text": "".join(pending),
                                  "characters": characters, "model": self.model})
                pending.clear()
                last_delta = time.monotonic()

        def pending_delay() -> float | None:
            deadlines = []
            if pending and last_delta is not None:
                deadlines.append(last_delta + 0.075)
            if activity_pending and last_activity is not None:
                deadlines.append(last_activity + 0.075)
            return max(0.0, min(deadlines) - time.monotonic()) if deadlines else None

        def flush_activity() -> None:
            nonlocal activity_pending, last_activity
            if activity_pending and self.on_progress is not None:
                self.on_progress({"type": "activity", "model": self.model})
                last_activity = time.monotonic()
                activity_pending = False

        def flush_due() -> None:
            now = time.monotonic()
            if last_delta is not None and now - last_delta >= 0.075:
                flush_delta()
            if last_activity is not None and now - last_activity >= 0.075:
                flush_activity()

        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST", f"{self.base_url}/chat/completions",
                headers=self._headers(), json=body,
            ) as response:
                response.raise_for_status()
                self._stage("waiting", "Waiting for model output")
                fields: list[str] = []
                event_type = "message"
                try:
                    async with aclosing(_lines_with_flush(response, pending_delay, flush_due)) as lines:
                        async for line in lines:
                            if line.startswith(":"):
                                continue
                            if line:
                                field, _, value = line.partition(":")
                                if field == "data":
                                    fields.append(value.removeprefix(" "))
                                elif field == "event":
                                    event_type = value.removeprefix(" ")
                                continue
                            if event_type == "error":
                                raise ValueError("Model stream reported an error")
                            event_type = "message"
                            if not fields:
                                continue
                            payload = "\n".join(fields)
                            fields.clear()
                            if payload.strip() == "[DONE]":
                                done = True
                                break
                            try:
                                chunk = json.loads(payload)
                            except (ValueError, TypeError):
                                raise ValueError("Invalid model stream frame") from None
                            if not isinstance(chunk, dict):
                                raise ValueError("Invalid model stream frame")
                            if "error" in chunk:
                                raise ValueError("Model stream reported an error")
                            choices = chunk.get("choices")
                            if not isinstance(choices, list):
                                raise ValueError("Invalid model stream choices")
                            if not choices:
                                continue  # Usage frames are not model output/activity.
                            choice = choices[0]
                            if not isinstance(choice, dict) or "error" in choice:
                                raise ValueError("Model stream reported an invalid choice")
                            reason = choice.get("finish_reason")
                            if reason is not None:
                                if reason != "stop":
                                    raise ValueError("Model stream did not finish normally")
                                finish_reason = reason
                            delta = choice.get("delta") or {}
                            if not isinstance(delta, dict):
                                raise ValueError("Invalid model stream delta")
                            content = delta.get("content")
                            if content is not None and not isinstance(content, str):
                                raise ValueError("Invalid model stream content")
                            # Inspect only presence, never copy reasoning into events.
                            actual_data = bool(content) or any(
                                delta.get(key) for key in ("reasoning", "reasoning_content", "reasoning_details")
                            )
                            now = time.monotonic()
                            if actual_data:
                                if not streaming:
                                    self._stage("streaming", "Receiving model output")
                                    streaming = True
                                activity_pending = True
                                if self.on_progress is not None and (
                                    last_activity is None or now - last_activity >= 0.075
                                ):
                                    flush_activity()
                            if content:
                                parts.append(content)
                                pending.append(content)
                                characters += len(content)
                            if pending and (last_delta is None or now - last_delta >= 0.075):
                                flush_delta()
                except BaseException:
                    # Report already-received output on failure/cancellation.
                    # A cleanup callback must not replace the original failure.
                    for flush in (flush_delta, flush_activity):
                        with suppress(BaseException):
                            flush()
                    raise
                # Flush real buffered output even on an incomplete EOF, but do
                # not let callers parse it as a successful answer.
                flush_delta()
                flush_activity()
                if not done or finish_reason != "stop":
                    raise ValueError("Model stream ended before completion")
        return message_text({"content": "".join(parts)}, finish_reason=finish_reason)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "OSINT Atlas",
        }

    def _completion_body(
        self,
        messages: list[dict],
        max_tokens: int | None,
        *,
        stream: bool,
        reasoning_effort: str | None = None,
        response_format: dict | None = None,
    ) -> dict:
        body: dict = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        # None means no output cap. Reasoning tokens still count against
        # whatever cap the provider applies, so uncapped callers should
        # pass a low reasoning effort or content can still come back null.
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if reasoning_effort:
            body["reasoning"] = {"effort": reasoning_effort}
        if response_format is not None:
            body["response_format"] = response_format
        return body

    # ------------------------------------------------------------------
    # Non-streaming chat completion
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict],
        max_tokens: int | None = 4096,
        reasoning_effort: str | None = None,
    ) -> str:
        """Return full response text, streaming progress when configured.

        ``max_tokens=None`` omits the cap. Uncapped calls default to low
        reasoning effort so the provider's own ceiling is not spent on
        reasoning before the answer.
        """
        effort = reasoning_effort
        if max_tokens is None and effort is None:
            effort = "low"
        # Uncapped analysis can run longer than a normal completion.
        timeout = 600.0 if max_tokens is None else 300.0
        if self.on_progress is not None:
            return await self._stream_completion(
                self._completion_body(messages, max_tokens, stream=True, reasoning_effort=effort),
                timeout=timeout,
            )
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._completion_body(
                    messages,
                    max_tokens,
                    stream=False,
                    reasoning_effort=effort,
                ),
            )
            resp.raise_for_status()
            data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            return message_text(
                choice.get("message") or {},
                finish_reason=choice.get("finish_reason"),
            )

    async def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Single-prompt completion. Returns full response text."""
        return await self.chat(
            [{"role": "user", "content": prompt}], max_tokens=max_tokens
        )

    # ------------------------------------------------------------------
    # Streaming chat completion
    # ------------------------------------------------------------------

    async def chat_stream(
        self,
        messages: list[dict],
        max_tokens: int = 4096,
        reasoning_effort: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming chat completion. Yields content strings.

        Uses standard OpenAI SSE format::

            data: {"choices":[{"delta":{"content":"..."}}]}

        ``delta.reasoning`` chunks (GLM-5.3 reasoning traces) and
        OpenRouter keepalive comment lines are skipped.
        """
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._completion_body(
                    messages,
                    max_tokens,
                    stream=True,
                    reasoning_effort=reasoning_effort,
                ),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    # Strip the "data: " prefix; skip keepalive comments
                    # (": OPENROUTER PROCESSING") and anything else.
                    if line.startswith("data: "):
                        payload = line[6:]
                    else:
                        continue

                    if payload.strip() == "[DONE]":
                        break

                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content

    # ------------------------------------------------------------------
    # Structured JSON output
    # ------------------------------------------------------------------

    async def chat_structured(
        self,
        messages: list[dict],
        schema: dict,
        max_tokens: int = 4096,
        reasoning_effort: str = "low",
    ) -> dict:
        """Chat with structured JSON output. Returns parsed dict.

        Defaults to low reasoning effort. Structured calls only need a
        short JSON object; max effort spends the token cap on reasoning
        and returns ``content: null``.
        """
        if self.on_progress is not None:
            raw = await self._stream_completion(
                self._completion_body(
                    messages, max_tokens, stream=True, reasoning_effort=reasoning_effort,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {"name": "structured_output", "strict": True, "schema": schema},
                    },
                ),
                timeout=300.0,
            )
            self._stage("parsing", "Parsing structured model output")
            return parse_structured_message({"content": raw})
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._completion_body(
                    messages,
                    max_tokens,
                    stream=False,
                    reasoning_effort=reasoning_effort,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "structured_output",
                            "strict": True,
                            "schema": schema,
                        },
                    },
                ),
            )
            resp.raise_for_status()
            data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            try:
                return parse_structured_message(choice.get("message") or {})
            except ValueError as e:
                finish = choice.get("finish_reason")
                raise ValueError(f"{e} (finish_reason={finish})") from e

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True when an API key is configured."""
        return bool(self.api_key)
