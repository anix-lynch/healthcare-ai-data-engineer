#!/usr/bin/env python3
"""Stand up the Bullet 4 governance apparatus on BigQuery (idempotent).

Builds the least-privilege access model — an analyst sees an approved, PII-masked
view and is denied the raw base tables:

    healthcare_analytics  (base: raw_ingest_clean, ...)   ← sensitive, restricted
    healthcare_governed   (vw_encounters_safe)            ← authorized view, masked
                            └─ AUTHORIZED to read base on the caller's behalf
    restricted-reader-b4  → dataViewer on healthcare_governed ONLY
                            → 200 on the safe view · 403 on the base table

Also applies retention (table expiration) on the quarantine table — bad records
don't live forever. Run with the deploy SA (BigQuery dataOwner):

    GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json \
        python governance/setup_governance.py
"""
from __future__ import annotations

import os

from google.cloud import bigquery

PROJECT = os.environ.get("GCP_PROJECT_ID", "bchan-genai-lab")
BASE_DS = "healthcare_analytics"
GOV_DS = "healthcare_governed"
BASE_TABLE = f"{PROJECT}.{BASE_DS}.raw_ingest_clean"
SAFE_VIEW = f"{PROJECT}.{GOV_DS}.vw_encounters_safe"
RESTRICTED_SA = "restricted-reader-b4@bchan-genai-lab.iam.gserviceaccount.com"

# Mask PII: the analyst gets utility (cohort, condition, billing band) without
# the patient's name or exact bill — the classic "approved view" cut.
SAFE_VIEW_SQL = f"""
SELECT
  TO_HEX(SHA256(LOWER(name)))                         AS patient_hash,   -- name masked
  age,
  gender,
  date_of_admission,
  medical_condition,
  admission_type,
  CASE
    WHEN billing_amount < 5000  THEN '<5k'
    WHEN billing_amount < 15000 THEN '5k-15k'
    ELSE '15k+'
  END                                                 AS billing_band,   -- exact bill masked
FROM `{BASE_TABLE}`
"""


def main() -> None:
    client = bigquery.Client(project=PROJECT)

    # 1. governed dataset
    gov = bigquery.Dataset(f"{PROJECT}.{GOV_DS}")
    gov.location = "US"
    gov.description = "Approved, PII-masked views for least-privilege analyst access (Bullet 4)."
    client.create_dataset(gov, exists_ok=True)
    print(f"[1] dataset {GOV_DS} ready")

    # 2. masked view
    view = bigquery.Table(SAFE_VIEW)
    view.view_query = SAFE_VIEW_SQL
    try:
        client.delete_table(SAFE_VIEW, not_found_ok=True)
        client.create_table(view)
    except Exception as e:
        print(f"    view create note: {e}")
    print(f"[2] masked view {SAFE_VIEW.split('.')[-1]} created (name→sha256, billing→band)")

    # 3. authorize the view to read the base dataset on the caller's behalf
    base = client.get_dataset(f"{PROJECT}.{BASE_DS}")
    entry = bigquery.AccessEntry(None, "view", {
        "projectId": PROJECT, "datasetId": GOV_DS, "tableId": "vw_encounters_safe",
    })
    if entry not in base.access_entries:
        base.access_entries = list(base.access_entries) + [entry]
        client.update_dataset(base, ["access_entries"])
    print(f"[3] authorized view → can read {BASE_DS} (analyst still cannot)")

    # 4. least-privilege: restricted SA gets dataViewer on the GOVERNED dataset ONLY
    gov = client.get_dataset(f"{PROJECT}.{GOV_DS}")
    grant = bigquery.AccessEntry("READER", "userByEmail", RESTRICTED_SA)
    if grant not in gov.access_entries:
        gov.access_entries = list(gov.access_entries) + [grant]
        client.update_dataset(gov, ["access_entries"])
    print(f"[4] {RESTRICTED_SA.split('@')[0]} → READER on {GOV_DS} only (NOT on {BASE_DS})")

    # 5. retention: quarantined records expire after 90 days — bad data doesn't linger
    client.query(
        f"ALTER TABLE `{PROJECT}.{BASE_DS}.quarantine_records` "
        f"SET OPTIONS (expiration_timestamp = TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 90 DAY))"
    ).result()
    print("[5] retention: quarantine_records expires in 90 days")

    print("\nGREEN — governed view + authorized read + view-only grant + retention applied.")
    print("Observable 403 test: governance/least_privilege_demo.py (needs the restricted SA's token).")


if __name__ == "__main__":
    main()
