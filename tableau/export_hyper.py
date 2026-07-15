#!/usr/bin/env python3
"""
Tableau BI Delivery Layer — export_hyper.py

Reads from BigQuery gold layer (healthcare_analytics.raw_ingest_clean),
aggregates by medical condition, writes a Tableau Hyper extract (.hyper).

This is the backend data-engineer side of Tableau:
  BigQuery (gold) → .hyper extract → handed to viz team

No Tableau Desktop needed. No GUI. Pure Python pipeline.

Usage:
    python tableau/export_hyper.py           # BigQuery mode
    python tableau/export_hyper.py --dry-run # local JSONL fallback (no GCP creds)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from tableauhyperapi import (
    Connection, CreateMode, HyperProcess,
    Inserter, SqlType, TableDefinition, TableName, Telemetry,
)

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent
HYPER_OUT = HERE / "healthcare_by_condition.hyper"
CHART_OUT = HERE / "healthcare_by_condition.png"
JSONL_FALLBACK = REPO_ROOT / "ingestion" / "stream_source.jsonl"

PROJECT = os.environ.get("GCP_PROJECT_ID", "bchan-genai-lab")
DATASET = os.environ.get("BQ_DATASET", "healthcare_analytics")


# ── data sources ──────────────────────────────────────────────────────────────

def fetch_from_bigquery() -> list[dict]:
    from google.cloud import bigquery
    client = bigquery.Client(project=PROJECT)
    sql = f"""
        SELECT
            medical_condition,
            COUNT(*)                        AS patient_count,
            ROUND(AVG(billing_amount), 2)   AS avg_billing_usd,
            ROUND(AVG(age), 1)              AS avg_age
        FROM `{PROJECT}.{DATASET}.raw_ingest_clean`
        GROUP BY medical_condition
        ORDER BY patient_count DESC
    """
    rows = list(client.query(sql).result())
    return [dict(r) for r in rows]


def fetch_from_jsonl() -> list[dict]:
    records: dict[str, dict] = defaultdict(lambda: {"count": 0, "billing": 0.0, "age": 0})
    with open(JSONL_FALLBACK) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            cond = r.get("medical_condition", "Unknown")
            records[cond]["count"] += 1
            records[cond]["billing"] += float(r.get("billing_amount", 0))
            try:
                records[cond]["age"] += int(r.get("age", 0))
            except (ValueError, TypeError):
                pass  # quarantine-mode rows have intentionally bad ages

    return [
        {
            "medical_condition": cond,
            "patient_count": v["count"],
            "avg_billing_usd": round(v["billing"] / v["count"], 2),
            "avg_age": round(v["age"] / v["count"], 1),
        }
        for cond, v in sorted(records.items(), key=lambda x: -x[1]["count"])
    ]


# ── hyper export ──────────────────────────────────────────────────────────────

TABLE_DEF = TableDefinition(
    table_name=TableName("Extract", "HealthcareByCondition"),
    columns=[
        TableDefinition.Column("Medical Condition", SqlType.text()),
        TableDefinition.Column("Patient Count",     SqlType.int()),
        TableDefinition.Column("Avg Billing USD",   SqlType.double()),
        TableDefinition.Column("Avg Age",           SqlType.double()),
    ],
)


def write_hyper(rows: list[dict]) -> None:
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(
            endpoint=hyper.endpoint,
            database=str(HYPER_OUT),
            create_mode=CreateMode.CREATE_AND_REPLACE,
        ) as conn:
            conn.catalog.create_schema("Extract")
            conn.catalog.create_table(TABLE_DEF)

            with Inserter(conn, TABLE_DEF) as ins:
                ins.add_rows([
                    (r["medical_condition"], int(r["patient_count"]),
                     float(r["avg_billing_usd"]), float(r["avg_age"]))
                    for r in rows
                ])
                ins.execute()

            count = conn.execute_scalar_query(
                'SELECT COUNT(*) FROM "Extract"."HealthcareByCondition"'
            )
            print(f"[hyper] {count} conditions written → {HYPER_OUT.name}")
            assert count == len(rows)


# ── chart ─────────────────────────────────────────────────────────────────────

def write_chart(rows: list[dict]) -> None:
    conditions   = [r["medical_condition"] for r in rows]
    patient_counts = [r["patient_count"] for r in rows]
    avg_billings   = [r["avg_billing_usd"] for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
    fig.suptitle("Healthcare Analytics — Tableau Hyper Extract Preview", fontsize=12)

    bars1 = ax1.bar(conditions, patient_counts, color="#1a6db5", edgecolor="white")
    ax1.set_title("Patient Count by Condition")
    ax1.set_ylabel("Patients")
    ax1.set_ylim(0, max(patient_counts) * 1.25)
    for bar, val in zip(bars1, patient_counts):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                 str(val), ha="center", va="bottom", fontsize=9)
    ax1.tick_params(axis="x", rotation=20)

    bars2 = ax2.bar(conditions, avg_billings, color="#e8632a", edgecolor="white")
    ax2.set_title("Avg Billing (USD) by Condition")
    ax2.set_ylabel("USD")
    ax2.set_ylim(0, max(avg_billings) * 1.25)
    for bar, val in zip(bars2, avg_billings):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 100,
                 f"${val:,.0f}", ha="center", va="bottom", fontsize=8)
    ax2.tick_params(axis="x", rotation=20)

    plt.tight_layout()
    plt.savefig(CHART_OUT, dpi=120)
    print(f"[chart] saved → {CHART_OUT.name}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Use local JSONL instead of BigQuery")
    args = parser.parse_args()

    print("=" * 55)
    print("Healthcare → Tableau Hyper export")
    print("=" * 55)

    if args.dry_run:
        print(f"[source] dry-run — reading {JSONL_FALLBACK.name}")
        rows = fetch_from_jsonl()
    else:
        print(f"[source] BigQuery — {PROJECT}.{DATASET}.raw_ingest_clean")
        rows = fetch_from_bigquery()

    print(f"[data]   {len(rows)} medical conditions aggregated\n")
    print(f"  {'Condition':<20} {'Patients':>8}  {'Avg Billing':>12}  {'Avg Age':>8}")
    print(f"  {'-'*20} {'-'*8}  {'-'*12}  {'-'*8}")
    for r in rows:
        print(f"  {r['medical_condition']:<20} {int(r['patient_count']):>8}  "
              f"${float(r['avg_billing_usd']):>11,.2f}  {float(r['avg_age']):>8.1f}")

    print()
    write_hyper(rows)
    write_chart(rows)

    print()
    print("=" * 55)
    print("EXPORT COMPLETE")
    print(f"  Extract : {HYPER_OUT}")
    print(f"  Chart   : {CHART_OUT}")
    print("  Hand off .hyper to viz team → open in Tableau Desktop/Public")
    print("=" * 55)


if __name__ == "__main__":
    main()
