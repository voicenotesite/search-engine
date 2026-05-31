# DarkSearch

**Wyszukiwarka clearnet + darknet** z filtrem nielegalnego contentu.

🌐 **Live:** https://search-engine-l2zt.onrender.com

| Warstwa | Źródło |
|---------|--------|
| Clearnet | DuckDuckGo Lite (scraping) |
| Darknet | Ahmia API (wyniki .onion) |
| Filtr | NCII – regex + blokada 403 |

## Stack

- FastAPI + uvicorn
- BeautifulSoup4 + requests
- DuckDuckGo Lite HTML
- Docker + Render
- pytest (12 testów)

