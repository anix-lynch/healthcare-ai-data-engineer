"""
Full Trust pipeline — one button, fail-closed, the SAME chain CI runs (audit QA gap #1).

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
sys.path.insert(0, str(REPO / "ingestion"))
import verify_e2e, ledger
PY = sys.executable
GE_PY = os.environ.get("GE_PY", str(REPO / ".ge-venv" / "bin" / "python"))
DBT = os.environ.get("DBT", str(REPO / ".venv" / "bin" / "dbt"))

# Downstream stages read the CLEAN partition (quarantine isolates malformed records
# first, so good records still flow). quarantine itself reads raw (default).
CLEAN = str(REPO / "data" / "clean")
DOWN = {"OPENFDA_DATA_DIR": CLEAN}
STAGES = [
    ("pull",       [PY, "ingestion/openfda_pull.py", "--since", "20260101", "--max", "300"], REPO, {}),
    ("quarantine", [PY, "ingestion/quarantine.py"], REPO, {}),
    ("gate",       [PY, "ingestion/openfda_gate.py", "--strict"], REPO, DOWN),
    ("bq_load",    [PY, "ingestion/bq_load.py"], REPO, DOWN),
    ("ge",         [GE_PY, "ingestion/ge_validate.py", "--strict"], REPO, DOWN),
    ("dbt_build",  [DBT, "build", "--profiles-dir", "."], REPO / "dbt-project", {}),
    ("freshness",  [PY, "ingestion/freshness_check.py", "--strict"], REPO, DOWN),
]


def main():
    started_at = ledger.now_iso()
    run_t0 = time.time()
    results, failed = [], None
    for name, cmd, cwd, env_extra in STAGES:
        t0 = time.time()
        rc = subprocess.run(cmd, cwd=cwd, env={**os.environ, **env_extra},
                            capture_output=True, text=True).returncode
        results.append({"stage": name, "exit": rc, "seconds": round(time.time() - t0, 1)})
        print(f"  {'✅' if rc == 0 else '❌'} {name} (exit {rc})")
        if rc != 0:                       # fail-closed: stop at first critical failure
            failed = name
            break
    stages_ok = failed is None and len(results) == len(STAGES)
    # FINAL verification gates the success stamp: stages exiting 0 is necessary but
    # NOT sufficient. last_successful_e2e is written only after verify() passes too.
    verification = verify_e2e.verify() if stages_ok else None
    verified = bool(verification and verification.get("all_passed"))
    report = {
        "ran_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stages": results,
        "stages_total": len(STAGES),
        "stages_passed": sum(1 for r in results if r["exit"] == 0),
        "failed_stage": failed,
        "stages_ok": stages_ok,
        "verification": verification,
        "passed": stages_ok and verified,
    }
    out = REPO / "data" / "quality" / "openfda_pipeline_run.json"
    out.write_text(json.dumps(report, indent=2))
    # Single source of truth for "last successfully COMPLETED + VERIFIED E2E run".
    # Written ONLY when stages AND final verification pass — the watchdog reads this
    # and never refreshes it on failure, so a dead/unverified pipeline stays stale.
    if report["passed"]:
        (REPO / "data" / "freshness" / "last_successful_e2e.json").write_text(json.dumps({
            "completed_at": report["ran_at"], "stages_passed": report["stages_passed"],
            "verified": True}, indent=2))
    # durable ledger: record EVERY primary run. Only success+verified advances the
    # latest-verified watermark (the watchdog reads this from BigQuery, not repo JSON).
    try:
        ledger.record_run(
            dag_type="primary", started_at=started_at, completed_at=report["ran_at"],
            result="success" if report["passed"] else "fail", attempts=1,
            recovery_state="na", final_verification=verified,
            duration_seconds=round(time.time() - run_t0, 1))
    except Exception as e:
        print(f"  [warn] ledger record failed: {repr(e)[:120]}", file=sys.stderr)
    print(json.dumps({k: report[k] for k in ("stages_passed", "stages_total", "failed_stage", "passed")}, indent=2))
    print(f"  verification: {verification and {k: v for k, v in verification.items() if k != 'bq_dup_check_error'}}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
