"""Per-record validation + classification for the event-driven ingestion path.

ONE validator, shared by both entry points so the rules can never drift:
  - `ingestion/ingest.py`        (the streaming batch ingester)
  - `POST /api/ingest`           (the Cloud Run event endpoint)

It does NOT touch the database. It takes a single raw record and returns a
`Decision` describing what should happen to it. The caller (ingester or API)
is responsible for actually writing to the clean table or the quarantine table.
This keeps validation pure and unit-testable with no BigQuery dependency.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

# Natural key for an encounter — one row per (patient, admission date).
KEY_FIELDS = ("name", "date_of_admission")

REQUIRED = ("name", "date_of_admission", "age", "gender", "medical_condition", "admission_type")
VALID_GENDER = {"male", "female"}
VALID_ADMISSION = {"emergency", "urgent", "elective"}
AGE_MIN, AGE_MAX = 0, 120


@dataclass
class Decision:
    """What the ingester should do with one streamed record."""
    record: dict[str, Any]
    status: str                       # accepted_new | accepted_revised | quarantined
    reasons: list[str] = field(default_factory=list)
    key: tuple | None = None
    event_ts: datetime | None = None


def _key(rec: dict) -> tuple:
    return tuple(str(rec.get(k, "")).strip().lower() for k in KEY_FIELDS)


def _parse_ts(rec: dict) -> datetime | None:
    raw = rec.get("event_ts")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def validate_record(rec: dict, seen: dict[tuple, datetime]) -> Decision:
    """Classify one record against the schema + what we've already ingested.

    `seen` maps an already-accepted natural key -> its event timestamp, so we can
    tell a fresh insert from a revision (newer ts supersedes) and from a
    late-arriving / duplicate row (same-or-older ts → quarantine).
    """
    reasons: list[str] = []

    # 1. structural: required fields present and non-empty
    for f in REQUIRED:
        v = rec.get(f)
        if v is None or str(v).strip() == "":
            reasons.append(f"missing_required:{f}")

    # 2. typed/range checks — only meaningful if the field is actually there
    age = rec.get("age")
    if age not in (None, "") and "missing_required:age" not in reasons:
        try:
            a = int(age)
            if not (AGE_MIN <= a <= AGE_MAX):
                reasons.append(f"age_out_of_range:{a}")
        except (ValueError, TypeError):
            reasons.append(f"malformed_age:{age!r}")

    g = str(rec.get("gender", "")).strip().lower()
    if g and g not in VALID_GENDER:
        reasons.append(f"bad_gender:{rec.get('gender')!r}")

    at = str(rec.get("admission_type", "")).strip().lower()
    if at and at not in VALID_ADMISSION:
        reasons.append(f"bad_admission_type:{rec.get('admission_type')!r}")

    if "missing_required:date_of_admission" not in reasons:
        try:
            datetime.fromisoformat(str(rec["date_of_admission"]))
        except (ValueError, TypeError, KeyError):
            reasons.append(f"malformed_date:{rec.get('date_of_admission')!r}")

    if reasons:
        return Decision(record=rec, status="quarantined", reasons=reasons)

    # 3. idempotency / ordering — record is structurally valid, now place it
    key = _key(rec)
    ts = _parse_ts(rec)
    prior = seen.get(key)

    if prior is None:
        return Decision(rec, "accepted_new", key=key, event_ts=ts)

    # same key already accepted — decide by event time
    if ts is not None and prior is not None and ts > prior:
        return Decision(rec, "accepted_revised", key=key, event_ts=ts)

    # same-or-older timestamp → this is a duplicate or a late-arriving replay
    label = "late_arriving" if (ts is not None and prior is not None and ts < prior) else "duplicate"
    return Decision(rec, "quarantined", reasons=[f"{label}:key_already_ingested"], key=key, event_ts=ts)
