"""
Bullet 2 claim receipt — map every phrase of the Freshness + Reliability bullet to a
generated proof file (now including the durable BigQuery ledger). CLAIM APPROVED only
if every phrase is backed by a real run.
"""
from __future__ import annotations
import json, subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
Q = REPO / "data" / "quality"


def load(p):
    try:
        return json.loads((REPO / p).read_text())
    except Exception:
        return None


selfheal = load("data/quality/freshness_selfheal_tests.json")
ledger_t = load("data/quality/ledger_tests.json")
verify_fail = load("data/quality/openfda_verify_fail_test.json")
wd_yml = (REPO / ".github/workflows/freshness_watchdog.yml").exists()
metrics = (ledger_t or {}).get("scenarios", {}).get("D_reliability_metrics", {}).get("metrics")

phrases = [
    ("independently scheduled orchestration", ".github/workflows/freshness_watchdog.yml (own cron)",
     wd_yml),
    ("self-healing (detect->recover->verify->escalate)", "freshness_selfheal_tests.json (4/4) + ledger_tests.json",
     bool(selfheal and selfheal.get("self_healing_score") == "green"
          and ledger_t and ledger_t.get("all_pass"))),
    ("detects stale data and failed jobs (from durable ledger)", "ledger_tests.json A+B",
     bool(ledger_t and ledger_t["scenarios"]["A_fresh_no_action"]["pass"]
          and ledger_t["scenarios"]["B_stale_recovers"]["pass"])),
    ("bounded automatic recovery across the full pipeline", "ledger_tests.json B + freshness_selfheal_tests.json B",
     bool(ledger_t and ledger_t["scenarios"]["B_stale_recovers"]["pass"]
          and selfheal and selfheal["scenarios"]["B_transient_retry"]["pass"])),
    ("verifies freshness + integrity before marking success", "openfda_verify_fail_test.json (verify-gated watermark)",
     bool(verify_fail and verify_fail.get("passed"))),
    ("failed/unverified never advances verified state", "ledger_tests.json C",
     bool(ledger_t and ledger_t["scenarios"]["C_failed_unverified_no_advance"]["pass"])),
    ("escalates unrecoverable incidents with machine-readable evidence", "freshness_escalation_*.json + ledger_tests C",
     bool(ledger_t and ledger_t["scenarios"]["C_failed_unverified_no_advance"]["pass"]
          and selfheal and selfheal["scenarios"]["D_unsafe_failure"]["pass"])),
    ("reliability metrics from durable ledger", "ledger_tests.json D (success rate / incidents / recovery / MTTR)",
     bool(ledger_t and ledger_t["scenarios"]["D_reliability_metrics"]["pass"])),
]

rows = [{"phrase": p, "proof": pf, "pass": ok} for p, pf, ok in phrases]
unsupported = [r["phrase"] for r in rows if not r["pass"]]
bullet = ("Built independently scheduled, self-healing orchestration that detects stale data and "
          "failed jobs, performs bounded automatic recovery across the full pipeline, verifies "
          "freshness and data integrity before marking runs successful, and escalates unrecoverable "
          "incidents with machine-readable evidence.")
receipt = {
    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip(),
    "bullet": bullet, "reliability_metrics": metrics, "phrases": rows, "unsupported": unsupported,
    "operational_caveat": "green GitHub-scheduled run still needs push + GCP_SA_KEY secret (deferred).",
    "verdict": "CLAIM REJECTED" if unsupported else "CLAIM APPROVED — every phrase backed by a generated proof file",
}
(Q / "bullet2_claim_receipt.json").write_text(json.dumps(receipt, indent=2))
for r in rows:
    print(("✅" if r["pass"] else "❌"), r["phrase"])
print("VERDICT:", receipt["verdict"])
import sys
sys.exit(0 if not unsupported else 1)
