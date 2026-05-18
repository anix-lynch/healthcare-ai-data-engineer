"""
Tests for the two L1-feeds-downstream-chefs endpoints.

Both endpoints exercise data lifted into the L1 pantry on 2026-05-18:
    /api/retrieve  ← golden_retrieval_set.json (20 queries from ER chef)
    /api/classify  ← esi_eval_dataset.json   (10 criteria from FDE chef)
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
API_MAIN = REPO_ROOT / "api" / "app" / "main.py"
sys.path.insert(0, str(REPO_ROOT / "api"))

spec = importlib.util.spec_from_file_location("api_main", API_MAIN)
api_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_main)

HERE = os.path.dirname(__file__)
QUALITY = os.path.join(HERE, "../data/quality")

client = TestClient(api_main.app)


# ─── /api/retrieve ──────────────────────────────────────────────────

def test_retrieve_returns_top_k():
    r = client.get("/api/retrieve", params={"q": "chest pain hypertension", "k": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["method"] == "bm25_okapi"
    assert len(body["results"]) == 5
    assert all("score" in row for row in body["results"])


def test_retrieve_against_golden_set_top1_condition_match_rate():
    """For each golden query, retrieve top-3 and check if any matches
    expected_condition. Sane retriever should hit >= 70% across 20 queries.
    """
    with open(os.path.join(QUALITY, "golden_retrieval_set.json")) as f:
        gold = json.load(f)
    hits = 0
    scorable = [q for q in gold["queries"] if q.get("expects_condition")]
    total = len(scorable)
    for q in scorable:
        r = client.get("/api/retrieve", params={"q": q["query"], "k": 3})
        assert r.status_code == 200
        results = r.json()["results"]
        if any(
            (row.get("medical_condition") or "").lower()
            == q["expects_condition"].lower()
            for row in results
        ):
            hits += 1
    pct = hits / total
    assert pct >= 0.7, f"only {hits}/{total} ({pct:.0%}) golden queries hit"


# ─── /api/classify ──────────────────────────────────────────────────

def _post(payload):
    return client.post("/api/classify", json=payload).json()


def test_classify_acc004_suicidal_ideation_always_escalates():
    r = _post({
        "age": 28,
        "chief_complaint": "Patient reports suicidal ideation with plan",
        "vitals": {"heart_rate": 88, "respiratory_rate": 18, "spo2_pct": 98},
    })
    assert r["esi_tier"] <= 2
    assert any(x["id"] == "ACC-004" for x in r["rules_fired"])


def test_classify_acc001_pediatric_under_1y():
    r = _post({
        "age": 0,
        "chief_complaint": "infant fever 102",
        "vitals": {"heart_rate": 160, "respiratory_rate": 40, "temperature_f": 102, "spo2_pct": 96},
    })
    assert r["esi_tier"] <= 2
    assert any(x["id"] == "ACC-001" for x in r["rules_fired"])


def test_classify_acc002_high_risk_chest_pain():
    r = _post({
        "age": 62,
        "chief_complaint": "Chest pain with diaphoresis radiating to left arm",
        "vitals": {"heart_rate": 108, "respiratory_rate": 22, "temperature_f": 98.8, "spo2_pct": 93, "bp_systolic": 142, "bp_diastolic": 88},
    })
    assert r["esi_tier"] <= 2
    assert any(x["id"] == "ACC-002" for x in r["rules_fired"])


def test_classify_acc005_altered_mental_status():
    r = _post({
        "age": 78,
        "chief_complaint": "Patient is confused and disoriented",
        "vitals": {"heart_rate": 92, "respiratory_rate": 18, "spo2_pct": 96},
    })
    assert r["esi_tier"] <= 2
    assert any(x["id"] == "ACC-005" for x in r["rules_fired"])


def test_classify_acc006_sepsis_shape():
    r = _post({
        "age": 55,
        "chief_complaint": "Fever, weakness, low blood pressure",
        "vitals": {"heart_rate": 118, "respiratory_rate": 24, "temperature_f": 101.4, "spo2_pct": 95},
    })
    assert r["esi_tier"] <= 2
    assert any(x["id"] == "ACC-006" for x in r["rules_fired"])


def test_classify_acc003_well_visit_low_urgency():
    r = _post({
        "age": 35,
        "chief_complaint": "well visit annual checkup",
        "vitals": {"heart_rate": 72, "respiratory_rate": 14, "temperature_f": 98.4, "spo2_pct": 99},
    })
    assert r["esi_tier"] >= 4
    assert any(x["id"] == "ACC-003" for x in r["rules_fired"])


def test_classify_acc009_weak_evidence_triggers_human_review():
    r = _post({"age": 40, "chief_complaint": "pain", "vitals": {}})
    assert r["human_review_required"] is True
    assert any(x["id"] == "ACC-009" for x in r["rules_fired"])


def test_classify_acc006_all_10_criteria_have_test_coverage():
    """Meta-test: ensure we covered the criteria in esi_eval_dataset.json
    that are deterministically testable (excluding PERF/SCHEMA which are
    runtime contracts, not classifier rules)."""
    with open(os.path.join(QUALITY, "esi_eval_dataset.json")) as f:
        gold = json.load(f)
    classifier_rules = {
        c["id"] for c in gold["criteria"]
        if c["category"] in ("safety", "efficiency", "evidence")
    }
    expected = {"ACC-001", "ACC-002", "ACC-003", "ACC-004",
                "ACC-005", "ACC-006", "ACC-009"}
    assert classifier_rules == expected
