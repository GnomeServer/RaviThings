# backend/mercury_client.py
"""Client for Mercury2 (Inception Labs) OpenAI-compatible API."""
import json
import os
from typing import AsyncGenerator

import httpx


class MercuryClient:
    """Async client for the Mercury2 diffusion language model.

    Mercury2 is accessed via an OpenAI-compatible API at
    https://api.inceptionlabs.ai/v1.  The API key is read from the
    ``INCEPTION_API_KEY`` environment variable when not supplied explicitly.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("INCEPTION_API_KEY", "")
        self.base_url = "https://api.inceptionlabs.ai/v1"
        self.model = "mercury-2"

    # ------------------------------------------------------------------
    # Non-streaming chat completion
    # ------------------------------------------------------------------

    async def chat(self, messages: list[dict], max_tokens: int = 4096) -> str:
        """Non-streaming chat completion. Returns full response text."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
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

    # ------------------------------------------------------------------
    # Streaming chat completion (diffusion mode)
    # ------------------------------------------------------------------

    async def chat_stream(
        self, messages: list[dict], max_tokens: int = 4096
    ) -> AsyncGenerator[str, None]:
        """Streaming chat with diffusion mode. Yields content strings.

        Mercury uses standard OpenAI SSE format::

            data: {"choices":[{"delta":{"content":"..."}}]}
        """
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
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
                    # Strip the "data: " prefix
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
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
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
