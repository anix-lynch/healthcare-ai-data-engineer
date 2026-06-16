"""
Baymax CASE OWNERSHIP — the v1.5 agency jump.

Not "Baymax picks organs" (that risks agent-theater). Instead Baymax OWNS a case
over time: each tick it OBSERVES the real world (the outcome organ) and DECIDES the
next transition itself — until the case is CLOSED or ESCALATED. The decision is
driven by observed state, not a frontend script. This gives memory + state +
workflow + verification + agency at once, and — the part recruiters care about —
the system FINISHES work (or hands off when stuck).

who owns the next decision? → advance() does, from observed state. Generic: any
case with an action_id flows through the same machine.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

STORE = Path(__file__).resolve().parent / "cases_store.json"

# OPEN → SENT → (verified? SCHEDULED → CLOSED : follow-up loop → ESCALATED)
TERMINAL = {"CLOSED", "ESCALATED"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load() -> Dict[str, Any]:
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(cases: Dict[str, Any]) -> None:
    STORE.write_text(json.dumps(cases, indent=2, ensure_ascii=False), encoding="utf-8")


def get_case(case_id: str) -> Dict[str, Any]:
    case = _load().get(case_id)
    if not case:
        return {"available": False, "case_id": case_id, "reason": "no such case"}
    return {"available": True, **case}


def advance_case(case_id: str, observe_outcome) -> Dict[str, Any]:
    """One tick. Baymax observes the real outcome and decides the next transition."""
    cases = _load()
    case = cases.get(case_id)
    if not case:
        return {"available": False, "case_id": case_id, "reason": "no such case"}
    if case["status"] in TERMINAL:
        return {"available": True, **case, "note": "case already terminal"}

    outcome = observe_outcome(case["action_id"])  # the world, observed (not scripted)
    verified = bool(outcome.get("real_world_verified"))
    status = case["status"]

    if status == "OPEN":
        status, reason = "SENT", f"action {case['action_id']} drafted and sent"
    elif status == "SENT":
        if verified:
            status, reason = "SCHEDULED", "outcome verified in the real world → schedule"
        else:
            case["checks"] += 1
            if case["checks"] >= case["max_checks"]:
                status, reason = "ESCALATED", (
                    f"still not verified after {case['checks']} follow-ups → hand to a human "
                    "(Baymax does not pretend it finished)"
                )
            else:
                status, reason = "SENT", f"not verified yet → follow up (check {case['checks']})"
    elif status == "SCHEDULED":
        status, reason = "CLOSED", "appointment completed → close the case"
    else:
        reason = "no transition"

    case["status"] = status
    case["observed_verified"] = verified
    case["history"].append({"at": _now().isoformat(timespec="seconds"), "to": status, "reason": reason})
    case["next_check_at"] = None if status in TERMINAL else (_now() + timedelta(days=1)).date().isoformat()
    cases[case_id] = case
    _save(cases)
    return {"available": True, **case, "last_decision": reason}
