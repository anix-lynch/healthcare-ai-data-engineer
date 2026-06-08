"""
Full Trust pipeline — one button, fail-closed, the SAME chain CI runs (Codex QA gap #1).

Before this, the scheduled workflow ran only pull -> gate -> freshness -> features;
BigQuery load / GE / dbt / reconciliation ran only when invoked by hand. This wires
every filter onto the pump and proves a single end-to-end run, stopping at the first
critical failure.

  1 pull            real openFDA -> jsonl
  2 gate --strict   null/dup/schema/temporal/value (fail-closed)
  3 bq_load         canonical MERGE -> BigQuery + window reconciliation
  4 ge --strict     Great Expectations on the normalized contract
  5 dbt build       staging/fact/dims/bridge + tests (incl referential + reconciliation)
  6 freshness --strict  3 clocks + stale alert

Writes data/quality/openfda_pipeline_run.json (per-stage exit + duration). Exits non-zero
if any stage fails. Env: GOOGLE_APPLICATION_CREDENTIALS (SA key), GCP_PROJECT_ID, BQ_DATASET.
"""
from __future__ import annotations
import json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable
GE_PY = os.environ.get("GE_PY", str(REPO / ".ge-venv" / "bin" / "python"))
DBT = os.environ.get("DBT", str(REPO / ".venv" / "bin" / "dbt"))

STAGES = [
    ("pull",      [PY, "ingestion/openfda_pull.py", "--since", "20260101", "--max", "300"], REPO),
    ("gate",      [PY, "ingestion/openfda_gate.py", "--strict"], REPO),
    ("bq_load",   [PY, "ingestion/bq_load.py"], REPO),
    ("ge",        [GE_PY, "ingestion/ge_validate.py", "--strict"], REPO),
    ("dbt_build", [DBT, "build", "--profiles-dir", "."], REPO / "dbt-project"),
    ("freshness", [PY, "ingestion/freshness_check.py", "--strict"], REPO),
]


def main():
    results, failed = [], None
    for name, cmd, cwd in STAGES:
        t0 = time.time()
        rc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True).returncode
        results.append({"stage": name, "exit": rc, "seconds": round(time.time() - t0, 1)})
        print(f"  {'✅' if rc == 0 else '❌'} {name} (exit {rc})")
        if rc != 0:                       # fail-closed: stop at first critical failure
            failed = name
            break
    report = {
        "ran_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stages": results,
        "stages_total": len(STAGES),
        "stages_passed": sum(1 for r in results if r["exit"] == 0),
        "failed_stage": failed,
        "passed": failed is None and len(results) == len(STAGES),
    }
    out = REPO / "data" / "quality" / "openfda_pipeline_run.json"
    out.write_text(json.dumps(report, indent=2))
    # The single source of truth for "last successfully COMPLETED end-to-end run".
    # Written ONLY on full success — the watchdog reads this and never refreshes it
    # on failure, so a dead pipeline stays detectably stale.
    if report["passed"]:
        (REPO / "data" / "freshness" / "last_successful_e2e.json").write_text(json.dumps({
            "completed_at": report["ran_at"], "stages_passed": report["stages_passed"]}, indent=2))
    print(json.dumps({k: report[k] for k in ("stages_passed", "stages_total", "failed_stage", "passed")}, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
