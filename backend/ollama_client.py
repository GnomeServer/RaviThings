# backend/ollama_client.py
import json
from typing import AsyncGenerator
import httpx

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "dolphin3"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def chat_stream(self, messages: list[dict]) -> AsyncGenerator[str, None]:
        """Stream chat tokens from Ollama. Yields content strings."""
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": True},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break

    async def generate(self, prompt: str) -> str:
        """Single-shot generation. Returns full response text."""
        async with httpx.AsyncClient(timeout=None) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def is_available(self) -> bool:
        """Check if Ollama is reachable and model is loaded."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                return any(self.model in m for m in models)
        except Exception:
            return False
