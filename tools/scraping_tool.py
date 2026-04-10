"""
tools/scraping_tool.py
----------------------
Web scraping tool that fetches and cleans article text from URLs.
Used by the Research Agent to deep-read pages found in search results.
"""

import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional

logger = logging.getLogger(__name__)

# Common browser headers to avoid bot detection
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 10  # seconds


def scrape_page(url: str, max_chars: int = 3000) -> Optional[str]:
    """
    Fetch a webpage and extract its main text content.

    Args:
        url: The URL to scrape.
        max_chars: Truncate extracted text to this many characters.

    Returns:
        Cleaned text string, or None if scraping failed.
    """
    try:
        logger.info(f"[Scraper] Fetching: {url}")
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")

        # Remove noise elements
        for tag in soup(["script", "style", "nav", "footer",
                          "header", "aside", "form", "noscript"]):
            tag.decompose()

        # Prefer <article> or <main> body when available
        body = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", {"id": "content"})
            or soup.find("div", {"class": "content"})
            or soup.body
        )

        if body is None:
            return None

        text = body.get_text(separator=" ", strip=True)
        # Collapse excessive whitespace
        text = " ".join(text.split())

        logger.info(f"[Scraper] Extracted {len(text)} chars from {url}")
        return text[:max_chars]

    except requests.exceptions.Timeout:
        logger.warning(f"[Scraper] Timeout for {url}")
    except requests.exceptions.ConnectionError:
        logger.warning(f"[Scraper] Connection error for {url}")
    except Exception as e:
        logger.warning(f"[Scraper] Failed to scrape {url}: {e}")

    return None


def scrape_multiple(urls: list[str], max_chars_each: int = 3000) -> dict[str, str]:
    """
    Scrape multiple URLs and return a dict of {url: text}.

    Args:
        urls: List of URLs to scrape.
        max_chars_each: Per-page character limit.

    Returns:
        Dict mapping each URL to its extracted text (skips failures).
    """
    results = {}
    for url in urls:
        text = scrape_page(url, max_chars=max_chars_each)
        if text:
            results[url] = text
    return results
