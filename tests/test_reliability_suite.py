"""Tests for the self-healing reliability layer (Bullet 4).

Asserts the BEHAVIOR, not the exact numbers — except the one invariant that must
never move: zero bad data ever reaches consumers.
"""
from __future__ import annotations

from reliability import harness, metrics
from reliability.core import (
    FailureSeverity,
    PLATFORM_SLAS,
    bounded_retry,
    check_sla,
    classify,
    gate_publish,
)


def test_classify_unknown_fails_safe():
    sev, recover = classify("something_never_seen")
    assert sev == FailureSeverity.CRITICAL
    assert recover is False


def test_classify_known_kinds():
    assert classify("transient_api") == (FailureSeverity.RECOVERABLE, True)
    assert classify("failed_validation")[0] == FailureSeverity.CRITICAL
    assert classify("failed_validation")[1] is False


def test_bounded_retry_recovers_transient():
    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] < 2:
            raise RuntimeError("transient")
        return "ok"

    result, outcome = bounded_retry(flaky, operation="t", reason="transient", max_attempts=3, base_delay_ms=0.1)
    assert result == "ok"
    assert outcome.succeeded is True
    assert outcome.attempts == 2


def test_bounded_retry_is_bounded():
    def always():
        raise RuntimeError("permanent")

    result, outcome = bounded_retry(always, operation="p", reason="permanent", max_attempts=3, base_delay_ms=0.1)
    assert outcome.succeeded is False
    assert outcome.attempts == 3            # NEVER infinite
    assert len(outcome.backoff_ms) == 2     # backed off between attempts only


def test_sla_breach_detection():
    assert check_sla("freshness_hours", 30.0).breached is True
    assert check_sla("freshness_hours", 5.0).breached is False
    assert check_sla("pipeline_success_pct", 99.5).breached is False
    assert check_sla("pipeline_success_pct", 97.0).breached is True


def test_gate_is_load_bearing():
    # The gate — not a hardcoded flag — is what blocks bad data. Prove both branches.
    assert gate_publish(FailureSeverity.CRITICAL, recovered=False) is False
    assert gate_publish(FailureSeverity.CRITICAL, recovered=True) is False   # critical never publishes
    assert gate_publish(FailureSeverity.RECOVERABLE, recovered=False) is False  # unrecovered blocked
    assert gate_publish(FailureSeverity.RECOVERABLE, recovered=True) is True
    assert gate_publish(FailureSeverity.INFO, recovered=False) is True


def test_suite_meets_resume_bar():
    runs = harness.run_suite()
    m = metrics.compute(runs)
    assert m["total_runs"] == 1000
    assert m["pipeline_success_rate"] >= 99.0
    assert m["auto_recovery_rate"] >= 80.0
    assert m["sla_compliance_rate"] >= 99.0


def test_cardinal_invariant_no_bad_data_ever():
    runs = harness.run_suite()
    # served_bad_data is COMPUTED by gate_publish, so this can actually fail if the
    # gate regresses. No run may serve bad data; every CRITICAL must be blocked.
    assert all(r["served_bad_data"] is False for r in runs)
    criticals = [r for r in runs if r["severity"] == "CRITICAL"]
    assert criticals, "expected the batch to exercise CRITICAL faults"
    assert all(r["published"] is False for r in criticals)


def test_artifacts_written():
    runs = harness.run_suite()
    m = metrics.compute(runs)
    written = metrics.write_artifacts(runs, m)
    for name in ("pipeline_success_rate.json", "recovery_metrics.json", "sla_report.json",
                 "failure_catalog.json", "retry_history.json", "stale_data_report.json",
                 "reliability_summary.md"):
        assert name in written
        assert (metrics.ARTIFACTS / name).exists()
