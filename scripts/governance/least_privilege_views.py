#!/usr/bin/env python3
"""
Bullet 4 proof: least-privilege access via a BigQuery AUTHORIZED VIEW.

Pattern: analysts get access ONLY to a curated `healthcare_secure` dataset holding a
view that exposes a reduced, governed column set — never the raw `healthcare_analytics`
tables. The view is added to the SOURCE dataset's access list (authorized view), so it
can read the base table on the analyst's behalf without the analyst holding any grant on
the base. That is least-privilege: data minimization (fewer columns) + privilege
minimization (no direct base-table access).

Proof captured: (a) the view exists in the secure dataset, (b) it is registered in the
source dataset's authorized-view ACL, (c) it exposes strictly fewer columns than the base.
IAM principal grants (binding a human/group to the secure dataset only) are owner-level and
recorded in the data contract; this script proves the dataset/view mechanism the SA controls.
"""
import json
from pathlib import Path
from google.cloud import bigquery
from google.api_core.exceptions import Conflict, Forbidden

REPO = Path(__file__).resolve().parents[2]
PROJECT = "PROJECT"
SRC_DS = "healthcare_analytics"
SEC_DS = "healthcare_secure"
BASE = "fact_adverse_events"
VIEW = "vw_adverse_events_safe"
SAFE_COLS = ["safetyreportid", "received_date", "primary_drug", "is_serious",
             "n_reactions", "occurcountry"]  # excludes internal ingest_ts + reactions blob


def main():
    c = bigquery.Client(project=PROJECT)
    steps, errors = {}, []

    # 1. ensure secure dataset
    sec_ref = bigquery.Dataset(f"{PROJECT}.{SEC_DS}")
    sec_ref.location = "US"
    try:
        c.create_dataset(sec_ref, exists_ok=True)
        steps["secure_dataset"] = f"{PROJECT}.{SEC_DS}"
    except Exception as e:
        errors.append(f"create_dataset: {e}")

    # 2. create the reduced-column view
    view_sql = (f"SELECT {', '.join(SAFE_COLS)} "
                f"FROM `{PROJECT}.{SRC_DS}.{BASE}`")
    view_id = f"{PROJECT}.{SEC_DS}.{VIEW}"
    v = bigquery.Table(view_id)
    v.view_query = view_sql
    try:
        c.delete_table(view_id, not_found_ok=True)
        c.create_table(v)
        steps["view"] = view_id
    except Exception as e:
        errors.append(f"create_view: {e}")

    # 3. authorize the view on the SOURCE dataset
    authorized = False
    try:
        src = c.get_dataset(f"{PROJECT}.{SRC_DS}")
        entries = list(src.access_entries)
        already = any(getattr(e, "entity_type", "") == "view"
                      and getattr(e, "entity_id", {}).get("tableId") == VIEW for e in entries)
        if not already:
            entries.append(bigquery.AccessEntry(
                role=None, entity_type="view",
                entity_id={"projectId": PROJECT, "datasetId": SEC_DS, "tableId": VIEW}))
            src.access_entries = entries
            c.update_dataset(src, ["access_entries"])
        authorized = True
        steps["authorized_on_source"] = f"{SRC_DS} ACL includes {SEC_DS}.{VIEW}"
    except Forbidden as e:
        errors.append(f"authorize(Forbidden-needs-owner): {e}")
    except Exception as e:
        errors.append(f"authorize: {e}")

    # 4. prove the view reads + column reduction
    base_cols = [f.name for f in c.get_table(f"{PROJECT}.{SRC_DS}.{BASE}").schema]
    view_rows, view_cols = None, None
    try:
        df = c.query(f"SELECT * FROM `{view_id}` LIMIT 5").result()
        view_cols = [f.name for f in df.schema]
        view_rows = sum(1 for _ in df)
    except Exception as e:
        errors.append(f"query_view: {e}")

    reduced = bool(view_cols) and len(view_cols) < len(base_cols)
    green = bool(steps.get("view")) and authorized and reduced
    receipt = {
        "proof": "bullet4_least_privilege_authorized_view",
        "claim_phrase": "least-privilege access ... and authorized views",
        "secure_dataset": f"{PROJECT}.{SEC_DS}",
        "authorized_view": view_id,
        "base_table_columns": base_cols,
        "view_columns": view_cols,
        "columns_dropped": sorted(set(base_cols) - set(view_cols or [])),
        "authorized_on_source": authorized,
        "view_query_rows_sampled": view_rows,
        "steps": steps,
        "errors": errors,
        "verdict": "GREEN — authorized view registered on source, exposes reduced column set"
                   if green else "YELLOW — view built but authorization/reduction incomplete (see errors)",
    }
    out = REPO / "data" / "quality" / "bullet4_least_privilege_proof.json"
    json.dump(receipt, open(out, "w"), indent=2, default=str)
    print("WROTE", out)
    print("  base cols:", len(base_cols), "view cols:", len(view_cols or []),
          "dropped:", receipt["columns_dropped"])
    print("  authorized_on_source:", authorized)
    if errors:
        print("  errors:", errors)
    print("VERDICT:", receipt["verdict"])
    raise SystemExit(0 if green else 1)


if __name__ == "__main__":
    main()
