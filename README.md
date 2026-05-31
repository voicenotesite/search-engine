# DarkSearch

**Wyszukiwarka clearnet + darknet** z filtrem nielegalnego contentu.

🌐 **Live:** https://search-engine-l2zt.onrender.com

| Warstwa | Źródło | Wyniki |
|---------|--------|--------|
| Clearnet | DuckDuckGo Lite | ✅ |
| Darknet (.onion) | Ahmia przez Playwright | ✅ |
| Filtr | NCII – regex + blokada 403 | ✅ |

## Stack

- FastAPI + uvicorn
- Playwright (headless Chromium) + BeautifulSoup
- DuckDuckGo Lite HTML
- Ahmia darknet search engine
- Docker + Render
- pytest (12 testów)

## Użycie

```
GET /api/search?q=python&num=10
GET /health
```

