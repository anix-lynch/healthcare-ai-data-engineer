"""
Quarantine replay — fix a quarantined record and replay it EXACTLY ONCE (Bullet 1 proof 2).

Re-classifies every quarantined record. Records that now satisfy the contract are
merged into the warehouse and recorded in a replay ledger (by row_hash). The ledger
makes replay idempotent/exactly-once: re-running never re-merges or double-counts a
record already replayed. Replayed records are removed from the quarantine file.

Auth: SA key. Bounded BigQuery. Writes data/quality/openfda_quarantine_replay.json.
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from google.cloud import bigquery

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ingestion"))
from quarantine import classify, QUAR
from bq_load import SCHEMA, COLS

PROJECT = os.environ.get("GCP_PROJECT_ID", "bchan-genai-lab")
DATASET = os.environ.get("BQ_DATASET", "healthcare_analytics")
TARGET = f"{PROJECT}.{DATASET}.raw_openfda_events"
LEDGER = REPO / "data" / "quarantine" / "replayed_ledger.json"
RPT = REPO / "data" / "quality" / "openfda_quarantine_replay.json"
JOB = bigquery.QueryJobConfig(maximum_bytes_billed=100 * 1024 * 1024)


def _merge(client, rows):
    if not rows:
        return 0
    stg = f"{PROJECT}.{DATASET}._stg_replay"
    client.load_table_from_json([{c: r.get(c) for c in COLS} for r in rows], stg,
        job_config=bigquery.LoadJobConfig(schema=SCHEMA, write_disposition="WRITE_TRUNCATE")).result()
    setc = ", ".join(f"T.{c}=S.{c}" for c in COLS if c != "safetyreportid")
    ic, iv = ", ".join(COLS), ", ".join(f"S.{c}" for c in COLS)
    client.query(f"""MERGE `{TARGET}` T USING `{stg}` S ON T.safetyreportid=S.safetyreportid
        WHEN MATCHED AND S.ingest_ts >= T.ingest_ts THEN UPDATE SET {setc}
        WHEN NOT MATCHED THEN INSERT ({ic}) VALUES ({iv})""", job_config=JOB).result()
    client.query(f"DROP TABLE `{stg}`", job_config=JOB).result()
    return len(rows)


def main():
    if not QUAR.exists():
        print("no quarantine file", file=sys.stderr); return 0
    quarantined = [json.loads(l) for l in QUAR.read_text().splitlines() if l.strip()]
    ledger = set(json.loads(LEDGER.read_text())) if LEDGER.exists() else set()

    still_bad, fixed_new, already = [], [], 0
    for r in quarantined:
        rec = {k: v for k, v in r.items() if k != "_quarantine_reason"}
        if classify(rec):                      # still malformed -> stays quarantined
            still_bad.append(r)
        elif rec["row_hash"] in ledger:        # already replayed -> exactly-once no-op
            already += 1
        else:
            fixed_new.append(rec)

    client = bigquery.Client(project=PROJECT)
    before = list(client.query(f"SELECT COUNT(*) c FROM `{TARGET}`", job_config=JOB).result())[0].c
    merged = _merge(client, fixed_new)
    after = list(client.query(f"SELECT COUNT(*) c FROM `{TARGET}`", job_config=JOB).result())[0].c

    ledger |= {r["row_hash"] for r in fixed_new}
    LEDGER.write_text(json.dumps(sorted(ledger), indent=2))
    QUAR.write_text("\n".join(json.dumps(r) for r in still_bad) + ("\n" if still_bad else ""))

    report = {"ran_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "quarantined_examined": len(quarantined), "still_malformed": len(still_bad),
              "newly_replayed": merged, "already_replayed_skipped": already,
              "warehouse_before": before, "warehouse_after": after,
              "net_new_rows": after - before,
              "exactly_once": (after - before) == merged}
    RPT.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
