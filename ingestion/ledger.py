"""
Persistent run-history ledger in BigQuery (Bullet 2 operational durability).

GitHub Actions runners are ephemeral — a last_successful_e2e.json written in one run
is gone the next, so the independently scheduled watchdog can't trust repo-local JSON
to know the latest VERIFIED primary success. This ledger is the durable source of truth:
both the primary DAG and the watchdog append every run here, and the watchdog reads
"latest verified successful PRIMARY run" from BigQuery.

Only result='success' AND final_verification=TRUE rows count as latest-verified — failed
or unverified runs are recorded but never advance the latest-success watermark.

Env: LEDGER_TABLE overrides the table name (tests use a throwaway table). 100MB caps, no
always-on compute, no Dataflow.
"""
from __future__ import annotations
import os
from datetime import datetime, timezone
from google.cloud import bigquery

PROJECT = os.environ.get("GCP_PROJECT_ID", "bchan-genai-lab")
DATASET = os.environ.get("BQ_DATASET", "healthcare_analytics")
TABLE = f"{PROJECT}.{DATASET}.{os.environ.get('LEDGER_TABLE', 'pipeline_run_history')}"
JOB = bigquery.QueryJobConfig(maximum_bytes_billed=100 * 1024 * 1024)

SCHEMA = [
    bigquery.SchemaField("run_id", "STRING"),
    bigquery.SchemaField("dag_type", "STRING"),          # primary | watchdog
    bigquery.SchemaField("started_at", "TIMESTAMP"),
    bigquery.SchemaField("completed_at", "TIMESTAMP"),
    bigquery.SchemaField("result", "STRING"),            # success | fail
    bigquery.SchemaField("attempts", "INT64"),
    bigquery.SchemaField("recovery_state", "STRING"),    # recovered | escalated | na
    bigquery.SchemaField("final_verification", "BOOL"),
    bigquery.SchemaField("duration_seconds", "FLOAT64"),
]


def _client():
    return bigquery.Client(project=PROJECT)


def ensure_table(c=None):
    c = c or _client()
    c.create_table(bigquery.Table(TABLE, schema=SCHEMA), exists_ok=True)


def record_run(dag_type, started_at, completed_at, result, attempts,
               recovery_state, final_verification, duration_seconds, c=None):
    c = c or _client()
    ensure_table(c)
    run_id = f"{dag_type}_{started_at}"
    # DML INSERT (not streaming insert) so the row is immediately queryable — the
    # watchdog/tests read latest-verified right after writing it.
    p = [
        bigquery.ScalarQueryParameter("run_id", "STRING", run_id),
        bigquery.ScalarQueryParameter("dag_type", "STRING", dag_type),
        bigquery.ScalarQueryParameter("started_at", "TIMESTAMP", started_at),
        bigquery.ScalarQueryParameter("completed_at", "TIMESTAMP", completed_at),
        bigquery.ScalarQueryParameter("result", "STRING", result),
        bigquery.ScalarQueryParameter("attempts", "INT64", attempts),
        bigquery.ScalarQueryParameter("recovery_state", "STRING", recovery_state),
        bigquery.ScalarQueryParameter("final_verification", "BOOL", final_verification),
        bigquery.ScalarQueryParameter("duration_seconds", "FLOAT64", duration_seconds),
    ]
    c.query(f"""INSERT INTO `{TABLE}`
        (run_id,dag_type,started_at,completed_at,result,attempts,recovery_state,final_verification,duration_seconds)
        VALUES (@run_id,@dag_type,@started_at,@completed_at,@result,@attempts,@recovery_state,@final_verification,@duration_seconds)""",
        job_config=bigquery.QueryJobConfig(maximum_bytes_billed=100*1024*1024, query_parameters=p)).result()
    return run_id


def latest_verified_primary(c=None):
    """Completed_at (ISO) of the latest verified successful PRIMARY run, or None."""
    c = c or _client()
    ensure_table(c)
    rows = list(c.query(
        f"SELECT MAX(completed_at) m FROM `{TABLE}` "
        f"WHERE dag_type='primary' AND result='success' AND final_verification=TRUE",
        job_config=JOB).result())
    m = rows[0].m
    return m.strftime("%Y-%m-%dT%H:%M:%SZ") if m else None


def reliability_metrics(c=None):
    c = c or _client()
    ensure_table(c)
    r = list(c.query(f"""
        SELECT
          COUNTIF(dag_type='primary') AS primary_runs,
          COUNTIF(dag_type='primary' AND result='success' AND final_verification) AS primary_ok,
          COUNTIF(result='fail' OR recovery_state='escalated') AS incidents,
          COUNTIF(recovery_state='recovered') AS recovered,
          COUNTIF(recovery_state IN ('recovered','escalated')) AS recovery_attempts,
          AVG(IF(recovery_state='recovered', duration_seconds, NULL)) AS mttr_seconds
        FROM `{TABLE}`""", job_config=JOB).result())[0]
    pr, ok = r.primary_runs or 0, r.primary_ok or 0
    ra, rec = r.recovery_attempts or 0, r.recovered or 0
    return {
        "dag_success_rate": round(ok / pr, 4) if pr else None,
        "incident_count": r.incidents or 0,
        "retry_recovery_rate": round(rec / ra, 4) if ra else None,
        "mttr_seconds": round(r.mttr_seconds, 1) if r.mttr_seconds is not None else None,
        "primary_runs": pr,
    }


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
