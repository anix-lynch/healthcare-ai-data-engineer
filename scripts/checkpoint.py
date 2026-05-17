"""
Layer 1 — lightweight data-quality gate (NOT HIPAA-grade, NOT enterprise cosplay).

Honest scope:
    Runs BEFORE dbt/gold mart release to catch the dumb-but-pipeline-killing
    failures: duplicate encounters, PII leaking into narrative fields, schema
    drift, discharge-before-admission, negative LoS, missing critical columns,
    missing audit-lineage fields when source_system claims to populate them.

NOT in scope (do NOT claim these):
    - HIPAA compliance certification
    - SOC 2 controls
    - probabilistic entity resolution (rapidfuzz / SPLINK)
    - clinical accuracy validation
    - real PII redaction (this is detection only; redaction lives elsewhere)
    - Great Expectations / Soda / Monte Carlo replacement
    - ingestion contract enforcement at the source-system boundary

Brutal one-liner:
    L2 has an exam proctor.
    Now L1 has a kitchen health inspector. Not a hospital lawyer. 😭

Usage:
    python scripts/checkpoint.py
        scans data/raw/healthcare_dataset_enriched.csv by default
        writes data/quality/l1_checkpoint_report.json
        exits 1 if any CRITICAL check fails, 0 if only WARNINGs

    python scripts/checkpoint.py --csv path/to/other.csv --strict
        --strict treats WARNINGs as critical
"""
from __future__ import annotations
import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = REPO_ROOT / "data" / "raw" / "healthcare_dataset_enriched.csv"
DEFAULT_REPORT = REPO_ROOT / "data" / "quality" / "l1_checkpoint_report.json"


# ── Expected schema (drift target) ──────────────────────────────────────────
EXPECTED_ORIGINAL_COLS = {
    "Name", "Age", "Gender", "Blood Type", "Medical Condition",
    "Date of Admission", "Doctor", "Hospital", "Insurance Provider",
    "Billing Amount", "Room Number", "Admission Type", "Discharge Date",
    "Medication", "Test Results",
}
EXPECTED_ENRICHED_COLS = {
    "chief_complaint", "hpi", "physician_note",
    "bp_systolic", "bp_diastolic", "heart_rate", "respiratory_rate",
    "temperature_f", "spo2_pct",
    "lab_panel_json", "lab_flags",
    "esi_tier_truth", "acuity_red_flags",
}
CRITICAL_NON_NULL_COLS = {
    "Name", "Age", "Gender", "Medical Condition",
    "Date of Admission", "Discharge Date",
}
OPTIONAL_AUDIT_COLS = {"source_system", "ingest_ts", "row_hash", "pii_redaction_status"}


# ── PII detection patterns (regex; detection only, not redaction) ───────────
PII_PATTERNS = {
    "ssn":          re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone":        re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "email":        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "credit_card":  re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "mrn_like":     re.compile(r"\bMRN[#:\s]?\d{6,}\b", re.I),
    "dob_like":     re.compile(r"\b(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/(19|20)\d{2}\b"),
}
# Free-text fields that should NEVER contain raw PII (LLM hallucination check)
NARRATIVE_FIELDS = ("chief_complaint", "hpi", "physician_note")


# ── Helpers ─────────────────────────────────────────────────────────────────
def _parse_date(s: str | None):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except (ValueError, TypeError):
            continue
    return None


def _encounter_key(row: dict) -> tuple[str, str]:
    return (row.get("Name", ""), row.get("Date of Admission", ""))


# ── Check implementations ───────────────────────────────────────────────────
def check_schema_drift(headers: list[str]) -> dict:
    present = set(headers)
    missing_required = sorted(EXPECTED_ORIGINAL_COLS - present)
    enriched_present = sorted(present & EXPECTED_ENRICHED_COLS)
    enriched_missing = sorted(EXPECTED_ENRICHED_COLS - present)
    unexpected = sorted(present - EXPECTED_ORIGINAL_COLS - EXPECTED_ENRICHED_COLS
                        - OPTIONAL_AUDIT_COLS - {"case_type", "scenario_hint", "holdout"})
    return {
        "n_columns_present": len(headers),
        "missing_required_original": missing_required,
        "enriched_columns_present": enriched_present,
        "enriched_columns_missing": enriched_missing,
        "unexpected_columns": unexpected,
        "verdict_critical": bool(missing_required),
    }


def check_critical_nulls(rows: list[dict]) -> dict:
    null_counts = {c: 0 for c in CRITICAL_NON_NULL_COLS}
    for r in rows:
        for c in CRITICAL_NON_NULL_COLS:
            v = r.get(c)
            if v is None or (isinstance(v, str) and not v.strip()):
                null_counts[c] += 1
    failing = {c: n for c, n in null_counts.items() if n > 0}
    return {
        "null_counts": null_counts,
        "failing_columns": failing,
        "verdict_critical": bool(failing),
    }


def check_duplicate_encounters(rows: list[dict]) -> dict:
    keys = [_encounter_key(r) for r in rows]
    counts = Counter(keys)
    dupes = {f"{name}|{admit}": n for (name, admit), n in counts.items() if n > 1}
    return {
        "n_unique_encounter_keys": len(counts),
        "n_duplicate_keys": len(dupes),
        "sample_duplicates": dict(list(dupes.items())[:5]),
        "verdict_critical": bool(dupes),
    }


def check_temporal_sanity(rows: list[dict]) -> dict:
    bad_order = 0
    negative_los = 0
    unparseable = 0
    for r in rows:
        a = _parse_date(r.get("Date of Admission"))
        d = _parse_date(r.get("Discharge Date"))
        if a is None or d is None:
            unparseable += 1
            continue
        delta = (d - a).days
        if delta < 0:
            bad_order += 1
        if delta < 0 or delta > 365:
            negative_los += 1
    return {
        "discharge_before_admission_count": bad_order,
        "negative_or_extreme_los_count": negative_los,
        "unparseable_dates": unparseable,
        "verdict_critical": bad_order > 0,
    }


def check_pii_in_narrative(rows: list[dict]) -> dict:
    """
    LLM hallucination guard: free-text enrich fields should not contain
    raw SSN/phone/email/credit card. Names in narrative are EXPECTED
    (the prompt enforces "use 'patient' or 'pt'") but we still flag
    if the raw Name appears verbatim — that's a leak from the source row.
    """
    hits_by_pattern = defaultdict(int)
    name_leaks = 0
    sample_offenders: list[dict] = []
    for r in rows:
        raw_name = (r.get("Name") or "").strip()
        for field in NARRATIVE_FIELDS:
            text = r.get(field) or ""
            for label, rx in PII_PATTERNS.items():
                if rx.search(text):
                    hits_by_pattern[label] += 1
                    if len(sample_offenders) < 5:
                        sample_offenders.append({"field": field, "pattern": label})
            if raw_name and len(raw_name) > 3 and raw_name.lower() in text.lower():
                name_leaks += 1
                if len(sample_offenders) < 5:
                    sample_offenders.append({"field": field, "pattern": "raw_name_leak"})
    return {
        "pii_pattern_hits": dict(hits_by_pattern),
        "raw_name_leaks_in_narrative": name_leaks,
        "sample_offenders": sample_offenders,
        "verdict_critical": (sum(hits_by_pattern.values()) > 0) or (name_leaks > 0),
    }


def check_patient_identity_resolvable(rows: list[dict]) -> dict:
    """
    Spot-check: every row's Name should resolve to a non-empty patient_id via
    the identity map produced by patient_identity.py. If the map is missing
    OR a row has no resolvable patient, flag it.
    """
    identity_path = REPO_ROOT / "data" / "derived" / "patient_identity_map.json"
    if not identity_path.exists():
        return {
            "identity_map_present": False,
            "unresolved_count": None,
            "verdict_critical": False,
            "note": (
                "data/derived/patient_identity_map.json missing — "
                "run scripts/patient_identity.py to enable this check"
            ),
        }
    with identity_path.open() as f:
        m = json.load(f)
    pid_lookup = set(m.get("encounter_to_patient", {}).values())
    n_unresolved = 0
    # We can't reverse-lookup name→patient_id from the dict; instead, recompute
    import hashlib
    def _pid(name: str) -> str:
        norm = " ".join((name or "").lower().split())
        if not norm: return "P-unknown"
        return "P-" + hashlib.sha256(norm.encode()).hexdigest()[:10]

    for r in rows:
        pid = _pid(r.get("Name", ""))
        if pid == "P-unknown" or pid not in pid_lookup:
            n_unresolved += 1
    return {
        "identity_map_present": True,
        "n_unique_patients_in_map": len(pid_lookup),
        "unresolved_count": n_unresolved,
        "verdict_critical": False,  # warning, not block
    }


def check_audit_lineage_optional(headers: list[str]) -> dict:
    """If any audit-lineage column is present, ALL of them should be present.
    Partial lineage is worse than no lineage."""
    present = set(headers) & OPTIONAL_AUDIT_COLS
    missing = OPTIONAL_AUDIT_COLS - present
    if not present:
        return {
            "audit_lineage_status": "absent (acceptable for Phase A)",
            "verdict_critical": False,
        }
    if present and missing:
        return {
            "audit_lineage_status": "partial",
            "present": sorted(present),
            "missing": sorted(missing),
            "verdict_critical": False,
            "note": "partial lineage detected — phase B should complete it",
        }
    return {"audit_lineage_status": "complete", "verdict_critical": False}


# ── Runner ──────────────────────────────────────────────────────────────────
def run(csv_path: Path, *, strict: bool = False) -> dict:
    if not csv_path.exists():
        return {"error": f"input CSV missing: {csv_path}", "exit_code": 2}

    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)

    report = {
        "checkpoint_version": 1,
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": str(csv_path),
        "n_rows": len(rows),
        "checks": {
            "schema_drift":            check_schema_drift(headers),
            "critical_nulls":          check_critical_nulls(rows),
            "duplicate_encounters":    check_duplicate_encounters(rows),
            "temporal_sanity":         check_temporal_sanity(rows),
            "pii_in_narrative":        check_pii_in_narrative(rows),
            "patient_identity":        check_patient_identity_resolvable(rows),
            "audit_lineage":           check_audit_lineage_optional(headers),
        },
    }

    critical = [name for name, c in report["checks"].items() if c.get("verdict_critical")]
    report["critical_failures"] = critical
    report["passed"] = not critical
    report["exit_code"] = 1 if critical else 0
    if strict:
        report["strict_mode"] = True
        # In strict mode, also fail on unresolved patient identities and partial lineage
        if report["checks"]["patient_identity"].get("unresolved_count"):
            report["critical_failures"].append("patient_identity (strict)")
            report["exit_code"] = 1
        if "partial" in report["checks"]["audit_lineage"].get("audit_lineage_status", ""):
            report["critical_failures"].append("audit_lineage (strict)")
            report["exit_code"] = 1

    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as critical")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress stdout, just write report")
    args = ap.parse_args()

    report = run(args.csv, strict=args.strict)
    if "error" in report:
        print(f"ERROR: {report['error']}", file=sys.stderr)
        sys.exit(report.get("exit_code", 2))

    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("w") as f:
        json.dump(report, f, indent=2, default=str)

    if not args.quiet:
        print(f"L1 checkpoint @ {report['scanned_at']}")
        print(f"  input:  {report['input_file']}")
        print(f"  rows:   {report['n_rows']}")
        print(f"  report: {args.report}")
        print()
        for name, c in report["checks"].items():
            verdict = "❌ CRITICAL" if c.get("verdict_critical") else "✅"
            print(f"  {verdict}  {name}")
        print()
        if report["passed"]:
            print("PASS — no critical failures.")
        else:
            print(f"FAIL — {len(report['critical_failures'])} critical: {report['critical_failures']}")

    sys.exit(report["exit_code"])


if __name__ == "__main__":
    main()
