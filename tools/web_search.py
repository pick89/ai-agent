"""
Web Search Tool
Optimized with caching
"""

import hashlib
import json
import os
from datetime import datetime, timedelta

# Cache configuration
CACHE_DIR = "/tmp/web_search_cache"
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_DURATION = 30  # minutes

def web_search(query: str, max_results: int = 3) -> str:
    """
    Search the web with caching.

    Args:
        query: Search query
        max_results: Number of results to return (1-5)

    Returns:
        Formatted search results
    """
    # Validate inputs
    if not query or not query.strip():
        return "Error: Empty search query"

    query = query.strip()
    max_results = min(max(1, max_results), 5)  # Limit to 1-5

    print(f"🔍 Searching: {query}")

    # Check cache
    cache_key = hashlib.md5(query.encode()).hexdigest()
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cached = json.load(f)

            cache_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cache_time < timedelta(minutes=CACHE_DURATION):
                print(f"📦 Using cached results")
                return cached['results']
        except:
            pass  # Cache corrupted, continue

    try:
        # Try new package first, fallback to old
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = []
            try:
                # Use text search (faster than html)
                for r in ddgs.text(query, max_results=max_results):
                    if len(results) >= max_results:
                        break

                    title = r.get('title', 'No title')[:100]
                    body = r.get('body', '')[:200]
                    url = r.get('href', '')

                    if body:  # Only add if we have content
                        results.append({
                            'title': title,
                            'body': body,
                            'url': url
                        })

                if not results:
                    result_text = "No relevant results found. Try a different search query."
                else:
                    # Format results concisely
                    formatted = []
                    for i, r in enumerate(results, 1):
                        formatted.append(
                            f"[{i}] {r['title']}\n"
                            f"     {r['body']}\n"
                            f"     Source: {r['url']}\n"
                        )
                    result_text = "\n".join(formatted)

                # Cache results
                cache_data = {
                    'query': query,
                    'results': result_text,
                    'timestamp': datetime.now().isoformat()
                }
                try:
                    with open(cache_file, 'w') as f:
                        json.dump(cache_data, f)
                except:
                    pass  # Ignore cache write errors

                return result_text

            except Exception as e:
                print(f"❌ Search error: {e}")
                return f"Search failed: {str(e)[:100]}"

    except Exception as e:
        print(f"❌ Fatal search error: {e}")
        return f"Search system error: {str(e)[:100]}"