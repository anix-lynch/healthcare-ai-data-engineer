"""Enrich healthcare_dataset.csv with synthetic clinical narrative + vitals + labs.

Why:
    Layer 1's 55K-row CSV is a billing registry, not an EHR. The 12-step patient
    lifecycle in docs/05 demands chief_complaint, hpi, vitals, lab_panel,
    physician_note — none of which exist in raw data. This script generates
    those fields per row using Vertex AI gemini-2.5-flash, anchored to the
    structured columns already on the row.

Strategy:
    - Use Vertex AI (NOT Anthropic API) so spend hits the $900 GCP credit
    - gemini-2.5-flash: cheap, fast, follows JSON schema reliably
    - Anchor narrative to existing structured columns (condition + age + gender)
    - One LLM call per row generates ALL enrichment fields at once
    - Write to data/raw/healthcare_dataset_enriched.csv (new file, original untouched)

Usage:
    # Test on 5 rows
    python3 scripts/enrich_clinical_narrative.py --rows 5 --dry-run

    # Run on 100-row sample
    python3 scripts/enrich_clinical_narrative.py --rows 100 --out data/raw/sample_enriched.csv

    # Full 5000-row enrichment for portfolio demo
    python3 scripts/enrich_clinical_narrative.py --rows 5000 --out data/raw/healthcare_dataset_enriched.csv
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = REPO_ROOT / "data" / "raw" / "healthcare_dataset.csv"
DEFAULT_OUT = REPO_ROOT / "data" / "raw" / "healthcare_dataset_enriched.csv"

# Fields added on top of the 15 original columns
ENRICHMENT_FIELDS = [
    "chief_complaint",     # Step 1, 2, 5
    "hpi",                 # Step 2, 5, 8
    "physician_note",      # Step 8 (Mad Lib grounding target)
    "bp_systolic",         # Step 1, 5
    "bp_diastolic",
    "heart_rate",
    "respiratory_rate",
    "temperature_f",
    "spo2_pct",
    "lab_panel_json",      # Step 3 — discrete tests: troponin/wbc/glucose/lactate (JSON-encoded)
    "lab_flags",            # Step 3 — semicolon-joined: "elevated_troponin;low_glucose"
    "esi_tier_truth",      # Step 5 ground truth (1-5)
    "acuity_red_flags",    # Step 5 — semicolon-joined hard-rule triggers
]

PROMPT_TEMPLATE = """You are a senior ER physician generating realistic synthetic clinical data for an AI training corpus. Anchor the narrative to the structured patient row below.

PATIENT ROW:
- Age: {age}
- Gender: {gender}
- Blood Type: {blood_type}
- Medical Condition: {medical_condition}
- Admission Type: {admission_type}
- Medication on record: {medication}
- Test Results (single value): {test_results}
- Length of stay (days): {los_days}

Generate ONE plausible ER encounter narrative consistent with this row. Return ONLY valid JSON matching this exact schema:

{{
  "chief_complaint": "<3-12 words, lay-person style>",
  "hpi": "<2-4 sentence history of present illness, clinical tone>",
  "physician_note": "<3-5 sentence A&P (assessment & plan), include differential>",
  "bp_systolic": <int 70-220>,
  "bp_diastolic": <int 40-130>,
  "heart_rate": <int 40-180>,
  "respiratory_rate": <int 8-40>,
  "temperature_f": <float 95.0-105.5>,
  "spo2_pct": <int 70-100>,
  "lab_panel": {{
    "troponin_ng_ml": <float or null>,
    "wbc_k_ul": <float or null>,
    "glucose_mg_dl": <int or null>,
    "lactate_mmol_l": <float or null>
  }},
  "lab_flags": ["<flag1>", "<flag2>"],
  "esi_tier_truth": <int 1-5, where 1=resuscitation, 5=non-urgent>,
  "acuity_red_flags": ["<red_flag1>", ...]
}}

RULES:
- vitals must be PLAUSIBLE for the condition (e.g. sepsis → fever + tachycardia + hypotension)
- lab values match condition (e.g. cancer + Abnormal test → elevated WBC OR low platelets)
- esi_tier must reflect acuity (Cancer chemo follow-up = 3-4, MI = 1-2, well-child = 5)
- lab_flags use snake_case: "elevated_troponin", "low_glucose", "leukocytosis"
- acuity_red_flags use snake_case: "stroke_symptoms", "active_bleeding", "altered_mental_status"
- Never invent specific patient names. Use "patient" or "pt" in narrative.
- If test_results is "Normal" → keep most labs normal but condition-consistent
- If test_results is "Abnormal" → 1-2 lab flags fired
- If test_results is "Inconclusive" → borderline values, flag includes "result_inconclusive"

Return ONLY the JSON object, no markdown fences, no preamble."""


# JSON Schema: forces gemini to return exactly this shape (no truncation, no malformed JSON)
RESPONSE_SCHEMA = {
    "type": "object",
    "required": [
        "chief_complaint", "hpi", "physician_note",
        "bp_systolic", "bp_diastolic", "heart_rate", "respiratory_rate",
        "temperature_f", "spo2_pct",
        "lab_panel", "lab_flags", "esi_tier_truth", "acuity_red_flags",
    ],
    "properties": {
        "chief_complaint": {"type": "string"},
        "hpi": {"type": "string"},
        "physician_note": {"type": "string"},
        "bp_systolic": {"type": "integer", "minimum": 70, "maximum": 220},
        "bp_diastolic": {"type": "integer", "minimum": 40, "maximum": 130},
        "heart_rate": {"type": "integer", "minimum": 40, "maximum": 180},
        "respiratory_rate": {"type": "integer", "minimum": 8, "maximum": 40},
        "temperature_f": {"type": "number", "minimum": 95.0, "maximum": 105.5},
        "spo2_pct": {"type": "integer", "minimum": 70, "maximum": 100},
        "lab_panel": {
            "type": "object",
            "properties": {
                "troponin_ng_ml": {"type": "number", "nullable": True},
                "wbc_k_ul": {"type": "number", "nullable": True},
                "glucose_mg_dl": {"type": "integer", "nullable": True},
                "lactate_mmol_l": {"type": "number", "nullable": True},
            },
        },
        "lab_flags": {"type": "array", "items": {"type": "string"}},
        "esi_tier_truth": {"type": "integer", "minimum": 1, "maximum": 5},
        "acuity_red_flags": {"type": "array", "items": {"type": "string"}},
    },
}


def _vertex_generate(prompt: str, model_name: str = "gemini-2.5-flash") -> dict[str, Any]:
    """Single Vertex AI call returning parsed JSON. Lazy import so dry-run skips SDK init."""
    import vertexai
    from vertexai.generative_models import GenerativeModel, GenerationConfig

    if not getattr(_vertex_generate, "_initialized", False):
        project = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GCP_LOCATION", "us-central1")
        if not project:
            raise RuntimeError("Set GCP_PROJECT_ID env var (or GOOGLE_CLOUD_PROJECT) to a billing-linked project")
        vertexai.init(project=project, location=location)
        _vertex_generate._initialized = True

    model = GenerativeModel(model_name)
    resp = model.generate_content(
        prompt,
        generation_config=GenerationConfig(
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
            temperature=0.7,
            max_output_tokens=3072,
        ),
    )
    return json.loads(resp.text)


def _mock_generate(row: dict) -> dict[str, Any]:
    """Deterministic fake output for --dry-run sanity check (no API call)."""
    cond = (row.get("Medical Condition") or "").lower()
    age = int(row.get("Age") or 50)
    return {
        "chief_complaint": f"[MOCK] follow-up for {cond}",
        "hpi": f"[MOCK] {age}yo presents with {cond}-related symptoms x 3 days.",
        "physician_note": f"[MOCK] A&P: {cond}. Monitor vitals. Labs pending. Will reassess in 4h.",
        "bp_systolic": 130,
        "bp_diastolic": 80,
        "heart_rate": 88,
        "respiratory_rate": 16,
        "temperature_f": 98.6,
        "spo2_pct": 97,
        "lab_panel": {"troponin_ng_ml": None, "wbc_k_ul": 7.5, "glucose_mg_dl": 95, "lactate_mmol_l": 1.2},
        "lab_flags": [],
        "esi_tier_truth": 3,
        "acuity_red_flags": [],
    }


def _flatten(enrich: dict) -> dict[str, str]:
    """Convert nested LLM output into flat CSV-friendly columns."""
    lab_panel = enrich.get("lab_panel") or {}
    return {
        "chief_complaint": enrich.get("chief_complaint", ""),
        "hpi": enrich.get("hpi", ""),
        "physician_note": enrich.get("physician_note", ""),
        "bp_systolic": str(enrich.get("bp_systolic", "")),
        "bp_diastolic": str(enrich.get("bp_diastolic", "")),
        "heart_rate": str(enrich.get("heart_rate", "")),
        "respiratory_rate": str(enrich.get("respiratory_rate", "")),
        "temperature_f": str(enrich.get("temperature_f", "")),
        "spo2_pct": str(enrich.get("spo2_pct", "")),
        "lab_panel_json": json.dumps(lab_panel, separators=(",", ":")),
        "lab_flags": ";".join(enrich.get("lab_flags") or []),
        "esi_tier_truth": str(enrich.get("esi_tier_truth", "")),
        "acuity_red_flags": ";".join(enrich.get("acuity_red_flags") or []),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=5, help="how many rows to enrich")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output CSV path")
    ap.add_argument("--dry-run", action="store_true", help="use mock LLM output (no API call)")
    ap.add_argument("--model", default="gemini-2.5-flash")
    ap.add_argument("--sleep", type=float, default=0.0, help="seconds between calls (rate-limit safety)")
    args = ap.parse_args()

    if not RAW_CSV.exists():
        sys.exit(f"raw CSV missing: {RAW_CSV}")

    with RAW_CSV.open(newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames + ENRICHMENT_FIELDS
        rows_in = []
        for i, row in enumerate(reader):
            if i >= args.rows:
                break
            rows_in.append(row)

    print(f"Loaded {len(rows_in)} rows from {RAW_CSV.name}")
    print(f"Mode: {'DRY-RUN (mock)' if args.dry_run else 'LIVE (Vertex ' + args.model + ')'}")
    print(f"Output: {args.out}")
    print()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    enriched_rows = []
    for i, row in enumerate(rows_in, 1):
        if args.dry_run:
            enrich = _mock_generate(row)
        else:
            prompt = PROMPT_TEMPLATE.format(
                age=row.get("Age", ""),
                gender=row.get("Gender", ""),
                blood_type=row.get("Blood Type", ""),
                medical_condition=row.get("Medical Condition", ""),
                admission_type=row.get("Admission Type", ""),
                medication=row.get("Medication", ""),
                test_results=row.get("Test Results", ""),
                los_days="?",
            )
            enrich = None
            for attempt in range(2):
                try:
                    enrich = _vertex_generate(prompt, model_name=args.model)
                    break
                except Exception as e:
                    if attempt == 1:
                        print(f"  [{i}/{len(rows_in)}] FAILED after 2 tries: {e}", file=sys.stderr)
                    else:
                        time.sleep(1.0)
            if enrich is None:
                continue
            if args.sleep:
                time.sleep(args.sleep)

        merged = {**row, **_flatten(enrich)}
        enriched_rows.append(merged)
        if i <= 3 or i % 25 == 0:
            print(f"  [{i:>4}/{len(rows_in)}] {row.get('Medical Condition', '?'):<15} → "
                  f"CC: {enrich.get('chief_complaint', '')[:50]}")

    with args.out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_rows)

    elapsed = time.time() - t0
    print()
    print(f"DONE. {len(enriched_rows)} rows → {args.out}  ({elapsed:.1f}s)")
    if not args.dry_run and len(enriched_rows):
        print(f"Estimated cost: ~${len(enriched_rows) * 0.0003:.2f} "
              f"(gemini-2.5-flash, ~500 in + 600 out tokens/call)")


if __name__ == "__main__":
    main()
