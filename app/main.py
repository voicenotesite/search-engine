import os
import logging
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

from .searcher import search
from .filter import is_blocked

load_dotenv()

# Configure structured logging
log = logging.getLogger("search-engine")
log.setLevel(logging.INFO)
if not log.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Search Engine", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent.parent / "static"


@app.get("/", response_class=HTMLResponse)
def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return index.read_text(encoding="utf-8")
    return "<h1>Search Engine</h1><p>UI not found</p>"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/search")
@limiter.limit("30/minute")  # Rate limit: 30 requests per minute per IP
def api_search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    num: int = Query(10, ge=1, le=50),
    sort: str = Query("relevance", pattern="^(relevance|date|source)$"),
    range: str = Query("any", pattern="^(any|day|week|month|year)$"),
):
    if is_blocked(q):
        log.warning(f"Blocked query from {request.client.host}: {q}")
        raise HTTPException(
            status_code=403,
            detail="Zapytanie zostało zablokowane przez filtr bezpieczeństwa.",
        )

    try:
        log.info(f"Search query from {request.client.host}: {q}")
        results = search(q, num)
        return results
    except Exception as e:
        log.exception(f"search failed for query: {q}")
        raise HTTPException(status_code=500, detail=str(e))
