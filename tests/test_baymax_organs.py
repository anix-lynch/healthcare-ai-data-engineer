"""Baymax belt endpoints: workflow, tradeoff, memory, and outcome proof."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
API_MAIN = REPO_ROOT / "api" / "app" / "main.py"
sys.path.insert(0, str(REPO_ROOT / "api"))

os.environ["BAYMAX_GOAL_DB"] = str(Path(os.environ.get("TMPDIR", "/tmp")) / "baymax_test_goals.sqlite3")

spec = importlib.util.spec_from_file_location("api_main_baymax", API_MAIN)
api_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_main)

client = TestClient(api_main.app)


def test_orange_bed_ack_requires_receiver_registration():
    r = client.get("/api/ops/bed", params={"patient_id": "mom-001"})
    assert r.status_code == 200
    body = r.json()
    assert body["requested"] is True
    assert body["nurse_said_sent"] is True
    assert body["registered"] is False
    assert body["ack"] is False
    assert body["outcome_stage"] == "waiting_for_ack"
    assert body["reason_code"] == "BED_ACK_MISSING"


def test_orange_lab_status_blocks_kidney_risk_decision():
    r = client.get("/api/lab-status", params={"patient_id": "mom-001"})
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is False
    assert body["eta_days"] == 2
    assert {"creatinine", "eGFR"}.issubset(set(body["pending"]))
    assert body["reason_code"] == "LABS_PENDING"


def test_green_tradeoff_explains_why_option_b_wins():
    r = client.post("/api/tradeoff", json={"patient_id": "mom-001", "context": {"ckd_stage": 3}})
    assert r.status_code == 200
    body = r.json()
    assert len(body["options"]) >= 2
    assert body["recommend"] == "B"
    assert body["requires_human_review"] is True
    assert "kidney" in body["why"].lower()
    assert all("counterfactual" in option for option in body["options"])


def test_blue_goal_is_recalled_from_memory_not_current_turn_echo():
    patient_id = "memory-test-001"
    write = client.post(
        "/api/goal",
        json={
            "patient_id": patient_id,
            "stated_request": "please discharge fast",
            "inferred_goal": "safe discharge with low rebound risk",
            "preferences": ["call daughter before discharge"],
        },
    )
    assert write.status_code == 200

    read = client.get("/api/goal", params={"patient_id": patient_id})
    assert read.status_code == 200
    body = read.json()
    assert body["source"] == "memory"
    assert body["inferred_goal"] == "safe discharge with low rebound risk"
    assert body["preferences"] == ["call daughter before discharge"]


def test_black_outcome_distinguishes_tool_success_from_verified_result():
    r = client.get("/api/outcome", params={"action_id": "ref-1"})
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "submitted"
    assert body["tool_success"] is True
    assert body["real_world_verified"] is False
    assert body["open"] is True
    assert body["reason_code"] == "OUTCOME_NOT_VERIFIED"


def test_black_trajectory_shows_worsening_path_and_branches():
    r = client.get("/api/trajectory", params={"patient_id": "mom-001"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["points"]) >= 2
    assert body["slope"] == "worsening"
    assert body["changed"][0]["field"] == "ckd_stage"
    assert body["branches"]


def test_status_endpoint_reports_waiting_and_blocking_state():
    r = client.get("/v1/cases/demo-correlation/status")
    assert r.status_code == 200
    body = r.json()
    assert body["current_stage"] == "WAIT_FOR_ACK"
    assert body["current_owner"] == "bed_ops"
    assert "bed ops ACK" in body["blocking_reason"]
    assert body["latest_safety_decision"] == "WAIT_FOR_ACK"
    assert body["latest_reason_code"] == "BED_ACK_MISSING"
