# Roadmap — Incremental Population from Monorepo

Source of truth: [`healthcare-genai-fullstack`](https://github.com/anix-lynch/healthcare-genai-fullstack)  
Standalone L1 mirror: [`healthcare-api`](https://github.com/anix-lynch/healthcare-api)  
This file tracks what lands in this presentation cut, in small steps.

---

## Target scaffold (AI Data Engineer lens)

```
healthcare-ai-data-engineer/
├── api/                           # FastAPI 11 endpoints over the warehouse
├── dbt-project/                   # bronze → silver → gold
├── data/
│   ├── raw/                       # 55K registry + 497 enriched corpus
│   ├── derived/                   # patient_identity_map.json
│   └── quality/                   # l1_checkpoint_report.json
├── scripts/
│   ├── enrich_clinical_narrative.py
│   ├── enrich_parallel.py
│   ├── stratified_sampler.py
│   ├── split_holdout.py
│   ├── patient_identity.py
│   └── checkpoint.py
├── ml-pipeline/                   # MLflow + readmission proxy scaffold
├── tests/
├── demo/                          # quickstart + sample endpoints
└── docs/                          # contracts · L1 hardening · honest gaps
```

---

## Phase status

- [x] **Phase 1:** repo + README + ROADMAP + minimal folder tree
- [ ] **Phase 2:** scripts/ — copy 6 enrichment/identity/checkpoint files
- [ ] **Phase 3:** dbt-project/ — copy staging + marts + tests
- [ ] **Phase 4:** data/ — copy enriched corpus + identity map + checkpoint report
- [ ] **Phase 5:** api/ — copy FastAPI surface
- [ ] **Phase 6:** docs/ — copy L1_HARDENING.md + add contracts.md
- [ ] **Phase 7:** demo/ + tests/ — small quickstart script + checkpoint test

Each phase = one commit. No phase invents new architecture.

---

## Anti-overbuild reminders

- Recycle from monorepo. Do not rewrite.
- Honest tone. No buzzword inflation.
- Data quality first. Schema drift visible. Lineage honest.
- ML pipeline stays a scaffold — no claims of trained production models.
