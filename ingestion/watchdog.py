"""
Freshness self-healing watchdog (Bchan smart-pipe standard).

Runs INDEPENDENTLY of the ingestion pipeline. Detects a stale/missed end-to-end
run, attempts BOUNDED safe recovery, VERIFIES the promised state was actually
restored, and if recovery fails or is unsafe, STOPS and escalates with evidence —
without falsely refreshing the last-successful-E2E timestamp.

detected   = watchdog found a stale/missed completed run
recovered  = bounded rerun restored ALL verification checks
escalated  = bounded recovery exhausted, or an unsafe failure (no auto-repair)

A JSON flag / exit code is detection + an escalation ARTIFACT — not an external
notification. We never call it "alert sent".

Exit-code contract from the recovery command: 0 ok · 3 unsafe (escalate now) · else transient.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ingestion"))
from verify_e2e import verify   # canonical verification, shared with run_pipeline
import ledger                    # durable BigQuery run-history (source of truth, not repo JSON)
E2E = REPO / "data" / "freshness" / "last_successful_e2e.json"
SLA = REPO / "config" / "freshness_sla.json"
Q = REPO / "data" / "quality"
UNSAFE_RC = 3


def _now():
    return datetime.now(timezone.utc)


def _ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _age_hours(iso):
    if not iso:
        return None
    t = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (_now() - t).total_seconds() / 3600


def _load(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--base-backoff", type=float, default=0.0)  # seconds; 0 for tests
    ap.add_argument("--recovery-cmd", default="ingestion/run_pipeline.py")
    ap.add_argument("--scenario", default="adhoc")
    ap.add_argument("--force-stale", action="store_true", help="treat E2E as stale regardless of age (test)")
    args = ap.parse_args()

    sla = _load(SLA) or {}
    err_h = sla.get("error_after_h", 48)
    t0 = time.time()
    started_at = _ts(_now())

    # SOURCE OF TRUTH = durable BigQuery ledger, NOT repo-local JSON (which evaporates
    # on ephemeral CI runners). Staleness is measured from the latest VERIFIED primary run.
    before_ts = ledger.latest_verified_primary()
    age = _age_hours(before_ts)
    stale = args.force_stale or age is None or age > err_h
    detected_at = _ts(_now())

    receipt = {"scenario": args.scenario, "detected_at": detected_at,
               "staleness_source": "bigquery_ledger.pipeline_run_history",
               "last_verified_primary_before": before_ts,
               "e2e_age_hours_at_detect": round(age, 2) if age else None,
               "stale_detected": stale, "max_attempts": args.max_attempts,
               "attempts": [], "actions": [], "failure_classification": None,
               "verification": None, "final_state": None, "last_verified_primary_after": None,
               "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                                            capture_output=True, text=True).stdout.strip()}

    if not stale:
        receipt["final_state"] = "ok_no_action"
        _record_watchdog(receipt, started_at, t0)
        _write(receipt, t0)
        print(f"[watchdog] fresh ({age:.1f}h < {err_h}h) — no action")
        return 0

    print(f"[watchdog] DETECTED stale/missed E2E (age={age}) — bounded recovery, max {args.max_attempts}")
    final = "escalated"
    for attempt in range(1, args.max_attempts + 1):
        env = {**os.environ, "WATCHDOG_ATTEMPT": str(attempt)}
        cmd = [sys.executable] + args.recovery_cmd.split()
        receipt["actions"].append(f"attempt {attempt}: {' '.join(cmd)}")
        rc = subprocess.run(cmd, cwd=REPO, env=env).returncode

        if rc == UNSAFE_RC:                              # unsafe -> escalate immediately
            receipt["attempts"].append({"attempt": attempt, "exit": rc, "result": "unsafe"})
            receipt["failure_classification"] = "unsafe_no_auto_repair"
            final = "escalated"
            break
        if rc == 0:                                      # candidate success -> must verify
            v = verify()
            receipt["attempts"].append({"attempt": attempt, "exit": rc,
                                        "result": "verified" if v["all_passed"] else "verify_failed"})
            receipt["verification"] = v
            if v["all_passed"]:
                final = "recovered"
                break
            receipt["failure_classification"] = "recovery_ran_but_verification_failed"
            final = "escalated"
            break
        # transient -> bounded exponential backoff, keep counting
        receipt["attempts"].append({"attempt": attempt, "exit": rc, "result": "transient_retry"})
        receipt["failure_classification"] = "transient"
        if attempt < args.max_attempts and args.base_backoff > 0:
            time.sleep(args.base_backoff * (2 ** (attempt - 1)))

    # CRITICAL: only a recovered+verified primary run advances the ledger watermark.
    after_ts = ledger.latest_verified_primary()
    receipt["last_verified_primary_after"] = after_ts
    receipt["final_state"] = final
    if final == "escalated":
        # an escalated recovery never produced a verified primary success, so the
        # ledger watermark must be unchanged. Assert it explicitly.
        receipt["latest_verified_unchanged_on_escalation"] = (after_ts == before_ts)
        esc = Q / f"freshness_escalation_{args.scenario}.json"
        esc.write_text(json.dumps(receipt, indent=2))
        receipt["escalation_artifact"] = str(esc.relative_to(REPO))
    _record_watchdog(receipt, started_at, t0)
    _write(receipt, t0)
    print(f"[watchdog] {final.upper()} after {len(receipt['attempts'])} attempt(s)")
    return 0 if final == "recovered" else 1


def _record_watchdog(receipt, started_at, t0):
    """Append this watchdog run to the durable ledger."""
    final = receipt["final_state"]
    try:
        ledger.record_run(
            dag_type="watchdog", started_at=started_at, completed_at=_ts(_now()),
            result="success" if final == "recovered" else ("na" if final == "ok_no_action" else "fail"),
            attempts=len(receipt["attempts"]),
            recovery_state=final if final in ("recovered", "escalated") else "na",
            final_verification=bool(receipt.get("verification", {}) and receipt["verification"].get("all_passed")),
            duration_seconds=round(time.time() - t0, 1))
    except Exception as e:
        receipt["ledger_warn"] = repr(e)[:120]


def _write(receipt, t0):
    receipt["mttr_seconds"] = round(time.time() - t0, 1)
    out = Q / f"freshness_watchdog_{receipt['scenario']}.json"
    out.write_text(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    sys.exit(main())
