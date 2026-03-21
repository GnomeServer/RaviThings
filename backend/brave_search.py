"""Brave Search API client for web research augmentation."""
import os
import httpx


class BraveSearchClient:
    """Async client for Brave Web Search API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("BRAVE_SEARCH_API_KEY", "")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    async def search(self, query: str, count: int = 5) -> list[dict]:
        """Search the web and return structured results.

        Returns list of dicts with: title, url, description, snippet
        """
        if not self.api_key:
            return []

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    self.base_url,
                    params={"q": query, "count": count},
                    headers={
                        "X-Subscription-Token": self.api_key,
                        "Accept": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return []

        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", ""),
            })
        return results

    async def search_for_context(self, query: str, count: int = 5) -> str:
        """Search and format results as context text for LLM consumption."""
        results = await self.search(query, count=count)
        if not results:
            return ""

        lines = []
        for r in results:
            lines.append(f"- [{r['title']}]({r['url']})")
            if r["description"]:
                lines.append(f"  {r['description']}")
        return "\n".join(lines)

    def is_available(self) -> bool:
        return bool(self.api_key)
