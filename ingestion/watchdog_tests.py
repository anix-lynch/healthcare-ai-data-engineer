"""
Self-healing watchdog test suite (Bchan smart-pipe claim gate).

Proves all four required scenarios. "self-healing freshness" stays YELLOW unless
every scenario passes:
  A recoverable missed-run  -> detect -> recover (REAL pipeline) -> verify -> recorded
  B transient API failure   -> bounded retry eventually succeeds, warehouse dup-free
  C exhausted recovery      -> exactly max_attempts, no infinite loop,
                               E2E timestamp NOT falsely refreshed, escalation artifact
  D unsafe failure          -> NO auto-repair, stop + escalate immediately
"""
from __future__ import annotations
import json, os, subprocess, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# staleness/watermark now live in the durable ledger — use a throwaway table here
os.environ["LEDGER_TABLE"] = "pipeline_run_history_wtest"
os.environ.setdefault("GCP_PROJECT_ID", "PROJECT")
os.environ.setdefault("BQ_DATASET", "healthcare_analytics")
REPO = Path(__file__).resolve().parents[1]
Q = REPO / "data" / "quality"
PY = sys.executable
sys.path.insert(0, str(REPO / "ingestion"))
import ledger


def watchdog(scenario, max_attempts, recovery_cmd, fault=None):
    env = {**os.environ, "BQ_LOCATION": "US"}
    if fault:
        env["FAULT_MODE"] = fault
    subprocess.run([PY, "ingestion/watchdog.py", "--scenario", scenario, "--force-stale",
                    "--max-attempts", str(max_attempts), "--base-backoff", "0",
                    "--recovery-cmd", recovery_cmd], cwd=REPO, env=env)
    return json.loads((Q / f"freshness_watchdog_{scenario}.json").read_text())


def set_baseline_e2e(hours_old):
    """Seed a verified-primary watermark in the durable ledger (not repo JSON)."""
    ledger.record_run("primary", "2026-01-01T00:00:00Z",
                      (datetime.now(timezone.utc) - timedelta(hours=hours_old)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                      "success", 1, "na", True, 10.0)
    return ledger.latest_verified_primary()


def _drop():
    from google.cloud import bigquery
    bigquery.Client(project=ledger.PROJECT).query(
        f"DROP TABLE IF EXISTS `{ledger.TABLE}`", job_config=ledger.JOB).result()


def main():
    results = {}

    # A — recoverable missed run via the REAL pipeline
    a = watchdog("A", 2, "ingestion/run_pipeline.py")
    results["A_recoverable_missed_run"] = {
        "final_state": a["final_state"],
        "pass": a["final_state"] == "recovered" and a["verification"]["all_passed"],
    }

    # B — transient failures then success; bounded retry recovers, warehouse dup-free
    b = watchdog("B", 4, "ingestion/recovery_target.py", fault="transient_then_ok:2")
    b_attempts = [x["result"] for x in b["attempts"]]
    results["B_transient_retry"] = {
        "attempts": b_attempts, "final_state": b["final_state"],
        "pass": (b["final_state"] == "recovered"
                 and b_attempts[:2] == ["transient_retry", "transient_retry"]
                 and b["verification"]["all_passed"]
                 and b["verification"].get("no_duplicate_pks_in_bq") is True),
    }

    # C — exhausted: exactly max_attempts, no infinite loop, ledger watermark NOT advanced, escalated
    _drop(); base_c = set_baseline_e2e(100)
    c = watchdog("C", 3, "ingestion/recovery_target.py", fault="always_transient")
    results["C_exhausted_recovery"] = {
        "attempts_made": len(c["attempts"]), "final_state": c["final_state"],
        "watermark_unchanged": c.get("latest_verified_unchanged_on_escalation"),
        "pass": (c["final_state"] == "escalated" and len(c["attempts"]) == 3
                 and all(x["result"] == "transient_retry" for x in c["attempts"])
                 and c.get("latest_verified_unchanged_on_escalation") is True
                 and c["last_verified_primary_after"] == base_c
                 and bool(c.get("escalation_artifact"))),
    }

    # D — unsafe: no auto-repair, escalate immediately (single attempt)
    _drop(); base_d = set_baseline_e2e(100)
    d = watchdog("D", 5, "ingestion/recovery_target.py", fault="unsafe")
    results["D_unsafe_failure"] = {
        "attempts_made": len(d["attempts"]), "final_state": d["final_state"],
        "classification": d["failure_classification"],
        "pass": (d["final_state"] == "escalated" and len(d["attempts"]) == 1
                 and d["failure_classification"] == "unsafe_no_auto_repair"
                 and d["last_verified_primary_after"] == base_d
                 and bool(d.get("escalation_artifact"))),
    }

    _drop()
    all_pass = all(v["pass"] for v in results.values())
    score = "green" if all_pass else "yellow"
    report = {"suite": "freshness_self_healing", "scenarios": results,
              "all_scenarios_pass": all_pass, "self_healing_score": score,
              "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                                           capture_output=True, text=True).stdout.strip()}
    (Q / "freshness_selfheal_tests.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v["pass"] for k, v in results.items()}, indent=2))
    print(f"self_healing_score = {score}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
