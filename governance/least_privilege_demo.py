#!/usr/bin/env python3
"""Observable least-privilege proof: the analyst reads the approved
masked view (200) but is denied the raw base table (403).

Authenticate AS the restricted reader, then run both queries:

    GOOGLE_APPLICATION_CREDENTIALS=/path/to/restricted-reader-b4-key.json \
        python governance/least_privilege_demo.py

The restricted SA (`restricted-reader-b4`) holds only `bigquery.jobUser` +
READER on `healthcare_governed`. It has NO access to `healthcare_analytics`, so
the base-table read must raise 403 Forbidden — that denial IS the proof.

Setup (one-time, by the project owner — the deploy SA cannot self-mint a token):
    gcloud iam service-accounts add-iam-policy-binding \
      restricted-reader-b4@bchan-genai-lab.iam.gserviceaccount.com \
      --member="serviceAccount:bchan-genai-deploy@bchan-genai-lab.iam.gserviceaccount.com" \
      --role="roles/iam.serviceAccountTokenCreator" --project bchan-genai-lab
    # then: export GOOGLE_APPLICATION_CREDENTIALS pointing at a restricted key,
    # or run with --impersonate once the deploy SA can mint the token.
"""
from __future__ import annotations

import json
import os
import sys

from google.cloud import bigquery
from google.api_core.exceptions import Forbidden

PROJECT = "bchan-genai-lab"
BASE_TABLE = f"{PROJECT}.healthcare_analytics.raw_ingest_clean"
SAFE_VIEW = f"{PROJECT}.healthcare_governed.vw_encounters_safe"


def _client():
    if "--impersonate" in sys.argv:
        import google.auth
        from google.auth import impersonated_credentials
        src, _ = google.auth.default()
        creds = impersonated_credentials.Credentials(
            source_credentials=src,
            target_principal="restricted-reader-b4@bchan-genai-lab.iam.gserviceaccount.com",
            target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return bigquery.Client(project=PROJECT, credentials=creds)
    return bigquery.Client(project=PROJECT)


def main() -> None:
    client = _client()
    result = {"identity": None, "approved_view_read": None, "base_table_read": None}
    try:
        result["identity"] = client._credentials.service_account_email
    except Exception:
        result["identity"] = "unknown"

    # 1. approved masked view — must succeed
    try:
        rows = list(client.query(f"SELECT * FROM `{SAFE_VIEW}` LIMIT 3").result())
        result["approved_view_read"] = {
            "status": "200_ALLOWED",
            "sample": [dict(r) for r in rows],
        }
    except Exception as e:
        result["approved_view_read"] = {"status": "UNEXPECTED_DENY", "error": str(e)[:200]}

    # 2. raw base table — must be denied 403
    try:
        list(client.query(f"SELECT name, billing_amount FROM `{BASE_TABLE}` LIMIT 3").result())
        result["base_table_read"] = {"status": "LEAK_200_ALLOWED",
                                     "note": "FAIL — analyst could read raw PII"}
    except Forbidden as e:
        result["base_table_read"] = {"status": "403_DENIED", "detail": str(e)[:160]}
    except Exception as e:
        result["base_table_read"] = {"status": "DENIED_OTHER", "detail": str(e)[:160]}

    v = result["approved_view_read"]["status"]
    b = result["base_table_read"]["status"]
    result["verdict"] = (
        "GREEN — analyst reads the masked view (200) and is denied the base table (403)"
        if v == "200_ALLOWED" and b == "403_DENIED"
        else f"CHECK — view={v} base={b}"
    )
    out = os.path.join(os.path.dirname(__file__), "proof_least_privilege.json")
    with open(out, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(json.dumps(result, indent=2, default=str))
    print(f"\nWROTE {out}")


if __name__ == "__main__":
    main()
