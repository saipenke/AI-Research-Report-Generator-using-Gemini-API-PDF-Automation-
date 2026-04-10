"""
tools/web_search_tool.py
------------------------
Web search tool — tries ddgs first, falls back to requests+BeautifulSoup scraping.
"""

import os
import logging
import requests
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def search_web(query: str, max_results: int = 8) -> List[Dict[str, Any]]:
    """
    Search the web. Tries ddgs → Tavily → direct Bing scrape → empty list.
    Always returns a list (never raises).
    """
    provider = os.getenv("SEARCH_PROVIDER", "duckduckgo").lower()
    logger.info(f"[WebSearch] Provider: {provider} | Query: {query}")

    results = []

    # ── Try ddgs (new package name) ───────────────────────────────
    results = _ddgs_search(query, max_results)
    if results:
        return results

    # ── Try Tavily if key present ─────────────────────────────────
    if os.getenv("TAVILY_API_KEY"):
        results = _tavily_search(query, max_results)
        if results:
            return results

    # ── Last resort: scrape Bing directly ────────────────────────
    results = _bing_scrape(query, max_results)
    if results:
        return results

    logger.warning(f"[WebSearch] All providers returned 0 results for: {query}")
    return []


# ── ddgs backend (new package) ────────────────────────────────────

def _ddgs_search(query: str, max_results: int) -> List[Dict[str, Any]]:
    try:
        from ddgs import DDGS
        ddgs = DDGS()
        raw = ddgs.text(query, max_results=max_results)
        results = []
        for item in (raw or []):
            results.append({
                "title":   item.get("title", ""),
                "url":     item.get("href", ""),
                "content": item.get("body", ""),
            })
        logger.info(f"[ddgs] Retrieved {len(results)} results.")
        return results
    except ImportError:
        logger.warning("[ddgs] Package not installed — trying fallback.")
    except Exception as e:
        logger.warning(f"[ddgs] Failed: {e}")
    return []


# ── Tavily backend ────────────────────────────────────────────────

def _tavily_search(query: str, max_results: int) -> List[Dict[str, Any]]:
    try:
        from tavily import TavilyClient
        client   = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        response = client.search(query=query, search_depth="advanced",
                                  max_results=max_results, include_raw_content=True)
        results  = []
        for item in response.get("results", []):
            results.append({
                "title":   item.get("title", ""),
                "url":     item.get("url", ""),
                "content": item.get("content", "") or item.get("raw_content", ""),
            })
        logger.info(f"[Tavily] Retrieved {len(results)} results.")
        return results
    except Exception as e:
        logger.warning(f"[Tavily] Failed: {e}")
    return []


# ── Direct Bing scrape (no API key) ──────────────────────────────

def _bing_scrape(query: str, max_results: int) -> List[Dict[str, Any]]:
    """Scrape Bing search results page as last resort."""
    try:
        from bs4 import BeautifulSoup
        url      = f"https://www.bing.com/search?q={requests.utils.quote(query)}&count={max_results}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        soup     = BeautifulSoup(response.text, "lxml")

        results = []
        for li in soup.select("li.b_algo")[:max_results]:
            title_tag   = li.select_one("h2 a")
            snippet_tag = li.select_one(".b_caption p") or li.select_one("p")
            if title_tag:
                results.append({
                    "title":   title_tag.get_text(strip=True),
                    "url":     title_tag.get("href", ""),
                    "content": snippet_tag.get_text(strip=True) if snippet_tag else "",
                })

        logger.info(f"[BingScrape] Retrieved {len(results)} results.")
        return results
    except Exception as e:
        logger.warning(f"[BingScrape] Failed: {e}")
    return []
