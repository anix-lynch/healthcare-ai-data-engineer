# Portfolio Cockpit

This folder is the human-eye layer for the repo.

Open these first:

1. [B1_executive_dashboard/README.md](B1_executive_dashboard/README.md)
1. [B2_trust_dashboard/README.md](B2_trust_dashboard/README.md)
1. [B3_dbt_documentation/README.md](B3_dbt_documentation/README.md)
1. [B4_airflow_dag/README.md](B4_airflow_dag/README.md)
1. [B5_bigquery_dataset/README.md](B5_bigquery_dataset/README.md)
1. [B6_architecture_diagram/README.md](B6_architecture_diagram/README.md)

What this layer does:

- turns backend proof into quick visual artifacts
- shows which file proves which claim
- keeps the repo honest about synthetic scope
- gives a hiring manager the 60-second path

Artifact legend:

- B1 Executive Dashboard: "Can we trust the hospital data today?"
- B2 Trust Dashboard: "Can we trust the patient and visit numbers?"
- B3 Data Model Explorer: "Where did this number come from?"
- B4 Airflow DAG: "Does the pipeline run every day?"
- B5 BigQuery Dataset: "What tables or queries actually exist?"
- B6 Architecture Diagram: "How does the whole machine connect?"

Machine-readable index:

- [manifest.json](manifest.json)
- [PROMPT_FOR_AGENT.md](PROMPT_FOR_AGENT.md)

The actual evidence stays in:

- [README.md](../README.md)
- [ROADMAP.md](../ROADMAP.md)
- [data/quality/l1_checkpoint_report.json](../data/quality/l1_checkpoint_report.json)
- [data/derived/patient_identity_map.json](../data/derived/patient_identity_map.json)
- [B1_executive_dashboard/control_room_payload.json](B1_executive_dashboard/control_room_payload.json)
- [dbt-project/](../dbt-project/)
- [docs/contracts.md](../docs/contracts.md)
- [docs/dag.md](../docs/dag.md)
- [openapi_snapshot.json](../openapi_snapshot.json)
- [.github/workflows/quality.yml](../.github/workflows/quality.yml)
