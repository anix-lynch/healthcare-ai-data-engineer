# healthcare-ai-data-engineer

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

This repo is the canonical source of truth for the data layer: it publishes
quality-gated, lineage-aware, identity-resolved artifacts that downstream
GenAI and delivery layers consume. Analytics engineering is here too, but it
is the supporting act, not the headline.

![Demo](demo.gif)

**Live cockpit (A1–A6):** https://healthcare-ai-data-819957310168.us-west1.run.app/app
&nbsp;·&nbsp; **API docs:** [/docs](https://healthcare-ai-data-819957310168.us-west1.run.app/docs)
&nbsp;·&nbsp; **Grounded agent:** [`/api/ask?q=…`](https://healthcare-ai-data-819957310168.us-west1.run.app/api/ask?q=which%20patients%20show%20cardiac%20red%20flags)

Built for hiring managers who want proof, not adjectives. **Every number on the
cockpit traces to a test or a committed artifact — not a vibe.**

---

## Architecture

![Architecture](portfolio/A6_architecture_diagram/architecture.png)

Raw synthetic data → identity + enrichment → **L1 quality gate** → dbt medallion
marts → FastAPI on Cloud Run → consumed by **humans** (A1/A2 cockpit) and
**agents** (BM25 retrieval + grounded Gemini, redacted surfaces only).

---

## Repo Map

What lives where, at a glance:



```
healthcare-ai-data-engineer/
├── api/                              the live FastAPI service
│   ├── app/
│   │   ├── main.py                   ✅ entry point — wires routes + serves the A1–A6 cockpit
│   │   ├── ask.py                    ✅ the /api/ask grounded-agent answer logic
│   │   ├── retrieval.py              ✅ BM25 — pulls the records that match the question
│   │   ├── classifier.py             ✅ tags each encounter (ESI tier / red-flag)
│   │   ├── control_room.py           ✅ builds the A1 executive dashboard numbers live
│   │   ├── trust_room.py             ✅ builds the A2 trust / data-quality panel live
│   │   └── warehouse_room.py         ✅ builds the A5 warehouse-inventory panel live
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
├── scripts/                          one-shot pipeline jobs (run by hand / CI)
│   ├── checkpoint.py                 ✅ the L1 data-quality gate (7 checks)
│   ├── patient_identity.py           ✅ rolls encounters up to stable patient IDs
│   ├── enrich_clinical_narrative.py  ✅ adds Vertex-generated clinical text
│   ├── enrich_parallel.py            ✅ the real 500-row parallel enrich run
│   ├── load_bigquery.py              ✅ loads the marts into BigQuery
│   ├── stratified_sampler.py         ✅ picks a representative slice
│   ├── split_holdout.py              ✅ carves out an eval hold-out set
│   ├── build_portfolio_snapshot.py   ✅ regenerates the A1/A2/A5 dashboard payloads
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
├── portfolio/                        🖼️  A1–A6 — one folder per cockpit panel
│   ├── A1…A6/screenshots/*.png       🖼️  proof shots of each live panel
│   ├── A1…A6/*_ascii.md · *.md       📖 panel notes + ASCII mockups
│   ├── A1/A2/A5/*_payload.json       🖼️  captured dashboard data behind each shot
│   └── A6/architecture.png           🖼️  the system diagram used up top
├── web/                              ✅ index.html · app.js · styles.css (the static cockpit)
├── deploy/cloudrun.sh · Dockerfile   ✅ how it ships to Cloud Run
├── demo/quickstart.sh                ✅ clone-to-running in one script
├── .github/workflows/quality.yml     ✅ CI — runs the quality gate + tests on push
├── openapi_snapshot.json             ✅ frozen public API surface
├── Makefile                          ✅ test · feast-apply · serve · checkpoint
├── requirements*.txt                 ✅ app deps (deploy split out, leaner image)
├── LOOKER_STUDIO.md · *.md           📖 BI / setup notes
└── demo.gif · README.md              🖼️📖 the 10-second story
```

---

## 60-Second Read

- 55,500 synthetic encounters modeled through dbt bronze/silver/gold layers.
- 497-row enriched slice shipped with a passing L1 quality gate.
- 55,500 encounters resolved into 40,235 unique patient identities.
- Published contracts and frozen OpenAPI snapshot keep the surface stable.
- FastAPI exposes the data product as reusable endpoints, not a pile of scripts.
- **L2 grounded agent** (`/api/ask`): BM25 retrieves top-K from the redacted
  enriched corpus, then Gemini answers with `[doc N]` citations — no raw PII indexed.

If you open only three files, open these:

- [data/quality/l1_checkpoint_report.json](data/quality/l1_checkpoint_report.json)
- [data/derived/patient_identity_map.json](data/derived/patient_identity_map.json)
- [docs/contracts.md](docs/contracts.md)

---

## Artifact Map

The repo reads cleanest when you start from artifact, then work backward to proof.

| Artifact | What it proves | Code that creates it | Who cares |
| --- | --- | --- | --- |
| [docs/contracts.md](docs/contracts.md) | Stable L1 outputs for downstream consumers | `dbt-project/` + API schemas | GenAI and warehouse teams |
| [data/quality/l1_checkpoint_report.json](data/quality/l1_checkpoint_report.json) | Trust gate passed: schema, nulls, duplicates, temporal sanity, PII leakage, identity resolution, lineage | `scripts/checkpoint.py` | Hiring manager, data platform, auditors |
| [data/derived/patient_identity_map.json](data/derived/patient_identity_map.json) | Encounters can be rolled up to stable patient identities | `scripts/patient_identity.py` | Modeling, dedupe, entity resolution |
| [docs/dag.md](docs/dag.md) | Bronze -> silver -> gold lineage is explicit | `dbt-project/models/` | Analytics engineering, data modeling |
| [openapi_snapshot.json](openapi_snapshot.json) | Public API surface is frozen and documented | `api/app/main.py` | Consumer teams, integration owners |
| [dbt-project/](dbt-project/) | The warehouse model is real, testable, and modular | staging, intermediate, marts, tests | Analytics engineers, warehouse reviewers |

For the recruiter-facing cockpit layer, start here:
[portfolio/README.md](portfolio/README.md)

For machine-readable navigation, use:
- [portfolio/manifest.json](portfolio/manifest.json)
- [portfolio/PROMPT_FOR_AGENT.md](portfolio/PROMPT_FOR_AGENT.md)

---

## What This Repo Publishes

### Trust layer

- A 7-check L1 gate committed in [data/quality/l1_checkpoint_report.json](data/quality/l1_checkpoint_report.json).
- Explicit failure modes for schema drift, nulls, duplicates, temporal sanity, PII leakage, identity mapping, and lineage completeness.
- Honest scope: this is a synthetic lab/demo corpus, not a HIPAA-compliant production system.

### Identity resolution

- A stable encounter-to-patient mapping in [data/derived/patient_identity_map.json](data/derived/patient_identity_map.json).
- Deterministic short patient identifiers so repeated encounters collapse cleanly.
- Synthetic edge cases are flagged instead of hand-waved away.

### Lineage and modeling

- dbt medallion modeling in [dbt-project/](dbt-project/): staging -> intermediate -> marts.
- Gold models include `fact_patient_encounters` plus seven dimensions.
- Tests in `dbt-project/tests/` make the DAG verifiable, not decorative.

### Contracted data products

- Stable contracts in [docs/contracts.md](docs/contracts.md):
  - `canonical_patient_context`
  - `retrieval_corpus_view`
  - `feature_view`
  - `eval_holdout_view`
  - `audit_lineage_view`
- Frozen API surface in [openapi_snapshot.json](openapi_snapshot.json).
- FastAPI endpoints documented in [api/README.md](api/README.md).

---

## Proof Snapshot

```text
quality gate
  497 enriched rows scanned
  7/7 checks passed
  0 critical failures

identity resolution
  55,500 encounters
  40,235 unique patients
  47 unresolved synthetic edges flagged

API surface
  /app                cockpit UI (A1–A6, links every number to its proof file)
  /api/control-room   A1 executive trust overview
  /api/trust-room     A2 quality + evidence
  /api/warehouse-room A5 warehouse explorer
  /api/retrieve       BM25 retrieval over the enriched corpus
  /api/ask            L2 grounded Gemini answer (cites [doc N])
  /api/classify       rule-based ESI triage with safety floors
  /api/encounters /api/patients /api/doctors /api/hospitals
  /api/conditions /api/medications /api/insurance /api/stats /api/search
  /docs
```

---

## Bridge To Downstream Repos

This repo is the backbone. The other repos consume its outputs.

- **L1 Fabric repo**: the warehouse-backed implementation of the same trust story. Same contract shape, different warehouse flavor.
- **L2 GenAI repo**: consumes `canonical_patient_context`, `retrieval_corpus_view`, and the holdout/eval artifacts to prove retrieval, grounding, evaluation, and safe generation on trusted data.
- **FDE repo**: consumes the L2 system and packages deployment, integration, runbook, acceptance tests, and handoff.

Short version: this repo publishes the data product; downstream repos prove they can use it.

---

## Repo Layout

```text
api/                 FastAPI data surface over the synthetic corpus
dbt-project/         dbt staging, intermediate, marts, and tests
data/raw/            raw synthetic data plus enriched slices and splits
data/derived/        identity resolution outputs
data/quality/        L1 checkpoint evidence
docs/                lineage and contract docs
scripts/             enrichment, sampling, identity, checkpoint pipelines
tests/               pytest coverage for checkpoint, identity, API, retrieval
demo/quickstart.sh   one-command sanity flow
openapi_snapshot.json frozen API contract
```

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

---

## Common Commands

```bash
make install       # install repo requirements
make serve         # run FastAPI on :8000
make checkpoint    # run the 7-check L1 quality gate
make patient-id    # rebuild encounter -> patient identity map
make test          # run pytest
make clean         # remove caches
```

---

## Honest Scope

| This repo is | This repo is not |
| --- | --- |
| Synthetic healthcare data backbone | HIPAA-compliant production system |
| dbt medallion model with tests | Enterprise MDM or real EHR integration |
| Identity-resolution proof | Production MRN matching |
| Stable API and published contracts | Authenticated multi-tenant SaaS |
| Proof-backed artifact catalog | A vague "AI platform" claim |

---

## Related Repos

- [healthcare-genai-engineer](https://github.com/anix-lynch/healthcare-genai-engineer) - L2 GenAI consumer layer
- [healthcare-forward-deployed-engineer](https://github.com/anix-lynch/healthcare-forward-deployed-engineer) - FDE delivery layer
- [healthcare-genai-fullstack](https://github.com/anix-lynch/healthcare-genai-fullstack) - full three-layer system
- [healthcare-api](https://github.com/anix-lynch/healthcare-api) - richer mirror with more script history

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the phase-ordered audit trail and commit history.

## License

MIT.