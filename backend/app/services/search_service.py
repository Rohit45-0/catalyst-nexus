import httpx
import re
import logging
import json
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class SearchService:
    """
    Hybrid Search Service.
    1. Tries Official APIs (Brave, Serper) if keys exist.
    2. Fallbacks to DuckDuckGo HTML scraping (Zero-Dependency) if no keys.
    """
    
    def __init__(self):
        self.brave_key = getattr(settings, "BRAVE_API_KEY", None)
        self.serper_key = getattr(settings, "SERPER_API_KEY", None)
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        if self.brave_key:
            return await self._search_brave(query, max_results)
            
        if self.serper_key:
            return await self._search_serper(query, max_results)
            
        return await self._scrape_duckduckgo(query, max_results)
        
    async def _search_brave(self, query: str, max_results: int) -> List[Dict[str, str]]:
        # Implementation for Brave Search API
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"X-Subscription-Token": self.brave_key}
        params = {"q": query, "count": min(max_results, 20)}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                results = []
                for item in data.get("web", {}).get("results", []):
                    results.append({
                        "title": item.get("title"),
                        "link": item.get("url"),
                        "snippet": item.get("description")
                    })
                return results
            except Exception as e:
                logger.error(f"Brave Search failed: {e}")
                return await self._scrape_duckduckgo(query, max_results)

    async def _search_serper(self, query: str, max_results: int) -> List[Dict[str, str]]:
         # Implementation for Serper (Google wrapper)
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_key,
            "Content-Type": "application/json"
        }
        payload = {"q": query, "num": max_results}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                results = []
                for item in data.get("organic", []):
                    results.append({
                        "title": item.get("title"),
                        "link": item.get("link"),
                        "snippet": item.get("snippet")
                    })
                return results
            except Exception as e:
                logger.error(f"Serper Search failed: {e}")
                return await self._scrape_duckduckgo(query, max_results)

    async def _scrape_duckduckgo(self, query: str, max_results: int) -> List[Dict[str, str]]:
        logger.info(f"Searching DuckDuckGo (HTML Scraper): {query}")
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": self.user_agent}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, data={"q": query}, headers=headers)
                resp.raise_for_status()
                return self._parse_ddg_html(resp.text, max_results)
            except Exception as e:
                logger.error(f"DDG Scrape failed: {e}")
                return []
                
    def _parse_ddg_html(self, html: str, max_results: int) -> List[Dict[str, str]]:
        results = []
        # Regex to match result blocks
        # Pattern looks for <a class="result__a" href="...">Title</a>
        link_pattern = re.compile(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
        snippet_pattern = re.compile(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL)
        
        links = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)
        
        for i in range(min(len(links), max_results)):
            href, title = links[i]
            snippet = snippets[i] if i < len(snippets) else ""
            
            # Basic cleanup
            title = self._clean_html(title)
            snippet = self._clean_html(snippet)
            
            results.append({"title": title, "link": href, "snippet": snippet})
            
        return results

    def _clean_html(self, text: str) -> str:
        text = re.sub(r'<[^>]+>', '', text) # Remove tags
        text = text.replace("&quot;", '"').replace("&#x27;", "'").replace("&amp;", "&").replace("&gt;", ">").replace("&lt;", "<")
        return text.strip()

_search_service = None

def get_search_service() -> SearchService:
    global _search_service
    if not _search_service:
        _search_service = SearchService()
    return _search_service
