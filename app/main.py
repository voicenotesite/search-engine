import os
import logging
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .searcher import search
from .filter import is_blocked

load_dotenv()

log = logging.getLogger("search-engine")

app = FastAPI(title="Search Engine", version="1.0.0")

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
def api_search(
    q: str = Query(..., min_length=1, max_length=200),
    num: int = Query(10, ge=1, le=50),
    sort: str = Query("relevance", pattern="^(relevance|date|source)$"),
    range: str = Query("any", pattern="^(any|day|week|month|year)$"),
):
    if is_blocked(q):
        raise HTTPException(
            status_code=403,
            detail="Zapytanie zostało zablokowane przez filtr bezpieczeństwa.",
        )

    try:
        results = search(q, num)
        return results
    except Exception as e:
        log.exception("search failed")
        raise HTTPException(status_code=500, detail=str(e))
