#!/usr/bin/env python3
"""
Load the raw healthcare data into BigQuery as the dbt source table.

Builds ONE table `<project>.<dataset>.raw_healthcare_data`:
  - 55,500 base encounters (data/raw/healthcare_dataset.csv)
  - LEFT JOIN the 497 enriched rows (data/raw/healthcare_dataset_enriched.csv)
    on (name, date_of_admission) → enriched columns are NULL for the rest.

Columns are snake_cased so dbt's BigQuery models can reference them cleanly.
Auth = ADC (owner). Run: python scripts/load_bigquery.py
"""
from __future__ import annotations

import os
import pandas as pd
from google.cloud import bigquery

PROJECT = os.environ.get("GCP_PROJECT_ID", "bchan-genai-lab")
DATASET = os.environ.get("BQ_DATASET", "healthcare_analytics")
LOCATION = os.environ.get("BQ_LOCATION", "US")
TABLE = "raw_healthcare_data"

BASE_CSV = "data/raw/healthcare_dataset.csv"
ENRICHED_CSV = "data/raw/healthcare_dataset_enriched.csv"

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


def main() -> None:
    base = pd.read_csv(BASE_CSV).rename(columns=RENAME)
    enr = pd.read_csv(ENRICHED_CSV).rename(columns=RENAME)

    # enriched-only columns + join keys
    keep = ["name", "date_of_admission"] + [c for c in ENRICHED_COLS if c in enr.columns]
    enr_slice = enr[keep].drop_duplicates(subset=["name", "date_of_admission"])

    df = base.merge(enr_slice, on=["name", "date_of_admission"], how="left")

    # Parse dates → real DATE type in BigQuery
    for col in ("date_of_admission", "discharge_date"):
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    # esi_tier_truth as string (mixed/NA) keeps the API contract stable
    if "esi_tier_truth" in df.columns:
        df["esi_tier_truth"] = df["esi_tier_truth"].astype("string")

    client = bigquery.Client(project=PROJECT)
    client.create_dataset(
        bigquery.Dataset(f"{PROJECT}.{DATASET}"), exists_ok=True, timeout=60
    ).location = LOCATION

    table_id = f"{PROJECT}.{DATASET}.{TABLE}"
    job = client.load_table_from_dataframe(
        df,
        table_id,
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
    )
    job.result()

    n_enriched = df["chief_complaint"].notna().sum() if "chief_complaint" in df else 0
    print(f"✅ loaded {len(df):,} rows → {table_id} ({n_enriched} enriched)")


if __name__ == "__main__":
    main()
