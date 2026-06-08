# openFDA pipeline -- build notes

Live FDA adverse-event ingestion (api.fda.gov, free, no key, 20M+ reports).

| stage | file | what it proves |
|---|---|---|
| ingest | openfda_pull.py | scheduled pull, real `ingest_ts` per run, partitioned landing, audit lineage, dedup |
| quality gate | openfda_gate.py | fail-closed: null/dup/schema/temporal/value + reconciliation vs source |
| freshness | freshness_check.py | data-latency, SLA (24h/48h), stale-table alert |
| features | openfda_features.py | point-in-time correctness + future-leak guard test |
| orchestration | ../.github/workflows/openfda_pipeline.yml | daily cron + 3x retry + run artifacts |
| dbt | ../dbt-project/models/{staging,marts}/openfda | source freshness + incremental merge + fact + reconcile test |

Run: `bash demo/quickstart.sh`  ·  honest limit: synthetic-free but portfolio-scale (daily slice of the live feed).
