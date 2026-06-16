"""
Baymax CROSS-DOMAIN JOIN 👂×👃 — the real "openFDA whisper".

This is the organ that was missing: it does NOT just show platform ML stats. It
takes THIS patient's medications (from their encounter record) and JOINS them
against real openFDA FAERS adverse-event reports, counting serious + renal
reactions — then flags the drug-vs-kidney conflict for a CKD patient.

Generic + lineage-clean: any patient with meds + any drug in FAERS works. Values
come from data (corpus meds × FAERS reports), never hardcoded per patient.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

_ROOT = Path(__file__).resolve().parents[2]
_CORPUS = _ROOT / "data" / "raw" / "enriched_use_397.jsonl"
_FAERS = _ROOT / "data" / "openfda" / "openfda_reports_scaled.json"
_RENAL_RE = re.compile(r"renal|kidney|nephro|creatinine", re.I)
_TOKEN_RE = re.compile(r"[a-z]+")
_STOP = {
    "with", "and", "for", "the", "plus", "from", "that", "this", "oral", "once",
    "twice", "daily", "home", "meds", "medication", "medications", "tablet", "tablets",
    "dose", "drug", "drugs", "patient", "history", "type", "stage", "disease", "renal",
    "kidney", "chronic", "acute", "mild", "over", "past", "days", "week", "year", "old",
    "female", "male", "presents", "fluid", "blood", "pressure", "swelling", "edema",
}


def _faers() -> List[Dict[str, Any]]:
    try:
        return json.loads(_FAERS.read_text(encoding="utf-8"))
    except Exception:
        return []


def _patient_record(patient_id: str) -> Dict[str, Any] | None:
    if not _CORPUS.exists():
        return None
    rows = []
    for ln in _CORPUS.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except Exception:
            continue
        if r.get("patient_id") == patient_id:
            rows.append(r)
    if not rows:
        return None
    rows.sort(key=lambda r: str(r.get("Date of Admission", "")))
    return rows[-1]


def build_drug_risk(patient_id: str = "mom-001") -> Dict[str, Any]:
    rec = _patient_record(patient_id)
    if not rec:
        return {"available": False, "patient_id": patient_id,
                "reason": "no encounter record for this patient",
                "lineage": {"corpus": "enriched_use_397.jsonl", "found": False}}

    reports = _faers()
    drug_vocab = set()
    for rp in reports:
        for tok in _TOKEN_RE.findall((rp.get("primary_drug") or "").lower()):
            if len(tok) > 3:
                drug_vocab.add(tok)

    med_text = " ".join([str(rec.get("Medication") or ""), str(rec.get("hpi") or ""),
                         str(rec.get("physician_note") or "")]).lower()
    med_tokens = {t for t in _TOKEN_RE.findall(med_text) if t not in _STOP}
    patient_drugs = sorted(med_tokens & drug_vocab)

    per_drug = []
    any_renal = False
    for drug in patient_drugs:
        hits = [r for r in reports if drug in (r.get("primary_drug") or "").lower()]
        if not hits:
            continue
        serious = sum(1 for r in hits if r.get("is_serious"))
        renal = sum(1 for r in hits if _RENAL_RE.search(r.get("reactions") or ""))
        if renal:
            any_renal = True
        per_drug.append({
            "drug": drug,
            "faers_reports": len(hits),
            "serious_reports": serious,
            "renal_reaction_reports": renal,
            "flag": "renal adverse-event signal" if renal else
                    ("serious adverse-event signal" if serious else "low signal"),
        })
    per_drug.sort(key=lambda d: (-d["renal_reaction_reports"], -d["serious_reports"]))

    ckd = rec.get("ckd_stage")
    cross_flag = bool(any_renal and ckd)
    return {
        "available": True,
        "patient_id": patient_id,
        "patient_medications": patient_drugs,
        "patient_renal_state": f"CKD stage {ckd}" if ckd else "unknown",
        "per_drug": per_drug,
        "cross_domain_flag": cross_flag,
        "verdict": (
            "Cross-domain conflict: a medication this patient takes has renal "
            "adverse-event reports in openFDA, and the patient already has reduced "
            "kidney function — review before continuing it."
            if cross_flag else
            "No renal-specific cross-domain conflict found for this patient's drugs."
        ),
        "interpretation": "openFDA FAERS is a population safety signal; it shows risk, not causation.",
        "lineage": {
            "patient_meds": "enriched_use_397.jsonl (this patient's record)",
            "drug_safety": "openfda_reports_scaled.json (5000 real FAERS reports)",
            "computed": "join patient meds × FAERS by drug name; count serious + renal reactions",
        },
    }
