healthcare-ai-data-engineer/
│
├── portfolio/                           👁 HUMAN COCKPIT LAYER
│                                        tech: Markdown + screenshots + Looker mock
│                                        proves: hiring manager can understand repo fast
│                                        and L2 engineers can discover trusted L1 handoff points
│
│   ├── README.md                        🚪 START HERE
│   │                                    tech: Markdown
│   │                                    proves: 60-sec artifact map
│   │
│   ├── A1_executive_dashboard/          📊 A1 | Executive Dashboard
│   │                                    tech: Looker Studio + BigQuery summary views
│   │                                    proves: 5 L1 domains visible in one screen
│   │                                    ~~resume: Trust/Freshness/Reliability overview~~
│   │                                    resume: Trust/Freshness/Reliability + AI readiness overview
│   │
│   │   ├── README.md                    purpose + audience + links
│   │   ├── executive_dashboard_ascii.md human-eye mockup
│   │   ├── dashboard_spec.yml           KPI definitions + thresholds
│   │   └── screenshots/
│   │       └── executive_dashboard.png  final visual proof
│   │
│   ├── A2_trust_dashboard/              ❤️ A2 | Trust + Agent Readiness Dashboard
│   │                                    tech: Looker Studio + BigQuery + dbt tests
│   │                                    proves: data quality + patient/visit trust
│   │                                    resume: 99.2% tests, 0.04% nulls, 0 dupes
│   │
│   │   ├── README.md                    trust story: "can we trust the chart and feed agents?"
│   │   ├── trust_dashboard_ascii.md     Trust Me Bro UI mockup
│   │   ├── trust_metrics_spec.yml       good/strong benchmark rules
│   │   ├── evidence_links.md            dbt/BigQuery/proof file map
│   │   └── screenshots/
│   │       └── trust_dashboard.png      final visual proof
│   │
│   ├── A3_dbt_documentation/            🧬 A3 | Data Model + Agent Contract Explorer
│   │                                    tech: dbt Core + dbt Docs + SQL
│   │                                    proves: marts + lineage + contracts
│   │                                    ~~resume: Bronze → Silver → Gold → Mart~~
│   │                                    resume: Bronze → Silver → Gold → Mart (AI-ready handoff)
│   │
│   │   ├── README.md                    what models exist + what agents can safely consume
│   │   ├── mart_catalog_ascii.md        what can I use?
│   │   ├── lineage_ascii.md             raw → staging → fact/dim → mart lineage
│   │   ├── model_map.md                 fact + dim + mart inventory
│   │   ├── sample_queries.sql           proof queries for BI + retrieval prep
│   │   └── screenshots/
│   │       └── mart_catalog.png         marketplace + lineage preview
│   │
│   ├── A4_airflow_dag/                  🔄 A4 | Airflow DAG / Pipeline Ops
│   │                                    tech: Airflow + Python + GitHub Actions
│   │                                    proves: scheduled pipeline + recovery
│   │                                    ~~resume: 99%+ DAG success / auto retry~~
│   │                                    resume: Freshness + Reliability for BI and AI consumers
│   │
│   │   ├── README.md                    pipeline purpose + downstream impact
│   │   ├── dag_ascii.md                 DAG flow + blast radius + call ownership
│   │   ├── runbook.md                   if broken → owner/action/fix
│   │   └── screenshots/
│   │       └── airflow_dag.png          DAG screenshot/mock
│   │
│   ├── A5_bigquery_dataset/             🏭 A5 | Warehouse + Agent Corpus Explorer
│   │                                    tech: BigQuery + SQL
│   │                                    proves: warehouse tables actually exist
│   │                                    resume: patient/visit marts + agent-ready warehouse surfaces
│   │
│   │   ├── README.md                    warehouse purpose + storytelling-over-root contract
│   │   ├── table_inventory.md           tables, rows, grain, owner, pii_status, agent_allowed
│   │   ├── sample_queries.sql           proof queries backed by root dbt models
│   │   ├── warehouse_room_payload.json  machine-readable panel payload for A5
│   │   └── screenshots/
│   │       └── bigquery_tables.png      BigQuery screenshot/mock
│   │
│   └── A6_architecture_diagram/         🏗 A6 | System Architecture + Dependency Map
│                                        tech: Mermaid + Markdown
│                                        question: How does the whole machine connect?
│                                        proves: end-to-end platform thinking + repo dependency awareness
│                                        resume: ingestion → warehouse → API → L1 trust → L2 action
│
│       ├── README.md                    architecture guide
│       ├── architecture_ascii.md        high-level system map
│       ├── dependency_map_ascii.md      what file/process feeds what downstream
│       ├── architecture.mmd             Mermaid system source
│       ├── dependency_map.mmd           Mermaid dependency source
│
├── dbt-project/                         ⚙️ ENGINE | Transform + tests
│                                        tech: dbt Core + SQL + BigQuery adapter
│                                        feeds: A2 Trust + A3 docs + A5 warehouse explorer
│                                        proves: Trust + Usability + AI readiness
│                                        future-proof cues:
│                                        - ai-safe views (planned)
│                                        - pii_redaction / agent_contract tests (planned)
│
├── airflow/                             ⏱ SCHEDULER | Pipeline runs
│                                        tech: Airflow + Python
│                                        feeds: A4 Pipeline Ops + agent export jobs (planned)
│                                        proves: Freshness + Reliability
│
├── api/                                 🔌 DATA PRODUCT SURFACE
│                                        tech: FastAPI + OpenAPI
│                                        proves: AI/BI teams can consume marts
│                                        supports: Usability + machine-readable portfolio payloads
│                                        current payload endpoints:
│                                        /api/control-room /api/trust-room /api/warehouse-room
│
├── data/                                🧾 EVIDENCE + SAMPLE DATA
│   ├── raw/                             source CSVs
│   ├── derived/                         patient_identity_map.json
│   └── quality/                         l1_checkpoint_report.json
│                                        feeds: A1/A2/A5 trust signals + L2 runtime gating
│   └── exports/                         (planned) pii-safe corpus for retrieval/index
│                                        agent_corpus_ndjson + agent_tables_manifest.json
│
├── contracts/                           📜 L2 CONSUMER CONTRACTS (planned)
│   ├── l2_manifest.json                 agent-safe assets, pii status, freshness SLA, allowed uses
│   └── README.md                        L1 trust -> L2 action handoff guide
│
├── tests/                               🧪 SAFETY NET
│                                        tech: pytest + API smoke tests
│                                        proves: CI does not run on vibes 😭
│                                        future-proof cues:
│                                        no raw PII in agent-facing exports (planned)
│
├── docs/                                📚 CONTRACTS + DECISIONS
│                                        tech: Markdown
│                                        feeds: A3 + A6 + L2 design
│                                        future-proof docs:
│                                        ai_ready_marts.md + trust_to_action.md (planned)
│
└── .github/workflows/                   ✅ CI
                                         tech: GitHub Actions
                                         proves: quality gate runs on PR
                                         future-proof: guards trust + AI readiness contracts
