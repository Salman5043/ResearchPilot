import os
from urllib.parse import urlparse

from tavily import TavilyClient


_api_key = os.getenv("TAVILY_API_KEY")
client = TavilyClient(api_key=_api_key) if _api_key else None


def web_search(query: str, max_results: int = 3):
    """Search Tavily and return normalized, compact source records."""
    if not query or client is None:
        return []

    query = query.strip()[:300]
    if not query:
        return []

    response = client.search(
        query=query,
        max_results=max_results,
        search_depth=os.getenv("TAVILY_SEARCH_DEPTH", "basic"),
        include_answer=False,
    )

    results = []
    seen_urls = set()

    for result in response.get("results", []):
        url = (result.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        content = (result.get("content") or "").strip()
        results.append({
            "title": (result.get("title") or "Untitled source").strip(),
            "content": content[:1800],
            "url": url,
            "domain": urlparse(url).netloc.replace("www.", ""),
        })

    return results
