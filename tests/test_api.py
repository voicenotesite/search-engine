from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.filter import is_blocked, filter_results


client = TestClient(app)


class TestFilter:
    def test_clean_query(self):
        assert is_blocked("python programming tutorial") is False

    def test_blocked_cp(self):
        assert is_blocked("child porn") is True

    def test_blocked_weapon(self):
        assert is_blocked("buy illegal firearm") is True

    def test_blocked_hitman(self):
        assert is_blocked("hire a hitman") is True

    def test_filter_results_blocks_bad(self):
        results = [
            {"title": "good", "snippet": "python tutorial", "url": "http://x.com"},
            {"title": "bad", "snippet": "child porn video", "url": "http://y.com"},
        ]
        clean = filter_results(results)
        assert len(clean) == 1
        assert clean[0]["title"] == "good"

    def test_filter_results_keeps_all_clean(self):
        results = [
            {"title": "a", "snippet": "hello world", "url": "http://a.com"},
            {"title": "b", "snippet": "how to code", "url": "http://b.com"},
        ]
        assert len(filter_results(results)) == 2


class TestAPI:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "DarkSearch" in r.text

    def test_search_blocked_query(self):
        r = client.get("/api/search?q=child+porn")
        assert r.status_code == 403
        assert "zablokowane" in r.json()["detail"].lower()

    def test_search_no_query(self):
        r = client.get("/api/search")
        assert r.status_code == 422

    def test_search_empty_query(self):
        r = client.get("/api/search?q=")
        assert r.status_code == 422

    def test_search_long_query(self):
        r = client.get("/api/search?q=" + "a" * 201)
        assert r.status_code == 422
