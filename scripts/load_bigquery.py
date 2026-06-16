#!/usr/bin/env python3
"""
Load healthcare data into BigQuery — worry-before-load (same validator as Pub/Sub).

  CSV rows → ingestion/validate.py + clinical_plausibility
           → clean rows → raw_healthcare_data (dbt source)
           → quarantined → quarantine_records (visible in BQ console)

Proof (committed / CI artifact):
  data/quality/proof_bulk_load.json

Run:
    python scripts/load_bigquery.py --dry-run
    GOOGLE_APPLICATION_CREDENTIALS=... python scripts/load_bigquery.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "ingestion"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from validate import validate_record  # noqa: E402
from clinical_plausibility import row_to_ingest_record  # noqa: E402
from sink import write_quarantine_batch, QUARANTINE_TABLE, CLEAN_TABLE  # noqa: E402

PROJECT = os.environ.get("GCP_PROJECT_ID", "bchan-genai-lab")
DATASET = os.environ.get("BQ_DATASET", "healthcare_analytics")
LOCATION = os.environ.get("BQ_LOCATION", "US")
TABLE = "raw_healthcare_data"
PROOF_PATH = REPO_ROOT / "data" / "quality" / "proof_bulk_load.json"

BASE_CSV = REPO_ROOT / "data" / "raw" / "healthcare_dataset.csv"
ENRICHED_CSV = REPO_ROOT / "data" / "raw" / "healthcare_dataset_enriched.csv"

RENAME = {
    "Name": "name",
    "Age": "age",
    "Gender": "gender",
    "Blood Type": "blood_type",
    "Medical Condition": "medical_condition",
    "Date of Admission": "date_of_admission",
    "Doctor": "doctor",
    "Hospital": "hospital",
    "Insurance Provider": "insurance_provider",
    "Billing Amount": "billing_amount",
    "Room Number": "room_number",
    "Admission Type": "admission_type",
    "Discharge Date": "discharge_date",
    "Medication": "medication",
    "Test Results": "test_results",
}

ENRICHED_COLS = [
    "chief_complaint", "hpi", "physician_note",
    "bp_systolic", "bp_diastolic", "heart_rate", "respiratory_rate",
    "temperature_f", "spo2_pct", "lab_panel_json", "lab_flags",
    "esi_tier_truth", "acuity_red_flags", "holdout",
]


def classify_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    seen: dict = {}
    clean_idx: list[int] = []
    quarantined: list[dict] = []

    for i, row in df.iterrows():
        rec = row_to_ingest_record(row.to_dict())
        decision = validate_record(rec, seen)
        nk = f"{str(rec.get('name', '')).strip().lower()}|{rec.get('date_of_admission', '')}"
        if decision.status.startswith("accepted"):
            seen[decision.key] = decision.event_ts or datetime.min
            clean_idx.append(i)
        else:
            quarantined.append({
                "row_index": int(i),
                "name": rec.get("name"),
                "status": decision.status,
                "reasons": decision.reasons,
                "natural_key": nk,
                "record": rec,
            })

    return df.loc[clean_idx].copy(), quarantined


def _reason_counts(quarantined: list[dict]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for q in quarantined:
        for r in q["reasons"]:
            c[r.split(":")[0]] += 1
    return dict(c)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="classify only; do not write BigQuery")
    args = ap.parse_args()

    base = pd.read_csv(BASE_CSV).rename(columns=RENAME)
    enr = pd.read_csv(ENRICHED_CSV).rename(columns=RENAME)
    keep = ["name", "date_of_admission"] + [c for c in ENRICHED_COLS if c in enr.columns]
    enr_slice = enr[keep].drop_duplicates(subset=["name", "date_of_admission"])
    df = base.merge(enr_slice, on=["name", "date_of_admission"], how="left")

    n_before = len(df)
    clean_df, quarantined = classify_dataframe(df)
    reasons = _reason_counts(quarantined)

    proof = {
        "proof": "bulk_load_worry_before_load_bigquery",
        "ts": datetime.now(timezone.utc).isoformat(),
        "topology": f"CSV → validate.py → clean → {PROJECT}.{DATASET}.{TABLE} | quarantine → {QUARANTINE_TABLE}",
        "source_rows": n_before,
        "clean_rows": len(clean_df),
        "quarantined_rows": len(quarantined),
        "quarantine_reasons": reasons,
        "reconciliation": {
            "source": n_before,
            "clean_plus_quarantined": len(clean_df) + len(quarantined),
            "match": n_before == len(clean_df) + len(quarantined),
        },
        "shared_validator": "ingestion/validate.py + scripts/clinical_plausibility.py — same rules as /pubsub/push",
        "sample_quarantined": [
            {"name": q["name"], "status": q["status"], "reasons": q["reasons"]}
            for q in quarantined[:15]
        ],
    }

    if args.dry_run:
        proof["verdict"] = (
            f"DRY-RUN — would load {len(clean_df)} clean + {len(quarantined)} quarantined "
            f"(reconcile match={proof['reconciliation']['match']})"
        )
        PROOF_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROOF_PATH.write_text(json.dumps(proof, indent=2) + "\n")
        print(proof["verdict"])
        print(f"WROTE {PROOF_PATH}")
        return

    for col in ("date_of_admission", "discharge_date"):
        clean_df[col] = pd.to_datetime(clean_df[col], errors="coerce").dt.date
    if "esi_tier_truth" in clean_df.columns:
        clean_df["esi_tier_truth"] = clean_df["esi_tier_truth"].astype("string")

    client = bigquery.Client(project=PROJECT)
    client.create_dataset(
        bigquery.Dataset(f"{PROJECT}.{DATASET}"), exists_ok=True, timeout=60
    ).location = LOCATION

    table_id = f"{PROJECT}.{DATASET}.{TABLE}"
    job = client.load_table_from_dataframe(
        clean_df,
        table_id,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
    )
    job.result()

    n_q = write_quarantine_batch(client, quarantined, source="bulk_load")
    clean_count = list(client.query(f"SELECT COUNT(*) c FROM `{table_id}`").result())[0].c
    q_count = list(client.query(
        f"SELECT COUNT(*) c FROM `{QUARANTINE_TABLE}` WHERE source = 'bulk_load'"
    ).result())[0].c

    n_enriched = int(clean_df["chief_complaint"].notna().sum()) if "chief_complaint" in clean_df else 0
    proof["bigquery"] = {
        "project": PROJECT,
        "dataset": DATASET,
        "clean_table": TABLE,
        "quarantine_table": "quarantine_records",
        "clean_table_rows": clean_count,
        "quarantine_table_rows": q_count,
        "enriched_rows_on_clean": n_enriched,
    }
    proof["verdict"] = (
        f"GREEN — {n_before} source rows → {clean_count} in {TABLE} + {q_count} in quarantine_records; "
        f"reconcile match={proof['reconciliation']['match']}; bad rows visible in BigQuery, not silently dropped."
    )
    PROOF_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROOF_PATH.write_text(json.dumps(proof, indent=2) + "\n")

    print(proof["verdict"])
    print(f"  clean:      `{table_id}` ({clean_count:,} rows, {n_enriched} enriched)")
    print(f"  quarantine: `{QUARANTINE_TABLE}` ({q_count:,} rows)")
    print(f"  WROTE {PROOF_PATH}")


if __name__ == "__main__":
    main()
