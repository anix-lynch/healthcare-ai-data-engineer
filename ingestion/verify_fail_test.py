"""
Proof: a verification failure leaves last_successful_e2e UNCHANGED (Bullet 2 gap 4).

Stages may all exit 0, but if final verification fails the run is NOT successful and
the E2E timestamp must NOT advance — otherwise a broken pipeline could lie "fresh".
We force verification to fail (FAULT_VERIFY=1) and assert the timestamp is untouched.
Writes data/quality/openfda_verify_fail_test.json.
"""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
E2E = REPO / "data" / "freshness" / "last_successful_e2e.json"


def main():
    before = E2E.read_text() if E2E.exists() else None
    before_ts = json.loads(before)["completed_at"] if before else None

    env = {**os.environ, "FAULT_VERIFY": "1"}
    rc = subprocess.run([sys.executable, "ingestion/run_pipeline.py"], cwd=REPO, env=env).returncode

    run = json.loads((REPO / "data" / "quality" / "openfda_pipeline_run.json").read_text())
    after_ts = json.loads(E2E.read_text())["completed_at"] if E2E.exists() else None

    checks = {
        "pipeline_exits_nonzero_on_verify_fail": rc != 0,
        "stages_ran_ok": bool(run.get("stages_ok")),
        "verification_failed": run.get("verification", {}).get("all_passed") is False,
        "run_marked_not_passed": run.get("passed") is False,
        "e2e_timestamp_unchanged": after_ts == before_ts,
    }
    report = {"test": "verify_failure_leaves_timestamp_unchanged",
              "pipeline_exit": rc, "e2e_before": before_ts, "e2e_after": after_ts,
              "checks": checks, "passed": all(checks.values())}
    out = REPO / "data" / "quality" / "openfda_verify_fail_test.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
