"""Bullet 2 — self-monitoring data-platform DAG.

    ingest_source_a ─┐
                     ├─► transform ─► freshness_sla ─► quality_gate ─┬─► publish   (ALL_SUCCESS)
    ingest_source_b ─┘                                               └─► escalate  (ONE_FAILED)

Every clause is real, not a comment:
  • parallel ingest      two ingest tasks fan out, transform joins them
  • data-freshness SLA   computes lag of newest record vs as-of; fails if too stale
  • ML anomaly gate       IsolationForest auto-quarantines outlier rows
  • LLM-explained failure  one Gemini call explains the quarantine in plain language
  • bounded recovery       quality_gate retries (retries=2); on final fail, escalate runs

Run it (offline, no scheduler):
    AIRFLOW_HOME=$PWD/.airflow_home \
    AIRFLOW__CORE__DAGS_FOLDER=$PWD/orchestration/dags \
    .airflow-venv/bin/airflow dags test data_platform 2024-07-10
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from airflow.decorators import dag, task
from airflow.exceptions import AirflowException

# make orchestration/{anomaly,explain}.py importable from the dags folder
ORCH = Path(__file__).resolve().parents[1]
if str(ORCH) not in sys.path:
    sys.path.insert(0, str(ORCH))
from anomaly import quarantine_split           # noqa: E402
from explain import explain_failure            # noqa: E402

FIXTURE = ORCH / "fixtures" / "daily_batch.csv"
RUN_DIR = ORCH / ".run"
RUN_DIR.mkdir(exist_ok=True)

FRESHNESS_SLA_HOURS = float(os.environ.get("FRESHNESS_SLA_HOURS", "24"))
QUARANTINE_FAIL_RATE = float(os.environ.get("QUARANTINE_FAIL_RATE", "0.20"))  # gate fails above this

default_args = {
    "retries": 2,                                  # bounded recovery
    "retry_delay": timedelta(seconds=2),
}


@dag(
    dag_id="data_platform",
    schedule=None,
    start_date=datetime(2024, 7, 1),
    catchup=False,
    default_args=default_args,
    tags=["bullet2", "self-monitoring"],
)
def data_platform():

    @task
    def ingest_source_a() -> str:
        df = pd.read_csv(FIXTURE)
        shard = df.iloc[::2]                        # even rows — "source A"
        p = RUN_DIR / "ingest_a.csv"; shard.to_csv(p, index=False)
        return str(p)

    @task
    def ingest_source_b() -> str:
        df = pd.read_csv(FIXTURE)
        shard = df.iloc[1::2]                       # odd rows — "source B"
        p = RUN_DIR / "ingest_b.csv"; shard.to_csv(p, index=False)
        return str(p)

    @task
    def transform(a_path: str, b_path: str) -> str:
        df = pd.concat([pd.read_csv(a_path), pd.read_csv(b_path)]).sort_values("encounter_id")
        p = RUN_DIR / "transformed.csv"; df.to_csv(p, index=False)
        print(f"transform: joined {len(df)} rows from 2 parallel sources")
        return str(p)

    @task
    def freshness_sla(path: str) -> str:
        df = pd.read_csv(path)
        ts = pd.to_datetime(df["event_ts"], utc=True)
        as_of = pd.to_datetime(os.environ.get("AS_OF", ts.max().isoformat()), utc=True)
        lag_hours = (as_of - ts.max()).total_seconds() / 3600
        print(f"freshness: newest record lags as-of by {lag_hours:.2f}h (SLA {FRESHNESS_SLA_HOURS}h)")
        if lag_hours > FRESHNESS_SLA_HOURS:
            raise AirflowException(f"FRESHNESS SLA breached: {lag_hours:.1f}h > {FRESHNESS_SLA_HOURS}h")
        return path

    @task
    def quality_gate(path: str) -> str:
        df = pd.read_csv(path)
        clean, quarantined = quarantine_split(df)
        rate = len(quarantined) / len(df)
        (RUN_DIR / "published.csv").write_text(clean.to_csv(index=False))
        quarantined.to_csv(RUN_DIR / "quarantined.csv", index=False)

        sample = quarantined.drop(columns=["name"], errors="ignore").to_dict("records")[:3]
        print(f"quality_gate: {len(quarantined)}/{len(df)} rows anomalous (rate={rate:.0%})")
        if len(quarantined):
            explanation = explain_failure("ML anomaly auto-quarantine", len(quarantined), sample)
            print(f"LLM-explained [{explanation['source']}]: {explanation['explanation']}")
            (RUN_DIR / "explanation.json").write_text(json.dumps(explanation, indent=2, default=str))
        if rate > QUARANTINE_FAIL_RATE:
            raise AirflowException(f"quarantine rate {rate:.0%} > {QUARANTINE_FAIL_RATE:.0%} — gate failed")
        return str(RUN_DIR / "published.csv")

    @task(trigger_rule="all_success")
    def publish(path: str) -> None:
        df = pd.read_csv(path)
        print(f"publish: {len(df)} clean rows promoted to the marts ✅")

    @task(trigger_rule="one_failed")
    def escalate() -> None:
        notice = {"escalated_at": datetime.now(timezone.utc).isoformat(),
                  "to": "on-call data engineer",
                  "reason": "quality gate failed after bounded retries — human needed"}
        (RUN_DIR / "escalation.json").write_text(json.dumps(notice, indent=2))
        print(f"escalate: paged a human — {notice['reason']}")

    a, b = ingest_source_a(), ingest_source_b()
    t = transform(a, b)
    f = freshness_sla(t)
    g = quality_gate(f)
    publish(g)
    escalate() << g                                # runs only if the gate ultimately fails


data_platform()
