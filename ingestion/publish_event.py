#!/usr/bin/env python3
"""Publish one encounter record to the `encounter-events` Pub/Sub topic.

This is the *producer* side of Bullet 1's streaming leg. The message is delivered
by a push subscription to the Cloud Run `/pubsub/push` endpoint, which validates
and persists it to BigQuery — proving a real event flows
Pub/Sub → Cloud Run → BigQuery end to end.

    python ingestion/publish_event.py '{"name":"zoe young","age":61,...}'
    python ingestion/publish_event.py --demo        # a known-good new encounter
"""
from __future__ import annotations

import argparse
import json
import os
import sys

PROJECT = os.environ.get("GCP_PROJECT_ID", "bchan-genai-lab")
TOPIC = os.environ.get("PUBSUB_TOPIC", "encounter-events")

DEMO = {
    "name": "zoe young",
    "age": 61,
    "gender": "Female",
    "date_of_admission": "2024-07-09",
    "medical_condition": "Diabetes",
    "admission_type": "Elective",
    "medication": "Metformin",
    "test_results": "Normal",
    "billing_amount": 8210.50,
    "event_ts": "2024-07-09T10:00:00Z",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record", nargs="?", help="JSON record to publish")
    ap.add_argument("--demo", action="store_true", help="publish the known-good demo encounter")
    args = ap.parse_args()

    if args.demo:
        record = DEMO
    elif args.record:
        record = json.loads(args.record)
    else:
        ap.error("pass a JSON record or --demo")

    from google.cloud import pubsub_v1

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT, TOPIC)
    future = publisher.publish(topic_path, json.dumps(record).encode("utf-8"))
    msg_id = future.result(timeout=30)
    print(f"published message_id={msg_id} to {topic_path}")
    print(f"  record name={record.get('name')!r} key={record.get('name')}|{record.get('date_of_admission')}")


if __name__ == "__main__":
    main()
