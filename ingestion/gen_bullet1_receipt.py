"""
Bullet 1 claim receipt (proof 8) — map every phrase of the Trust + dual-mode bullet
to a generated proof file. CLAIM APPROVED only if every phrase is backed by a real run.
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


pipe = load("data/quality/openfda_pipeline_run.json")
stream = load("data/quality/openfda_streaming_proof.json")
recon = load("data/quality/openfda_reconciliation.json")
reconf = load("data/quality/openfda_reconciliation_full.json")
quar = load("data/quality/openfda_quarantine_tests.json")
ge = load("data/quality/openfda_ge_validation.json")
rr = load("dbt-project/proof/run_results.json")
fc = load("data/quality/openfda_failclose_test.json")
late = load("data/quality/openfda_late_arriving.json")
backf = load("data/quality/openfda_backfill_test.json")

dbt_ok = bool(rr and all(r["status"] in ("pass", "success") for r in rr["results"]))

phrases = [
    ("batch ingestion pipeline", "openfda_pipeline_run.json",
     bool(pipe and pipe.get("passed"))),
    ("real-time ingestion pipeline (native Pub/Sub->BigQuery)", "openfda_streaming_proof.json",
     bool(stream and stream.get("checks", {}).get("p3_native_pubsub_to_bq"))),
    ("idempotent BigQuery merges", "openfda_reconciliation.json + streaming converge",
     bool(recon and recon["leg_b_accepted_to_warehouse"]["net_new_rows"] == 0
          and stream and stream["checks"].get("p4_converged_no_dup_pk"))),
    ("record-level quarantine", "openfda_quarantine_tests.json",
     bool(quar and quar["scenarios"]["A_isolate_and_continue"]["pass"]
          and quar["scenarios"]["B_replay_exactly_once"]["pass"])),
    ("Great Expectations + dbt quality gates", "openfda_ge_validation.json + run_results.json + failclose",
     bool(ge and ge.get("success") and dbt_ok and fc and fc.get("passed"))),
    ("source-to-warehouse reconciliation", "openfda_reconciliation_full.json",
     bool(reconf and reconf.get("reconciles"))),
    ("safely process DUPLICATE", "openfda_reconciliation.json (net_new=0)",
     bool(recon and recon["leg_b_accepted_to_warehouse"]["net_new_rows"] == 0)),
    ("safely process MALFORMED", "openfda_quarantine_tests.json + streaming DLQ",
     bool(quar and quar["scenarios"]["A_isolate_and_continue"]["pass"]
          and stream and stream["checks"].get("p5_malformed_to_dlq_valid_unblocked"))),
    ("safely process REVISED", "openfda_late_arriving.json (revised_updated_not_duplicated)",
     bool(late and late["checks"].get("revised_updated_not_duplicated"))),
    ("safely process LATE-ARRIVING", "openfda_late_arriving.json (late_new_inserted)",
     bool(late and late["checks"].get("late_new_inserted"))),
    ("safely process MISSING", "openfda_backfill_test.json",
     bool(backf and backf.get("passed"))),
]

rows = [{"phrase": p, "proof": pf, "pass": ok} for p, pf, ok in phrases]
unsupported = [r["phrase"] for r in rows if not r["pass"]]
bullet = ("Engineered batch and real-time ingestion pipelines for openFDA healthcare data, "
          "using idempotent BigQuery merges, record-level quarantine, Great Expectations and dbt "
          "quality gates, and source-to-warehouse reconciliation to safely process duplicate, "
          "malformed, revised, late-arriving, and missing records.")
receipt = {
    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip(),
    "bullet": bullet, "phrases": rows, "unsupported": unsupported,
    "verdict": "CLAIM REJECTED" if unsupported else "CLAIM APPROVED — every phrase backed by a generated proof file",
}
(Q / "bullet1_claim_receipt.json").write_text(json.dumps(receipt, indent=2))
for r in rows:
    print(("✅" if r["pass"] else "❌"), r["phrase"])
print("VERDICT:", receipt["verdict"])
import sys
sys.exit(0 if not unsupported else 1)
