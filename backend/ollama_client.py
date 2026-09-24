# backend/ollama_client.py
"""Local embedding client. Chat goes through GLMClient / OpenRouter."""
import httpx


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", embed_model: str = "nomic-embed-text"):
        self.base_url = base_url.rstrip("/")
        self.embed_model = embed_model


    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Compute embeddings via Ollama /api/embed using the dedicated embed model."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.embed_model, "input": texts},
            )
            resp.raise_for_status()
            return resp.json()["embeddings"]

    def embed_sync(self, texts: list[str]) -> list[list[float]]:
        """Synchronous embedding for use in non-async contexts (graph building, etc.)."""
        import httpx as httpx_sync
        resp = httpx_sync.post(
            f"{self.base_url}/api/embed",
            json={"model": self.embed_model, "input": texts},
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]

    async def is_available(self) -> bool:
        """Return True when Ollama is up and the embed model is loaded."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                return any(self.embed_model in m for m in models)
        except Exception:
            return False
