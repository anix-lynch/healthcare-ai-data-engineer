"""Self-healing reliability primitives — Bullet 4.

The platform takes responsibility for its own survival. Three real primitives:

  1. FailureSeverity / classify()  — one taxonomy for every failure path
  2. bounded_retry()               — exponential backoff, NEVER infinite, fully traced
  3. SLA + check_sla()             — explicit platform SLAs with breach detection

These are exercised for real by reliability/harness.py (fault injection) and the
live DAG (orchestration/dags/data_platform_dag.py). Nothing here is a comment —
every function executes and returns an inspectable outcome.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class FailureSeverity(str, Enum):
    """Unified failure classification — ordered least → most severe."""

    INFO = "INFO"              # noted, no action (e.g. soft clinical warning)
    WARNING = "WARNING"        # degraded but serving (e.g. elevated quarantine rate)
    RECOVERABLE = "RECOVERABLE"  # transient — retry/backfill should fix it
    CRITICAL = "CRITICAL"      # cannot self-heal — block promotion + escalate


# Which failure kinds the platform knows how to classify. Maps a raw failure
# source to a default severity + whether automated recovery should be attempted.
_FAILURE_RULES: dict[str, tuple[FailureSeverity, bool]] = {
    "transient_api":        (FailureSeverity.RECOVERABLE, True),   # retry
    "transient_bigquery":   (FailureSeverity.RECOVERABLE, True),   # retry
    "stale_partition":      (FailureSeverity.RECOVERABLE, True),   # backfill
    "failed_validation":    (FailureSeverity.CRITICAL, False),     # block (bad rows)
    "reconciliation_mismatch": (FailureSeverity.CRITICAL, False),  # block (row loss)
    "schema_drift":         (FailureSeverity.CRITICAL, False),     # block (contract broke)
    "quality_gate_breach":  (FailureSeverity.CRITICAL, False),     # block (poison data)
    "stale_source":         (FailureSeverity.CRITICAL, False),     # block (don't refresh API)
    "elevated_quarantine":  (FailureSeverity.WARNING, False),      # serve, watch
}


def classify(failure_kind: str) -> tuple[FailureSeverity, bool]:
    """Map a failure kind → (severity, recovery_should_be_attempted).

    Unknown kinds default to CRITICAL/no-recovery — fail safe, never silently INFO.
    """
    return _FAILURE_RULES.get(failure_kind, (FailureSeverity.CRITICAL, False))


def gate_publish(severity: FailureSeverity, recovered: bool) -> bool:
    """The load-bearing promotion gate — decides if a run may publish.

    The ONLY door to consumers. A run publishes iff it is clean/degraded, or it was
    recoverable AND actually recovered. CRITICAL — or anything that exhausted its
    retry budget without recovering — is blocked. This is what makes
    'serve nothing > serve bad data' a property, not a comment: if this function
    returned True for CRITICAL, bad data would reach consumers, and the invariant
    test would fail. It does not.
    """
    if severity == FailureSeverity.CRITICAL:
        return False
    if severity == FailureSeverity.RECOVERABLE:
        return recovered
    return True  # INFO / WARNING — serve (WARNING is flagged degraded upstream)


@dataclass
class RetryOutcome:
    """Inspectable record of one bounded-retry sequence."""

    operation: str
    reason: str
    max_attempts: int
    attempts: int = 0
    succeeded: bool = False
    backoff_ms: list[int] = field(default_factory=list)
    error: str | None = None

    @property
    def total_backoff_ms(self) -> int:
        return sum(self.backoff_ms)


def bounded_retry(
    fn: Callable[[], Any],
    *,
    operation: str,
    reason: str,
    max_attempts: int = 3,
    base_delay_ms: float = 1.0,
    max_delay_ms: float = 1000.0,
) -> tuple[Any, RetryOutcome]:
    """Run ``fn`` with bounded exponential backoff. NEVER infinite.

    Returns (result, RetryOutcome). On exhaustion the last error is raised only
    via the outcome (succeeded=False) — the caller decides escalation, so a
    failed retry can be classified and persisted rather than crashing the run.

    Backoff = base_delay_ms * 2**(attempt-1), capped at max_delay_ms.
    """
    outcome = RetryOutcome(operation=operation, reason=reason, max_attempts=max_attempts)
    result: Any = None
    for attempt in range(1, max_attempts + 1):
        outcome.attempts = attempt
        try:
            result = fn()
            outcome.succeeded = True
            outcome.error = None
            return result, outcome
        except Exception as exc:  # noqa: BLE001 — deliberate: classify, don't crash
            outcome.error = str(exc)[:300]
            if attempt < max_attempts:
                delay = min(base_delay_ms * (2 ** (attempt - 1)), max_delay_ms)
                outcome.backoff_ms.append(int(delay))
                time.sleep(delay / 1000.0)
    return result, outcome


@dataclass(frozen=True)
class SLA:
    """One platform SLA: a named threshold the platform promises to hold."""

    name: str
    threshold: float
    unit: str
    comparator: str  # "<=" means observed must be <= threshold; ">=" the reverse


# Platform SLAs — the promises downstream AI consumers rely on.
PLATFORM_SLAS: dict[str, SLA] = {
    "freshness_hours":      SLA("freshness_hours", 24.0, "hours", "<="),
    "dbt_completion_min":   SLA("dbt_completion_min", 10.0, "minutes", "<="),
    "api_availability_pct": SLA("api_availability_pct", 99.0, "percent", ">="),
    "pipeline_success_pct": SLA("pipeline_success_pct", 99.0, "percent", ">="),
}


@dataclass
class SLAResult:
    name: str
    observed: float
    threshold: float
    unit: str
    breached: bool


def check_sla(name: str, observed: float) -> SLAResult:
    """Compare an observed value against its platform SLA → SLAResult(breached?)."""
    sla = PLATFORM_SLAS[name]
    if sla.comparator == "<=":
        breached = observed > sla.threshold
    else:  # ">="
        breached = observed < sla.threshold
    return SLAResult(name=name, observed=round(observed, 3), threshold=sla.threshold,
                     unit=sla.unit, breached=breached)
