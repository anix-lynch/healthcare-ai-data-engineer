# A4 — Pipeline Operations DAG

> Runtime / data-production flow only. `portfolio/` is the cockpit (how humans
> read the system), **not** part of the pipeline — it appears here only as a
> final consumer of the published marts/API.

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ 🔄 A4 PIPELINE OPERATIONS DAG                                                  │
│ What runs first? What depends on what? What breaks downstream?                 │
│ tech: Airflow + Python + dbt + GitHub Actions                                  │
└───────────────────────────────────────────────────────────────────────────────┘
                         ┌───────────────────────┐
                         │ (1) data/raw/          │
                         │ source healthcare data │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │ (2) ingest_raw.py      │
                         │ validate/load raw      │
                         └───────────┬───────────┘
                                     │
               ┌─────────────────────┴─────────────────────┐
               ▼                                           ▼
┌──────────────────────────────┐             ┌──────────────────────────────┐
│ (3) identity_resolver.py      │             │ (4) provider_cleaning.py      │
│ patient_identity_map.json     │             │ provider reference data       │
└──────────────┬───────────────┘             └──────────────┬───────────────┘
               │                                            │
               │ both must finish                           │
               └─────────────────────┬──────────────────────┘
                                     ▼
                         ┌───────────────────────┐
                         │ (5) dbt build          │
                         │ bronze → silver → gold │
                         └───────────┬───────────┘
                                     │
               ┌─────────────────────┼─────────────────────┐
               ▼                     ▼                     ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│ (6) dbt tests         │ │ (7) schema checks     │ │ (8) recon checks      │
│ not_null / unique     │ │ contracts valid       │ │ finance vs billing    │
└──────────┬───────────┘ └──────────┬───────────┘ └──────────┬───────────┘
           │                        │                        │
           │ all must pass          │                        │
           └────────────────────────┴────────────┬───────────┘
                                                ▼
                                      ┌───────────────────────┐
                                      │ (9) quality_gate.py    │
                                      │ PASS → publish         │
                                      │ FAIL → block + alert   │
                                      └───────────┬───────────┘
                                                  │
                   ┌──────────────────────────────┼──────────────────────────────┐
                   ▼                              ▼                              ▼
        ┌──────────────────────┐       ┌──────────────────────┐       ┌──────────────────────┐
        │ (10) mart_patient     │       │ (11) mart_visit       │       │ (12) mart_claims      │
        │ precomputed mart      │       │ prejoined mart        │       │ finance mart          │
        └──────────┬───────────┘       └──────────┬───────────┘       └──────────┬───────────┘
                   │                              │                              │
                   │ marts published together     │                              │
                   └──────────────────────────────┼──────────────────────────────┘
                                                  ▼
                                      ┌───────────────────────┐
                                      │ (13) api_refresh       │
                                      │ FastAPI / OpenAPI      │
                                      └───────────┬───────────┘
                                                  │
                         ┌────────────────────────┼────────────────────────┐
                         ▼                        ▼                        ▼
            ┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
            │ (14) A1 dashboard     │ │ (15) A2 trust view    │ │ (16) AI consumers     │
            │ executive cockpit     │ │ quality cockpit       │ │ RAG / agents          │
            └──────────────────────┘ └──────────────────────┘ └──────────────────────┘
```

## Dependency rules

```
1 → 2
2 → 3,4
3,4 → 5
5 → 6,7,8
6,7,8 → 9
9 → 10,11,12
10,11,12 → 13
13 → 14,15,16
```

## Blast radius

```
If (3) identity_resolver.py fails:
    patient_identity_map.json fails
    → dbt build may still run but trust quality drops
    → A2 Trust Dashboard turns yellow/red

If (6) dbt tests fail:
    quality_gate.py blocks publish
    → marts do not refresh
    → API/dashboard serve last-known-good snapshot

If (9) quality_gate.py fails:
    mart_patient / mart_visit / mart_claims blocked
    → A1 Executive Dashboard shows degraded mode
    → AI consumers do not receive bad data
```

## What A4 proves

- **Freshness** — data arrives and refreshes on schedule
- **Reliability** — tasks run in dependency order
- **Recovery** — failed jobs retry or block publish safely
- **Blast radius** — you know what breaks downstream

`portfolio/` stays out of the DAG except as final consumers (marts/API → A1/A2
screenshots), because the DAG is about runtime flow, not folder layout.
