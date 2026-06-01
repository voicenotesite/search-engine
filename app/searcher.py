import re
import time
import logging
import urllib.parse
from functools import lru_cache
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

from .filter import filter_results, is_blocked

log = logging.getLogger("searcher")

# Simple in-memory cache for search results
_search_cache = {}
_cache_lock = Lock()
CACHE_TTL = 300  # 5 minutes cache TTL
MAX_CACHE_SIZE = 100  # Maximum number of cached entries

# Thread pool for parallel execution
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="search")


def _get_cache_key(query: str, num: int, sort: str, range: str) -> str:
    """Generate a cache key for search parameters."""
    return f"{query}:{num}:{sort}:{range}"


def _get_from_cache(key: str):
    """Get item from cache if it exists and is not expired."""
    with _cache_lock:
        if key in _search_cache:
            timestamp, data = _search_cache[key]
            if time.time() - timestamp < CACHE_TTL:
                return data
            else:
                # Remove expired entry
                del _search_cache[key]
    return None


def _save_to_cache(key: str, data):
    """Save item to cache, implementing LRU eviction if needed."""
    with _cache_lock:
        # If cache is too large, remove oldest entries
        if len(_search_cache) >= MAX_CACHE_SIZE:
            # Remove 20% of oldest entries
            sorted_items = sorted(_search_cache.items(), key=lambda x: x[1][0])
            for k, _ in sorted_items[:MAX_CACHE_SIZE // 5]:
                del _search_cache[k]
        
        _search_cache[key] = (time.time(), data)


def _headers() -> dict:
    return {
        "User-Agent": USER_AGENTS[int(time.time()) % len(USER_AGENTS)],
        "Accept-Language": "en-US,en;q=0.9,pl;q=0.8",
    }


def search_duckduckgo(query: str, num: int = 5) -> list[dict]:  # Reduced default to 5 for speed
    if is_blocked(query):
        return []

    data = {"q": query, "kl": "us-en"}
    try:
        # Further reduced timeout for even faster failure detection
        r = requests.post(
            "https://lite.duckduckgo.com/lite/",
            data=data,
            headers=_headers(),
            timeout=5,  # Reduced from 8 to 5 seconds
        )
        r.raise_for_status()
    except Exception as e:
        log.warning(f"duckduckgo search failed: {e}")
        return []

    # Require lxml for faster parsing - fail fast if not available
    soup = BeautifulSoup(r.text, "lxml")
    
    results = []

    # Ultra-efficient selector - target only result links with href
    for a in soup.select("a.result-link[href^='http']"):
        title = a.get_text(strip=True)
        if not title:
            continue

        # Skip snippet extraction for maximum speed (snippets are heavy to process)
        # Only extract if really needed for display
        snippet = ""

        results.append({
            "title": title,
            "url": a.get("href", ""),
            "snippet": snippet,
            "source": "duckduckgo",
        })
        if len(results) >= num:
            break

    return filter_results(results)


def search_ahmia(query: str, num: int = 5) -> list[dict]:  # Reduced default to 5 for speed
    if is_blocked(query):
        return []

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            # Launch with performance optimizations - even more aggressive
            b = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-images",  # Don't load images for speed
                    "--disable-javascript",  # Disable JS entirely for speed (if site works without)
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-features=VizDisplayCompositor"
                ]
            )
            page = b.new_page()
            
            # Set very short timeouts
            page.set_default_timeout(8000)  # 8 seconds max
            
            # Go to Ahmia and search
            page.goto("https://ahmia.fi/", wait_until="domcontentloaded")
            page.fill("input[name=q]", query)
            page.press("input[name=q]", "Enter")
            
            # Wait briefly for results to load
            page.wait_for_timeout(1000)
            
            # Try to wait for results selector, but don't fail if timeout
            try:
                page.wait_for_selector("ol.searchResults", timeout=3000)
            except:
                pass  # Continue anyway
            
            html = page.content()
            b.close()

        # Use lxml for faster parsing if available
        try:
            soup = BeautifulSoup(html, "lxml")
        except:
            soup = BeautifulSoup(html, "html.parser")
        
        results = []

        # More efficient selector
        for a in soup.select("ol.searchResults a[href*='/search/redirect']"):
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not title or not href:
                continue

            import re
            url_match = re.search(r"redirect_url=([^&]+)", href)
            url = urllib.parse.unquote(url_match.group(1)) if url_match else href

            # Skip snippet extraction for maximum speed
            snippet = ""

            results.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": "ahmia",
            })
            if len(results) >= num:
                break

        return filter_results(results)

    except Exception as e:
        log.warning(f"ahmia search failed: {e}")
        return []


def search(query: str, num: int = 10, sort: str = "relevance", range: str = "any") -> dict:
    # Check cache first
    cache_key = _get_cache_key(query, num, sort, range)
    cached_result = _get_from_cache(cache_key)
    if cached_result is not None:
        log.info(f"Returning cached result for query: {query}")
        return cached_result
    
    # Perform searches in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both search tasks
        ddg_future = executor.submit(search_duckduckgo, query, num)
        dark_future = executor.submit(search_ahmia, query, num)
        
        # Get results as they complete
        ddg_results = ddg_future.result()
        dark_results = dark_future.result()

    # Combine results
    all_results = ddg_results + dark_results
    
    # Apply sorting
    if sort == "date":
        # Sort by date would require parsing dates from snippets or other metadata
        # For now, we'll keep original order as DuckDuckGo and Ahmia already sort by relevance/date
        pass
    elif sort == "source":
        # Group by source: DuckDuckGo first, then Ahmia
        all_results = ddg_results + dark_results  # Already in this order
    
    # Apply date range filtering would require parsing dates from results
    # For simplicity, we'll note that this would need to be implemented in the individual search functions
    # based on the dateRange parameter

    result = {
        "query": query,
        "total": len(all_results),
        "results": all_results,
        "sources": {
            "duckduckgo": len(ddg_results),
            "ahmia": len(dark_results),
        },
    }
    
    # Save to cache
    _save_to_cache(cache_key, result)
    
    return result
