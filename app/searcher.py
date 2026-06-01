import re
import time
import logging
import urllib.parse

import requests
from bs4 import BeautifulSoup

from .filter import filter_results, is_blocked

log = logging.getLogger("searcher")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
]


def _headers() -> dict:
    return {
        "User-Agent": USER_AGENTS[int(time.time()) % len(USER_AGENTS)],
        "Accept-Language": "en-US,en;q=0.9,pl;q=0.8",
    }


def search_duckduckgo(query: str, num: int = 10) -> list[dict]:
    if is_blocked(query):
        return []

    data = {"q": query, "kl": "us-en"}
    try:
        # Reduced timeout for faster failure detection
        r = requests.post(
            "https://lite.duckduckgo.com/lite/",
            data=data,
            headers=_headers(),
            timeout=8,  # Reduced from 10 to 8 seconds
        )
        r.raise_for_status()
    except Exception as e:
        log.warning(f"duckduckgo search failed: {e}")
        return []

    # Parse with lxml for faster parsing if available, fallback to html.parser
    try:
        soup = BeautifulSoup(r.text, "lxml")
    except:
        soup = BeautifulSoup(r.text, "html.parser")
    
    results = []

    # More efficient selector - target only result links with href
    for a in soup.select("a.result-link[href^='http']"):
        title = a.get_text(strip=True)
        if not title:
            continue

        # More efficient snippet extraction
        snippet = ""
        parent = a.find_parent("tr")
        if parent:
            # Look for snippet in the next row
            snippet_td = parent.find_next_sibling("tr")
            if snippet_td:
                s = snippet_td.select_one("td.result-snippet")
                if s:
                    snippet = s.get_text(strip=True)[:300]

        results.append({
            "title": title,
            "url": a.get("href", ""),
            "snippet": snippet,
            "source": "duckduckgo",
        })
        if len(results) >= num:
            break

    return filter_results(results)


def search_ahmia(query: str, num: int = 10) -> list[dict]:
    if is_blocked(query):
        return []

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            # Launch with performance optimizations
            b = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-images",  # Don't load images for speed
                    "--disable-javascript-harmony-shipping",
                    "--disable-background-timer-throttling",
                    "--disable-renderer-backgrounding",
                    "--disable-backgrounding-occluded-windows"
                ]
            )
            page = b.new_page()
            
            # Set shorter timeouts
            page.set_default_timeout(15000)  # 15 seconds max
            
            # Go to Ahmia and search
            page.goto("https://ahmia.fi/", wait_until="domcontentloaded")
            page.fill("input[name=q]", query)
            page.press("input[name=q]", "Enter")
            
            # Wait for results to load (reduced from 4000ms)
            page.wait_for_timeout(1500)
            
            # Try to wait for results selector, but don't fail if timeout
            try:
                page.wait_for_selector("ol.searchResults", timeout=5000)
            except:
                pass  # Continue anyway
            
            html = page.content()
            b.close()

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

            # More efficient snippet extraction
            snippet = ""
            parent = a.find_parent("li")
            if parent:
                # Look for snippet in order of preference
                snippet_el = (parent.select_one(".description, p, small") or 
                             parent.find_next_sibling())
                if snippet_el:
                    snippet = snippet_el.get_text(strip=True)[:300]

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
    ddg_results = search_duckduckgo(query, num)
    dark_results = search_ahmia(query, num)

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

    return {
        "query": query,
        "total": len(all_results),
        "results": all_results,
        "sources": {
            "duckduckgo": len(ddg_results),
            "ahmia": len(dark_results),
        },
    }
