"""
Web Search Tool
Search the internet using DuckDuckGo
"""

from duckduckgo_search import DDGS
from typing import List, Dict, Any


def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default 5)
        
    Returns:
        Formatted search results as a string
    """
    try:
        print(f"🔍 Searching for: {query}")
        
        results = []
        with DDGS() as ddgs:
            search_results = ddgs.text(query, max_results=max_results)
            
            for i, result in enumerate(search_results, 1):
                results.append({
                    "position": i,
                    "title": result.get('title', 'No title'),
                    "url": result.get('href', 'No URL'),
                    "snippet": result.get('body', 'No description')
                })
        
        if not results:
            return f"No results found for '{query}'"
        
        # Format results
        formatted = f"Search results for '{query}':\n\n"
        for r in results:
            formatted += f"{r['position']}. {r['title']}\n"
            formatted += f"   {r['snippet'][:200]}...\n"
            formatted += f"   URL: {r['url']}\n\n"
        
        print(f"✅ Found {len(results)} results")
        return formatted
        
    except Exception as e:
        error_msg = f"Search error: {str(e)}"
        print(f"❌ {error_msg}")
        return error_msg


# Test function (optional)
if __name__ == "__main__":
    # Test the search
    result = web_search("Python programming language", max_results=3)
    print(result)
