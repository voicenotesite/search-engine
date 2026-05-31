import re
import time
import logging
from urllib.parse import quote_plus

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


def search_google(query: str, num: int = 10) -> list[dict]:
    if is_blocked(query):
        return []

    params = {"q": query, "num": min(num, 20), "hl": "en"}
    try:
        r = requests.get(
            "https://www.google.com/search",
            params=params,
            headers=_headers(),
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        log.warning(f"google search failed: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    for g in soup.select("div.g, div[data-hveid]"):
        a = g.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        if not href.startswith("http"):
            continue

        title_el = g.select_one("h3")
        title = title_el.get_text(strip=True) if title_el else ""

        snippet_el = g.select_one("div[data-sncf], span.aCOpRe, div.VwiC3b")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        results.append({
            "title": title,
            "url": href,
            "snippet": snippet[:300] if snippet else "",
            "source": "google",
        })

        if len(results) >= num:
            break

    return filter_results(results)


def search_ahmia(query: str, num: int = 10) -> list[dict]:
    if is_blocked(query):
        return []

    try:
        r = requests.get(
            "https://ahmia.fi/search/",
            params={"q": query},
            headers={"User-Agent": USER_AGENTS[0]},
            timeout=15,
        )
        r.raise_for_status()
    except Exception as e:
        log.warning(f"ahmia search failed: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    for li in soup.select("ul#results li, li.result"):
        a = li.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        if not href.startswith("http"):
            continue

        title = a.get_text(strip=True)

        snippet_el = li.select_one("p, span.snippet")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        results.append({
            "title": title,
            "url": href,
            "snippet": snippet[:300] if snippet else "",
            "source": "ahmia",
        })

        if len(results) >= num:
            break

    return filter_results(results)


def search(query: str, num: int = 10) -> dict:
    google_results = search_google(query, num)
    dark_results = search_ahmia(query, num)

    return {
        "query": query,
        "total": len(google_results) + len(dark_results),
        "results": google_results + dark_results,
        "sources": {
            "google": len(google_results),
            "ahmia": len(dark_results),
        },
    }
