"""
Canonical end-to-end verification (shared by run_pipeline.py and watchdog.py).

A run is "successfully COMPLETED" ONLY when every promised check holds:
freshness within SLA, reconciliation passes, GE passes, dbt passes, and the
warehouse has no duplicate primary keys. last_successful_e2e is stamped ONLY
after this returns all_passed — so stages exiting 0 is necessary but not sufficient.

FAULT_VERIFY=1 forces a verification failure (test hook for "verify fail leaves
timestamp unchanged").
"""
from __future__ import annotations
import json, os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
Q = REPO / "data" / "quality"


def _load(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def verify():
    if os.environ.get("FAULT_VERIFY") == "1":
        return {"injected_failure": True, "all_passed": False}
    fr = _load(REPO / "data" / "freshness" / "freshness_report.json")
    rec = _load(Q / "openfda_reconciliation.json")
    ge = _load(Q / "openfda_ge_validation.json")
    rr = _load(REPO / "dbt-project" / "proof" / "run_results.json")
    checks = {
        "ingestion_within_sla": bool(fr and fr.get("sla_status") != "stale"),
        "reconciliation_passes": bool(rec and rec.get("reconciles")),
        "ge_passes": bool(ge and ge.get("success")),
        "dbt_passes": bool(rr and all(r["status"] in ("pass", "success") for r in rr["results"])),
    }
    try:
        from google.cloud import bigquery
        c = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID", "PROJECT"))
        ds = os.environ.get("BQ_DATASET", "healthcare_analytics")
        jc = bigquery.QueryJobConfig(maximum_bytes_billed=100 * 1024 * 1024)
        dup = list(c.query(f"SELECT COUNT(*)-COUNT(DISTINCT safetyreportid) d "
                           f"FROM `{ds}.raw_openfda_events`", job_config=jc).result())[0].d
        checks["no_duplicate_pks_in_bq"] = (dup == 0)
    except Exception as e:
        checks["no_duplicate_pks_in_bq"] = None
        checks["bq_dup_check_error"] = repr(e)[:120]
    checks["all_passed"] = all(v is True for k, v in checks.items() if k != "bq_dup_check_error")
    return checks
