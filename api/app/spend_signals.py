"""
B5 — AI Spend Governance Layer: spend_signals feature view.

Computes 4 structural signals that govern inference budget BEFORE any LLM call.
These signals measure information density, novelty, and structural completeness.
They do NOT interpret clinical meaning (that belongs to B3 semantic_features).

B3 / B5 boundary:
    B3 semantic_features: what IS this encounter (clinical meaning, risk, profile)
    B5 spend_signals:     how MUCH is here, how NOVEL, how COMPLETE (structural)

Portability:
    Same 4 signals apply to any high-variance AI pipeline:
    - Finance:   text_density of transaction memos, novelty vs. known fraud patterns
    - Insurance: completeness of claim fields, novelty vs. settled-claim corpus
    - Legal:     completeness of contract fields, novelty vs. precedent embeddings
    - Support:   instability_count of SLA breaches, novelty vs. known issue corpus
"""
from __future__ import annotations
from typing import Dict, Any


# ------------------------------------------------------------------
# Reference ranges for vital_instability_count.
# These are structural THRESHOLDS, not clinical diagnoses.
# We count boundary violations — not interpret what they mean.
# ------------------------------------------------------------------
_VITAL_RULES = {
    "bp_systolic":       lambda v: v < 90 or v > 180,
    "heart_rate":        lambda v: v > 120 or v < 50,
    "respiratory_rate":  lambda v: v > 24 or v < 10,
    "spo2_pct":          lambda v: v < 90,
    "temperature_f":     lambda v: v > 103.0,
}

_STRUCT_FIELDS = [
    "bp_systolic", "bp_diastolic", "heart_rate", "respiratory_rate",
    "temperature_f", "spo2_pct", "lab_flags", "acuity_red_flags",
    "Admission Type", "Billing Amount", "Room Number", "Insurance Provider",
]


def _to_float(v, default: float) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def vital_instability_count(record: Dict[str, Any]) -> int:
    """Count of vital signs outside structural reference ranges (0-5).

    Counts boundary violations only — does not assess clinical severity.
    '3 vitals are out of range' is a structural measurement.
    'This patient may be septic' is B3's job.
    """
    count = 0
    defaults = {"bp_systolic": 120, "heart_rate": 80, "respiratory_rate": 16,
                "spo2_pct": 98, "temperature_f": 98.6}
    for field, rule in _VITAL_RULES.items():
        val = _to_float(record.get(field), defaults[field])
        if rule(val):
            count += 1
    return count


def struct_completeness_score(record: Dict[str, Any]) -> float:
    """Fraction of structured fields that are non-null and non-empty (0.0-1.0).

    Lower completeness = more ambiguity = MORE compute warranted, not less.
    An incomplete record cannot be handled cheaply — the AI must infer gaps.
    """
    filled = sum(
        1 for f in _STRUCT_FIELDS
        if record.get(f) and str(record.get(f)).strip() not in ("", "None", "nan")
    )
    return round(filled / len(_STRUCT_FIELDS), 3)


def text_density_score(record: Dict[str, Any]) -> int:
    """Total character count of narrative fields (chief_complaint + hpi + physician_note).

    Measures information VOLUME, not meaning. Counts characters, does not read them.
    Low variance in this synthetic corpus (500-1500 char range for 397/401 records).
    Included for portability: real EHR data spans 50-10,000+ chars.
    """
    return sum(
        len(str(record.get(k) or ""))
        for k in ("chief_complaint", "hpi", "physician_note")
    )


def build_embedding_text(record: Dict[str, Any]) -> str:
    """Concatenate structural fields for embedding. Excludes clinical labels.

    We embed the DESCRIPTION, not the diagnosis.
    chief_complaint + hpi captures the structural presentation.
    """
    parts = [
        str(record.get("chief_complaint") or ""),
        str(record.get("hpi") or ""),
    ]
    return " ".join(p for p in parts if p).strip()


def compute_novelty_score(embedding: list, neighbor_embeddings: list) -> float:
    """Cosine distance from this embedding to its K nearest neighbors.

    novelty_score = 1 - mean_cosine_similarity_to_top5_neighbors.
    Range: 0.0 (identical to all neighbors) to 1.0 (orthogonal to all neighbors).

    High novelty = encounter unlike anything in the corpus = needs more reasoning.
    Low novelty  = familiar pattern = cached Flash sufficient.

    This is pure geometry — no clinical interpretation.
    Same pattern applies to: fraud detection, contract review, issue triage.
    """
    import math

    def cosine_sim(a: list, b: list) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    sims = [cosine_sim(embedding, nb) for nb in neighbor_embeddings]
    return round(1.0 - (sum(sims) / len(sims)), 4) if sims else 0.0
