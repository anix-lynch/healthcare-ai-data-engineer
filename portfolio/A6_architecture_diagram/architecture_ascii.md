+--------------------------------------------------------------------------------+
| 🏗 A6 LA CITY MAP — system architecture + dependency awareness                 |
| How does the whole machine connect?                                            |
| tech: Mermaid + Markdown | city-scale system map, not a tiny flowchart         |
+--------------------------------------------------------------------------------+

                              [ Pacific Coast ]
                                      |
                                      v
    +----------------------+    +----------------------+    +----------------------+
    | data/raw/            |    | data/derived/       |    | data/quality/        |
    | source datasets      |    | identity map        |    | checkpoint report    |
    +----------+-----------+    +----------+-----------+    +----------+-----------+
               |                            |                            |
               +------------+---------------+---------------+------------+
                            v
    +----------------------+    +----------------------+    +----------------------+
    | scripts/             |    | dbt-project/         |    | docs/                |
    | ingest + resolver    |    | models + tests       |    | contracts + dag      |
    +----------+-----------+    +----------+-----------+    +----------+-----------+
               |                            |                            |
               +------------+---------------+---------------+------------+
                            v
    +----------------------+    +----------------------+    +----------------------+
    | api/                 |    | tests/               |    | portfolio/           |
    | FastAPI + OpenAPI    |    | pytest + smoke       |    | cockpit artifacts    |
    +----------+-----------+    +----------+-----------+    +----------+-----------+
                            \              |              /
                             \             |             /
                              \            v            /
                               +----------------------+
                               | downstream consumers |
                               | L2 GenAI / FDE       |
                               +----------------------+

                         [ Downtown LA = source of truth core ]

Key idea:
- raw -> scripts -> dbt -> api/tests -> portfolio consumers
- every neighborhood links back to a real repo artifact
- portfolio is the cockpit, not the pipeline

Proof files:
- README.md
- ROADMAP.md
- docs/contracts.md
- docs/dag.md
- data/quality/l1_checkpoint_report.json
- openapi_snapshot.json
