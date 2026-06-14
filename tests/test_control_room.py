"""Tests for the B1 control-room payload."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[1]
API_MAIN = REPO_ROOT / "api" / "app" / "main.py"
sys_path = str(REPO_ROOT / "api")


spec = importlib.util.spec_from_file_location("api_main_control_room", API_MAIN)
api_main = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(api_main)


def test_control_room_endpoint_returns_payload():
    client = TestClient(api_main.app)
    r = client.get("/api/control-room")
    assert r.status_code == 200
    body = r.json()
    assert body["artifact"] == "B1_executive_dashboard"
    assert body["header"]["title"].startswith("📊 EXECUTIVE CONTROL ROOM")
    assert len(body["sections"]) == 5
    # first metric is the L1 quality-gate pass rate, evidence-computed by the snapshot builder
    assert body["sections"][0]["metrics"][0]["display_value"].endswith("🟢")


def test_portfolio_alias_matches_control_room():
    client = TestClient(api_main.app)
    a = client.get("/api/control-room").json()
    b = client.get("/api/portfolio/b1").json()
    assert a["header"]["subtitle"] == b["header"]["subtitle"]
    assert a["routing"] == b["routing"]
