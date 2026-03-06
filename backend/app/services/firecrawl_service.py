"""
Firecrawl Service
=================
Web scraping and search using the Firecrawl API.
Used for Reference Content analytics — scraping YouTube pages,
competitor articles, and full web content for LLM analysis.
"""

from typing import Optional, List, Dict, Any
from firecrawl import FirecrawlApp
from backend.app.core.config import settings


def get_firecrawl_client() -> Optional[FirecrawlApp]:
    """Return a Firecrawl client if API key is configured."""
    if not settings.FIRECRAWL_API_KEY:
        return None
    return FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)


def scrape_url(url: str, formats: list[str] = None) -> dict:
    """
    Scrape a single URL and return LLM-ready content.
    
    Args:
        url: The URL to scrape (YouTube, article, competitor page, etc.)
        formats: List of formats to return. Default: ["markdown", "metadata"]
    
    Returns:
        dict with keys: markdown, metadata (title, description, url, etc.)
    """
    client = get_firecrawl_client()
    if not client:
        raise ValueError("FIRECRAWL_API_KEY not configured")
    
    if formats is None:
        formats = ["markdown", "metadata"]
    
    try:
        result = client.scrape_url(url, formats=formats)
        return {
            "url": url,
            "markdown": result.markdown if hasattr(result, "markdown") else "",
            "metadata": result.metadata if hasattr(result, "metadata") else {},
        }
    except Exception as e:
        # Graceful failure
        return {"url": url, "error": str(e), "markdown": "", "metadata": {}}


def search_web(query: str, limit: int = 5, scrape_content: bool = False) -> list[dict]:
    """
    Search the web using Firecrawl and optionally scrape full content.
    
    Args:
        query: Search query string
        limit: Number of results (max 10)
        scrape_content: If True, also scrapes full page content for each result
    
    Returns:
        List of result dicts with url, title, description, and optionally markdown
    """
    client = get_firecrawl_client()
    if not client:
        raise ValueError("FIRECRAWL_API_KEY not configured")
    
    # Updated for newer firecrawl-py SDK: search(query, limit=..., scrape_options=...)
    scrape_opts = {"formats": ["markdown"]} if scrape_content else None
    
    try:
        if scrape_opts:
            results = client.search(query, limit=limit, scrape_options=scrape_opts)
        else:
            results = client.search(query, limit=limit)
        
        # Normalize output
        output = []
        
        # SDK output handling
        # It typically returns a dictionary with 'data' key or list of objects
        data = []
        if isinstance(results, dict):
            data = results.get("data", [])
        elif hasattr(results, "data"):
            data = results.data
        elif isinstance(results, list): # fallback
            data = results

        for item in data:
            # item could be dict or object
            if isinstance(item, dict):
                output.append({
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "markdown": item.get("markdown", ""),
                })
            else:
                output.append({
                    "url": getattr(item, "url", ""),
                    "title": getattr(item, "title", ""),
                    "description": getattr(item, "description", ""),
                    "markdown": getattr(item, "markdown", ""),
                })
        return output
        
    except Exception as e:
        # Log error in production, here we return empty list to not crash callers
        print(f"Firecrawl search error: {e}")
        return []


def extract_youtube_content(youtube_url: str) -> dict:
    """
    Scrape a YouTube video page to extract title, description, and transcript info.
    
    Args:
        youtube_url: Full YouTube video URL
    
    Returns:
        dict with title, description, markdown content
    """
    return scrape_url(youtube_url, formats=["markdown", "metadata"])
