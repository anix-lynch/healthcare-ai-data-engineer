# L1 Hardening — From Clean Meal Prep → Surviving Real-World Groceries

> **Where we are:** L1 is **GenAI-friendly** — covers the 7 patterns' field needs.  
> **Where we are NOT:** L1 is **not real-life realistic** yet.  
> **Next upgrade:** real-world ingestion disguise. Same canonical contract on the other side.

---

## Current state (audit pass, 2026-05-16)

```
GENAI READINESS         ✅ pass — 7 patterns can chew on the enriched 497-row corpus
REAL-LIFE REALISM       ❌ fail — data arrives as one clean CSV, not hospital chaos
```

Right now L1 = **clean meal prep**. The 497 enriched rows look like a hospital
already pre-chewed everything, JSON-encoded it, and handed it over with a bow.
That's enough for Layer 2 patterns to develop against. It is **not** what an
actual hospital data engineer faces on day one.

---

## What real life actually looks like 😭

```
Hospital data engineer's Monday morning:
─────────────────────────────────────────────────────────────────────
└── EHR exports     → 8 different CSVs from 4 different vendors, no schema docs
└── discharge notes → PDFs in SharePoint, scanned + OCR'd + typo'd
└── nurse handoffs  → JSONL from a custom tool, free-text, inconsistent
└── policy docs     → DOCX from compliance, mixed with screenshots
└── billing exports → Excel with merged cells, "N/A" as string, no dates
└── lab feeds       → HL7 messages dropped on FTP every 4 minutes (ignored for now)
─────────────────────────────────────────────────────────────────────

Right now L1 is clean meal prep.
Next upgrade:
make L1 survive groceries arriving
in plastic bags, receipts, PDFs, and cursed Excel 😭
```

---

## Next upgrade scope (deliberately small)

**Goal:** prove L1 can turn real-world file chaos into the same AI-ready contract.

**NOT the goal:** perfect hospital ETL with FHIR/HL7 ingestion. That's a 6-month
project. We're doing the 2-day demo version that PROVES the architecture survives
diverse sources.

### File chaos to add

```
layer1-data-backbone/
└── source_systems/                 ← NEW
    ├── csv/
    │   └── encounters_raw.csv      messy export with inconsistent headers
    ├── pdf/
    │   ├── discharge_summary_001.pdf   synthetic discharge note
    │   └── triage_note_002.pdf         synthetic triage scribble
    ├── notes/
    │   └── nurse_notes.jsonl       free-text shift handoffs
    └── sharepoint_export/
        └── policy_guidelines.md    clinical protocol prose
```

### Scripts to add

```
scripts/
├── ingest_csv.py              messy CSV → typed rows + audit_lineage
├── ingest_pdf.py              pdfplumber + simple regex extract
├── ingest_notes.py            JSONL handoffs → patient_id resolved rows
└── normalize_to_canonical.py  union all sources → canonical_patient_context
                                (the output L2 already consumes today)
```

Each ingest script:
- writes to a staging table
- records `source_system`, `ingest_ts`, `row_hash`, `pii_redaction_status`
  in `audit_lineage_view`
- never blocks Layer 2 (L2 reads from canonical_patient_context, not raw sources)

---

## The L1 OUTPUT CONTRACT (frozen — L2 depends on this shape)

This is the contract Layer 2 already consumes. **Adding new ingestion paths must
NOT change this shape.** New sources land in `source_systems/`, get normalized
into `canonical_patient_context`, and downstream patterns are unaware.

```
L1_OUTPUT_CONTRACT
│
├── canonical_patient_context          ← The fact table L2 reads
│   ├── encounter_id                    Rachel + Crystal Ball + Police Lineup
│   ├── patient_id                      Rachel guard + identity audit
│   ├── chief_complaint                 Traffic Light + Rachel snippet
│   ├── hpi                             Mad Lib grounding + Rachel snippet
│   ├── vitals                          Traffic Light + Smoke Detector
│   ├── lab_flags                       Smoke Detector + Crystal Ball features
│   ├── diagnosis_family                Treasure Map clustering
│   ├── medication_summary              Crystal Ball features
│   ├── outcome                         Crystal Ball target + Mad Lib disposition
│   └── source_refs                     [{source_id, source_type, ingest_ts}]
│
├── retrieval_corpus_view              ← Rachel reads this
│   ├── source_id                       L1-NNNNNN | GUIDE-* | POLICY-*
│   ├── patient_id                      enables cross-patient leak guard
│   ├── encounter_id
│   ├── doc_text                        rendered snippet ready for BM25/dense
│   ├── source_type                     past_case | guideline | protocol
│   ├── clinical_bucket                 enables clinical_recall@K eval metric
│   └── timestamp
│
├── feature_view                       ← Crystal Ball + Smoke Detector read this
│   ├── predicted_los_features          age, condition, admission_type, season
│   ├── readmission_features            prior_visits, comorbidity_proxy
│   ├── mortality_features              age, condition, acuity_red_flags
│   └── ops_capacity_features           bed_pressure, ER_utilization, staffing
│
├── eval_holdout_view                  ← Layer 3 eval reads this
│   ├── query                           rendered question or case dump
│   ├── relevant_ids                    ground-truth source_ids
│   ├── graded_relevance                {source_id: 0|1|2|3}
│   └── query_bucket                    enables ClinicalRecall@K
│
└── audit_lineage_view                 ← Compliance + drift reads this
    ├── source_system                   csv | pdf | notes | sharepoint | direct
    ├── ingest_ts                       when this row landed
    ├── transform_version               which normalize_to_canonical.py shipped it
    ├── row_hash                        sha256 of canonical row for change detection
    └── pii_redaction_status            cleared | partial | needs_review
```

---

## Pattern → field needs map

This is **what each L2 pattern depends on**. Use it as a contract test: if any
ingestion path drops a field, the matching pattern will start hallucinating.

```
PATTERN          NEEDS FROM L1 (must survive any ingestion path)
─────────────────────────────────────────────────────────────────────
🔍 Rachel        clinical narrative (HPI + CC + physician_note)
                 + patient_id (cross-patient leak guard)
                 + source_id (citation validation)
                 + clinical_bucket (ClinicalRecall@K eval metric)

🚦 Traffic Light chief_complaint + vitals (BP/HR/RR/T/SpO2)
                 + acuity_red_flags
                 + esi_tier_truth (eval only, NEVER as feature)

🔮 Crystal Ball  LoS target (length_of_stay_days)
                 + readmission target (is_readmission)
                 + risk features (age, condition, prior_visits, vitals)
                 — NO discharge-time fields at predict time (leakage guard)

📖 Mad Lib       Rachel citations (source_id list)
                 + guideline text (retrieval_corpus_view, source_type=guideline)
                 + physician_note as grounding ceiling

🚨 Smoke Detector baseline distribution per cohort
                 + anomaly_score-able fields (vitals, lab values)
                 + outlier_reasons hooks

🗺️ Treasure Map  clusterable patient features
                 (demographics + condition family + admission pattern + outcome)
                 + cluster_label for human-readable phenotype names

👮 Police Lineup graded_relevance from eval_holdout_view
                 + evidence_scores per source_id
                 + the Rachel hits to rerank over
```

---

## Roadmap order (do NOT skip steps)

```
PHASE A — current (DONE 2026-05-16)
   ✅ L1 emits clean canonical_patient_context for 497 rows
   ✅ L2 patterns all consume it
   ✅ identity bridge wired for Rachel cross-patient guard
   ✅ holdout split preserved (100 rows, never trained on)

PHASE B — small ingestion realism (NEXT, 2-3 days)
   ⌛ source_systems/ folder with 1 sample each: csv, pdf, notes, sharepoint
   ⌛ 4 ingest_*.py scripts
   ⌛ normalize_to_canonical.py union pipeline
   ⌛ audit_lineage_view populated
   ⌛ existing canonical_patient_context unchanged (contract frozen)

PHASE C — light-touch real-world hardening (1-2 weeks)
   ⌛ PII redaction at ingest time (spaCy + regex), not just runtime
   ⌛ schema validation per source (Pydantic at ingest, not just downstream)
   ⌛ source freshness SLA tracking (last_ingest_ts per source_system)
   ⌛ dbt tests for canonical_patient_context completeness

PHASE D — production-grade EHR (deferred, 1-3 months)
   ❌ FHIR / HL7 message ingestion (real EHR feed)
   ❌ probabilistic entity resolution (rapidfuzz / SPLINK)
   ❌ change data capture from live EHR
   ❌ MRN-based identity (replaces name-hash patient_id)
   ❌ Synthea-grade synthetic generator OR PhysioNet credential
```

**Why this order:**
- Layer 2 is built and Layer 3 eval baselines exist. If we change the L1
  contract now, BOTH layers regress.
- Phase B teaches the SAME contract a new trick (source diversity). No L2
  changes.
- Phase D is when realism actually pays for itself, but only after the
  contract has survived Phase B + C without drift.

---

## Brutal one-liner

```
Right now L1 is clean meal prep.
Next upgrade:
   make L1 survive groceries arriving in
   plastic bags, receipts, PDFs, and cursed Excel 😭
```

---

## 🔮 Crystal Ball ceiling — the L1 data screams

Crystal Ball is the **loudest pattern** about L1 quality because regression
on snapshot-only data hits a hard ceiling. Adding chef skill (LightGBM,
calibration, ensembles) closes the gap to ceiling, but **the ceiling itself
is set by L1**.

### The ingredient vs chef split (architect realization)

```
L1 = ingredients quality           sets the CEILING
L2 = chef skill                     determines how close you get to ceiling

if ingredients are half-cursed gas-station chicken 💀
   even a Michelin chef plates a sad dish.
   BUT a good chef still beats a bad chef on the same ingredients.

→ Crystal Ball today is operationally honest, clinically NOT trustworthy.
   Honesty + warnings = the only thing keeping it out of felony territory.
```

### What Crystal Ball NEEDS from L1 (in order of impact)

```
RANK  L1 NEED                        UNLOCKS                                 PHASE
─────────────────────────────────────────────────────────────────────────────────
1️⃣    Temporal aggregation           "this patient over 3 admissions" view   C
       multiple encounters per         → real readmission_30d targets         
       patient indexed chronologically  → time-since-last-visit features      
                                        → readmission risk → calibrated 0-1

2️⃣    Real outcome labels             true mortality_indicator label          C
       death_in_hospital + 30d_mort    → mortality model instead of keyword
       30d_readmit ground truth        → calibrated risk scores
                                        → eval against real labels (AUC, Brier)

3️⃣    Vital trends over time          BP/HR/SpO2 trajectories instead         D
       not single-snapshot vitals       of door-entry single point
                                        → early-warning score (MEWS/NEWS2)
                                        → Smoke Detector ALSO benefits

4️⃣    Lab values over time            trending troponin / lactate / WBC       D
       discrete tests with timestamps  → trajectory inputs for prognosis
                                        → sepsis BUNDLE rule eval
                                        → Smoke Detector trending signals

5️⃣    Clinical trajectory markers     procedure events / med admin timeline   D
       what happened DURING the stay   → days-on-pressor, days-intubated
                                        → severity-of-illness scoring

6️⃣    Comorbidity / problem list      Charlson / Elixhauser comorbidity      C
       per patient, not per encounter  → comorbidity-adjusted LoS target
                                        → real readmission features

7️⃣    SDoH (social determinants)      housing / insurance churn / language   D
       discharge readiness inputs       → readmission risk features
                                        → discharge planning quality
```

### What L2 chef can still do TODAY (without L1 upgrades)

Crystal Ball today = cohort-mean LoS + sigmoid-on-prior-visits readmission +
keyword mortality heuristic. The chef has room to grow WITHOUT new ingredients:

```
✅ WORK WITH CURRENT L1
   LightGBM trained on existing 15-col features
     → likely beats cohort-mean on RMSE (already scaffolded in train_lightgbm.py)
   Calibration via isotonic regression on the 100-row holdout
     → readmission risk that actually means "70% chance" when it says 0.70
   Feature engineering on existing fields
     → age × condition interaction, season × admission_type
   Uncertainty quantification (LightGBM quantile regression)
     → "predicted_los = 4 days, 80% CI [2, 9]"
   Ensemble (cohort + LightGBM + rule heuristic)
     → vote-based, drops outlier predictions

❌ HITS HARD CEILING UNTIL L1 IMPROVES
   Real mortality prediction (needs death-event labels — currently NONE)
   Real readmission prediction (needs 30-day return tracking — currently NONE)
   Trajectory-aware prognosis (needs vitals/labs over time — currently NONE)
   Patient-level calibration (needs multi-encounter view — partially blocked)
```

### Confidence ceiling per L1 phase

```
L1 PHASE                              CRYSTAL BALL CONFIDENCE CAP   data_source value
─────────────────────────────────────────────────────────────────────────────────────
A — current (snapshot registry)       LOW                            registry_v1
B — small ingestion realism           LOW                            registry_v2_enriched
                                       (better narrative, still no temporal)

C — temporal aggregation +            MED                            registry_v3_temporal
    real outcome labels +              (real readmission/mortality
    comorbidity                         labels → real model)

D — full EHR realism                  HIGH (governed)                ehr_v1
    (telemetry over time + labs        (only allowed after eval
     over time + trajectory + SDoH)     gate passes on holdout)
```

**Hard rule:** Crystal Ball will NEVER emit `confidence="high"` on
`data_source="registry_v1"` or `registry_v2_enriched`. The cap stays MED at
best. This is enforced in `shared/regress/baseline.py` and audited in
`shared/regress/eval.py`. Marketing wants to remove the cap; the lawyer's
favorite slide is what keeps it there.

### Why this is correct sequencing (not a bug, a loop)

```
L2 builds with L1 as-is
   ↓
L2 surfaces realism gaps via eval failures
   ↓
gaps tell L1 what to fix next (= this section's roadmap)
   ↓
L1 upgrades land
   ↓
L2 retunes against new ceiling
   ↓
loop

That feedback loop IS modern GenAI architecture.
Build L2 against weak L1 first, otherwise you don't know what to harden.
```

### Brutal Crystal Ball self-portrait

```
Crystal Ball today:
  ✅ operationally honest
  ✅ architecturally believable
  ❌ clinically trustworthy
  ❌ FDA-approved prophecy
  ❌ ICU supercomputer
  ❌ Dr. Strange medical timeline engine 💀

What it actually is:
  honest survival calculator
  built from:
    cohort statistics
    + rule heuristics
    + "bro this looks dangerous 😭"
  capped at confidence=low until L1 grows up.

Pretending otherwise = felony. The warnings array exists for that reason.
```

---

## Cross-references

- L1 README (current shipped state): [`README.md`](README.md)
- L2 pattern scaffolds (consumers of this contract): `../layer2-ai-application/shared/`
- L1 honest gaps audit: [`../docs/03_implementation_phases.md`](../docs/03_implementation_phases.md)
- Full lifecycle (where the contract is enforced): [`../docs/05_patient_lifecycle.md`](../docs/05_patient_lifecycle.md)
