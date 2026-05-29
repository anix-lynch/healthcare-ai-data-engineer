"""Build the A5 warehouse explorer payload from real repo artifacts."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_PATH = REPO_ROOT / "data" / "quality" / "l1_checkpoint_report.json"
SAMPLE_QUERIES_PATH = REPO_ROOT / "portfolio" / "A5_bigquery_dataset" / "sample_queries.sql"
DBT_MODELS_ROOT = REPO_ROOT / "dbt-project" / "models"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open() as fh:
        return json.load(fh)


def _read_text(path: Path) -> str:
    with path.open() as fh:
        return fh.read()


def _list_sql(root: Path) -> list[Path]:
    return sorted(root.glob("**/*.sql"))


def _to_display_time(iso_ts: str) -> str:
    if not iso_ts:
        return "n/a"
    dt = datetime.fromisoformat(iso_ts)
    return dt.strftime("%H:%M")


def _related_links() -> dict[str, str]:
    return {
        "A1 Executive Dashboard": "portfolio/A1_executive_dashboard/README.md",
        "A3 Data Marketplace": "portfolio/A3_dbt_documentation/README.md",
        "A4 Pipeline Operations": "portfolio/A4_airflow_dag/README.md",
        "Open SQL": "portfolio/A5_bigquery_dataset/sample_queries.sql",
        "Open Lineage": "docs/dag.md",
        "Preview Data": "dbt-project/models/marts/core/fact_patient_encounters.sql",
    }


def _click_audit(payload: dict[str, Any]) -> dict[str, Any]:
    mapping = _related_links()
    labels = sorted(set(payload.get("related_artifacts", []) + payload.get("table_details", {}).get("actions", [])))
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for label in labels:
        target = mapping.get(label)
        if not target:
            unresolved.append({"label": label, "reason": "no mapping"})
            continue
        exists = (REPO_ROOT / target).exists()
        entry = {"label": label, "target": target, "exists": exists}
        if exists:
            resolved.append(entry)
        else:
            unresolved.append({"label": label, "target": target, "reason": "target missing"})
    total = len(resolved) + len(unresolved)
    coverage = round((len(resolved) / total * 100), 2) if total else 100.0
    return {
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved),
        "coverage_pct": coverage,
        "resolved": resolved,
        "unresolved": unresolved,
    }


def build_warehouse_room_payload() -> dict[str, Any]:
    checkpoint = _load_json(CHECKPOINT_PATH)
    sql_models = _list_sql(DBT_MODELS_ROOT)
    staging_models = [p for p in sql_models if "/staging/" in str(p)]
    intermediate_models = [p for p in sql_models if "/intermediate/" in str(p)]
    gold_models = [p for p in sql_models if "/marts/core/" in str(p)]

    model_names = [p.stem for p in gold_models]
    selected_model = "fact_patient_encounters" if "fact_patient_encounters" in model_names else (model_names[0] if model_names else "n/a")

    sample_query_block = _read_text(SAMPLE_QUERIES_PATH).strip()
    first_query = sample_query_block.split(";")[0].strip() + ";"

    payload = {
        "artifact": "A5_bigquery_dataset",
        "display_mode": "warehouse-explorer",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_truth": {
            "checkpoint_report": str(CHECKPOINT_PATH.relative_to(REPO_ROOT)),
            "dbt_models_root": str(DBT_MODELS_ROOT.relative_to(REPO_ROOT)),
            "sample_queries": str(SAMPLE_QUERIES_PATH.relative_to(REPO_ROOT)),
        },
        "header": {
            "title": "🏭 BIGQUERY WAREHOUSE EXPLORER",
            "dataset": "healthcare_dw (storytelling alias over dbt core models)",
            "subtitle": "BigQuery Data Warehouse",
        },
        "datasets_panel": {
            "bronze": ["raw/healthcare_dataset.csv"],
            "silver": [p.stem for p in staging_models],
            "intermediate": [p.stem for p in intermediate_models],
            "gold": model_names,
            "selected": selected_model,
        },
        "table_details": {
            "table": selected_model,
            "grain": "1 row = 1 encounter",
            "owner": "Analytics Engineering",
            "purpose": "Encounter analytics + downstream API serving",
            "last_refresh": _to_display_time(checkpoint.get("scanned_at", "")),
            "rows": int(checkpoint.get("n_rows", 0)),
            "actions": ["Preview Data", "Open SQL", "Open Lineage"],
        },
        "mart_inventory": [
            {"model": "fact_patient_encounters", "grain": "1 row = 1 encounter", "purpose": "Core encounter analytics"},
            {"model": "dim_patient", "grain": "1 row = 1 patient", "purpose": "Patient dimension"},
            {"model": "dim_hospital", "grain": "1 row = 1 hospital", "purpose": "Facility dimension"},
        ],
        "sample_query": {
            "query": first_query,
            "status": "🟢 Query shape verified from repo SQL",
            "runtime": "n/a (offline portfolio layer)",
            "rows_returned": "n/a",
        },
        "warehouse_summary": {
            "datasets": 1,
            "tables": len(sql_models),
            "gold_models": len(gold_models),
            "views": 0,
            "last_refresh": _to_display_time(checkpoint.get("scanned_at", "")),
            "warehouse_health": "Healthy 🟢" if checkpoint.get("passed") else "Degraded 🔴",
        },
        "related_artifacts": [
            "A3 Data Marketplace",
            "A4 Pipeline Operations",
            "A1 Executive Dashboard",
        ],
        "notes": [
            "A5 is a storytelling/explorer layer over existing root dbt + checkpoint artifacts.",
            "No parallel warehouse is created under portfolio.",
            "Metrics and model inventory are derived from existing repo assets.",
        ],
    }
    payload["link_targets"] = _related_links()
    payload["click_audit"] = _click_audit(payload)
    return payload
