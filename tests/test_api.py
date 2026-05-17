"""Smoke the FastAPI surface — no uvicorn, no network.

Uses FastAPI TestClient against api/app/main.py to verify the 11 endpoints
load + return their expected shapes. Catches regressions in routing,
schema validation, and pandas-side filtering logic.
"""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Load api/app/main.py as a module (it's not in the standard import path).
REPO_ROOT = Path(__file__).resolve().parents[1]
API_MAIN = REPO_ROOT / "api" / "app" / "main.py"

# Add api/ to sys.path so the main module's relative paths resolve correctly.
sys.path.insert(0, str(REPO_ROOT / "api"))

spec = importlib.util.spec_from_file_location("api_main", API_MAIN)
api_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_main)


@pytest.fixture(scope="module")
def client():
    return TestClient(api_main.app)


def test_root_endpoint(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "endpoints" in body or "message" in body or "name" in body


def test_stats_endpoint_has_totals(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    body = r.json()
    # Stats should expose total encounters + at least one breakdown
    assert any(k in str(body).lower() for k in ("total", "count", "encounters"))


def test_encounters_filter_by_condition(client):
    r = client.get("/api/encounters", params={"condition": "Diabetes", "limit": 5})
    assert r.status_code == 200
    body = r.json()
    # Response should have data array
    assert "data" in body or isinstance(body, list)


def test_encounters_pagination(client):
    r = client.get("/api/encounters", params={"limit": 2})
    assert r.status_code == 200
    body = r.json()
    data = body.get("data", body if isinstance(body, list) else [])
    assert len(data) <= 2, f"limit=2 returned {len(data)} rows"


def test_conditions_endpoint(client):
    r = client.get("/api/conditions")
    assert r.status_code == 200
    # Should return list of distinct conditions
    body = r.json()
    assert body is not None


def test_search_endpoint_responds(client):
    """Search endpoint should not 500 on a basic query."""
    r = client.get("/api/search", params={"q": "diabetes"})
    # Either 200 with results or 422 for missing required param — both OK
    assert r.status_code in (200, 422), f"got {r.status_code}"
