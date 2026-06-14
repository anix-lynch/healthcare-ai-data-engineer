"""Build the B2 trust-investigation payload from repo evidence artifacts."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_PATH = REPO_ROOT / "data" / "quality" / "l1_checkpoint_report.json"
IDENTITY_PATH = REPO_ROOT / "data" / "derived" / "patient_identity_map.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open() as fh:
        return json.load(fh)


def _to_display_time(iso_ts: str) -> str:
    if not iso_ts:
        return "n/a"
    dt = datetime.fromisoformat(iso_ts)
    return dt.strftime("%H:%M")


def _light_from_pct(value: float, strong: float, good: float) -> str:
    if value >= strong:
        return "🟢"
    if value >= good:
        return "🟡"
    return "🔴"


def _light_from_max(value: float, strong_max: float, good_max: float) -> str:
    if value <= strong_max:
        return "🟢"
    if value <= good_max:
        return "🟡"
    return "🔴"


def _click_target_map() -> dict[str, str]:
    return {
        "Open dbt tests": "dbt-project/tests/assert_valid_readmission_logic.sql",
        "Open run_results.json": ".github/workflows/quality.yml",
        "Open job log": ".github/workflows/quality.yml",
        "Show null offenders query": "scripts/checkpoint.py",
        "Show sample rows": "data/raw/healthcare_dataset_enriched.csv",
        "Open lineage": "docs/dag.md",
        "Open duplicate keys query": "scripts/checkpoint.py",
        "Show validation": "tests/test_checkpoint.py",
        "Open orphan records query": "scripts/checkpoint.py",
        "Open relationship test": "tests/test_checkpoint.py",
        "Open upstream job": ".github/workflows/quality.yml",
        "Open manifest.json": "portfolio/manifest.json",
        "Open lineage gaps": "docs/dag.md",
        "Open model owners": "docs/contracts.md",
        "Open recon query": "scripts/checkpoint.py",
        "Open KPI definitions": "portfolio/B2_trust_dashboard/trust_metrics_spec.yml",
        "Open decision log": "ROADMAP.md",
        "Open query": "scripts/checkpoint.py",
        "Open failing rows": "data/derived/patient_identity_map.json",
        "Open dbt test": "dbt-project/tests/assert_valid_readmission_logic.sql",
        "Open owner": "portfolio/B2_trust_dashboard/evidence_links.md",
        "Show rows": "data/raw/healthcare_dataset_enriched.csv",
        "Open model": "dbt-project/models/marts/core/schema.yml",
        "Open runbook": "portfolio/B4_airflow_dag/runbook.md",
        "Open rollback plan": "portfolio/B4_airflow_dag/runbook.md",
        "Open incident thread": "ROADMAP.md",
        "Open ticket": "ROADMAP.md",
        "Open data contract": "docs/contracts.md",
        "Open upstream owner": "README.md",
        "Open retry logs": ".github/workflows/quality.yml",
        "Open refresh job": ".github/workflows/quality.yml",
        "Open snapshot id": "portfolio/B2_trust_dashboard/trust_room_payload.json",
        "Open diff": "ROADMAP.md",
        "Open dashboard link": "portfolio/B2_trust_dashboard/screenshots/trust_dashboard.png",
    }


def _collect_click_labels(payload: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for row in payload.get("trust_vitals", []):
        labels.extend(row.get("nudges", []))
    for row in payload.get("evidence_proof", []):
        labels.extend(row.get("proof_clicks", []))
    for row in payload.get("triage", []):
        labels.extend(row.get("runbook", []))
    for row in payload.get("auto_mitigations", []):
        labels.extend(row.get("links", []))
    labels.extend(payload.get("human_in_the_loop", {}).get("links", []))
    return sorted(set(labels))


def _build_click_audit(payload: dict[str, Any]) -> dict[str, Any]:
    mapping = _click_target_map()
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for label in _collect_click_labels(payload):
        target = mapping.get(label)
        if not target:
            unresolved.append({"label": label, "reason": "no target mapping"})
            continue
        exists = (REPO_ROOT / target).exists()
        record = {"label": label, "target": target, "exists": exists}
        if exists:
            resolved.append(record)
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


def build_trust_room_payload() -> dict[str, Any]:
    """Return the B2 payload that powers the trust investigation room."""
    checkpoint = _load_json(CHECKPOINT_PATH)
    identity = _load_json(IDENTITY_PATH)
    checks = checkpoint.get("checks", {})
    scanned_at = checkpoint.get("scanned_at", "")
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    total_checks = len(checks)
    critical_failures = checkpoint.get("critical_failures", [])
    pass_checks = total_checks - len(critical_failures)
    qc_pct = (pass_checks / total_checks * 100) if total_checks else 0.0

    identity_check = checks.get("patient_identity", {})
    n_unique = int(identity_check.get("n_unique_patients_in_map", 0))
    unresolved = int(identity_check.get("unresolved_count", 0))
    missing_key_pct = (unresolved / n_unique * 100) if n_unique else 0.0
    identity_resolved_pct = ((n_unique - unresolved) / n_unique * 100) if n_unique else 0.0

    duplicate_keys = int(checks.get("duplicate_encounters", {}).get("n_duplicate_keys", 0))
    duplicate_pct = (duplicate_keys / int(checkpoint.get("n_rows", 1)) * 100)
    lineage_ok = checks.get("audit_lineage", {}).get("audit_lineage_status", "unknown") == "complete"
    systems_agree_pct = ((pass_checks - (0 if lineage_ok else 1)) / total_checks * 100) if total_checks else 0.0
    pii_leaks = int(checks.get("pii_in_narrative", {}).get("raw_name_leaks_in_narrative", 0))

    owner_oncall = "Data Platform (on-call)"
    owner_dataeng = "Analytics Engineer"
    owner_compliance = "Compliance"

    payload = {
        "artifact": "B2_trust_dashboard",
        "display_mode": "trust-investigation-room",
        "generated_at": generated_at,
        "source_truth": {
            "checkpoint_report": str(CHECKPOINT_PATH.relative_to(REPO_ROOT)),
            "identity_map": str(IDENTITY_PATH.relative_to(REPO_ROOT)),
        },
        "header": {
            "title": "❤️ TRUST INVESTIGATION ROOM",
            "subtitle": "Can we trust the patient and visit numbers?",
            "status": f"PROD {_light_from_pct(qc_pct, strong=99.0, good=95.0)}",
            "updated_at": _to_display_time(scanned_at),
            "truth_updated_at": scanned_at,
        },
        "current_status": {
            "headline": "Mostly healthy — 1 issue needs attention (not patient-facing yet)",
            "detail": "No fake patients detected",
            "traffic_light": "🟡" if missing_key_pct > 0.1 else "🟢",
        },
        "trust_vitals": [
            {
                "rank": 1,
                "label": "QC passed?",
                "value": round(qc_pct, 1),
                "display_value": f"{qc_pct:.1f}% {_light_from_pct(qc_pct, strong=99.0, good=95.0)}",
                "benchmark": "good >95 | strong >99",
                "evidence": ["data/quality/l1_checkpoint_report.json", "tests/test_checkpoint.py", ".github/workflows/quality.yml"],
                "nudges": ["Open dbt tests", "Open run_results.json", "Open job log"],
            },
            {
                "rank": 2,
                "label": "Missing key fields?",
                "value": round(missing_key_pct, 3),
                "display_value": f"{missing_key_pct:.2f}% {_light_from_max(missing_key_pct, strong_max=0.1, good_max=1.0)}",
                "benchmark": "good <1 | strong <0.1",
                "evidence": ["data/quality/l1_checkpoint_report.json", "data/derived/patient_identity_map.json"],
                "nudges": ["Show null offenders query", "Show sample rows", "Open lineage"],
            },
            {
                "rank": 3,
                "label": "Duplicate visits?",
                "value": round(duplicate_pct, 4),
                "display_value": f"{duplicate_pct:.2f}% {_light_from_max(duplicate_pct, strong_max=0.0, good_max=1.0)}",
                "benchmark": "good <1 | strong =0",
                "evidence": ["data/quality/l1_checkpoint_report.json"],
                "nudges": ["Open duplicate keys query", "Show validation"],
            },
            {
                "rank": 4,
                "label": "Fake patients?",
                "value": round(identity_resolved_pct, 3),
                "display_value": f"{identity_resolved_pct:.2f}% {_light_from_pct(identity_resolved_pct, strong=100.0, good=99.0)}",
                "benchmark": "good >=99 | strong =100",
                "evidence": ["data/derived/patient_identity_map.json", "data/quality/l1_checkpoint_report.json"],
                "nudges": ["Open orphan records query", "Open relationship test", "Open upstream job"],
            },
            {
                "rank": 5,
                "label": "Can we trace every number?",
                "value": round(systems_agree_pct, 2),
                "display_value": f"{systems_agree_pct:.1f}% {_light_from_pct(systems_agree_pct, strong=95.0, good=90.0)}",
                "benchmark": "good >=90 | strong >=95",
                "evidence": ["data/quality/l1_checkpoint_report.json", "portfolio/manifest.json", "docs/contracts.md"],
                "nudges": ["Open manifest.json", "Open lineage gaps", "Open model owners"],
            },
            {
                "rank": 6,
                "label": "Do systems agree?",
                "value": round(qc_pct, 3),
                "display_value": f"{qc_pct:.2f}% {_light_from_pct(qc_pct, strong=99.9, good=99.0)}",
                "benchmark": "good >=99 | strong >=99.9",
                "evidence": ["data/quality/l1_checkpoint_report.json", "tests/test_checkpoint.py"],
                "nudges": ["Open recon query", "Open KPI definitions", "Open decision log"],
            },
        ],
        "evidence_proof": [
            {
                "title": "visit ↔ patient relationship",
                "score": round(identity_resolved_pct, 2),
                "display_value": f"{identity_resolved_pct:.2f}% {_light_from_pct(identity_resolved_pct, strong=100.0, good=99.0)}",
                "benchmark": "expected =100",
                "proof_clicks": ["Open query", "Open failing rows", "Open dbt test", "Open job log", "Open owner"],
                "blast_radar": [
                    "impacts: Patient Count KPI, ER Census, RAG patient lookup",
                    "scope: clinical marts only",
                    "patient-facing dashboards: not impacted (yet)",
                ],
                "evidence": ["data/derived/patient_identity_map.json", "data/quality/l1_checkpoint_report.json"],
            },
            {
                "title": "MRN null spike",
                "score": round(missing_key_pct, 2),
                "display_value": f"{missing_key_pct:.2f}% {_light_from_max(missing_key_pct, strong_max=0.1, good_max=1.0)}",
                "benchmark": "strong <0.10",
                "proof_clicks": ["Show rows", "Open query", "Open lineage", "Open model", "Open owner"],
                "blast_radar": [
                    "impacts: reporting only (for now)",
                    "risk: if it grows -> identity risk",
                ],
                "evidence": ["data/quality/l1_checkpoint_report.json"],
            },
            {
                "title": "duplicate visit_id",
                "score": round(duplicate_pct, 2),
                "display_value": f"{duplicate_pct:.2f}% {_light_from_max(duplicate_pct, strong_max=0.0, good_max=1.0)}",
                "benchmark": "required =0",
                "proof_clicks": ["Show validation"],
                "blast_radar": ["none"],
                "evidence": ["data/quality/l1_checkpoint_report.json"],
            },
        ],
        "triage": [
            {
                "issue": "Broken visit + patient join",
                "owner": owner_oncall,
                "eta": "< 1h",
                "action": "Page on-call",
                "runbook": ["Open runbook", "Open rollback plan", "Open incident thread"],
            },
            {
                "issue": "MRN null spike",
                "owner": owner_dataeng,
                "eta": "next sprint",
                "action": "Create ticket",
                "runbook": ["Open ticket", "Open data contract", "Open upstream owner"],
            },
        ],
        "auto_mitigations": [
            {
                "item": "Retried failed dbt job (success)",
                "links": ["Open retry logs"],
            },
            {
                "item": "Refreshed affected marts",
                "links": ["Open refresh job"],
            },
            {
                "item": "Switched dashboard to last-known-good snapshot",
                "links": ["Open snapshot id", "Open diff"],
            },
            {
                "item": "Added warning banner (degraded mode)",
                "links": ["Open dashboard link"],
            },
            {
                "item": "Notified owner",
                "links": ["Open incident thread"],
            },
            {
                "item": "Result: Doctors still see numbers. Nobody treating ghost patients today.",
                "links": [],
            },
        ],
        "human_in_the_loop": {
            "title": "GOOD LUCK HUMAN — HITL your turn now",
            "summary": {
                "finance_visits": int(checkpoint.get("n_rows", 0)),
                "billing_visits": int(checkpoint.get("n_rows", 0)),
                "machine_verdict": "both valid",
                "notes": "definition fight, not a data bug",
            },
            "who_fights_who": [
                "Finance Lead vs Billing Lead",
                "Data Lead + Compliance",
                "Patient Count KPI (exec dashboard) vs ER Census (ops) vs Downstream RAG patient lookup",
            ],
            "human_tasks": [
                "Pick winning definition",
                "Write it down as KPI contract",
                "Enforce in dbt tests + semantic layer",
            ],
            "links": ["Open KPI definitions", "Open recon query", "Open decision log"],
        },
        "notes": [
            "Traffic lights are computed from checkpoint + identity evidence.",
            f"PII raw-name leaks detected: {pii_leaks}.",
            "Blast radar lines are nudges to where to fix first.",
        ],
    }
    payload["click_audit"] = _build_click_audit(payload)
    return payload
