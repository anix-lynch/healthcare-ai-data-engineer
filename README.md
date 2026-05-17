# healthcare-ai-data-engineer

> **Healthcare data backbone** — dbt medallion (bronze/silver/gold) + FastAPI 11 endpoints over 55,500 synthetic encounters + LLM-augmented enrichment (Vertex AI) + patient identity resolver + lightweight L1 quality gate. The data layer GenAI applications consume without hallucinating their way out of garbage input.

**Built for:** healthcare AI/data teams who need a trusted L1 layer before their RAG/agent stack lands on top. Patterns scale from this 55K demo to 50M+ row production via incremental dbt + Airflow-friendly idempotent scripts (each script in `scripts/` is checkpoint-driven and rerunnable without manual cleanup).

[![data-quality](https://github.com/anix-lynch/healthcare-ai-data-engineer/actions/workflows/quality.yml/badge.svg)](https://github.com/anix-lynch/healthcare-ai-data-engineer/actions/workflows/quality.yml)

```
55K raw encounters
  ↓ dbt bronze → silver → gold (medallion + tests)
  ↓ 497-row enriched subset (Vertex AI: CC/HPI/vitals/labs/ESI ground-truth)
  ↓ patient_identity_map (55K encounters → 40K unique patients)
  ↓ scripts/checkpoint.py — 7 quality checks before mart release
  ↓ FastAPI surface — /api/encounters · /api/patients · /api/stats · /docs
```

---

## Quick demo (no server needed)

```bash
git clone https://github.com/anix-lynch/healthcare-ai-data-engineer
cd healthcare-ai-data-engineer
make install
bash demo/quickstart.sh
```

Output (live, just run it):

```
── 1) L1 quality checkpoint ───────────────────────
L1 checkpoint @ 2026-05-17T...
  input:  data/raw/healthcare_dataset_enriched.csv
  rows:   497
  ✅  schema_drift
  ✅  critical_nulls
  ✅  duplicate_encounters
  ✅  temporal_sanity
  ✅  pii_in_narrative
  ✅  patient_identity
  ✅  audit_lineage

PASS — no critical failures.

── 2) Patient identity map ────────────────────────
  encounters:    55,500
  patients:      40,235
  avg per pt:    1.379
  top repeater:  24 encounters
```

Then start the FastAPI surface:

```bash
make serve   # uvicorn on :8000
curl localhost:8000/api/stats | jq
```

---

## What's inside

```
api/                 FastAPI 11 endpoints over the 55K corpus
                       /api/encounters · /api/patients · /api/doctors ·
                       /api/hospitals · /api/conditions · /api/medications ·
                       /api/insurance · /api/stats · /api/search · /docs
                       (auto-generated OpenAPI at /docs)

dbt-project/         medallion architecture: bronze → silver → gold
                       staging/stg_healthcare.sql
                       intermediate/int_encounters_enriched.sql · int_readmissions.sql
                       marts/core/fact_patient_encounters.sql + 7 dim_*.sql
                       tests/ + sources.yml + dbt_project.yml

data/raw/            55K row source CSV + 497 LLM-enriched rows (CC/HPI/vitals/labs/ESI)
                     + 397-row training subset + 100-row eval holdout
                     (holdout NEVER feeds training/index)
data/derived/        patient_identity_map.json (55K encounters → 40K patients)
data/quality/        l1_checkpoint_report.json (latest gate run)

scripts/
   enrich_clinical_narrative.py     Vertex gemini-2.5-flash + JSON schema
   enrich_parallel.py                x6 ThreadPoolExecutor + retry + checkpoint
   stratified_sampler.py             condition × admission × age × gender cube
   split_holdout.py                  stratified 397 use / 100 holdout (seed=42)
   patient_identity.py               SHA256 short-id resolver
   checkpoint.py                      7-check L1 data quality gate (exit 1 on fail)
   edge_cases.json                    47 hand-picked scenarios (STEMI/sepsis/etc.)

tests/               pytest — checkpoint integrity · identity map shape ·
                       FastAPI endpoint smoke · patient_id determinism
docs/
   L1_HARDENING.md     real-world ingestion realism roadmap (Phase B/C/D)
                        + Crystal Ball ceiling analysis (what L2 patterns need
                          from L1 to lift their confidence cap)
   contracts.md         frozen L1 output contracts (canonical / retrieval /
                        feature / eval-holdout / audit views)

demo/quickstart.sh   3-step sanity in 30 seconds (checkpoint + identity + OpenAPI)

Makefile · requirements.txt · openapi_snapshot.json
```

---

## Quality gate (committed at `data/quality/l1_checkpoint_report.json`)

```
✅ schema_drift            29 columns present · enriched cols complete
✅ critical_nulls          Name · Age · Gender · Condition · dates all populated
✅ duplicate_encounters    0 dups in 451 unique encounter keys
✅ temporal_sanity         discharge ≥ admission · LoS within [0, 365]
✅ pii_in_narrative        0 SSN/phone/email/CC patterns in CC/HPI/notes
✅ patient_identity        40,235 patients resolved · 47 synthetic edges flagged
✅ audit_lineage           complete · source_system + ingest_ts + row_hash + pii_redaction_status on every row

PASS — 7/7 checks · 0 critical failures
```

The gate runs in CI on every PR (`.github/workflows/quality.yml`) +
locally via `make checkpoint`. Honest scope: this is the floor that catches
the dumb-but-pipeline-killing failures (duplicate encounter ids, PII leaks
into narrative fields, discharge-before-admission, schema drift). NOT HIPAA
compliance. NOT Great Expectations replacement.

See [`scripts/checkpoint.py`](scripts/checkpoint.py) for the seven check
implementations and their failure semantics.

---

## dbt DAG (lineage view)

```
SOURCE              SILVER             INTERMEDIATE             GOLD MARTS
─────────────       ──────────────     ────────────────         ──────────────────────────
healthcare.         stg_healthcare ──> int_encounters_enriched  ┌──> dim_patient
 raw_healthcare_     │ clean             │                       ├──> dim_doctor
 data (33 cols       │ hash PII          ├──> int_readmissions   ├──> dim_hospital
  incl. 4 audit)     │ cast dates        │                       ├──> dim_diagnosis
                                          │                       ├──> dim_medication
                                          │                       ├──> dim_insurance
                                          │                       ├──> dim_date
                                          └──────────────────────►└──> fact_patient_encounters
                                                                       (1 row per encounter,
                                                                        FK to all 7 dims +
                                                                        8 measures)
```

Full DAG + per-model lineage rules: [`docs/dag.md`](docs/dag.md).
For interactive HTML: `dbt docs generate && dbt docs serve` against a live warehouse.

---

## Vertex enrichment run (497 rows, gemini-2.5-flash)

```
cost                $0.25 total · $0.0005 per row
runtime             789s wallclock with x6 parallel workers
throughput          ~37 rows/min sustained
per-row p50         ~9s   (single Vertex call w/ JSON schema enforced)
per-row p99         ~25s  (rare retry cycles)
retry rate          ~3% (response_schema eliminates most JSON parse failures)
schema-fail rate    0% (Pydantic-via-JSON-Schema enforced by Vertex)
success rate        100% (497/497, no failed-rows.jsonl entries)

GCP $900 credit absorbed the entire run.
Same pipeline scales to 55K rows ≈ $27 · or 1M rows ≈ $500.
```

Reproduce: `scripts/enrich_parallel.py` (full source + retry logic + checkpoint).

---

## Sample API output

```bash
curl 'http://localhost:8000/api/stats' | jq
```

```json
{
  "total_encounters": 55500,
  "date_range": {"earliest": "2019-01-01", "latest": "2024-05-08"},
  "by_condition": {
    "Diabetes": 9241,
    "Hypertension": 9245,
    "Cancer": 9227,
    "Obesity": 9279,
    "Asthma": 9275,
    "Arthritis": 9233
  },
  "by_admission_type": {
    "Emergency": 18534,
    "Urgent": 18558,
    "Elective": 18408
  }
}
```

Full endpoint reference + 14 more curl recipes: [`api/README.md`](api/README.md).

---

## L1 OUTPUT CONTRACTS (frozen — what Layer 2 patterns consume)

The point of this layer is **trusted, AI-ready data** with stable contracts.
Five views downstream patterns import:

```
canonical_patient_context    one row per encounter — Rachel / Mad Lib grounding
retrieval_corpus_view         doc_text + source_id + patient_id for RAG indexing
feature_view                  predicted_los / readmission / mortality features
eval_holdout_view             100 stratified rows — NEVER fed to training/index
audit_lineage_view            source_system + ingest_ts + row_hash + pii_redaction_status (live · every gold row)
```

Full schema spec: [`docs/contracts.md`](docs/contracts.md).

---

## Common commands

```bash
make install      # pip install requirements + api/requirements
make serve        # uvicorn api/app on :8000 (or `python api/app/main.py`)
make checkpoint   # run L1 quality gate (7 checks, exit 1 on failure)
make patient-id   # (re)build encounter→patient identity map
make enrich-sample # enrich 5 rows via Vertex (needs GCP_PROJECT_ID env)
make test         # pytest tests/
make clean        # remove __pycache__ + .pytest_cache
```

---

## Honest scope

```
WHAT THIS REPO IS                     WHAT IT'S NOT
─────────────────────────────────────────────────────────────────────
✅ dbt medallion star schema           ❌ HIPAA-compliant production system
✅ 55K synthetic patient corpus        ❌ real EHR data (Kaggle synthetic)
✅ Vertex AI LLM enrichment shipped    ❌ full clinical narrative dataset
✅ Patient identity bridge             ❌ MRN-based MDM (uses name hash)
✅ 7-check L1 quality gate             ❌ Great Expectations / Soda replacement
✅ FastAPI 11 endpoints                ❌ auth / rate limiting / multi-tenant
```

See [`docs/L1_HARDENING.md`](docs/L1_HARDENING.md) for the upgrade roadmap:
Phase B (small ingestion realism via PDF/CSV/SharePoint), Phase C (PII at
ingest + Charlson comorbidity + real outcome labels), Phase D (deferred FHIR/
HL7 + MRN-based MDM).

---

## Record your own demo (asciinema)

```bash
brew install asciinema    # one-time
asciinema rec demo.cast
# inside the recording:
bash demo/quickstart.sh
# Ctrl-D to stop
asciinema upload demo.cast   # free public link
```

Plain-text `.cast` file embeds cleanly in any markdown reader.

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the phase-ordered audit trail (Phase 1 → 3,
each with the commit hash that shipped it).

---

## Related repos

- [healthcare-genai-engineer](https://github.com/anix-lynch/healthcare-genai-engineer) — Layer 2 GenAI runtime (RAG + evals + guardrails + FastAPI)
- [healthcare-forward-deployed-engineer](https://github.com/anix-lynch/healthcare-forward-deployed-engineer) — customer-deployment package (integrations + runbook + acceptance tests + Docker)
- [healthcare-genai-fullstack](https://github.com/anix-lynch/healthcare-genai-fullstack) — full 3-layer monorepo
- [healthcare-api](https://github.com/anix-lynch/healthcare-api) — richer L1 mirror with full scripts/data history

---

## License

MIT.
