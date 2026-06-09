"""
Streaming proof — native Pub/Sub -> BigQuery, convergence with batch, malformed -> DLQ
(Bullet 1 proofs 3, 4, 5). NO Dataflow, tiny bounded volume, ALL resources deleted in a
finally block so nothing paid is left running.

FDA source stays scheduled batch — these are openFDA-DERIVED events (we replay a few
batch records as a synthetic real-time feed), never a claim of a live FDA stream.

  3 Pub/Sub topic -> BigQuery native subscription writes published events to a stream table
  4 a stream-gate MERGEs valid events into raw_openfda_events; batch+stream share the PK,
    converge with NO duplicate primary keys (one event reuses an existing batch id to test dedup)
  5 a malformed event (no safetyreportid) is routed to a DLQ table; valid events still process

Auth: owner/SA. Bounded BigQuery. Writes data/quality/openfda_streaming_proof.json.
"""
from __future__ import annotations
import json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
from google.cloud import bigquery
from google.cloud import pubsub_v1

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ingestion"))
from quarantine import classify
from bq_load import SCHEMA, COLS

PROJECT = os.environ.get("GCP_PROJECT_ID", "PROJECT")
DATASET = os.environ.get("BQ_DATASET", "healthcare_analytics")
TOPIC = "openfda-events"
SUB = "openfda-events-bqsub"
STREAM_TBL = f"{PROJECT}.{DATASET}.raw_openfda_stream"
DLQ_TBL = f"{PROJECT}.{DATASET}.raw_openfda_stream_dlq"
MAIN = f"{PROJECT}.{DATASET}.raw_openfda_events"
JOB = bigquery.QueryJobConfig(maximum_bytes_billed=100 * 1024 * 1024)
STREAM_IDS = ["STREAM_0001", "STREAM_0002", "STREAM_0003"]


def gcloud(*a):
    return subprocess.run(["gcloud", *a, "--project", PROJECT, "--quiet"],
                          capture_output=True, text=True)


def main():
    c = bigquery.Client(project=PROJECT)
    receipt = {"ran_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "steps": {}}
    created = {"topic": False, "sub": False}
    try:
        # --- create stream table (metadata-mode schema) + DLQ table ---
        c.query(f"""CREATE OR REPLACE TABLE `{STREAM_TBL}` (
            subscription_name STRING, message_id STRING, publish_time TIMESTAMP,
            data STRING, attributes STRING)""", job_config=JOB).result()
        c.query(f"""CREATE OR REPLACE TABLE `{DLQ_TBL}` (
            raw_data STRING, reason STRING, dlq_ts TIMESTAMP)""", job_config=JOB).result()

        # --- create topic + native BigQuery subscription (no Dataflow) ---
        gcloud("pubsub", "topics", "create", TOPIC); created["topic"] = True
        r = gcloud("pubsub", "subscriptions", "create", SUB, "--topic", TOPIC,
                   "--bigquery-table", f"{PROJECT}:{DATASET}.raw_openfda_stream", "--write-metadata")
        created["sub"] = (r.returncode == 0)
        receipt["steps"]["subscription_created"] = created["sub"]
        if not created["sub"]:
            receipt["steps"]["sub_error"] = r.stderr[-300:]
            raise RuntimeError("bq subscription create failed")

        # --- publish openFDA-derived events: valid (incl 1 overlap with batch) + 1 malformed ---
        batch_rows, _ = _batch_sample()
        overlap_id = batch_rows[0]["safetyreportid"]            # reuse an existing batch id
        valid = []
        for i, sid in enumerate(STREAM_IDS + [overlap_id]):
            ev = {**batch_rows[i % len(batch_rows)], "safetyreportid": sid,
                  "ingest_ts": "2026-06-08T18:00:00Z", "source_system": "openfda_faers",
                  "row_hash": f"streamhash_{sid}"}
            valid.append(ev)
        malformed = {"receivedate": "20260101", "serious": "1", "note": "no safetyreportid"}
        pub = pubsub_v1.PublisherClient()
        tp = pub.topic_path(PROJECT, TOPIC)
        for ev in valid + [malformed]:
            pub.publish(tp, json.dumps(ev).encode()).result()
        receipt["steps"]["published"] = len(valid) + 1

        # --- proof 3: events land in BigQuery via the native subscription ---
        landed = _poll(c, len(valid) + 1, timeout=120)
        receipt["steps"]["landed_in_bq_stream"] = landed

        # --- stream-gate: valid -> MERGE into main (converge); malformed -> DLQ ---
        rows = list(c.query(f"SELECT data FROM `{STREAM_TBL}`", job_config=JOB).result())
        good, bad = [], 0
        for row in rows:
            try:
                ev = json.loads(row.data)
            except Exception:
                ev = {}
            if classify(ev) is None:
                good.append(ev)
            else:
                bad += 1
                c.query("INSERT INTO `%s` (raw_data,reason,dlq_ts) VALUES(@d,@r,CURRENT_TIMESTAMP())" % DLQ_TBL,
                        job_config=bigquery.QueryJobConfig(
                            maximum_bytes_billed=100*1024*1024,
                            query_parameters=[bigquery.ScalarQueryParameter("d","STRING",row.data),
                                              bigquery.ScalarQueryParameter("r","STRING",classify(ev) or "unparseable")])).result()
        _merge_main(c, good)

        dup = list(c.query(f"SELECT COUNT(*)-COUNT(DISTINCT safetyreportid) d FROM `{MAIN}`", job_config=JOB).result())[0].d
        dlq_n = list(c.query(f"SELECT COUNT(*) n FROM `{DLQ_TBL}`", job_config=JOB).result())[0].n
        stream_in_main = list(c.query(
            f"SELECT COUNT(*) n FROM `{MAIN}` WHERE safetyreportid IN UNNEST(@ids)",
            job_config=bigquery.QueryJobConfig(maximum_bytes_billed=100*1024*1024,
                query_parameters=[bigquery.ArrayQueryParameter("ids","STRING",STREAM_IDS)])).result())[0].n

        checks = {
            "p3_native_pubsub_to_bq": landed >= len(valid) + 1,
            "p4_converged_no_dup_pk": dup == 0 and stream_in_main == len(STREAM_IDS),
            "p5_malformed_to_dlq_valid_unblocked": dlq_n == 1 and len(good) == len(valid),
        }
        receipt["checks"] = checks
        receipt["detail"] = {"published": len(valid)+1, "landed": landed, "valid_processed": len(good),
                             "dlq_count": dlq_n, "dup_pks_in_main": dup, "stream_ids_in_main": stream_in_main}
        receipt["passed"] = all(checks.values())
    finally:
        # --- cleanup: delete ALL paid resources + stream test rows (cost guard) ---
        if created["sub"]:
            gcloud("pubsub", "subscriptions", "delete", SUB)
        if created["topic"]:
            gcloud("pubsub", "topics", "delete", TOPIC)
        c.query(f"DROP TABLE IF EXISTS `{STREAM_TBL}`", job_config=JOB).result()
        c.query(f"DROP TABLE IF EXISTS `{DLQ_TBL}`", job_config=JOB).result()
        c.query(f"DELETE FROM `{MAIN}` WHERE safetyreportid IN UNNEST(@ids)",
                job_config=bigquery.QueryJobConfig(maximum_bytes_billed=100*1024*1024,
                    query_parameters=[bigquery.ArrayQueryParameter("ids","STRING",STREAM_IDS)])).result()
        receipt["cleanup"] = "topic/subscription/stream+dlq tables/stream rows deleted"

    out = REPO / "data" / "quality" / "openfda_streaming_proof.json"
    out.write_text(json.dumps(receipt, indent=2))
    print(json.dumps({**receipt.get("checks", {}), "passed": receipt.get("passed"),
                      "cleanup": receipt["cleanup"]}, indent=2))
    return 0 if receipt.get("passed") else 1


def _batch_sample():
    from openfda_gate import _load
    rows, _ = _load(REPO / "data" / "raw" / "openfda")
    return rows[:4], None


def _merge_main(c, rows):
    if not rows:
        return
    stg = f"{PROJECT}.{DATASET}._stg_stream"
    c.load_table_from_json([{col: r.get(col) for col in COLS} for r in rows], stg,
        job_config=bigquery.LoadJobConfig(schema=SCHEMA, write_disposition="WRITE_TRUNCATE")).result()
    setc = ", ".join(f"T.{col}=S.{col}" for col in COLS if col != "safetyreportid")
    ic, iv = ", ".join(COLS), ", ".join(f"S.{col}" for col in COLS)
    c.query(f"""MERGE `{MAIN}` T USING `{stg}` S ON T.safetyreportid=S.safetyreportid
        WHEN MATCHED AND S.ingest_ts >= T.ingest_ts THEN UPDATE SET {setc}
        WHEN NOT MATCHED THEN INSERT ({ic}) VALUES ({iv})""", job_config=JOB).result()
    c.query(f"DROP TABLE `{stg}`", job_config=JOB).result()


def _poll(c, n, timeout):
    end = time.time() + timeout
    last = 0
    while time.time() < end:
        last = list(c.query(f"SELECT COUNT(*) n FROM `{STREAM_TBL}`", job_config=JOB).result())[0].n
        if last >= n:
            return last
        time.sleep(5)
    return last


if __name__ == "__main__":
    sys.exit(main())
