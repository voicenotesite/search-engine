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
        r = requests.post(
            "https://lite.duckduckgo.com/lite/",
            data=data,
            headers=_headers(),
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        log.warning(f"duckduckgo search failed: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    for a in soup.select("a.result-link"):
        href = a.get("href", "")
        if not href.startswith("http"):
            continue
        title = a.get_text(strip=True)
        if not title:
            continue

        snippet = ""
        parent = a.find_parent("tr")
        if parent:
            snippet_td = parent.find_next_sibling("tr")
            if snippet_td:
                s = snippet_td.select_one("td.result-snippet")
                if s:
                    snippet = s.get_text(strip=True)[:300]

        results.append({
            "title": title,
            "url": href,
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
            b = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page = b.new_page()
            page.goto("https://ahmia.fi/", timeout=30000, wait_until="networkidle")
            page.fill("input[name=q]", query)
            page.press("input[name=q]", "Enter")
            page.wait_for_timeout(4000)
            html = page.content()
            b.close()

        soup = BeautifulSoup(html, "html.parser")
        results = []

        for a in soup.select("ol.searchResults a[href*='/search/redirect']"):
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not title or not href:
                continue

            import re
            url_match = re.search(r"redirect_url=([^&]+)", href)
            url = urllib.parse.unquote(url_match.group(1)) if url_match else href

            parent = a.find_parent("li")
            snippet = ""
            if parent:
                snippet_el = parent.select_one("small, .description, p")
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


def search(query: str, num: int = 10) -> dict:
    ddg_results = search_duckduckgo(query, num)
    dark_results = search_ahmia(query, num)

    return {
        "query": query,
        "total": len(ddg_results) + len(dark_results),
        "results": ddg_results + dark_results,
        "sources": {
            "duckduckgo": len(ddg_results),
            "ahmia": len(dark_results),
        },
    }
