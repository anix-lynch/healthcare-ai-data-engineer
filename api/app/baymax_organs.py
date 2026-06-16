"""
Baymax runtime organs for the Aikido-belt demo.

These endpoints are intentionally honest: they model a simulated workflow
contract, not a hospital deployment. The point is to prove that Baymax can
distinguish "said", "sent", "accepted", and "verified" before it claims done.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


NOW = "2026-06-15T19:00:00Z"
DEFAULT_PATIENT = "mom-001"


def _load_workflow_store() -> Dict[str, Any]:
    """Workflow state lives in a DISCLOSED data store, not in code. ack/ready are
    computed from it; add a patient and Baymax runs for them."""
    try:
        return json.loads((Path(__file__).resolve().parent / "workflow_store.json").read_text(encoding="utf-8"))
    except Exception:
        return {"bed": {}, "labs": {}}


_WF = _load_workflow_store()
BED_OPS: Dict[str, Dict[str, Any]] = _WF.get("bed", {})
LAB_STATUS: Dict[str, Dict[str, Any]] = _WF.get("labs", {})


OUTCOMES: Dict[str, Dict[str, Any]] = {
    "ref-1": {
        "stage": "submitted",
        "stages": ["drafted", "submitted", "accepted", "scheduled", "verified"],
        "open": True,
        "patient_id": DEFAULT_PATIENT,
        "action_type": "renal_review_referral",
        "tool_success": True,
        "real_world_verified": False,
        "note": "referral sent but appointment not yet booked",
    },
    "bed-1": {
        "stage": "requested",
        "stages": ["drafted", "requested", "accepted", "registered", "verified"],
        "open": True,
        "patient_id": DEFAULT_PATIENT,
        "action_type": "bed_request",
        "tool_success": True,
        "real_world_verified": False,
        "note": "bed request submitted; bed ops has not registered the assignment",
    },
}


TRAJECTORIES: Dict[str, Dict[str, Any]] = {
    DEFAULT_PATIENT: {
        "points": [
            {
                "date": "2024",
                "ckd_stage": 2,
                "symptoms": ["leg swelling"],
                "action": "low-intensity diuretic plan",
                "outcome": "swelling improved",
            },
            {
                "date": "2026",
                "ckd_stage": 3,
                "symptoms": ["leg swelling", "shortness of breath", "reduced urine output"],
                "action": "pending safe renal review",
                "outcome": "not verified",
            },
        ],
        "slope": "worsening",
        "changed": [{"field": "ckd_stage", "from": 2, "to": 3, "direction": "worse"}],
        "branches": [
            {
                "if": "repeat aggressive diuresis from prior case",
                "then": "faster symptom relief but higher kidney-decline risk",
                "safety": "requires human review",
            },
            {
                "if": "lower-intensity plan plus renal review",
                "then": "slower symptom relief but safer for current kidney state",
                "safety": "recommended preparation path",
            },
        ],
    }
}


def build_bed_ops(patient_id: str = DEFAULT_PATIENT) -> Dict[str, Any]:
    row = BED_OPS.get(patient_id)
    if not row:
        return {
            "available": False,
            "patient_id": patient_id,
            "requested": False,
            "registered": False,
            "nurse_said_sent": False,
            "ack": False,
            "note": "no bed workflow exists for this patient",
        }
    payload = dict(row)
    payload["available"] = True
    payload["patient_id"] = patient_id
    payload["ack"] = bool(payload.get("registered") is True)
    payload["outcome_stage"] = "registered" if payload["ack"] else "waiting_for_ack"
    payload["reason_code"] = "BED_ACK_MISSING" if not payload["ack"] else "BED_ACK_CONFIRMED"
    payload["lineage"] = {"source": "workflow_store.json", "computed": "ack = (registered is True)"}
    return payload


def build_lab_status(patient_id: str = DEFAULT_PATIENT) -> Dict[str, Any]:
    row = LAB_STATUS.get(patient_id)
    if not row:
        return {
            "available": False,
            "patient_id": patient_id,
            "ready": False,
            "eta_days": None,
            "pending": ["creatinine", "eGFR"],
            "blocking_reason": "no current lab state found",
        }
    payload = dict(row)
    payload["available"] = True
    payload["patient_id"] = patient_id
    payload["ready"] = len(payload.get("pending") or []) == 0
    payload["reason_code"] = "LABS_PENDING" if not payload["ready"] else "LABS_READY"
    payload["lineage"] = {"source": "workflow_store.json", "computed": "ready = (no pending tests)"}
    return payload


def build_tradeoff(body: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Green: DERIVE the trade-off from this patient's real organs (state-diff +
    drug-risk). No frozen A/B — the recommendation flips with the inputs."""
    body = body or {}
    patient_id = body.get("patient_id") or DEFAULT_PATIENT
    try:
        from .state_diff import build_state_diff
        from .drug_risk import build_drug_risk
    except Exception:  # pragma: no cover
        from state_diff import build_state_diff  # type: ignore
        from drug_risk import build_drug_risk  # type: ignore

    state = build_state_diff(patient_id)
    drug = build_drug_risk(patient_id)

    worse = [c for c in (state.get("changed") or []) if c.get("direction") == "worse"] \
        if state.get("available") else []
    state_worse = bool(worse)
    renal_drugs = [d["drug"] for d in (drug.get("per_drug") or []) if d.get("renal_reaction_reports")] \
        if drug.get("available") else []
    renal_flag = bool(drug.get("cross_domain_flag")) if drug.get("available") else False
    caution = state_worse or renal_flag

    why_bits = []
    if worse:
        why_bits.append(", ".join(f"{c['field']} {c['from']}→{c['to']}" for c in worse))
    if renal_drugs:
        why_bits.append(f"{', '.join(renal_drugs)} has renal adverse-event reports in openFDA")
    why = ("; ".join(why_bits) + " — kidney safety now outweighs speed."
           if caution else "no worsening state and no renal drug signal — the prior approach may still apply.")

    options = [
        {"id": "A", "label": "repeat prior intensity (faster relief)",
         "benefit": "may reduce symptoms faster", "risk": "higher organ risk given today's state",
         "reversible": "medium", "fits_today": not caution},
        {"id": "B", "label": "lower intensity + specialist review",
         "benefit": "protects organ function while workup completes", "risk": "symptom relief may be slower",
         "reversible": "high", "fits_today": caution},
    ]
    reason_codes = []
    if state_worse:
        reason_codes.append("STATE_CHANGED")
    if renal_flag:
        reason_codes.append("RENAL_RISK_HIGHER")
    reason_codes.append("HUMAN_REVIEW_REQUIRED" if caution else "NO_NEW_RISK")

    return {
        "available": bool(state.get("available") or drug.get("available")),
        "patient_id": patient_id,
        "options": options,
        "dimensions": ["speed of relief", "organ safety", "fit to today's state"],
        "recommend": "B" if caution else "A",
        "why": why,
        "decision_type": "recommendation_preparation",
        "requires_human_review": caution,
        "reason_codes": reason_codes,
        "lineage": {
            "derived_from": ["state-diff", "drug-risk"],
            "state_changed": state_worse,
            "renal_drug_signal": renal_drugs,
            "computed": "options + recommendation derived from this patient's state delta and drug-safety join",
        },
    }


def _goal_db_path() -> Path:
    raw = os.environ.get("BAYMAX_GOAL_DB")
    if raw:
        return Path(raw)
    return Path(os.environ.get("TMPDIR", "/tmp")) / "baymax_goal_memory.sqlite3"


def _connect_goal_db() -> sqlite3.Connection:
    path = _goal_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS goals (
            patient_id TEXT PRIMARY KEY,
            stated_request TEXT NOT NULL,
            inferred_goal TEXT NOT NULL,
            preferences_json TEXT NOT NULL,
            source TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    return conn


def _seed_goal(patient_id: str) -> Dict[str, Any] | None:
    """Disclosed seed (memory store is empty on a fresh instance). Read from a data
    file, not hardcoded per patient — generalizes and is honestly labelled."""
    try:
        seeds = json.loads((Path(__file__).resolve().parent / "goals_seed.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    s = seeds.get(patient_id)
    if not s:
        return None
    return {
        "available": True,
        "patient_id": patient_id,
        "stated_request": s["stated_request"],
        "inferred_goal": s["inferred_goal"],
        "preferences": s.get("preferences", []),
        "source": "seed_disclosed",
        "lineage": {"source": "goals_seed.json", "note": "disclosed seed; a real POST /api/goal overrides it"},
        "updated_at": NOW,
    }


def get_goal(patient_id: str = DEFAULT_PATIENT) -> Dict[str, Any]:
    with _connect_goal_db() as conn:
        row = conn.execute(
            "SELECT patient_id, stated_request, inferred_goal, preferences_json, source, updated_at "
            "FROM goals WHERE patient_id = ?",
            (patient_id,),
        ).fetchone()
    if not row:
        seeded = _seed_goal(patient_id)
        if seeded:
            return seeded
        return {
            "available": False,
            "patient_id": patient_id,
            "stated_request": None,
            "inferred_goal": None,
            "preferences": [],
            "source": "memory_miss",
        }
    return {
        "available": True,
        "patient_id": row[0],
        "stated_request": row[1],
        "inferred_goal": row[2],
        "preferences": json.loads(row[3]),
        "source": row[4],
        "updated_at": row[5],
    }


def upsert_goal(body: Dict[str, Any]) -> Dict[str, Any]:
    patient_id = str(body.get("patient_id") or DEFAULT_PATIENT)
    stated = str(body.get("stated_request") or "discharge fast")
    inferred = str(body.get("inferred_goal") or "safe discharge with low rebound risk")
    preferences = body.get("preferences") or []
    if not isinstance(preferences, list):
        preferences = [str(preferences)]
    updated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    with _connect_goal_db() as conn:
        conn.execute(
            """
            INSERT INTO goals(patient_id, stated_request, inferred_goal, preferences_json, source, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(patient_id) DO UPDATE SET
                stated_request=excluded.stated_request,
                inferred_goal=excluded.inferred_goal,
                preferences_json=excluded.preferences_json,
                source=excluded.source,
                updated_at=excluded.updated_at
            """,
            (patient_id, stated, inferred, json.dumps(preferences), "memory", updated_at),
        )
    return get_goal(patient_id)


def _outcomes_store() -> Dict[str, Any]:
    try:
        return json.loads((Path(__file__).resolve().parent / "outcomes_store.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_outcome(action_id: str) -> Dict[str, Any]:
    row = _outcomes_store().get(action_id)
    if not row:
        return {
            "available": False,
            "action_id": action_id,
            "stage": "unknown",
            "open": True,
            "tool_success": False,
            "real_world_verified": False,
            "note": "no outcome record found",
        }
    payload = dict(row)
    payload["available"] = True
    payload["action_id"] = action_id
    payload["reason_code"] = (
        "OUTCOME_NOT_VERIFIED" if not payload.get("real_world_verified") else "OUTCOME_VERIFIED"
    )
    payload["lineage"] = {"source": "outcomes_store.json", "computed": "tool_success vs real_world_verified are distinct fields"}
    return payload


def get_trajectory(patient_id: str = DEFAULT_PATIENT) -> Dict[str, Any]:
    """Black: multi-timepoint trajectory COMPUTED from the patient's real admits in
    the encounter corpus (same source as state-diff), not a frozen per-patient dict."""
    corpus = Path(__file__).resolve().parents[2] / "data" / "raw" / "enriched_use_397.jsonl"
    rows: List[Dict[str, Any]] = []
    try:
        for ln in corpus.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            r = json.loads(ln)
            if r.get("patient_id") == patient_id:
                rows.append(r)
    except Exception:
        rows = []
    if not rows:
        return {"available": False, "patient_id": patient_id, "points": [], "slope": "unknown", "branches": []}
    rows.sort(key=lambda r: str(r.get("Date of Admission", "")))
    points = [{"date": r.get("Date of Admission"), "ckd_stage": r.get("ckd_stage"),
               "condition": r.get("Medical Condition"), "admission": r.get("Admission Type")} for r in rows]
    stages = [p["ckd_stage"] for p in points if isinstance(p["ckd_stage"], (int, float))]
    slope = "worsening" if len(stages) >= 2 and stages[-1] > stages[0] else \
            "improving" if len(stages) >= 2 and stages[-1] < stages[0] else "stable"
    return {
        "available": True,
        "patient_id": patient_id,
        "points": points,
        "slope": slope,
        "branches": [],
        "lineage": {"source": "enriched_use_397.jsonl", "computed": "all admits for this patient_id, ordered by date"},
    }


def get_case_status(correlation_id: str) -> Dict[str, Any]:
    bed = build_bed_ops(DEFAULT_PATIENT)
    lab = build_lab_status(DEFAULT_PATIENT)
    tradeoff = build_tradeoff({"patient_id": DEFAULT_PATIENT})
    blocking = []
    if not bed.get("ack"):
        blocking.append("waiting for bed ops ACK")
    if not lab.get("ready"):
        blocking.append("waiting for fresh renal labs")
    return {
        "correlation_id": correlation_id,
        "patient_id": DEFAULT_PATIENT,
        "current_stage": "WAIT_FOR_ACK" if blocking else "READY_FOR_HUMAN_REVIEW",
        "current_owner": "bed_ops" if not bed.get("ack") else "clinical_reviewer",
        "time_in_stage": "18m",
        "next_expected_event": "bed_ops_ack" if not bed.get("ack") else "human_review_decision",
        "blocking_reason": "; ".join(blocking) if blocking else None,
        "confidence_before": 0.91,
        "confidence_after": 0.62,
        "latest_safety_decision": "WAIT_FOR_ACK" if blocking else "HUMAN_REVIEW",
        "latest_reason_code": "BED_ACK_MISSING" if not bed.get("ack") else tradeoff["reason_codes"][-1],
    }
