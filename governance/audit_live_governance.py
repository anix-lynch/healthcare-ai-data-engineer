"""Audit live BigQuery governance controls and persist a hashed receipt."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery

PROJECT = "bchan-genai-lab"
BASE = "healthcare_analytics"
GOVERNED = "healthcare_governed"
AUDIT_TABLE = f"{PROJECT}.{BASE}.governance_audit_log"
PROOF = Path(__file__).resolve().parent / "proof_live_governance.json"

EXPECTED = {
    "fact_patient_encounters": {
        "encounter_id", "patient_key", "admission_date_key", "discharge_date_key",
        "doctor_key", "hospital_key", "diagnosis_key", "medication_key",
        "insurance_key", "billing_amount", "length_of_stay_days",
        "admission_type_key",
    },
    "pipeline_run_history": {
        "run_id", "dag_type", "started_at", "completed_at", "result", "attempts",
        "recovery_state", "final_verification", "duration_seconds",
    },
    "quarantine_records": {"raw_json", "reasons", "source_event_ts", "quarantined_at"},
}


def _columns(client: bigquery.Client, table: str) -> set[str]:
    return {field.name for field in client.get_table(f"{PROJECT}.{BASE}.{table}").schema}


def main() -> int:
    client = bigquery.Client(project=PROJECT)
    schema_checks = {}
    for table, expected in EXPECTED.items():
        actual = _columns(client, table)
        schema_checks[table] = {
            "required": sorted(expected),
            "missing": sorted(expected - actual),
            "unexpected": sorted(actual - expected),
            "pass": not (expected - actual),
        }

    quarantine = client.get_table(f"{PROJECT}.{BASE}.quarantine_records")
    safe_view = client.get_table(f"{PROJECT}.{GOVERNED}.vw_encounters_safe")
    proof = {
        "proof": "bullet4_live_governance_audit",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "schema_drift": schema_checks,
        "masking_view": {
            "table": safe_view.full_table_id.replace(":", "."),
            "type": safe_view.table_type,
            "pass": safe_view.table_type == "VIEW",
        },
        "retention": {
            "table": quarantine.full_table_id.replace(":", "."),
            "expires": quarantine.expires.isoformat() if quarantine.expires else None,
            "pass": quarantine.expires is not None,
        },
    }
    proof["pass"] = (
        all(item["pass"] for item in schema_checks.values())
        and proof["masking_view"]["pass"]
        and proof["retention"]["pass"]
    )
    canonical = json.dumps(proof, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    proof["evidence_sha256"] = digest
    PROOF.write_text(json.dumps(proof, indent=2) + "\n")

    event = {
        "event_ts": proof["audited_at"],
        "actor": "bchan-genai-deploy@sa",
        "event": "resume_b_governance_audit_pass" if proof["pass"] else "resume_b_governance_audit_fail",
        "subject": "healthcare_analytics schema+masking+retention",
        "evidence_sha256": digest,
    }
    errors = client.insert_rows_json(AUDIT_TABLE, [event])
    if errors:
        raise RuntimeError(errors)
    print(json.dumps(proof, indent=2))
    return 0 if proof["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
