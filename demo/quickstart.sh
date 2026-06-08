#!/usr/bin/env bash
# Quickstart -- the whole openFDA trust pipeline in ~30s. Pure Python, no GCP auth.
set -e
cd "$(dirname "$0")/.."
echo "1/4 ingest live FDA adverse-event reports"; python ingestion/openfda_pull.py --since 20260101 --max 300
echo "2/4 fail-closed quality gate";             python ingestion/openfda_gate.py --strict
echo "3/4 freshness SLA + stale alert";          python ingestion/freshness_check.py --strict
echo "4/4 point-in-time features + leak guard";  python ingestion/openfda_features.py
echo "[ok] done -- see data/freshness/ + data/quality/ for receipts"
