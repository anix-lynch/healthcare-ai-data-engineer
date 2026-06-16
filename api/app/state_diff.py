"""
Baymax NERVES ⚡ — longitudinal state-diff computed from REAL encounter rows.

No per-patient answer is hardcoded. This module:
  1. loads the enriched encounter corpus
  2. groups a patient's encounters (admits) by patient_id, sorts by admission date
  3. diffs clinically meaningful fields between the FIRST and LAST admit
  4. returns the diff + lineage; available:false if the patient has < 2 admits

Lineage is honest: the corpus row dates + ids are reported. Mom's two admits are a
DISCLOSED synthetic record (every upstream patient has only 1 admit, so a real
'before vs now' needs a 2-admit patient to exist). Add any 2-admit patient and the
same generic differ runs for them.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

CORPUS = Path(__file__).resolve().parents[2] / "data" / "raw" / "enriched_use_397.jsonl"

# field -> True if a HIGHER value is worse (ckd stage), False if LOWER is worse (egfr).
_NUMERIC_FIELDS = {"ckd_stage": True, "egfr": False, "weight_kg": True, "fev1_pct": False}
_CATEGORICAL_FIELDS = ("Medical Condition", "Test Results", "Admission Type", "Medication")


def _load_rows(patient_id: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not CORPUS.exists():
        return rows
    for ln in CORPUS.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            rec = json.loads(ln)
        except Exception:
            continue
        if rec.get("patient_id") == patient_id:
            rows.append(rec)
    rows.sort(key=lambda r: str(r.get("Date of Admission", "")))
    return rows


def build_state_diff(patient_id: str = "__unknown__") -> Dict[str, Any]:
    rows = _load_rows(patient_id)
    if len(rows) < 2:
        return {
            "available": False,
            "patient_id": patient_id,
            "reason": f"only {len(rows)} admit on record — need 2+ for a longitudinal diff",
            "lineage": {"source": "enriched_use_397.jsonl", "admits_found": len(rows)},
        }

    first, last = rows[0], rows[-1]
    changed = []
    for field, higher_worse in _NUMERIC_FIELDS.items():
        a, b = first.get(field), last.get(field)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a != b:
            changed.append({"field": field, "from": a, "to": b,
                            "direction": "worse" if (b > a) == higher_worse else "better"})
    for field in _CATEGORICAL_FIELDS:
        a, b = first.get(field), last.get(field)
        if a and b and a != b:
            changed.append({"field": field, "from": a, "to": b, "direction": "changed"})

    return {
        "available": True,
        "patient_id": patient_id,
        "past": {"date": first.get("Date of Admission"), "ckd_stage": first.get("ckd_stage"),
                 "context": first.get("physician_note")},
        "now": {"date": last.get("Date of Admission"), "ckd_stage": last.get("ckd_stage"),
                "context": last.get("physician_note")},
        "changed": changed,
        "verdict": ("state changed — previous protocol may not transfer safely"
                    if changed else "state stable — prior approach may still apply"),
        "lineage": {
            "source": "enriched_use_397.jsonl",
            "computed": "diff between first and last admit for this patient_id",
            "admits": [r.get("Date of Admission") for r in rows],
            "synthetic": bool(last.get("synthetic")),
        },
    }
