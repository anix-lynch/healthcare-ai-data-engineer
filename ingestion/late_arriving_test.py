"""
Late-arriving / revised-record handling test (Trust + resilience).

Proves the warehouse MERGE handles real-world disorder without breaking:
  1. late-arriving NEW report (old receivedate, arrives in a later pull) -> INSERTED
  2. REVISED report (same id, newer ingest_ts, changed value)           -> UPDATED, not duplicated
  3. STALE replay (same id, OLDER ingest_ts)                            -> IGNORED (newer wins)

Uses clearly-synthetic ids (TEST_LATE_*) so cleanup is a safe DELETE — real rows untouched.
Auth: SA key. Bounded by maximum_bytes_billed. Writes data/quality/openfda_late_arriving.json.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
from google.cloud import bigquery

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ingestion"))
from bq_load import SCHEMA  # identical column types as the real loader (ingest_ts STRING)
PROJECT = os.environ.get("GCP_PROJECT_ID", "bchan-genai-lab")
DATASET = os.environ.get("BQ_DATASET", "healthcare_analytics")
TARGET = f"{PROJECT}.{DATASET}.raw_openfda_events"
TID = "TEST_LATE_0001"
JOB = bigquery.QueryJobConfig(maximum_bytes_billed=100 * 1024 * 1024)


def _row(serious, ingest_ts, receivedate="20200101"):
    return {"safetyreportid": TID, "receivedate": receivedate, "serious": serious,
            "seriousnessdeath": None, "occurcountry": "US", "patient_sex": "1",
            "patient_age": None, "primary_drug": "TESTDRUG", "n_drugs": 1,
            "reactions": "Headache", "n_reactions": 1, "source_system": "openfda_faers",
            "ingest_ts": ingest_ts, "row_hash": "test"+serious}


def main():
    c = bigquery.Client(project=PROJECT)
    cols = list(_row("1", "x").keys())
    setc = ", ".join(f"T.{x}=S.{x}" for x in cols if x != "safetyreportid")
    ic, iv = ", ".join(cols), ", ".join(f"S.{x}" for x in cols)
    stg = f"{PROJECT}.{DATASET}._stg_late"

    def merge(row):
        c.load_table_from_json([row], stg, job_config=bigquery.LoadJobConfig(
            write_disposition="WRITE_TRUNCATE", schema=SCHEMA)).result()
        c.query(f"""MERGE `{TARGET}` T USING `{stg}` S ON T.safetyreportid=S.safetyreportid
            WHEN MATCHED AND S.ingest_ts >= T.ingest_ts THEN UPDATE SET {setc}
            WHEN NOT MATCHED THEN INSERT ({ic}) VALUES ({iv})""", job_config=JOB).result()

    def state():
        n = list(c.query(f"SELECT COUNT(*) n FROM `{TARGET}`", job_config=JOB).result())[0].n
        r = list(c.query(f"SELECT serious FROM `{TARGET}` WHERE safetyreportid='{TID}'",
                         job_config=JOB).result())
        return n, (r[0].serious if r else None)

    c.query(f"DELETE FROM `{TARGET}` WHERE safetyreportid='{TID}'", job_config=JOB).result()
    before, _ = state()

    merge(_row("1", "2026-06-08T10:00:00Z"))              # 1. late new arrival
    after_insert, ser_insert = state()
    merge(_row("2", "2026-06-08T12:00:00Z"))              # 2. revised (newer ts, serious 1->2)
    after_revise, ser_revise = state()
    merge(_row("1", "2026-06-08T08:00:00Z"))              # 3. stale replay (older ts)
    after_stale, ser_stale = state()

    c.query(f"DELETE FROM `{TARGET}` WHERE safetyreportid='{TID}'", job_config=JOB).result()
    c.query(f"DROP TABLE IF EXISTS `{stg}`", job_config=JOB).result()
    final, _ = state()

    checks = {
        "late_new_inserted":   after_insert == before + 1 and ser_insert == "1",
        "revised_updated_not_duplicated": after_revise == before + 1 and ser_revise == "2",
        "stale_replay_ignored": after_stale == before + 1 and ser_stale == "2",
        "cleanup_restored":    final == before,
    }
    report = {"test": "late_arriving_and_revision", "target": TARGET,
              "counts": {"before": before, "after_late_insert": after_insert,
                         "after_revision": after_revise, "after_stale_replay": after_stale,
                         "after_cleanup": final},
              "serious_value": {"after_insert": ser_insert, "after_revise": ser_revise,
                                "after_stale": ser_stale},
              "checks": checks, "passed": all(checks.values())}
    out = REPO / "data" / "quality" / "openfda_late_arriving.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps({"checks": checks, "passed": report["passed"]}, indent=2))
    print(f"-> {out.relative_to(REPO)}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
