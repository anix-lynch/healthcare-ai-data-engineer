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
import os, sys
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

    # 1. stage the canonical batch (truncate-load — deterministic)
    job = client.load_table_from_json(
        rows, stage,
        job_config=bigquery.LoadJobConfig(
            schema=SCHEMA, write_disposition="WRITE_TRUNCATE"),
    )
    job.result()
    print(f"[stage] loaded {len(rows)} canonical rows -> {stage}")

    # 2. ensure target exists, then MERGE (idempotent upsert on safetyreportid)
    client.query(
        f"CREATE TABLE IF NOT EXISTS `{target}` "
        f"AS SELECT * FROM `{stage}` WHERE 1=0"
    ).result()
    set_clause = ", ".join(f"T.{c}=S.{c}" for c in COLS if c != "safetyreportid")
    insert_cols = ", ".join(COLS)
    insert_vals = ", ".join(f"S.{c}" for c in COLS)
    merge = client.query(f"""
        MERGE `{target}` T
        USING `{stage}` S
        ON T.safetyreportid = S.safetyreportid
        WHEN MATCHED AND S.ingest_ts >= T.ingest_ts THEN UPDATE SET {set_clause}
        WHEN NOT MATCHED THEN INSERT ({insert_cols}) VALUES ({insert_vals})
    """)
    merge.result()
    n = list(client.query(f"SELECT COUNT(*) c FROM `{target}`").result())[0].c
    print(f"[merge] target `{target}` now has {n} rows "
          f"(canonical {idem['canonical_rows']} from {idem['raw_rows']} raw, "
          f"{idem['cross_pull_collapsed']} collapsed)")
    client.query(f"DROP TABLE `{stage}`").result()
    return 0


if __name__ == "__main__":
    sys.exit(main())
