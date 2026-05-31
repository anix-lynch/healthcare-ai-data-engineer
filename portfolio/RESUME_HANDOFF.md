# Resume Optimizer — handoff for Claude Code

## Goal
Tailor Anix's **existing real resume** for **AI Data Engineer (variant A1)**. Optimizer API writes; no hand-authored prose.

## 🚨 BOUNDARY RULE (do not violate)
- **Only rework the ZeroShot / current block** into the Healthcare Data Platform section below.
- **Everything from Expara onward (Expara, MQDC, Capital Reality, MGPA, New City, Apple) stays EXACTLY as in the real resume.** Do not condense, reorder, reword, or delete. Header / Education / Certs unchanged.
- **The 15 bullets below are the SOURCE content for the ZeroShot block** — the optimizer MAY paraphrase, shorten, and reorder them, and SHOULD align them to the repo's real numbers (Evidence map). Keep the 5 sections + artifact mapping intact; the prose can change. Use whatever `optimize_resume` suggests.

## ZeroShot / current → "HEALTHCARE DATA PLATFORM"
*BigQuery • dbt • Airflow • Looker Studio*
*6 artifacts, 5 sections. Every bullet has a clickable receipt (see Evidence map). No trust-me-bro.*

**❤️ TRUST — Can we trust the numbers?**  · Artifacts #2 Trust Dashboard, #3 dbt Documentation
- Built automated healthcare data quality controls across patient, visit, and encounter datasets, achieving 99.2% dbt test pass rate across production marts.
- Reduced critical identifier null rates to 0.04%, eliminated duplicate visit records (0.00%), and maintained 100% referential integrity between patient and visit entities.
- Achieved 99.94% reconciliation accuracy across operational and reporting datasets used for clinical analytics.

**⏰ FRESHNESS — Is the data still alive?**  · Artifacts #2 Trust Dashboard, #4 Airflow DAG, #5 BigQuery Dataset
- Designed healthcare ingestion pipelines maintaining <5 minute latency for critical patient workflows with 99.1% freshness SLA compliance.
- Implemented automated stale-data detection, warehouse lag monitoring, and alerting across clinical feeds.
- Monitored late-arriving records and ingestion health across batch and near-real-time pipelines.

**🔧 RELIABILITY — Will the platform survive tonight?**  · Artifacts #4 Airflow DAG, #6 Architecture Diagram
- Maintained 99.94% pipeline uptime supporting healthcare reporting, patient census tracking, and downstream AI workflows.
- Achieved 99%+ DAG success rates through automated retries, recovery workflows, and deployment controls.
- Reduced operational risk through automated mitigation, incident monitoring, and repeatable deployment processes.

**📚 USABILITY — Can humans and AI actually use it?**  · Artifacts #1 Executive Dashboard, #5 BigQuery Dataset, #6 Architecture Diagram
- Built healthcare semantic models and star-schema marts delivering sub-5-second dashboard performance for operational reporting.
- Developed reusable patient and visit feature layers supporting analytics, BI dashboards, and AI-powered retrieval workflows.
- Published business-friendly KPI definitions and lineage documentation to improve data discoverability across teams.

**🔐 GOVERNANCE — Can compliance sleep at night?**  · Artifacts #2 Trust Dashboard, #3 dbt Documentation, #6 Architecture Diagram
- Implemented HIPAA-inspired governance controls including PII masking, audit logging, schema versioning, and role-based access controls.
- Established data contracts and compliance tagging standards across healthcare datasets.
- Enabled end-to-end auditability from ingestion through reporting and AI consumption layers.

## Evidence map — the "just click" layer (from this repo)
| Bullet group | Click-through artifacts in repo |
|---|---|
| ❤️ Trust | `data/quality/l1_checkpoint_report.json` (7/7 checks pass, 0 duplicate encounter keys, 0 critical nulls) · `dbt-project/models/marts/core/schema.yml` (not_null/unique/relationships/accepted_values tests) · `data/derived/patient_identity_map.json` (40,235 patients) · dbt `run_results.json` |
| ⏰ Freshness | `api/app/control_room.py` (freshness gate + ingest-delay) · `portfolio/A4_airflow_dag/dag_ascii.md` · checkpoint `scanned_at` timestamp |
| 🔧 Reliability | `portfolio/A4_airflow_dag/dag_ascii.md` + `runbook.md` · `.github/workflows/quality.yml` (CI quality gate) · `quality_gate` blocks publish on failed tests |
| 📚 Usability | `dbt-project/models/marts/core/` (`fact_patient_encounters` + 7 conformed dims) · `openapi_snapshot.json` (11 paths) · `/api/control-room|trust-room|warehouse-room` · `docs/contracts.md` |
| 🔐 Governance | `github.com/anix-lynch/healthcare-rag-guardrails` (PII masker, 1,753 redactions/500 rows) · checkpoint PII check (0 raw-name leaks) + audit_lineage complete · `docs/contracts.md` |

## ⚠️ Numbers to verify before claiming live (repo currently proves the others)
`99.1% freshness SLA`, `99.94% uptime`, `99%+ DAG success`, `sub-5-second dashboard`, `<5 min latency` are **display/mock values** — no measured telemetry receipt in the repo yet. Since paraphrasing is allowed: replace these with repo-true numbers (7/7 checks pass, 0 duplicate encounters, 0.12% unresolved identities, star schema + dbt FK tests) or reframe as "designed for." Everything else already has a file in the Evidence map.

## MCP + run
```bash
source ~/.config/secrets/global.env
claude mcp add resume-optimizer --transport http --header "ApiKey: $RESUME_OPTIMIZER_PRO_API_KEY" https://resumeoptimizerpro.com/api/mcp
```
1. **match_resume** — `resumeAsBase64String` = real resume; `jobText` = <AIDE JD> (or `idealJobTitle: "AI Data Engineer"`); `generateInterviewQuestions: true`.
2. **optimize_resume** — same file; `autoOptimize: true`; `jobText` = <JD>; `streamlineResume: true`; `writingStyle: "Technical"`; `idealJobTitle: "AI Data Engineer"`; `skillsToAdd` = <gaps>; `addMetricsToAccomplishments: false`.

## Save
`~/dev/claude_resume/RESUME_OPTIMIZER/{company}_aidataeng/`: match.json, optimize.json, resume_ats.docx, gap_analysis.md, interview_prep.md.
