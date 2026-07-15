# healthcare-ai-data-engineer

![Demo](demo.gif)

🔗 **Live:** https://healthcare-ai-data-819957310168.us-west1.run.app/app | **[▶ Storyboard — B1→B5 hero journey](https://healthcare-ai-data-819957310168.us-west1.run.app/storyboard)**

> 🟥 **L1 Truth + 🟧 L1.25 Context** part of the [L1→L3 healthcare AI platform](https://gozeroshot.dev) — Truth → Features → Signals → Actions → Human adoption. This repo = the trusted warehouse + Feast feature store everything downstream consumes.

Trusted healthcare data backbone for AI Data Engineer work — with an L2
grounded-agent layer that answers questions **only** from the trusted marts,
and a human cockpit where every displayed number links to the file that proves it.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-data%20surface-009688?logo=fastapi&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-medallion%20marts-FF694B?logo=dbt&logoColor=white)
![Vertex AI](https://img.shields.io/badge/Vertex%20AI-grounded%20Gemini-4285F4?logo=googlecloud&logoColor=white)
![Cloud Run](https://img.shields.io/badge/Cloud%20Run-live-4285F4?logo=googlecloud&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

![Demo](demo.gif)

**Live cockpit (B1–B6):** https://healthcare-ai-data-819957310168.us-west1.run.app/app
&nbsp;·&nbsp; **API docs:** [/docs](https://healthcare-ai-data-819957310168.us-west1.run.app/docs)
&nbsp;·&nbsp; **Grounded agent:** [`/api/ask?q=…`](https://healthcare-ai-data-819957310168.us-west1.run.app/api/ask?q=which%20patients%20show%20cardiac%20red%20flags)

Built for hiring managers who want proof, not adjectives. **Every number on the
cockpit traces to a test or a committed artifact — not a vibe.**

---

## Architecture

![Architecture](portfolio/B6_architecture_diagram/architecture.png)

Raw synthetic data → identity + enrichment → **L1 quality gate** → dbt medallion
marts → FastAPI on Cloud Run → consumed by **humans** (B1/B2 cockpit) and
**agents** (BM25 retrieval + grounded Gemini, redacted surfaces only).

---

## Repo Map

What lives where, at a glance:

```
healthcare-ai-data-engineer/
├── api/                              the live FastAPI service
│   ├── app/
│   │   ├── main.py                   ✅ entry point — wires routes + serves the B1–B6 cockpit
│   │   ├── ask.py                    ✅ the /api/ask grounded-agent answer logic
│   │   ├── retrieval.py              ✅ BM25 — pulls the records that match the question
│   │   ├── classifier.py             ✅ tags each encounter (ESI tier / red-flag)
│   │   ├── control_room.py           ✅ builds the B1 executive dashboard numbers live
│   │   ├── trust_room.py             ✅ builds the B2 trust / data-quality panel live
│   │   └── warehouse_room.py         ✅ builds the B5 warehouse-inventory panel live
│   ├── requirements.txt              ✅ API-only deps
│   └── README.md                     📖 how the API layer works
├── dbt-project/                      the warehouse (raw → clean → gold)
│   ├── models/staging/               ✅ stg_healthcare + sources — raw landing
│   ├── models/intermediate/          ✅ enriched encounters + readmission logic
│   ├── models/marts/core/            ✅ 8 dims + fact_patient_encounters (the gold tables)
│   ├── tests/                        ✅ 3 SQL data tests (no negative LOS, discharge>admit…)
│   ├── dbt_project.yml · profiles    ✅ dbt config
│   └── README.md                     📖 how the marts are built
├── feature-store/                    the L1.25 feature layer
│   ├── features.py                   ✅ Feast feature definitions (point-in-time correct)
│   ├── feature_store.yaml            ✅ Feast config (BigQuery offline / sqlite online)
│   ├── requirements.txt              ✅ feast[gcp] — kept out of the API image
│   └── README.md                     📖 what the features are + how to apply them
├── ingestion/                        event-driven streaming leg
│   ├── ingest.py · validate.py        ✅ batch replay + shared pure validator
│   ├── sink.py                        ✅ one idempotent-MERGE / quarantine contract
│   ├── publish_event.py               ✅ producer → Pub/Sub topic encounter-events
│   ├── proof_streaming.json           ✅ real Pub/Sub→Cloud Run→BigQuery flow
│   └── README.md                      📖 streaming + quarantine + entity-res
├── orchestration/                    self-monitoring Airflow DAG
│   ├── dags/data_platform_dag.py      ✅ parallel→transform→freshness→gate→publish/escalate
│   ├── anomaly.py                     ✅ IsolationForest auto-quarantine
│   ├── explain.py                     ✅ Gemini explains a failure in plain language
│   └── README.md · proof_*.json       📖 run-verified detect→recover→escalate
├── reliability/                      Self-healing — failure taxonomy + bounded retry + SLA
│   ├── core.py                       ✅ FailureSeverity · bounded_retry (exp backoff) · check_sla
│   ├── harness.py                    ✅ fault-injection over real primitives → ledger.jsonl
│   ├── metrics.py                    ✅ computes success/recovery/SLA from the ledger
│   └── run_suite.py                  ✅ `make reliability` → artifacts/ (no hand-typed numbers)
├── artifacts/                        🖼️  reliability evidence (success/recovery/SLA/failures)
│   └── reliability_summary.md        📖 99% success · 86% recovery · 0 stale-data incidents
├── governance/                       least-privilege + masking
│   ├── setup_governance.py            ✅ masked authorized view + view-only grant + retention
│   ├── least_privilege_demo.py        ✅ 200 on safe view · 403 on base table
│   └── README.md · proof_*.json       📖 the access model + its proof
├── scripts/                          one-shot pipeline jobs (run by hand / CI)
│   ├── checkpoint.py                 ✅ the L1 data-quality gate (7 checks)
│   ├── patient_identity.py           ✅ rolls encounters up to stable patient IDs
│   ├── enrich_clinical_narrative.py  ✅ adds Vertex-generated clinical text
│   ├── enrich_parallel.py            ✅ the real 500-row parallel enrich run
│   ├── load_bigquery.py              ✅ loads the marts into BigQuery
│   ├── stratified_sampler.py         ✅ picks a representative slice
│   ├── split_holdout.py              ✅ carves out an eval hold-out set
│   ├── build_portfolio_snapshot.py   ✅ regenerates the B1/B2/B5 dashboard payloads
│   └── edge_cases.json               ✅ tricky inputs the scripts guard against
├── tests/                            pytest — proves it all works
│   ├── test_api.py · test_ask.py     ✅ API + grounded-agent answers
│   ├── test_checkpoint.py            ✅ the quality gate catches bad data
│   ├── test_control_room.py          ✅ dashboard numbers are correct
│   ├── test_identity.py              ✅ patient identity rollup is correct
│   ├── test_retrieve_classify.py     ✅ retrieval + classifier behave
│   └── test_feature_store.py         ✅ the L1.25 feature definitions are valid
├── data/
│   ├── quality/                      ✅ checkpoint report + eval/golden sets (the proof JSONs)
│   └── derived/patient_identity_map  ✅ the resolved encounter→patient map
├── docs/                             📖 contracts.md · dag.md · L1_HARDENING.md (the "why")
├── portfolio/                        🖼️  B1–B6 — one folder per cockpit panel
│   ├── B1…B6/screenshots/*.png       🖼️  proof shots of each live panel
│   ├── B1…B6/*_ascii.md · *.md       📖 panel notes + ASCII mockups
│   ├── B1/B2/B5/*_payload.json       🖼️  captured dashboard data behind each shot
│   └── B6/architecture.png           🖼️  the system diagram used up top
├── web/                              ✅ index.html · app.js · styles.css (the static cockpit)
├── deploy/cloudrun.sh · Dockerfile   ✅ how it ships to Cloud Run
├── demo/quickstart.sh                ✅ clone-to-running in one script
├── .github/workflows/quality.yml     ✅ CI — runs the quality gate + tests on push
├── openapi_snapshot.json             ✅ frozen public API surface
├── Makefile                          ✅ test · feast-apply · serve · checkpoint
├── requirements*.txt                 ✅ app deps (deploy split out, leaner image)
└── demo.gif · README.md              🖼️📖 the 10-second story
```

---

## 60-Second Read

- 55,500 synthetic encounters modeled through dbt bronze/silver/gold layers.
- 8 governed dimensions + 1 encounter fact validated by 51/51 live BigQuery dbt tests.
- 497-row enriched slice shipped with a passing **7/7 L1 quality gate**, 0 critical failures.
- 55,500 encounters resolved into 40,235 unique patient identities (47 synthetic edges flagged).
- Published contracts + frozen OpenAPI snapshot keep the surface stable.
- **L2 grounded agent** (`/api/ask`): BM25 retrieves top-K from the redacted enriched corpus,
  then Gemini answers with `[doc N]` citations — no raw PII indexed.

If you open only three files, open these:

- [data/quality/l1_checkpoint_report.json](data/quality/l1_checkpoint_report.json) — the trust gate that passed
- [data/derived/patient_identity_map.json](data/derived/patient_identity_map.json) — encounter → patient resolution
- [docs/contracts.md](docs/contracts.md) — the stable contracts downstream consumes

**Honest scope:** synthetic lab/demo corpus with a real dbt model, tested DAG, and identity-resolution
proof — *not* a HIPAA-compliant production EHR or authenticated multi-tenant SaaS.

---

## Data Quality — two layers (deliberate split)

Not everything belongs in the same tool. This repo uses the right one for each job:

| Layer | Tool | Owns | Run |
|---|---|---|---|
| **Release-boundary contracts** | **Great Expectations** | all **55,500 source rows** before promotion + the **497-row AI-facing enrichment** before downstream use; schema · not-null · ranges · allowed sets · hashes — rendered as Data Docs HTML | `make ge` |
| **Healthcare-specific guards** | custom Python (`scripts/checkpoint.py`) | PII regex over free-text clinical notes · encounter→patient identity resolution · temporal sanity — things GE can't express | `make checkpoint` |

GE is a fail-closed release gate, not a decorative sample report. Duplicates are not
treated as a source-contract failure because the platform deliberately quarantines
and reconciles them; `quality/proof_reconciliation.json` proves every row is accounted for.
The two GE boundary suites currently pass **48/48 expectations** while explicitly
surfacing 108 source billing exceptions inside the approved tolerance.
The custom gate covers domain checks an off-the-shelf tool cannot express.

---

## Quick Start

```bash
git clone https://github.com/anix-lynch/healthcare-ai-data-engineer
cd healthcare-ai-data-engineer
make install
bash demo/quickstart.sh
```

Then run the API:

```bash
make serve
curl localhost:8000/api/stats | jq
```

Common commands:

```bash
make checkpoint    # run the 7-check L1 quality gate
make patient-id    # rebuild encounter -> patient identity map
make test          # run pytest
```

---

## Tableau BI Delivery Layer

The data pipeline extends to a Tableau extract for BI team consumption — no Tableau Desktop required on the data engineering side.

```
BigQuery gold layer (raw_ingest_clean)
    ↓ tableau/export_hyper.py
healthcare_by_condition.hyper        ← handed to viz team
```

**What it does:** aggregates patient encounters by medical condition (count, avg billing, avg age) → writes a `.hyper` Tableau extract via Tableau Hyper API → viz team opens in Tableau Desktop/Public, data is already there.

```bash
# BigQuery mode (needs GOOGLE_APPLICATION_CREDENTIALS)
python tableau/export_hyper.py

# Dry-run (local JSONL, no GCP creds needed)
python tableau/export_hyper.py --dry-run
```

![Tableau extract preview](tableau/healthcare_by_condition.png)

---

## Related Repos

This repo is the backbone — it publishes the data product; the others consume it.

- [healthcare-genai-engineer](https://github.com/anix-lynch/healthcare-genai-engineer) — L2 GenAI consumer layer
- [healthcare-forward-deployed-engineer](https://github.com/anix-lynch/healthcare-forward-deployed-engineer) — FDE delivery layer
- [healthcare-genai-fullstack](https://github.com/anix-lynch/healthcare-genai-fullstack) — full three-layer system
- [healthcare-api](https://github.com/anix-lynch/healthcare-api) — richer mirror with more script history

---

## License

MIT.
