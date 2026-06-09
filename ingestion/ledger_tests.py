"""
Persistent ledger proof suite (Bullet 2 durability — Codex proofs A,B,C,D).

A persisted FRESH primary success  -> watchdog takes no action
B persisted STALE primary success  -> watchdog detects and recovers (real pipeline)
C failed/unverified run             -> latest verified success watermark UNCHANGED
D ledger yields reliability metrics from the real test runs

Uses a throwaway ledger table (LEDGER_TABLE) dropped at the end — the real
pipeline_run_history is untouched.
"""
from __future__ import annotations
import json, os, subprocess, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

os.environ["LEDGER_TABLE"] = "pipeline_run_history_test"
os.environ.setdefault("GCP_PROJECT_ID", "PROJECT")
os.environ.setdefault("BQ_DATASET", "healthcare_analytics")
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ingestion"))
import ledger
from google.cloud import bigquery

PY = sys.executable
ENV = {**os.environ}
Q = REPO / "data" / "quality"


def drop():
    bigquery.Client(project=ledger.PROJECT).query(
        f"DROP TABLE IF EXISTS `{ledger.TABLE}`", job_config=ledger.JOB).result()


def seed_primary(hours_old, result="success", verified=True):
    ts = (datetime.now(timezone.utc) - timedelta(hours=hours_old)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ledger.record_run("primary", ts, ts, result, 1, "na", verified, 10.0)
    return ts


def watchdog(scenario, recovery_cmd, fault=None, force_stale=False, max_attempts=3):
    env = {**ENV}
    if fault:
        env["FAULT_MODE"] = fault
    cmd = [PY, "ingestion/watchdog.py", "--scenario", scenario, "--max-attempts", str(max_attempts),
           "--base-backoff", "0", "--recovery-cmd", recovery_cmd]
    if force_stale:
        cmd.append("--force-stale")
    subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True)
    return json.loads((Q / f"freshness_watchdog_{scenario}.json").read_text())


def main():
    res = {}

    # A — fresh persisted primary success -> no action
    drop(); seed_primary(0)
    a = watchdog("ledgerA", "ingestion/run_pipeline.py")
    res["A_fresh_no_action"] = {"final": a["final_state"],
                                "pass": a["final_state"] == "ok_no_action"}

    # B — stale persisted primary -> detect + recover via the real pipeline
    drop(); base_b = seed_primary(100)
    b = watchdog("ledgerB", "ingestion/run_pipeline.py")
    after_b = ledger.latest_verified_primary()
    res["B_stale_recovers"] = {"final": b["final_state"], "before": base_b, "after": after_b,
                               "pass": b["final_state"] == "recovered" and after_b != base_b and after_b is not None}

    # C — failed/unverified run must NOT advance the verified watermark
    drop(); base_c = seed_primary(100)                 # the only verified success
    seed_primary(1, result="fail", verified=False)     # a recent FAILED run
    seed_primary(1, result="success", verified=False)  # a recent stages-ok-but-UNVERIFIED run
    c = watchdog("ledgerC", "ingestion/recovery_target.py", fault="always_transient", force_stale=True)
    after_c = ledger.latest_verified_primary()
    res["C_failed_unverified_no_advance"] = {
        "final": c["final_state"], "watermark_before": base_c, "watermark_after": after_c,
        "pass": (c["final_state"] == "escalated" and after_c == base_c
                 and c.get("latest_verified_unchanged_on_escalation") is True)}

    # D — reliability metrics from the real runs recorded above
    m = ledger.reliability_metrics()
    res["D_reliability_metrics"] = {"metrics": m,
        "pass": (m["dag_success_rate"] is not None and m["incident_count"] >= 1
                 and m["retry_recovery_rate"] is not None and m["primary_runs"] >= 1)}

    drop()
    all_pass = all(v["pass"] for v in res.values())
    report = {"suite": "persistent_ledger", "scenarios": res, "all_pass": all_pass,
              "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                                           capture_output=True, text=True).stdout.strip()}
    (Q / "ledger_tests.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v["pass"] for k, v in res.items()}, indent=2))
    print("metrics:", json.dumps(res["D_reliability_metrics"]["metrics"]))
    print("all_pass:", all_pass)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
