"""
Land the canonical openFDA view into BigQuery `raw_openfda_events` (Trust branch).

Idempotent by construction: reuses the SAME canonical dedup as the quality gate
(latest row per safetyreportid), stages it, then MERGEs on safetyreportid so
running this N times converges to the same target table — no duplicate rows.
This is the load step dbt's staging model (source: raw_openfda_events) depends on.

Auth: service-account key via GOOGLE_APPLICATION_CREDENTIALS (headless, no popup).
Requires the SA to have roles/bigquery.dataEditor + jobUser on the dataset.

Usage:
    python ingestion/bq_load.py            # uses GCP_PROJECT_ID / BQ_DATASET env
"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ingestion"))
from openfda_gate import _load  # reuse canonical dedup — one source of truth

PROJECT = os.environ.get("GCP_PROJECT_ID", "bchan-genai-lab")
DATASET = os.environ.get("BQ_DATASET", "healthcare_analytics")
TARGET = "raw_openfda_events"

SCHEMA = [
    bigquery.SchemaField("safetyreportid", "STRING"),
    bigquery.SchemaField("receivedate", "STRING"),
    bigquery.SchemaField("serious", "STRING"),
    bigquery.SchemaField("seriousnessdeath", "STRING"),
    bigquery.SchemaField("occurcountry", "STRING"),
    bigquery.SchemaField("patient_sex", "STRING"),
    bigquery.SchemaField("patient_age", "STRING"),
    bigquery.SchemaField("primary_drug", "STRING"),
    bigquery.SchemaField("n_drugs", "INT64"),
    bigquery.SchemaField("reactions", "STRING"),
    bigquery.SchemaField("n_reactions", "INT64"),
    bigquery.SchemaField("source_system", "STRING"),
    bigquery.SchemaField("ingest_ts", "STRING"),
    bigquery.SchemaField("row_hash", "STRING"),
]
COLS = [f.name for f in SCHEMA]


def main():
    rows, idem = _load(REPO / "data" / "raw" / "openfda")
    if not rows:
        print("ERROR: no landed openFDA data to load", file=sys.stderr)
        return 1
    rows = [{c: r.get(c) for c in COLS} for r in rows]

    client = bigquery.Client(project=PROJECT)
    target = f"{PROJECT}.{DATASET}.{TARGET}"
    stage = f"{PROJECT}.{DATASET}._stg_{TARGET}"
    JOB = bigquery.QueryJobConfig(maximum_bytes_billed=100 * 1024 * 1024)  # 100MB cap (cost guard; ~$0)

    def count(tbl):
        try:
            return list(client.query(f"SELECT COUNT(*) c FROM `{tbl}`", job_config=JOB).result())[0].c
        except Exception:
            return 0

    before = count(target)

    # 1. stage the canonical batch (truncate-load — deterministic)
    client.load_table_from_json(
        rows, stage,
        job_config=bigquery.LoadJobConfig(schema=SCHEMA, write_disposition="WRITE_TRUNCATE"),
    ).result()
    print(f"[stage] loaded {len(rows)} canonical rows -> {stage}")

    # 2. ensure target exists, then MERGE (idempotent upsert on safetyreportid)
    client.query(f"CREATE TABLE IF NOT EXISTS `{target}` AS SELECT * FROM `{stage}` WHERE 1=0",
                 job_config=JOB).result()
    set_clause = ", ".join(f"T.{c}=S.{c}" for c in COLS if c != "safetyreportid")
    insert_cols, insert_vals = ", ".join(COLS), ", ".join(f"S.{c}" for c in COLS)
    client.query(f"""
        MERGE `{target}` T USING `{stage}` S ON T.safetyreportid = S.safetyreportid
        WHEN MATCHED AND S.ingest_ts >= T.ingest_ts THEN UPDATE SET {set_clause}
        WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals})
    """, job_config=JOB).result()

    after = count(target)
    inserted = after - before
    matched = len(rows) - inserted          # already existed → updated or unchanged
    # window-scoped reconciliation: how many of THIS batch's ids are in the warehouse?
    # (stays correct when the warehouse accumulates history beyond this slice)
    batch_ids = [r["safetyreportid"] for r in rows if r.get("safetyreportid")]
    wq = bigquery.QueryJobConfig(
        maximum_bytes_billed=100 * 1024 * 1024,
        query_parameters=[bigquery.ArrayQueryParameter("ids", "STRING", batch_ids)])
    window_in_warehouse = list(client.query(
        f"SELECT COUNT(*) c FROM `{target}` WHERE safetyreportid IN UNNEST(@ids)", job_config=wq).result())[0].c
    client.query(f"DROP TABLE `{stage}`", job_config=JOB).result()

    # 3. reconciliation report (leg a: API→accepted from manifest · leg b: accepted→warehouse)
    man = json.loads((REPO / "data" / "freshness" / "ingest_manifest.json").read_text())
    rec_a = man.get("reconciliation", {})
    # warehouse lag = clock #3 (ingest_ts → landed in BigQuery)
    loaded_at = datetime.now(timezone.utc)
    ingest_ts = datetime.strptime(man["last_successful_ingest"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    warehouse_lag_s = round((loaded_at - ingest_ts).total_seconds(), 1)
    report = {
        "generated_at": man.get("last_successful_ingest"),
        "source_url": man.get("source_url"), "window": man.get("window"),
        "leg_a_source_to_accepted": {
            **rec_a,
            "note": "fetched = accepted + rejected_null_key + rejected_duplicate_in_pull",
        },
        "leg_b_accepted_to_warehouse": {
            "canonical_rows_across_pulls": idem["canonical_rows"],
            "raw_rows_all_pulls": idem["raw_rows"],
            "cross_pull_collapsed": idem["cross_pull_collapsed"],
            "warehouse_before": before, "warehouse_after": after,
            "merge_inserted": inserted, "merge_matched_updated_or_unchanged": matched,
            "net_new_rows": inserted,
            "loaded_at": loaded_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "warehouse_lag_seconds": warehouse_lag_s,
        },
        "window_reconciliation": {
            "batch_accepted": len(rows),
            "batch_ids_present_in_warehouse": window_in_warehouse,
            "warehouse_total_all_windows": after,
            "note": "reconcile THIS batch's ids (window-scoped), not the whole warehouse — "
                    "stays correct as history accumulates beyond the current slice",
        },
        "reconciles": (
            rec_a.get("balances", False)
            and window_in_warehouse == len(rows)   # window-scoped, not total-warehouse
            and matched + inserted == len(rows)
        ),
    }
    out = REPO / "data" / "quality" / "openfda_reconciliation.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[merge] {target}: before={before} after={after} inserted={inserted} "
          f"matched={matched} | reconciles={report['reconciles']} -> {out.relative_to(REPO)}")
    return 0 if report["reconciles"] else 1


if __name__ == "__main__":
    sys.exit(main())
