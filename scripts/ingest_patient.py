#!/usr/bin/env python3
"""Generic patient ingestion PIPE — proves generalization, not VIP2.

ANY patient flows through the SAME ingest() into the SAME disclosed stores mom
uses. There is no per-patient code: add a record to PATIENTS (or call ingest from
a real feed) and every organ computes for them. Idempotent per patient_id.

This is the anti-VIP2 fix: a second full story exists because it went through the
pipe, not because someone hand-edited a special file.
"""
from __future__ import annotations
import json
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "api" / "app"
CORPUS = Path(__file__).resolve().parents[1] / "data" / "raw" / "enriched_use_397.jsonl"


def _load_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def ingest(rec: dict) -> None:
    pid = rec["patient_id"]
    mark = rec.get("name_mark", f"SYNTHETIC-{pid}")

    # 1. encounter corpus (feeds retrieve · state-diff · trajectory · drug-risk meds)
    lines = []
    for ln in CORPUS.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get("patient_id") == pid:      # idempotent: drop this patient's old rows
            continue
        lines.append(ln)
    for a in rec["admits"]:
        row = {**a, "patient_id": pid, "Name": f"{mark} ({pid})", "synthetic": True}
        lines.append(json.dumps(row, ensure_ascii=False))
    CORPUS.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 2. workflow store (bed + lab)
    wf = _load_json(APP / "workflow_store.json", {"bed": {}, "labs": {}})
    wf.setdefault("bed", {})[pid] = rec["bed"]
    wf.setdefault("labs", {})[pid] = rec["lab"]
    (APP / "workflow_store.json").write_text(json.dumps(wf, indent=2, ensure_ascii=False), encoding="utf-8")

    # 3. goal memory seed
    goals = _load_json(APP / "goals_seed.json", {})
    goals[pid] = rec["goal"]
    (APP / "goals_seed.json").write_text(json.dumps(goals, indent=2, ensure_ascii=False), encoding="utf-8")

    # 4. outcome store
    outs = _load_json(APP / "outcomes_store.json", {})
    outs[rec["outcome"]["action_id"]] = rec["outcome"]
    (APP / "outcomes_store.json").write_text(json.dumps(outs, indent=2, ensure_ascii=False), encoding="utf-8")


PATIENTS = [
    {
        "patient_id": "dad-002", "name_mark": "SYNTHETIC-FATHER-COPD",
        "admits": [
            {"Age": "70", "Gender": "Male", "Medical Condition": "COPD",
             "Date of Admission": "2023-02-14", "Discharge Date": "2023-02-16",
             "Admission Type": "Elective", "Medication": "Prednisone", "Test Results": "Normal",
             "fev1_pct": 68, "chief_complaint": "Shortness of breath on exertion",
             "hpi": "70-year-old male with COPD, stable on inhalers. Home meds: prednisone, albuterol.",
             "physician_note": "COPD baseline, FEV1 68%. Stable.", "esi_tier_truth": "3"},
            {"Age": "73", "Gender": "Male", "Medical Condition": "COPD",
             "Date of Admission": "2026-06-09", "Discharge Date": "",
             "Admission Type": "Emergency", "Medication": "Prednisone", "Test Results": "Abnormal",
             "fev1_pct": 52, "chief_complaint": "Worsening breathlessness at rest",
             "hpi": "73-year-old male, COPD, declining lung function, dyspnea at rest. Home meds: prednisone, albuterol.",
             "physician_note": "COPD exacerbation, FEV1 down to 52% from 68%.", "esi_tier_truth": "2"},
        ],
        "bed": {"requested": True, "nurse_said_sent": True, "registered": True,
                "receiver": "bed_ops", "requested_at": "2026-06-09T08:00:00Z",
                "note": "bed registered in ops system"},
        "lab": {"pending": [], "eta_days": 0, "last_result_at": "2026-06-09T09:00:00Z", "blocking_reason": ""},
        "goal": {"stated_request": "avoid a hospital stay",
                 "inferred_goal": "stable breathing, manage COPD at home",
                 "preferences": ["call my daughter with updates"]},
        "outcome": {"action_id": "dad-ref-1", "stage": "verified",
                    "stages": ["drafted", "submitted", "accepted", "scheduled", "verified"],
                    "open": False, "patient_id": "dad-002", "action_type": "pulmonology_referral",
                    "tool_success": True, "real_world_verified": True,
                    "note": "pulmonology appointment booked and confirmed"},
    },
]


if __name__ == "__main__":
    for rec in PATIENTS:
        ingest(rec)
        print("ingested:", rec["patient_id"])
