"""
Rule-based ESI (Emergency Severity Index) triage classifier.

Implements the customer-signed safety floors from
data/quality/esi_eval_dataset.json. Lower ESI number = more urgent
(1 = resuscitation, 5 = non-urgent).

Why rule-based, not ML:
    The 10 customer-contract criteria (ACC-001 through SCHEMA-001) are
    explicit, auditable, and signed off by the CMO + safety officer. An
    ML classifier would not be auditable to that standard at this corpus
    size (497 holdout rows). Rules satisfy the FDE acceptance gates;
    ML can be layered on later as a confidence-booster, not the primary
    decision path.

Why this lives in repo#2:
    /api/classify proves the L1 substrate feeds a classification chef
    (FDE-style), not just a retrieval chef. Same pantry, two consumers.
"""
from typing import Dict, Any, List, Tuple

SUICIDAL_PHRASES = [
    "suicidal", "suicide", "self-harm", "self harm",
    "kill myself", "end my life", "want to die",
]
ALTERED_MENTAL_PHRASES = [
    "altered mental", "confusion", "confused", "disoriented",
    "unresponsive", "obtunded", "lethargic",
]
CHEST_PAIN_PHRASES = ["chest pain", "substernal", "angina"]
HIGH_RISK_CHEST_PAIN_PHRASES = [
    "diaphoresis", "diaphoretic", "sweating", "radiating",
    "shortness of breath", "left arm", "jaw pain",
]
WELL_VISIT_PHRASES = [
    "well visit", "routine", "annual", "check-up", "checkup",
    "med refill", "medication refill", "follow-up",
]


def _norm(s: Any) -> str:
    return str(s or "").lower()


def _has_any(text: str, phrases: List[str]) -> bool:
    return any(p in text for p in phrases)


def _safe_int(v: Any, default: int = -1) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _safe_float(v: Any, default: float = -1.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def classify_esi(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Input:
      age (int years), chief_complaint (str),
      vitals: {bp_systolic, bp_diastolic, heart_rate, respiratory_rate,
               temperature_f, spo2_pct}

    Output:
      esi_tier (1-5), rules_fired [{id, rule, action}],
      confidence (low/medium/high), human_review_required (bool)
    """
    age = _safe_int(payload.get("age"), -1)
    cc = _norm(payload.get("chief_complaint"))
    vitals = payload.get("vitals") or {}
    hr = _safe_int(vitals.get("heart_rate"))
    rr = _safe_int(vitals.get("respiratory_rate"))
    temp = _safe_float(vitals.get("temperature_f"))
    spo2 = _safe_int(vitals.get("spo2_pct"))

    rules_fired: List[Dict[str, str]] = []
    tier = 3

    # ACC-004: suicidal ideation always escalates
    if _has_any(cc, SUICIDAL_PHRASES):
        tier = min(tier, 2)
        rules_fired.append({
            "id": "ACC-004",
            "rule": "suicidal_ideation_always_escalates",
            "action": "tier set min(tier, 2)",
        })

    # ACC-001: pediatric <1y min ESI 2
    if 0 <= age < 1:
        tier = min(tier, 2)
        rules_fired.append({
            "id": "ACC-001",
            "rule": "pediatric_under_1y_min_ESI_2",
            "action": "tier set min(tier, 2)",
        })

    # ACC-005: altered mental status min ESI 2
    if _has_any(cc, ALTERED_MENTAL_PHRASES):
        tier = min(tier, 2)
        rules_fired.append({
            "id": "ACC-005",
            "rule": "altered_mental_status_min_ESI_2",
            "action": "tier set min(tier, 2)",
        })

    # ACC-002: high-risk chest pain min ESI 2
    if _has_any(cc, CHEST_PAIN_PHRASES) and (
        _has_any(cc, HIGH_RISK_CHEST_PAIN_PHRASES) or age >= 50
    ):
        tier = min(tier, 2)
        rules_fired.append({
            "id": "ACC-002",
            "rule": "high_risk_chest_pain_min_ESI_2",
            "action": "tier set min(tier, 2)",
        })

    # ACC-006: sepsis shape (SIRS proxy w/o WBC: HR>90 + RR>20 + temp
    # extremes >100.4F or <96.8F) → min ESI 2
    sirs = 0
    if hr > 90:
        sirs += 1
    if rr > 20:
        sirs += 1
    if temp > 100.4 or (0 < temp < 96.8):
        sirs += 1
    if sirs >= 2:
        tier = min(tier, 2)
        rules_fired.append({
            "id": "ACC-006",
            "rule": "sepsis_shape_min_ESI_2",
            "action": f"SIRS proxy hits={sirs}/3 → tier set min(tier, 2)",
        })

    # Vital-derived escalation (hypoxia / extreme tachycardia / bradypnea)
    if 0 < spo2 < 92:
        tier = min(tier, 2)
        rules_fired.append({
            "id": "VITAL-SPO2",
            "rule": "hypoxia_spo2_under_92",
            "action": "tier set min(tier, 2)",
        })

    # ACC-003: well_visit max ESI 4 (lower urgency)
    if _has_any(cc, WELL_VISIT_PHRASES) and not rules_fired:
        tier = max(tier, 4)
        rules_fired.append({
            "id": "ACC-003",
            "rule": "well_visit_max_ESI_4_or_lower",
            "action": "tier set max(tier, 4)",
        })

    # ACC-009: weak evidence → human review
    has_vitals = any(_safe_int(vitals.get(k)) > 0 for k in (
        "heart_rate", "respiratory_rate", "spo2_pct"
    ))
    weak_evidence = (not has_vitals) or len(cc) < 8
    human_review = weak_evidence or len(rules_fired) >= 3

    if weak_evidence:
        rules_fired.append({
            "id": "ACC-009",
            "rule": "weak_evidence_triggers_human_review",
            "action": "human_review_required=true",
        })

    confidence = "high"
    if weak_evidence:
        confidence = "low"
    elif len(rules_fired) == 1:
        confidence = "medium"

    return {
        "esi_tier": tier,
        "rules_fired": rules_fired,
        "confidence": confidence,
        "human_review_required": human_review,
    }
