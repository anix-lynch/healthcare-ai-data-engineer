#!/usr/bin/env python3
"""Inject mom as a REAL longitudinal patient: 2 dated encounters (admits) into the
enriched retrieval corpus. DISCLOSED synthetic — the 55k upstream gives every
patient only 1 admit, so a 'before vs now' diff needs a 2-admit record to exist.

Idempotent: removes prior injected mom lines, then appends exactly two.
Schema-conformant: only fills keys already in the corpus + an explicit patient_id
so the generic state differ can group her two admits. Add any 2-admit patient the
same way and Baymax runs for them — no per-patient code.
"""
from __future__ import annotations
import json
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "data" / "raw" / "enriched_use_397.jsonl"
MARK = "SYNTHETIC-MOTHER-EDEMA"

_BASE = {
    "Name": f"{MARK} (mom-001, synthetic)", "patient_id": "mom-001",
    "Gender": "Female", "Blood Type": "O+", "Medical Condition": "Diabetes",
    "Doctor": "ER Night Shift", "Hospital": "Synthetic General",
    "Insurance Provider": "Synthetic", "Billing Amount": "0", "Room Number": "0",
    "synthetic": True, "lineage": "disclosed synthetic seed (upstream has no longitudinal patient)",
}

ADMIT_2024 = {**_BASE, "Age": "69", "Date of Admission": "2024-03-10", "Discharge Date": "2024-03-12",
    "Admission Type": "Elective", "Medication": "Furosemide", "Test Results": "Normal",
    "ckd_stage": 2, "egfr": 62,
    "chief_complaint": "Mild bilateral leg swelling",
    "hpi": "69-year-old female with type-2 diabetes, mild leg swelling / fluid retention. Responded to a low-intensity diuretic.",
    "physician_note": "CKD stage 2. Mild diuretic, fluid resolved, discharged. Stable renal reserve.",
    "esi_tier_truth": "3"}

ADMIT_2026 = {**_BASE, "Age": "71", "Date of Admission": "2026-06-10", "Discharge Date": "",
    "Admission Type": "Emergency", "Medication": "Furosemide", "Test Results": "Abnormal",
    "ckd_stage": 3, "egfr": 44,
    "chief_complaint": "Bilateral leg swelling and fluid retention for one week",
    "hpi": "71-year-old female with type-2 diabetes and chronic kidney disease, progressive bilateral lower-extremity edema, leg swelling, fluid retention, fatigue, mild dyspnea, reduced urine output. Home meds: metformin, lisinopril, furosemide.",
    "physician_note": "CKD stage 3 (declined from stage 2). Recurrent fluid overload from combined cardiac and renal disease; less renal reserve.",
    "esi_tier_truth": "2"}


def ensure_mother_encounters() -> int:
    lines = []
    if CORPUS.exists():
        for ln in CORPUS.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                rec = json.loads(ln)
            except Exception:
                continue
            if MARK in (rec.get("Name") or ""):
                continue
            lines.append(ln)
    lines.append(json.dumps(ADMIT_2024, ensure_ascii=False))
    lines.append(json.dumps(ADMIT_2026, ensure_ascii=False))
    CORPUS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sum(1 for ln in lines if MARK in ln)


if __name__ == "__main__":
    print("mom admits in corpus:", ensure_mother_encounters())
