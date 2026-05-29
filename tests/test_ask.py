"""Tests for the L2 grounded-answer path (/api/ask).

These assert the *contract*, not the LLM output: retrieval always returns
cited sources, and the endpoint degrades gracefully (never 500s) when Vertex
is unavailable in the test environment.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[1]
API_MAIN = REPO_ROOT / "api" / "app" / "main.py"

spec = importlib.util.spec_from_file_location("api_main_ask", API_MAIN)
api_main = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(api_main)


def test_ask_returns_cited_sources():
    client = TestClient(api_main.app)
    r = client.get("/api/ask", params={"q": "chest pain cardiac red flags", "k": 4})
    assert r.status_code == 200
    body = r.json()
    assert body["corpus"] == "enriched_use_397.jsonl"
    assert isinstance(body["grounded"], bool)
    # Retrieval must always return numbered sources, grounded or not.
    assert 1 <= len(body["sources"]) <= 4
    first = body["sources"][0]
    assert first["doc"] == 1
    assert "score" in first and "condition" in first


def test_ask_grounds_only_on_redacted_corpus():
    """PII contract: the answer path must never reference the raw PII table."""
    client = TestClient(api_main.app)
    body = client.get("/api/ask", params={"q": "diabetes management"}).json()
    assert body["corpus"] == "enriched_use_397.jsonl"
    assert "healthcare_dataset.csv" not in body["corpus"]
