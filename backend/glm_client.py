# backend/glm_client.py
"""Client for GLM-5.3 (Z.ai) via the OpenRouter OpenAI-compatible API."""
import json
import os
from typing import AsyncGenerator

import httpx


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

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = os.environ.get("OPENROUTER_MODEL", "z-ai/glm-5.3")

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
        """Non-streaming chat completion. Returns full response text.

        ``max_tokens=None`` omits the cap. Uncapped calls default to low
        reasoning effort so the provider's own ceiling is not spent on
        reasoning before the answer.
        """
        effort = reasoning_effort
        if max_tokens is None and effort is None:
            effort = "low"
        # Uncapped analysis can run longer than a normal completion.
        timeout = 600.0 if max_tokens is None else 300.0
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
