# backend/glm_client.py
"""Client for GLM-5.3 (Z.ai) via the OpenRouter OpenAI-compatible API."""
import json
import os
from typing import AsyncGenerator

import httpx


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

    # ------------------------------------------------------------------
    # Non-streaming chat completion
    # ------------------------------------------------------------------

    async def chat(self, messages: list[dict], max_tokens: int = 4096) -> str:
        """Non-streaming chat completion. Returns full response text."""
        # 300s: GLM-5.3 reasons before answering; long synthesis calls
        # can exceed a 2-minute budget.
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Single-prompt completion. Returns full response text."""
        return await self.chat(
            [{"role": "user", "content": prompt}], max_tokens=max_tokens
        )

    # ------------------------------------------------------------------
    # Streaming chat completion
    # ------------------------------------------------------------------

    async def chat_stream(
        self, messages: list[dict], max_tokens: int = 4096
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
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "stream": True,
                },
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
        self, messages: list[dict], schema: dict, max_tokens: int = 4096
    ) -> dict:
        """Chat with structured JSON output. Returns parsed dict."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "stream": False,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "structured_output",
                            "strict": True,
                            "schema": schema,
                        },
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data["choices"][0]["message"]["content"]
            return json.loads(raw)

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True when an API key is configured."""
        return bool(self.api_key)
