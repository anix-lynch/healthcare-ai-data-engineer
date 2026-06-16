"""Fault-injection harness — proves self-healing behavior on REAL primitives.

Instead of waiting months for production incidents, we inject a documented fault
distribution into the real reliability primitives (reliability/core.py) and record
what actually happens. The metrics are MEASURED, not assumed:

  • A transient fault is given a drawn clear-time (how many times it fails before it
    would succeed) from TRANSIENT_CLEAR_DIST. Whether it recovers is decided by
    running the REAL bounded_retry against it — if the clear-time exceeds the retry
    budget, it does NOT recover. So auto_recovery_rate is a true function of
    (max_attempts, backoff) vs the fault model. Break bounded_retry → the number moves.

  • Whether a run publishes is decided by the REAL gate_publish(). served_bad_data is
    computed by that gate, never hardcoded — so the cardinal-invariant test can fail
    if the gate ever regresses.

Faults are seeded (deterministic, auditable) so the run is reproducible.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from reliability.core import (
    FailureSeverity,
    SLAResult,
    bounded_retry,
    check_sla,
    classify,
    gate_publish,
)

LEDGER_PATH = Path(__file__).resolve().parent / "ledger.jsonl"
SEED = 4
MAX_ATTEMPTS = 4  # one initial try + up to 3 retries (documented retry-policy lever)

# Transient clear-time distribution: number of failures before the op would succeed.
# A transient recovers iff clear_time < MAX_ATTEMPTS (i.e. <= 3 here). The stubborn
# tail (>=4) genuinely exhausts the budget → escalates. This distribution is the
# fault MODEL; the recovery rate is whatever the real bounded_retry achieves against
# it. Break bounded_retry (e.g. try-once) and ~90% of these would fail instead.
TRANSIENT_CLEAR_DIST = [1, 1, 1, 1, 1, 2, 2, 2, 3, 5]  # stubborn tail at 5 exhausts the budget

# Documented fault plan over 1000 pipeline executions.
RUN_PLAN: dict[str, int] = {
    "clean": 925,
    "transient_api": 45,           # RECOVERABLE — retry
    "transient_bigquery": 20,      # RECOVERABLE — retry
    "stale_partition": 5,          # RECOVERABLE — backfill
    "failed_validation": 1,        # CRITICAL — block (bad rows never published)
    "reconciliation_mismatch": 1,  # CRITICAL — block (row-loss never published)
    "stale_source": 1,             # CRITICAL — don't refresh agent-facing API
    "elevated_quarantine": 2,      # WARNING — serve, but flagged degraded
}

# Fault kinds that corrupt data — if these ever reached consumers it would be bad data.
_DATA_CORRUPTING = {"failed_validation", "reconciliation_mismatch", "schema_drift",
                    "quality_gate_breach", "stale_source"}


@dataclass
class RunRecord:
    run_id: str
    started_at: str
    fault_kind: str
    severity: str
    recovery_attempted: bool
    recovery_successful: bool
    retry_attempts: int
    retry_backoff_ms: int
    final_state: str           # SUCCESS | RECOVERED | ESCALATED | DEGRADED
    published: bool
    served_bad_data: bool
    sla_freshness_hours: float
    sla_breached: bool
    escalation_reason: str | None = None
    notes: list[str] = field(default_factory=list)


def _flaky(fail_times: int) -> Any:
    """Callable that raises ``fail_times`` then succeeds — a transient with a clear-time."""
    state = {"calls": 0}

    def op() -> str:
        state["calls"] += 1
        if state["calls"] <= fail_times:
            raise RuntimeError(f"transient failure (call {state['calls']})")
        return "ok"

    return op


def _always_fails(msg: str) -> Any:
    def op() -> str:
        raise RuntimeError(msg)

    return op


def _execute_run(run_id: str, fault_kind: str, rng: random.Random, now: datetime) -> RunRecord:
    """Execute ONE run through the REAL primitives and record the measured truth."""
    severity, should_recover = (
        (FailureSeverity.INFO, False) if fault_kind == "clean" else classify(fault_kind)
    )

    if fault_kind == "stale_source":
        freshness = round(rng.uniform(26.0, 40.0), 2)
    elif fault_kind == "stale_partition":
        freshness = round(rng.uniform(20.0, 23.5), 2)
    else:
        freshness = round(rng.uniform(0.5, 12.0), 2)
    sla: SLAResult = check_sla("freshness_hours", freshness)

    recovery_attempted = False
    recovered = False
    attempts = 1
    backoff_ms = 0
    notes: list[str] = []

    if fault_kind == "clean":
        final_state = "SUCCESS"
    elif severity == FailureSeverity.WARNING:
        final_state = "DEGRADED"
        notes.append("quarantine rate elevated; served with watch flag")
    elif should_recover:  # RECOVERABLE — measure recovery via the REAL retry policy
        recovery_attempted = True
        clear_time = rng.choice(TRANSIENT_CLEAR_DIST)
        op = _flaky(clear_time)
        operation = "backfill_partition" if fault_kind == "stale_partition" else "retry_operation"
        _result, outcome = bounded_retry(
            op, operation=operation, reason=fault_kind,
            max_attempts=MAX_ATTEMPTS, base_delay_ms=1.0,
        )
        attempts = outcome.attempts
        backoff_ms = outcome.total_backoff_ms
        recovered = outcome.succeeded  # MEASURED: did the budget beat the clear-time?
        if recovered:
            final_state = "RECOVERED"
            notes.append(f"transient cleared after {clear_time} failure(s)")
        else:
            final_state = "ESCALATED"
            notes.append(f"transient clear-time {clear_time} exceeded {MAX_ATTEMPTS}-attempt budget")
    else:  # CRITICAL — attempt (and fail) bounded retry to prove the budget is bounded
        recovery_attempted = True
        _result, outcome = bounded_retry(
            _always_fails(f"{fault_kind} is not recoverable"),
            operation="recover_attempt", reason=fault_kind,
            max_attempts=MAX_ATTEMPTS, base_delay_ms=1.0,
        )
        attempts = outcome.attempts
        backoff_ms = outcome.total_backoff_ms
        final_state = "ESCALATED"
        if fault_kind == "stale_source":
            notes.append("agent-facing API NOT refreshed — consumers kept last-good data")

    # The REAL gate decides publication. served_bad_data is computed, never assumed.
    published = gate_publish(severity, recovered)
    served_bad_data = published and (fault_kind in _DATA_CORRUPTING)

    escalation_reason = None
    if final_state == "ESCALATED":
        escalation_reason = f"{fault_kind}: {severity.value} — promotion blocked, human paged"

    return RunRecord(
        run_id=run_id, started_at=now.isoformat(), fault_kind=fault_kind,
        severity=severity.value, recovery_attempted=recovery_attempted,
        recovery_successful=recovered, retry_attempts=attempts, retry_backoff_ms=backoff_ms,
        final_state=final_state, published=published, served_bad_data=served_bad_data,
        sla_freshness_hours=freshness, sla_breached=sla.breached,
        escalation_reason=escalation_reason, notes=notes,
    )


def run_suite(ledger_path: Path = LEDGER_PATH) -> list[dict]:
    """Execute the full RUN_PLAN, write the ledger, return the records as dicts."""
    rng = random.Random(SEED)
    base = datetime(2026, 6, 16, tzinfo=timezone.utc)
    plan: list[str] = []
    for kind, n in RUN_PLAN.items():
        plan.extend([kind] * n)
    rng.shuffle(plan)

    records: list[RunRecord] = []
    for i, kind in enumerate(plan):
        now = base + timedelta(minutes=15 * i)
        records.append(_execute_run(f"run-{i:04d}", kind, rng, now))

    dicts = [asdict(r) for r in records]
    ledger_path.write_text("\n".join(json.dumps(d) for d in dicts) + "\n")
    return dicts


if __name__ == "__main__":
    out = run_suite()
    print(f"harness: executed {len(out)} runs → {LEDGER_PATH}")
