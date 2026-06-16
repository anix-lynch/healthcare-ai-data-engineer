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


BED_OPS: Dict[str, Dict[str, Any]] = {
    DEFAULT_PATIENT: {
        "requested": True,
        "registered": False,
        "nurse_said_sent": True,
        "ack": False,
        "receiver": "bed_ops",
        "requested_at": "2026-06-15T18:42:00Z",
        "last_checked_at": NOW,
        "note": "nurse marked sent; bed not yet registered in ops system",
    }
}


LAB_STATUS: Dict[str, Dict[str, Any]] = {
    DEFAULT_PATIENT: {
        "ready": False,
        "eta_days": 2,
        "pending": ["creatinine", "eGFR"],
        "last_result_at": "2026-06-13T09:15:00Z",
        "blocking_reason": "renal panel is stale for a kidney-risk decision",
    }
}


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
    payload["reason_code"] = "LABS_PENDING" if not payload["ready"] else "LABS_READY"
    return payload


def build_tradeoff(body: Dict[str, Any] | None = None) -> Dict[str, Any]:
    body = body or {}
    patient_id = body.get("patient_id") or DEFAULT_PATIENT
    options: List[Dict[str, Any]] = [
        {
            "id": "A",
            "label": "repeat prior diuretic intensity",
            "benefit": "may reduce swelling faster",
            "risk": "higher kidney-risk now that CKD moved from stage 2 to stage 3",
            "reversible": "medium",
            "fits_today": False,
            "counterfactual": "would have looked safer in the 2024 state",
        },
        {
            "id": "B",
            "label": "lower intensity plus renal review",
            "benefit": "protects kidney function while workup completes",
            "risk": "symptom relief may be slower",
            "reversible": "high",
            "fits_today": True,
            "counterfactual": "if renal labs return reassuring, escalation can be reconsidered",
        },
    ]
    return {
        "patient_id": patient_id,
        "options": options,
        "dimensions": ["speed of relief", "kidney safety", "fit to today's state"],
        "recommend": "B",
        "why": "CKD stage 3 makes kidney risk more expensive than speed for this decision.",
        "decision_type": "recommendation_preparation",
        "requires_human_review": True,
        "reason_codes": ["STATE_CHANGED", "RENAL_RISK_HIGHER", "HUMAN_REVIEW_REQUIRED"],
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


def _default_goal(patient_id: str) -> Dict[str, Any]:
    return {
        "patient_id": patient_id,
        "stated_request": "discharge fast",
        "inferred_goal": "safe discharge with low rebound risk",
        "preferences": ["plain-language nightly update"],
        "source": "seed_memory",
        "updated_at": NOW,
    }


def get_goal(patient_id: str = DEFAULT_PATIENT) -> Dict[str, Any]:
    with _connect_goal_db() as conn:
        row = conn.execute(
            "SELECT patient_id, stated_request, inferred_goal, preferences_json, source, updated_at "
            "FROM goals WHERE patient_id = ?",
            (patient_id,),
        ).fetchone()
    if not row and patient_id == DEFAULT_PATIENT:
        return _default_goal(patient_id)
    if not row:
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


def get_outcome(action_id: str) -> Dict[str, Any]:
    row = OUTCOMES.get(action_id)
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
    return payload


def get_trajectory(patient_id: str = DEFAULT_PATIENT) -> Dict[str, Any]:
    row = TRAJECTORIES.get(patient_id)
    if not row:
        return {
            "available": False,
            "patient_id": patient_id,
            "points": [],
            "slope": "unknown",
            "branches": [],
        }
    payload = dict(row)
    payload["available"] = True
    payload["patient_id"] = patient_id
    return payload


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
