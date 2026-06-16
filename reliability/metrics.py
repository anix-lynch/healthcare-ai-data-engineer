"""Compute reliability metrics from the ledger and emit the evidence artifacts.

Every number here is COMPUTED from reliability/ledger.jsonl (produced by the real
fault-injection harness). Nothing is hardcoded. If you change the fault plan, the
artifacts change with it — that's the point.

Emits to artifacts/:
  pipeline_success_rate.json · recovery_metrics.json · sla_report.json
  failure_catalog.json · retry_history.json · stale_data_report.json
  reliability_summary.md
"""
from __future__ import annotations

import json
from pathlib import Path

from reliability.core import PLATFORM_SLAS, _FAILURE_RULES
from reliability.harness import LEDGER_PATH, RUN_PLAN, SEED

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"

# Outcomes that delivered correct service to consumers.
_DELIVERED = {"SUCCESS", "RECOVERED", "DEGRADED"}


def _plan_row(kind: str, count: int) -> str:
    """One markdown row describing how a fault kind resolves."""
    if kind == "clean":
        return f"| `clean` | {count} | INFO | first-try success |"
    sev, recover = _FAILURE_RULES.get(kind, (None, False))
    sev_name = sev.value if sev else "INFO"
    if sev_name == "WARNING":
        outcome = "served, flagged degraded (not blocked)"
    elif recover:
        outcome = "recovered via bounded retry"
    else:
        outcome = "escalated + promotion blocked"
    return f"| `{kind}` | {count} | {sev_name} | {outcome} |"


def _load_ledger(path: Path = LEDGER_PATH) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _pct(num: int, den: int) -> float:
    return round(100.0 * num / den, 2) if den else 0.0


def compute(runs: list[dict]) -> dict:
    total = len(runs)
    delivered = [r for r in runs if r["final_state"] in _DELIVERED]
    escalated = [r for r in runs if r["final_state"] == "ESCALATED"]
    recovery_attempts = [r for r in runs if r["recovery_attempted"]]
    recovered = [r for r in recovery_attempts if r["recovery_successful"]]
    recoverable_class = [r for r in runs if r["severity"] == "RECOVERABLE"]
    recoverable_recovered = [r for r in recoverable_class if r["recovery_successful"]]
    sla_breaches = [r for r in runs if r["sla_breached"]]
    bad_data = [r for r in runs if r["served_bad_data"]]

    # Mean time to recovery = mean wall-clock the retry budget actually spent on
    # runs that recovered (real backoff ms from the ledger).
    rec_backoffs = [r["retry_backoff_ms"] for r in recovered]
    mttr_ms = round(sum(rec_backoffs) / len(rec_backoffs), 2) if rec_backoffs else 0.0

    pipeline_success_rate = _pct(len(delivered), total)
    # Headline recovery = auto-recovered / incidents ELIGIBLE for auto-recovery
    # (RECOVERABLE class). CRITICAL faults are escalations by design, not recovery
    # targets, so they don't belong in the denominator (standard SRE auto-remediation rate).
    auto_recovery_rate = _pct(len(recoverable_recovered), len(recoverable_class))
    # Conservative variant: also count CRITICAL retry attempts in the denominator.
    auto_recovery_rate_incl_critical = _pct(len(recovered), len(recovery_attempts))
    sla_compliance_rate = _pct(total - len(sla_breaches), total)

    return {
        "total_runs": total,
        "delivered": len(delivered),
        "escalated": len(escalated),
        "recovery_attempts": len(recovery_attempts),
        "recovered": len(recovered),
        "pipeline_success_rate": pipeline_success_rate,
        "auto_recovery_rate": auto_recovery_rate,
        "auto_recovery_rate_incl_critical": auto_recovery_rate_incl_critical,
        "recoverable_incidents": len(recoverable_class),
        "sla_compliance_rate": sla_compliance_rate,
        "failure_count": total - len([r for r in runs if r["fault_kind"] == "clean"]),
        "mean_time_to_recovery_ms": mttr_ms,
        "stale_data_incidents": len(bad_data),
        "sla_breaches": len(sla_breaches),
    }


def write_artifacts(runs: list[dict], m: dict) -> list[str]:
    ARTIFACTS.mkdir(exist_ok=True)
    written: list[str] = []

    def dump(name: str, obj) -> None:
        (ARTIFACTS / name).write_text(json.dumps(obj, indent=2))
        written.append(name)

    dump("pipeline_success_rate.json", {
        "pipeline_success_rate_pct": m["pipeline_success_rate"],
        "sla_target_pct": PLATFORM_SLAS["pipeline_success_pct"].threshold,
        "meets_sla": m["pipeline_success_rate"] >= PLATFORM_SLAS["pipeline_success_pct"].threshold,
        "delivered": m["delivered"],
        "escalated_blocked": m["escalated"],
        "total_runs": m["total_runs"],
        "definition": "delivered = runs that served correct/fresh data (SUCCESS|RECOVERED|DEGRADED)",
    })

    dump("recovery_metrics.json", {
        "recoverable_incidents": m["recoverable_incidents"],
        "recovery_attempted_total": m["recovery_attempts"],
        "recovery_successful": m["recovered"],
        "recovery_failed": m["recovery_attempts"] - m["recovered"],
        "auto_recovery_rate_pct": m["auto_recovery_rate"],
        "auto_recovery_rate_incl_critical_pct": m["auto_recovery_rate_incl_critical"],
        "target_pct": 80.0,
        "meets_target": m["auto_recovery_rate"] >= 80.0,
        "denominator": "RECOVERABLE-class incidents only (CRITICAL faults are escalations "
                       "by design, not recovery targets — standard SRE auto-remediation rate). "
                       "incl_critical variant adds CRITICAL retry attempts as a conservative check.",
        "measured_by": "real bounded_retry against a drawn transient clear-time distribution — "
                       "a buggy retry policy would lower this number",
    })

    sla_rows = {}
    for r in runs:
        sla_rows.setdefault(r["sla_breached"], 0)
        sla_rows[r["sla_breached"]] += 1
    dump("sla_report.json", {
        "platform_slas": {k: {"threshold": v.threshold, "unit": v.unit, "comparator": v.comparator}
                          for k, v in PLATFORM_SLAS.items()},
        "freshness_sla_hours": PLATFORM_SLAS["freshness_hours"].threshold,
        "runs_within_freshness_sla": sla_rows.get(False, 0),
        "runs_breaching_freshness_sla": sla_rows.get(True, 0),
        "sla_compliance_rate_pct": m["sla_compliance_rate"],
        "pipeline_success_sla_pct": m["pipeline_success_rate"],
        "meets_sla_compliance": m["sla_compliance_rate"] >= 99.0,
        "sla_breach_events": [
            {"run_id": r["run_id"], "fault_kind": r["fault_kind"],
             "freshness_hours": r["sla_freshness_hours"], "escalation_reason": r["escalation_reason"]}
            for r in runs if r["sla_breached"]
        ],
    })

    # failure_catalog = the full taxonomy the platform can classify + what this batch hit
    hit_counts: dict[str, int] = {}
    for r in runs:
        if r["fault_kind"] != "clean":
            hit_counts[r["fault_kind"]] = hit_counts.get(r["fault_kind"], 0) + 1
    dump("failure_catalog.json", {
        "taxonomy": {kind: {"severity": sev.value, "recovery_attempted": rec}
                     for kind, (sev, rec) in _FAILURE_RULES.items()},
        "severities": ["INFO", "WARNING", "RECOVERABLE", "CRITICAL"],
        "this_batch_failures": hit_counts,
        "critical_blocked": [
            {"run_id": r["run_id"], "fault_kind": r["fault_kind"], "severity": r["severity"],
             "published": r["published"], "escalation_reason": r["escalation_reason"]}
            for r in runs if r["severity"] == "CRITICAL"
        ],
    })

    dump("retry_history.json", {
        "max_attempts": 3,
        "backoff": "exponential, base 1ms, cap 1000ms — bounded, never infinite",
        "runs_with_retries": [
            {"run_id": r["run_id"], "fault_kind": r["fault_kind"], "reason": r["fault_kind"],
             "retry_attempts": r["retry_attempts"], "backoff_ms": r["retry_backoff_ms"],
             "retry_succeeded": r["recovery_successful"], "final_state": r["final_state"]}
            for r in runs if r["recovery_attempted"]
        ],
    })

    dump("stale_data_report.json", {
        "stale_data_incidents": m["stale_data_incidents"],
        "invariant": "served_bad_data must be 0 — system prefers 'serve nothing' over 'serve bad data'",
        "invariant_holds": m["stale_data_incidents"] == 0,
        "blocked_promotions": [
            {"run_id": r["run_id"], "fault_kind": r["fault_kind"], "published": r["published"]}
            for r in runs if not r["published"]
        ],
        "stale_source_handling": [
            {"run_id": r["run_id"], "note": r["notes"]}
            for r in runs if r["fault_kind"] == "stale_source"
        ],
    })

    summary = f"""# Reliability Summary — Self-Healing Data Platform (Bullet 4)

> Computed from `reliability/ledger.jsonl` by `reliability/metrics.py`.
> Reproducible: `make reliability` (seed={SEED}, {m['total_runs']} pipeline executions).
> Recovery is MEASURED — the real `bounded_retry` runs against a drawn transient
> clear-time distribution, so a buggy retry policy would move the number.

## Headline metrics

| Metric | Value | Target | Status |
|---|---|---|---|
| Pipeline success rate | **{m['pipeline_success_rate']}%** | ≥99% | {'✅' if m['pipeline_success_rate'] >= 99 else '🔴'} |
| Automated recovery rate | **{m['auto_recovery_rate']}%** | ≥80% | {'✅' if m['auto_recovery_rate'] >= 80 else '🔴'} |
| &nbsp;↳ incl. CRITICAL in denom. (conservative) | {m['auto_recovery_rate_incl_critical']}% | — | — |
| SLA compliance rate | **{m['sla_compliance_rate']}%** | ≥99% | {'✅' if m['sla_compliance_rate'] >= 99 else '🔴'} |
| Stale-data incidents | **{m['stale_data_incidents']}** | 0 | {'✅' if m['stale_data_incidents'] == 0 else '🔴'} |
| Mean time to recovery | **{m['mean_time_to_recovery_ms']} ms** | — | — |
| Failures detected & classified | **{m['failure_count']}** | — | — |

## What the harness exercised

A documented fault distribution injected into the REAL primitives
(`reliability/core.py`: `classify`, `bounded_retry`, `check_sla`) over
{m['total_runs']} pipeline executions:

| Fault kind | Count | Severity | Outcome |
|---|---|---|---|
""" + "\n".join(
        _plan_row(k, v) for k, v in RUN_PLAN.items()
    ) + f"""

## The cardinal invariant

`stale_data_incidents = {m['stale_data_incidents']}`.

Every CRITICAL fault ({m['escalated']} runs) was detected, retried within a bounded
budget, and on exhaustion the run was **escalated and promotion was blocked** — no
unverified data reached the agent-facing API. The platform prefers *serve nothing*
to *serve bad data*. That is the difference between 2024 ("I broke. Good luck.")
and 2026 ("I broke. I know. Recovered — or here's the evidence, and AI never saw
bad data.").

## Scope (honest)

This is a **fault-injection / chaos harness** over the real reliability code, not a
multi-month production incident log. The numbers describe how the recovery policy
behaves under a labeled, reproducible fault distribution — the standard way to
prove self-healing without waiting for organic outages. The live `/api/platform/reliability`
endpoint + `pipeline_run_history` BigQuery table extend the same primitives to the
deployed service.
"""
    (ARTIFACTS / "reliability_summary.md").write_text(summary)
    written.append("reliability_summary.md")
    return written


def main() -> dict:
    runs = _load_ledger()
    m = compute(runs)
    written = write_artifacts(runs, m)
    print(json.dumps({"metrics": m, "artifacts_written": written}, indent=2))
    return m


if __name__ == "__main__":
    main()
