"""
Missing-record detection + safe backfill (Bullet 1 proof 6).

Compares the accepted canonical set (what SHOULD be in the warehouse) against what's
actually there. Missing ids are re-merged (backfill) idempotently. Proves: loss is
DETECTED by reconciliation and SAFELY restored without duplicates.

  before -> delete K ids from BQ (simulate loss) -> detect K missing -> backfill ->
  warehouse restored to `before`, missing now 0, no duplicate PKs.

Auth: SA key. Bounded BigQuery. Writes data/quality/openfda_backfill_test.json.
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from google.cloud import bigquery

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ingestion"))
from openfda_gate import _load
from bq_load import SCHEMA, COLS

PROJECT = os.environ.get("GCP_PROJECT_ID", "PROJECT")
DATASET = os.environ.get("BQ_DATASET", "healthcare_analytics")
MAIN = f"{PROJECT}.{DATASET}.raw_openfda_events"
JOB = bigquery.QueryJobConfig(maximum_bytes_billed=100 * 1024 * 1024)


def _ids_in_main(c):
    return {r.safetyreportid for r in c.query(f"SELECT safetyreportid FROM `{MAIN}`", job_config=JOB).result()}


def _merge(c, rows):
    if not rows:
        return
    stg = f"{PROJECT}.{DATASET}._stg_backfill"
    c.load_table_from_json([{col: r.get(col) for col in COLS} for r in rows], stg,
        job_config=bigquery.LoadJobConfig(schema=SCHEMA, write_disposition="WRITE_TRUNCATE")).result()
    setc = ", ".join(f"T.{col}=S.{col}" for col in COLS if col != "safetyreportid")
    ic, iv = ", ".join(COLS), ", ".join(f"S.{col}" for col in COLS)
    c.query(f"""MERGE `{MAIN}` T USING `{stg}` S ON T.safetyreportid=S.safetyreportid
        WHEN MATCHED AND S.ingest_ts >= T.ingest_ts THEN UPDATE SET {setc}
        WHEN NOT MATCHED THEN INSERT ({ic}) VALUES ({iv})""", job_config=JOB).result()
    c.query(f"DROP TABLE `{stg}`", job_config=JOB).result()


def main():
    c = bigquery.Client(project=PROJECT)
    canonical, _ = _load(REPO / "data" / "raw" / "openfda")
    by_id = {r["safetyreportid"]: r for r in canonical if r.get("safetyreportid")}

    def count():
        return list(c.query(f"SELECT COUNT(*) n FROM `{MAIN}`", job_config=JOB).result())[0].n

    before = count()
    lost = list(by_id)[:5]                       # simulate 5 lost records
    c.query(f"DELETE FROM `{MAIN}` WHERE safetyreportid IN UNNEST(@ids)",
            job_config=bigquery.QueryJobConfig(maximum_bytes_billed=100*1024*1024,
                query_parameters=[bigquery.ArrayQueryParameter("ids","STRING",lost)])).result()
    after_loss = count()

    # detect missing = accepted canonical ids NOT in warehouse
    in_wh = _ids_in_main(c)
    missing = [i for i in by_id if i not in in_wh]
    # backfill the missing canonical records
    _merge(c, [by_id[i] for i in missing])
    after_backfill = count()
    still_missing = [i for i in by_id if i not in _ids_in_main(c)]
    dup = list(c.query(f"SELECT COUNT(*)-COUNT(DISTINCT safetyreportid) d FROM `{MAIN}`", job_config=JOB).result())[0].d

    checks = {
        "loss_simulated": after_loss == before - len(lost),
        "missing_detected": set(missing) >= set(lost) and len(missing) == len(lost),
        "backfill_restored": after_backfill == before,
        "no_missing_after": len(still_missing) == 0,
        "no_duplicate_pks": dup == 0,
    }
    report = {"ran_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "warehouse_before": before, "after_loss": after_loss, "lost": len(lost),
              "missing_detected": len(missing), "after_backfill": after_backfill,
              "still_missing": len(still_missing), "dup_pks": dup,
              "checks": checks, "passed": all(checks.values())}
    (REPO / "data" / "quality" / "openfda_backfill_test.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"checks": checks, "passed": report["passed"]}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
