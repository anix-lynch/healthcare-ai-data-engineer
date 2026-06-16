"""Single-record BigQuery sink — the persistence shared by the live Pub/Sub
endpoint and the batch stream ingester, so an event lands the SAME way whether
it arrives one-at-a-time over Pub/Sub→Cloud Run or in the file replay.

`validate.py` decides *what* to do with a record (pure, no DB); this module is
the only place that actually writes. One accepted row is upserted by MERGE on
the natural key (idempotent — a re-published message does not duplicate); one
bad row is appended to the quarantine table with its reasons.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from validate import KEY_FIELDS, _key  # shared natural-key rule

PROJECT = os.environ.get("GCP_PROJECT_ID", "bchan-genai-lab")
DATASET = os.environ.get("BQ_DATASET", "healthcare_analytics")
CLEAN_TABLE = f"{PROJECT}.{DATASET}.raw_ingest_clean"
QUARANTINE_TABLE = f"{PROJECT}.{DATASET}.quarantine_records"


def clean_schema():
    from google.cloud import bigquery
    return [
        bigquery.SchemaField("name", "STRING"),
        bigquery.SchemaField("age", "INTEGER"),
        bigquery.SchemaField("gender", "STRING"),
        bigquery.SchemaField("date_of_admission", "DATE"),
        bigquery.SchemaField("medical_condition", "STRING"),
        bigquery.SchemaField("admission_type", "STRING"),
        bigquery.SchemaField("medication", "STRING"),
        bigquery.SchemaField("test_results", "STRING"),
        bigquery.SchemaField("billing_amount", "FLOAT"),
        bigquery.SchemaField("event_ts", "TIMESTAMP"),
        bigquery.SchemaField("natural_key", "STRING"),
    ]


def quarantine_schema():
    from google.cloud import bigquery
    return [
        bigquery.SchemaField("raw_json", "STRING"),
        bigquery.SchemaField("reasons", "STRING"),
        bigquery.SchemaField("source_event_ts", "STRING"),
        bigquery.SchemaField("quarantined_at", "TIMESTAMP"),
        bigquery.SchemaField("source", "STRING"),          # pubsub | bulk_load | stream_replay
        bigquery.SchemaField("natural_key", "STRING"),
    ]


def clean_row(rec: dict) -> dict:
    return {
        "name": rec["name"],
        "age": int(rec["age"]),
        "gender": rec["gender"],
        "date_of_admission": rec["date_of_admission"],
        "medical_condition": rec.get("medical_condition"),
        "admission_type": rec.get("admission_type"),
        "medication": rec.get("medication"),
        "test_results": rec.get("test_results"),
        "billing_amount": float(rec.get("billing_amount") or 0.0),
        "event_ts": rec.get("event_ts"),
        "natural_key": f"{str(rec['name']).strip().lower()}|{rec['date_of_admission']}",
    }


def seen_from_bigquery(client) -> dict[tuple, datetime]:
    """Rebuild the `seen` map (natural key -> event_ts) from what already landed,
    so the stateless endpoint can detect duplicates / late replays exactly like
    the in-memory batch run does."""
    seen: dict[tuple, datetime] = {}
    try:
        rows = client.query(
            f"SELECT name, date_of_admission, event_ts FROM `{CLEAN_TABLE}`"
        ).result()
    except Exception:
        return seen  # table not created yet → nothing seen
    for r in rows:
        key = _key({"name": r["name"], "date_of_admission": str(r["date_of_admission"])})
        seen[key] = r["event_ts"] or datetime.min
    return seen


def persist_decision(client, decision) -> str:
    """Write one classified record. Returns the action taken."""
    from google.cloud import bigquery

    if decision.status == "quarantined":
        client.create_table(bigquery.Table(QUARANTINE_TABLE, schema=quarantine_schema()), exists_ok=True)
        nk = f"{str(decision.record.get('name', '')).strip().lower()}|{decision.record.get('date_of_admission', '')}"
        client.insert_rows_json(QUARANTINE_TABLE, [{
            "raw_json": json.dumps(decision.record),
            "reasons": ";".join(decision.reasons),
            "source_event_ts": str(decision.record.get("event_ts", "")),
            "quarantined_at": datetime.now(timezone.utc).isoformat(),
            "source": os.environ.get("INGEST_SOURCE", "pubsub"),
            "natural_key": nk,
        }])
        return "quarantined"

    # accepted_new / accepted_revised → idempotent single-row MERGE on natural_key
    row = clean_row(decision.record)
    client.create_table(bigquery.Table(CLEAN_TABLE, schema=clean_schema()), exists_ok=True)
    cols = [f.name for f in clean_schema()]
    params = [
        bigquery.ScalarQueryParameter(c, "INT64" if c == "age"
                                      else "FLOAT64" if c == "billing_amount"
                                      else "TIMESTAMP" if c == "event_ts"
                                      else "DATE" if c == "date_of_admission"
                                      else "STRING", row[c])
        for c in cols
    ]
    set_clause = ", ".join(f"T.{c}=S.{c}" for c in cols if c != "natural_key")
    select_cols = ", ".join(f"@{c} AS {c}" for c in cols)
    merge_sql = f"""
    MERGE `{CLEAN_TABLE}` T
    USING (SELECT {select_cols}) S
    ON T.natural_key = S.natural_key
    WHEN MATCHED THEN UPDATE SET {set_clause}
    WHEN NOT MATCHED THEN INSERT ({', '.join(cols)}) VALUES ({', '.join('S.'+c for c in cols)})
    """
    client.query(merge_sql, job_config=bigquery.QueryJobConfig(query_parameters=params)).result()
    return decision.status


def write_quarantine_batch(client, rows: list[dict], *, source: str = "bulk_load") -> int:
    """Replace quarantine slice for one bulk load — visible in BigQuery console."""
    from google.cloud import bigquery

    client.create_table(bigquery.Table(QUARANTINE_TABLE, schema=quarantine_schema()), exists_ok=True)
    client.query(
        f"DELETE FROM `{QUARANTINE_TABLE}` WHERE source = @src",
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("src", "STRING", source)]
        ),
    ).result()
    if not rows:
        return 0

    payload = []
    now = datetime.now(timezone.utc).isoformat()
    for item in rows:
        rec = item.get("record") or item
        payload.append({
            "raw_json": json.dumps(rec if isinstance(rec, dict) else item),
            "reasons": ";".join(item.get("reasons") or []),
            "source_event_ts": str(rec.get("event_ts", "") if isinstance(rec, dict) else ""),
            "quarantined_at": now,
            "source": source,
            "natural_key": item.get("natural_key") or "",
        })

    client.create_table(bigquery.Table(QUARANTINE_TABLE, schema=quarantine_schema()), exists_ok=True)
    job = client.load_table_from_json(
        payload,
        QUARANTINE_TABLE,
        job_config=bigquery.LoadJobConfig(
            schema=quarantine_schema(),
            write_disposition="WRITE_APPEND",
        ),
    )
    job.result()
    return len(payload)
