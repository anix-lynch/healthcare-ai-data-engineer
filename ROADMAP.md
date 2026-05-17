# Roadmap — Incremental Population from Monorepo

Source of truth: [`healthcare-genai-fullstack`](https://github.com/anix-lynch/healthcare-genai-fullstack).
This file tracks what landed in this AI Data Engineer view, in small commits.

**Sequencing principle:** data backbone FIRST, then quality gate + identity
bridge, then operational polish + CI. The repo should run `make checkpoint`
and pass before anything else lands.

---

## Target scaffold (AI Data Engineer lens)

```
healthcare-ai-data-engineer/
├── api/                           # FastAPI 11 endpoints over the warehouse
│   ├── app/main.py
│   ├── examples.py · test_api.py · README.md · requirements.txt
├── dbt-project/                   # bronze → silver → gold medallion
│   ├── models/staging/            # stg_healthcare.sql + sources.yml + schema.yml
│   ├── models/intermediate/       # int_encounters_enriched · int_readmissions
│   ├── models/marts/core/         # fact_patient_encounters + 7 dim_*.sql
│   └── tests/                     # assert_discharge_after_admission · _no_negative_los · _valid_readmission_logic
├── data/
│   ├── raw/                       # 55K registry + 497 enriched + use/holdout splits
│   ├── derived/                   # patient_identity_map.json
│   └── quality/                   # l1_checkpoint_report.json
├── scripts/
│   ├── enrich_clinical_narrative.py · enrich_parallel.py
│   ├── stratified_sampler.py · split_holdout.py · edge_cases.json
│   ├── patient_identity.py
│   └── checkpoint.py
├── ml-pipeline/                   # MLflow + readmission proxy scaffold (partial)
├── tests/                          # pytest: checkpoint · identity · FastAPI
├── demo/quickstart.sh              # 3-step sanity (checkpoint + identity + OpenAPI)
├── docs/L1_HARDENING.md            # Phase B/C/D upgrade plan
├── docs/contracts.md               # frozen L1 output contracts
├── .github/workflows/quality.yml  # CI: make checkpoint + make test on PR
├── Makefile · requirements.txt
└── openapi_snapshot.json
```

---

## Phase status (phase = dependency order, NOT calendar)

```
☑️ Phase 1 — scaffold                                     commits 602afb2 → 7a54351
   ☑ repo + README + ROADMAP + .gitignore + folder tree

☑️ Phase 2 — full L1 data backbone                         commit a3e6bdc
   ☑ 7 scripts (enrich · sampler · split · identity · checkpoint)
   ☑ dbt-project (staging + marts + tests)
   ☑ api/ FastAPI 11 endpoints
   ☑ data/raw + data/derived + data/quality
   ☑ ml-pipeline/ scaffold
   ☑ docs/L1_HARDENING.md + docs/contracts.md
   ☑ tests/test_checkpoint.py (2 tests)
   ☑ Makefile + requirements.txt + openapi_snapshot.json

☑️ Phase 3 — operational polish + CI                       commit pending (this turn)
   ☑ .github/workflows/quality.yml — checkpoint + test on PR
   ☑ README reframe (drop "presentation cut", lead with artifact)
   ☑ README embeds sample checkpoint output + curl response
   ☑ README LLM-augmentation context (Vertex enrichment shipped)
   ☑ tests/test_api.py — FastAPI TestClient smoke (6 tests)
   ☑ tests/test_identity.py — patient_id determinism + shape (6 tests)
   ☑ asciinema "Record your own demo" section in README
```

---

## Why this order (mirrors the GenAI Engineer playbook)

```
WRONG ORDER                          RIGHT ORDER
─────────────────────────────────────────────────────────────────────
"impressive enterprise dbt"          checkpoint passes → contracts frozen
   ↓                                    ↓
                                     "data backbone is trustworthy"
   ↓                                    ↓
recruiter: "where's the gate?"       recruiter: "show me the report"
                                        (5-second skim → unlock)
```

The L1 quality gate is the AI Data Engineer equivalent of the GenAI
Engineer's `/ask` vertical slice — the one thing that demonstrates the
data layer is real, not just architectural.

---

## Anti-overbuild reminders

- Recycle from monorepo. Do not rewrite.
- Honest scope. dbt is real but ML pipeline is scaffold-only — say so.
- Quality gate over impressive-looking dashboards.
- Phase order = dependency. No calendar implication. Ship in one sitting.
- ML pipeline stays a scaffold — no claims of trained production models.
