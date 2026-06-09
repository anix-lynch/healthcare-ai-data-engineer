# healthcare-ai-data-engineer

## Repo Map

```
healthcare-ai-data-engineer/
├── ingestion/        ✅ openFDA pull → quarantine → idempotent BQ merge → reconcile (Bullet 1)
├── dbt-project/      ✅ medallion SQL: stg → fact_adverse_events + dim_drug/reaction + bridge → marts (Bullet 3)
│   └── models/marts/openfda/  ✅ semantic marts: drug-safety KPIs + reaction signals (+ tests)
├── feature_repo/     ✅ Feast features over openFDA (point-in-time correct) — discovery + serving
├── api/              ✅ grounded AI: BM25 retrieve → Gemini answer with [doc N] citations + refusal (Bullet 3)
├── scripts/governance/ ✅ Bullet 4: masking · audit ledger · versioned contract · retention/deletion
├── gx/               ✅ Great Expectations quality gates
├── contracts/        📜 versioned data contract (sha-pinned)
├── data/quality/     🟡 proof receipts — every resume bullet → a machine-readable JSON (the evidence bank)
├── data/raw|clean/   📦 bounded openFDA sample (real FAERS reports)
├── deploy/           ✅ Cloud Run watchdog deploy (Bullet 2: independently-scheduled self-healing)
├── tests/            ✅ pytest
└── README.md         📖 you are here
```

> A trust layer over a **live FDA adverse-event feed** — bad rows fail closed at the door, the feed never goes quietly stale, every number has a receipt, and the model reads only the clean, cited layer.

Ingests live drug-safety reports from **openFDA** (api.fda.gov — free, no key, 20M+ reports) on a schedule, gates them before anyone trusts them, keeps them fresh, and serves a grounded API that refuses when the evidence isn't there.

**Run it:** `bash demo/quickstart.sh` (the whole pipeline in ~30s, no cloud auth)

## What it does

```
Live FDA feed --> scheduled pull --> fail-closed gate --> dbt marts --> grounded /api/ask
                  (real ingest_ts)   (5 checks)           (incremental)  ([doc N] . refuses)
                       |                                       |
                  freshness SLA                          point-in-time features
                  + stale alert                          (no future leak)
```

- **Real, messy data** — live FAERS reports, pulled incrementally; missing fields, dupes across pulls, late rows handled.
- **Fails closed** — a quality gate blocks bad data (null keys, dupes, schema drift, bad dates) before it reaches the warehouse or the model.
- **Never silently stale** — every batch is stamped with when it landed; a freshness SLA fires a stale alert before anyone trusts an old number.
- **Runs itself** — daily orchestrated pull with retry recovery (GitHub Actions).
- **Every number has a receipt** — source->warehouse contracts, reconciliation, committed reports.
- **AI reads the clean layer** — `/api/ask` grounds on the redacted corpus with `[doc N]` citations and says *"not supported by the evidence"* rather than invent a drug interaction.

## Repo map

```
healthcare-ai-data-engineer/
|- ingestion/        pull + gate + freshness + point-in-time features (the pipeline)
|- config/           freshness SLA thresholds
|- dbt-project/      source freshness + incremental staging + fact + reconciliation test
|- api/app/          grounded /api/ask + /api/retrieve over the openFDA corpus
|- .github/workflows openFDA pipeline -- daily cron + retry
|- demo/             quickstart.sh -- run the whole thing in 30s
|- deploy/           Cloud Run deploy
\- Dockerfile . Makefile
```

## Stack
Python . openFDA API . dbt (incremental + source freshness) . BM25 + Vertex/Gemini (grounded) . FastAPI . Cloud Run . GitHub Actions.

*Honest scope: portfolio-scale (a daily slice of the live feed), real source and real machinery. Not a production hospital feed.*
