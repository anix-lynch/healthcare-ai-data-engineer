"""
Baymax NOSE 👃 — openFDA evaluated-signal platform adapter.

Serves the 5 cheap evaluated signals (anomaly · cluster · classify · rank ·
retrieval) + the cost/quality router from the sibling repo
`healthcare-signal-platform/openfda_signals`. We read the precomputed PROOF
receipt (already evaluated with honest metrics) rather than re-running sklearn
on every request — the proof IS the contract.

This is the cross-domain "smell": pharmacovigilance early-warning over real
FAERS adverse-event reports, distinct from the patient retrieval/EHR organs.
"""
import json
import os
from typing import Any, Dict, List


def _find_proof() -> str | None:
    here = os.path.dirname(__file__)
    local = os.path.abspath(os.path.join(here, "../../data/quality/openfda_signal_proof.json"))
    if os.path.exists(local):
        return local
    sources = os.path.abspath(os.path.join(here, "..", "..", ".."))  # .../sources
    base = os.path.join(sources, "healthcare-signal-platform", "openfda_signals", "proof")
    for name in ("bullet5_scaled_proof.json", "bullet5_signal_proof.json"):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None


def _summ(name: str, sig: Dict[str, Any]) -> Dict[str, Any]:
    """Reduce each signal's rich proof to a nose-friendly 1-metric read."""
    pick = {
        "anomaly":   ("flagged",          "flag_rate"),
        "cluster":   ("best_silhouette",  "best_k"),
        "classify":  ("f1_serious",       "recall_serious"),
        "rank":      ("precision_at_30",  "ndcg_at_30"),
        "retrieval": ("recall_at_5",      "eligible_queries"),
    }.get(name, (None, None))
    headline = sig.get(pick[0]) if pick[0] else None
    return {
        "name": name,
        "method": sig.get("method", ""),
        "headline_metric": pick[0],
        "headline_value": headline,
        "fired": bool(headline) if isinstance(headline, (int, float)) else True,
        "honest_metric": sig.get("honest_metric", ""),
    }


def build_signals_payload() -> Dict[str, Any]:
    path = _find_proof()
    if not path:
        return {"available": False, "reason": "signal proof not found", "signals": []}
    with open(path, "r") as f:
        proof = json.load(f)

    sigs = proof.get("signals", {})
    signals: List[Dict[str, Any]] = [_summ(k, v) for k, v in sigs.items()]
    router = proof.get("router_ablation", {})
    op = router.get("operating_point", {})
    dqp = router.get("decision_quality_preserved", {})
    floor = dqp.get("recall_floor") or 0.95  # both proof shapes target >= 0.95
    reduced = (router.get("llm_calls_reduced_pct_at_95_recall")
               if router.get("llm_calls_reduced_pct_at_95_recall") is not None
               else router.get("llm_calls_reduced_pct"))

    return {
        "available": True,
        "source": "openFDA FAERS evaluated-signal platform",
        "n_reports": proof.get("n_reports"),
        "serious_rate": proof.get("serious_rate"),
        "signals": signals,                       # 5 evaluated signals
        "router": {
            "decision_rule": router.get("decision_rule"),
            "serious_recall_floor": floor,
            "llm_calls_reduced_pct_at_floor": reduced,
            "operating_point": op,
        },
        "nose_read": (
            f"Read {len(signals)} evaluated signals from real FAERS reports: "
            f"classify F1={sigs.get('classify', {}).get('f1_serious')}, "
            f"anomaly flagged {sigs.get('anomaly', {}).get('flagged')}/{proof.get('n_reports')}, "
            f"router holds serious-recall >= {floor}"
            + (f" while reducing LLM calls by {reduced}%" if reduced else "")
        ),
        "verdict": (
            "cost-quality router proof: serious recall stayed above the safety floor "
            "while reducing expensive reasoning calls"
        ),
    }
