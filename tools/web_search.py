"""
Web Search Tool - Async Optimized
DuckDuckGo search with fallback methods
Python 3.14 compatible
"""

import asyncio
import time
import json
import re
import html
import urllib.parse
from typing import List, Dict, Optional
from dataclasses import dataclass

import httpx


@dataclass
class SearchResult:
    """Structured search result"""
    title: str
    url: str
    snippet: str
    source: str = "duckduckgo"


class WebSearchCache:
    """Simple in-memory cache for search results"""

    def __init__(self, ttl: int = 300):
        self._cache: Dict[str, tuple] = {}
        self._ttl = ttl

    def get(self, query: str) -> Optional[List[SearchResult]]:
        if query not in self._cache:
            return None
        timestamp, results = self._cache[query]
        if time.time() - timestamp > self._ttl:
            del self._cache[query]
            return None
        return results

    def set(self, query: str, results: List[SearchResult]):
        self._cache[query] = (time.time(), results)


# Global cache
_search_cache = WebSearchCache(ttl=300)


async def web_search(
    query: str,
    max_results: int = 5,
    use_cache: bool = True
) -> str:
    """
    Search the web using DuckDuckGo
    """

    if not query or not query.strip():
        return "Error: Empty search query"

    query = query.strip()
    max_results = max(1, min(max_results, 10))

    # Check cache
    if use_cache:
        cached = _search_cache.get(query)
        if cached:
            print(f"📦 Cache hit: {query[:40]}...")
            return _format_results(cached)

    try:
        # Try multiple search methods
        results = await _search_duckduckgo(query, max_results)

        if not results:
            # Fallback to alternative method
            results = await _search_duckduckgo_html(query, max_results)

        if not results:
            return f"No results found for: {query}"

        if use_cache:
            _search_cache.set(query, results)

        return _format_results(results)

    except Exception as e:
        return f"Search error: {str(e)[:100]}"


async def _search_duckduckgo(query: str, max_results: int) -> List[SearchResult]:
    """
    DuckDuckGo Instant Answer API (JSON)
    """
    # DuckDuckGo instant answer API
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()
        results = []

        # Parse Abstract (main result)
        if data.get("AbstractText"):
            results.append(SearchResult(
                title=data.get("Heading", "Result"),
                url=data.get("AbstractURL", ""),
                snippet=data.get("AbstractText", ""),
                source="duckduckgo"
            ))

        # Parse RelatedTopics
        for topic in data.get("RelatedTopics", [])[:max_results - 1]:
            if "Text" in topic:
                results.append(SearchResult(
                    title=topic.get("FirstURL", "").split("/")[-1].replace("_", " ").title() or "Related",
                    url=topic.get("FirstURL", ""),
                    snippet=topic.get("Text", ""),
                    source="duckduckgo"
                ))

        return results[:max_results]


async def _search_duckduckgo_html(query: str, max_results: int) -> List[SearchResult]:
    """
    Fallback: DuckDuckGo HTML scraping
    """
    url = "https://lite.duckduckgo.com/lite/"  # Use lite version
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Accept": "text/html",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "q": query,
        "kl": "us-en",
    }

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.post(url, data=data, headers=headers)
        response.raise_for_status()

        return _parse_lite_html(response.text, max_results)


def _parse_lite_html(html: str, max_results: int) -> List[SearchResult]:
    """
    Parse DuckDuckGo Lite HTML
    """
    results = []

    # DuckDuckGo Lite uses table rows
    # Pattern: <tr>...<a href="...">...</a>...</tr>

    # Find all result rows
    rows = re.findall(r'<tr[^>]*>.*?</tr>', html, re.DOTALL)

    for row in rows[:max_results * 2]:  # Check more rows
        try:
            # Extract link and title
            link_match = re.search(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', row, re.DOTALL)
            if not link_match:
                continue

            url = link_match.group(1)
            title = _clean_html(link_match.group(2))

            # Skip navigation links
            if any(x in url.lower() for x in ["duckduckgo", "javascript:", "#", "yahoo"]):
                continue

            # Extract snippet from nearby text
            snippet = ""
            # Remove the link tag and get surrounding text
            text_without_link = re.sub(r'<a[^>]*>.*?</a>', '', row, flags=re.DOTALL)
            snippet = _clean_html(text_without_link)

            if title and url and len(title) > 3:
                # Make URL absolute
                if url.startswith("//"):
                    url = "https:" + url
                elif url.startswith("/"):
                    url = "https://duckduckgo.com" + url

                results.append(SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet[:200],
                    source="duckduckgo"
                ))

                if len(results) >= max_results:
                    break

        except Exception:
            continue

    return results


def _clean_html(text: str) -> str:
    """Remove HTML tags and entities"""
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = ' '.join(text.split())
    return text.strip()


def _format_results(results: List[SearchResult]) -> str:
    """Format results as readable text"""
    if not results:
        return "No results found."

    lines = []
    for i, result in enumerate(results, 1):
        lines.append(f"{i}. {result.title}")
        lines.append(f"   🔗 {result.url}")
        if result.snippet:
            snippet = result.snippet[:200] + "..." if len(result.snippet) > 200 else result.snippet
            lines.append(f"   📝 {snippet}")
        lines.append("")

    return "\n".join(lines).strip()


# Test
if __name__ == "__main__":
    async def test():
        print("Testing web search...")
        result = await web_search("python asyncio tutorial", max_results=3)
        print("\n" + "=" * 60)
        print(result)
        print("=" * 60)

    asyncio.run(test())