"""Clinical plausibility rules — catches semantically absurd but schema-valid rows.

Example: age=2 + medication=Viagra passes GE (age 0–120, med column present)
but fails here. Rules live in data/quality/clinical_plausibility.yaml.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = REPO_ROOT / "data" / "quality" / "clinical_plausibility.yaml"

_FALLBACK = {
    "version": 1,
    "adult_only_medications": {
        "hard_min_age": 18,
        "soft_min_age": 18,
        "names": ["lipitor", "atorvastatin", "viagra", "sildenafil", "cialis", "tadalafil"],
    },
}


def load_rules(path: Path | None = None) -> dict:
    path = path or DEFAULT_RULES
    if path.exists() and yaml is not None:
        with path.open() as f:
            return yaml.safe_load(f) or _FALLBACK
    if path.exists():
        # minimal parse without PyYAML — only for the committed rule file shape
        text = path.read_text()
        if "lipitor" in text.lower():
            return _FALLBACK
    return _FALLBACK


def _row_age(row: dict[str, Any]) -> int | None:
    raw = row.get("Age") if row.get("Age") not in (None, "") else row.get("age")
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        return None


def _row_medication(row: dict[str, Any]) -> str:
    raw = row.get("Medication") if row.get("Medication") not in (None, "") else row.get("medication")
    return str(raw or "").strip().lower()


def check_row(row: dict[str, Any], rules: dict | None = None) -> list[str]:
    """Return violation reason codes; empty list = plausible enough to pass."""
    rules = rules or load_rules()
    reasons: list[str] = []

    age = _row_age(row)
    med = _row_medication(row)
    if age is None or not med:
        return reasons

    adult = rules.get("adult_only_medications") or {}
    hard_min = int(adult.get("hard_min_age", 12))
    soft_min = int(adult.get("soft_min_age", 18))
    adult_names = {str(n).strip().lower() for n in adult.get("names", [])}

    if med not in adult_names:
        return reasons

    if age < hard_min:
        reasons.append(f"clinical_plausibility_hard:age_{age}_with_adult_medication:{med}")
    elif age < soft_min:
        reasons.append(f"clinical_plausibility_soft:age_{age}_with_adult_medication:{med}")

    return reasons


def is_hard_violation(reason: str) -> bool:
    return reason.startswith("clinical_plausibility_hard:")


def check_rows(rows: list[dict], rules: dict | None = None) -> dict:
    rules = rules or load_rules()
    offenders: list[dict] = []
    soft_offenders: list[dict] = []
    for i, row in enumerate(rows):
        reasons = check_row(row, rules)
        if not reasons:
            continue
        entry = {
            "row_index": i,
            "name": row.get("Name") or row.get("name"),
            "age": _row_age(row),
            "medication": _row_medication(row),
            "reasons": reasons,
        }
        if any(is_hard_violation(r) for r in reasons):
            offenders.append(entry)
        else:
            soft_offenders.append(entry)
    return {
        "rules_file": str(DEFAULT_RULES),
        "n_rows": len(rows),
        "n_hard_violations": len(offenders),
        "n_soft_warnings": len(soft_offenders),
        "sample_hard_offenders": offenders[:10],
        "sample_soft_warnings": soft_offenders[:5],
        "verdict_critical": len(offenders) > 0,
    }


def row_to_ingest_record(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a CSV/BQ row (Title or snake case) for ingestion/validate.py."""
    def g(*keys, default=""):
        for k in keys:
            v = row.get(k)
            if v is not None and str(v).strip() != "":
                return v
        return default

    admit = g("date_of_admission", "Date of Admission")
    if hasattr(admit, "isoformat"):
        admit = admit.isoformat()

    return {
        "name": g("name", "Name"),
        "age": g("age", "Age"),
        "gender": g("gender", "Gender"),
        "date_of_admission": str(admit),
        "medical_condition": g("medical_condition", "Medical Condition"),
        "admission_type": g("admission_type", "Admission Type"),
        "medication": g("medication", "Medication"),
        "test_results": g("test_results", "Test Results"),
        "billing_amount": g("billing_amount", "Billing Amount", default=0),
    }
