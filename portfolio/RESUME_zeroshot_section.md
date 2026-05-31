# ZeroShot / current → Healthcare AI Data Platform
*This replaces ONLY the ZeroShot block. Everything from Expara onward stays as-is in the real resume.*
*Numbers below are grounded to real repo artifacts (the bracket = the file that proves it). Optimizer may paraphrase/shorten; keep the 5 sections + receipts.*

---

**HEALTHCARE AI DATA PLATFORM** — *featured project*
BigQuery · dbt · Airflow · FastAPI · Cloud Run · Vertex AI · GitHub Actions
*github.com/anix-lynch/healthcare-ai-data-engineer — live cockpit where every metric links to its evidence file*

**❤️ Trust — can we trust the numbers?**  · #2 Trust Dashboard, #3 dbt Docs
- Built an automated L1 data-quality gate across patient/visit/encounter data: **7/7 checks passing** (schema drift, nulls, duplicates, temporal, PII, identity, lineage), **0 duplicate encounters, 0 critical nulls**. *[data/quality/l1_checkpoint_report.json]*
- Enforced referential integrity in dbt — `not_null`/`unique` on encounter keys, **relationship tests across all 7 dimension FKs**, `accepted_values` on clinical flags — gating every `dbt build`. *[marts/core/schema.yml → run_results.json]*
- Surfaced unresolved patient identities explicitly (**47/40,235 = 0.12%**) with triage routing rather than hiding them. *[data/derived/patient_identity_map.json]*

**⏰ Freshness — is the data still alive?**  · #2 Trust, #4 Airflow DAG, #5 BigQuery
- Designed an Airflow ingestion DAG with a **freshness gate** (≤60m green / staleness thresholds) and ingest-delay surfaced live in the API. *[api/app/control_room.py, A4 dag_ascii.md]*
- Implemented automated stale-data detection and warehouse-lag monitoring across clinical feeds.

**🔧 Reliability — will the platform survive tonight?**  · #4 Airflow DAG, #6 Architecture
- Built a dependency-ordered pipeline where a **`quality_gate` blocks publish on any failed test** — bad data never reaches dashboards or agents. *[A4 dag_ascii.md]*
- Hardened with automated retries, a per-failure **runbook** (owner + rollback path), and a **CI quality gate on every PR**. *[runbook.md, .github/workflows/quality.yml]*

**📚 Usability — can humans AND AI use it?**  · #1 Executive Dashboard, #5 BigQuery, #6 Architecture
- Modeled a **Kimball star schema** (`fact_patient_encounters` + 7 conformed dims) with pre-aggregated marts so analysts query without join hell. *[dbt-project/models/marts/core/]*
- Exposed **machine-readable trust/warehouse payloads** over FastAPI (**11 documented paths**, OpenAPI) feeding both BI dashboards and AI retrieval. *[openapi_snapshot.json, /api/control-room|trust-room|warehouse-room]*
- Published KPI definitions + lineage for self-serve discoverability. *[docs/contracts.md]*

**🔐 Governance — can compliance sleep at night?**  · #2 Trust, #3 dbt Docs, #6 Architecture
- Implemented HIPAA-inspired controls: **PII masking (1,753 redactions / 500 rows, 0 raw-name leaks)**, audit logging, schema versioning, and data contracts. *[healthcare-rag-guardrails, l1_checkpoint pii check]*
- Delivered **end-to-end auditability** (ingestion → reporting → AI consumption, audit_lineage complete); agents read only redacted/governed marts. *[docs/contracts.md, l1_checkpoint_report.json]*

---

### Notes on grounding (why these numbers, vs the earlier draft)
- Used **7/7 checks (100%)** not "99.2%", **0 dupes**, **0.12% unresolved** — these are what `l1_checkpoint_report.json` actually reports, so an interviewer's click always matches.
- Dropped the mock telemetry numbers (99.1% SLA / 99.94% uptime / 99%+ DAG / sub-5s) — no receipt in the repo. Reframed Reliability/Freshness around the **quality gate + CI + DAG structure**, which *is* in the repo. Re-add the percentages only after uptime telemetry is instrumented.
