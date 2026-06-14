"""GCP-native reliability probe for the live data platform."""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from google.cloud import bigquery


PROJECT = "bchan-genai-lab"
DATASET = "healthcare_analytics"
RUN_TABLE = f"{PROJECT}.{DATASET}.pipeline_run_history"
LOGGER = logging.getLogger("platform.reliability")


def _query_with_retry(client: bigquery.Client, sql: str, attempts: int = 2) -> tuple[list[Any], int]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return list(client.query(sql).result()), attempt
        except Exception as exc:  # Cloud errors are deliberately retried once.
            last_error = exc
            LOGGER.warning("reliability_query_retry", extra={"attempt": attempt, "error": str(exc)[:200]})
            if attempt < attempts:
                time.sleep(1)
    raise RuntimeError(f"BigQuery probe failed after {attempts} attempts: {last_error}")


def run_reliability_probe(client: bigquery.Client | None = None) -> dict[str, Any]:
    """Check the live warehouse, retry boundedly, persist and verify the run receipt."""
    client = client or bigquery.Client(project=PROJECT)
    started = datetime.now(timezone.utc)
    run_id = f"gcp-reliability-{uuid.uuid4().hex[:12]}"
    attempts = 0
    checks: dict[str, Any] = {}
    result = "SUCCESS"
    recovery_state = "not_needed"

    try:
        rows, used = _query_with_retry(
            client,
            f"""
            SELECT
              (SELECT COUNT(*) FROM `{PROJECT}.{DATASET}.fact_patient_encounters`) AS fact_rows,
              (SELECT COUNT(*) FROM `{PROJECT}.{DATASET}.raw_ingest_clean`) AS clean_rows,
              (SELECT COUNT(*) FROM `{PROJECT}.{DATASET}.quarantine_records`) AS quarantine_rows
            """,
        )
        attempts += used
        row = rows[0]
        total_ingested = int(row.clean_rows) + int(row.quarantine_rows)
        checks = {
            "warehouse_queryable": int(row.fact_rows) > 0,
            "fact_rows": int(row.fact_rows),
            "clean_rows": int(row.clean_rows),
            "quarantine_rows": int(row.quarantine_rows),
            "ingestion_accounted_for": total_ingested > 0,
        }
        if not checks["warehouse_queryable"] or not checks["ingestion_accounted_for"]:
            result = "FAILED"
            recovery_state = "escalate"
    except Exception as exc:
        attempts = 2
        result = "FAILED"
        recovery_state = "escalate"
        checks = {"warehouse_queryable": False, "error": str(exc)[:300]}

    completed = datetime.now(timezone.utc)
    receipt = {
        "run_id": run_id,
        "dag_type": "gcp_native_reliability_probe",
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "result": result,
        "attempts": attempts,
        "recovery_state": recovery_state,
        "final_verification": result == "SUCCESS" and all(
            checks.get(name, False) for name in ("warehouse_queryable", "ingestion_accounted_for")
        ),
        "duration_seconds": round((completed - started).total_seconds(), 3),
    }
    errors = client.insert_rows_json(RUN_TABLE, [receipt])
    if errors:
        raise RuntimeError(f"Could not persist reliability receipt: {errors}")

    verify_rows, verify_attempts = _query_with_retry(
        client,
        f"SELECT COUNT(*) AS n FROM `{RUN_TABLE}` WHERE run_id = '{run_id}'",
    )
    attempts += verify_attempts
    receipt["attempts"] = attempts
    receipt["receipt_persisted"] = int(verify_rows[0].n) == 1
    receipt["checks"] = checks

    LOGGER.info(
        "platform_reliability_probe",
        extra={"run_id": run_id, "result": result, "final_verification": receipt["final_verification"]},
    )
    return receipt
