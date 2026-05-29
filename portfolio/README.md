# Portfolio Cockpit

This folder is the human-eye layer for the repo.

Open these first:

1. [A1_executive_dashboard/README.md](A1_executive_dashboard/README.md)
1. [A2_trust_dashboard/README.md](A2_trust_dashboard/README.md)
1. [A3_dbt_documentation/README.md](A3_dbt_documentation/README.md)
1. [A4_airflow_dag/README.md](A4_airflow_dag/README.md)
1. [A5_bigquery_dataset/README.md](A5_bigquery_dataset/README.md)
1. [A6_architecture_diagram/README.md](A6_architecture_diagram/README.md)

What this layer does:

- turns backend proof into quick visual artifacts
- shows which file proves which claim
- keeps the repo honest about synthetic scope
- gives a hiring manager the 60-second path

Artifact legend:

- A1 Executive Dashboard: "Can we trust the hospital data today?"
- A2 Trust Dashboard: "Can we trust the patient and visit numbers?"
- A3 Data Model Explorer: "Where did this number come from?"
- A4 Airflow DAG: "Does the pipeline run every day?"
- A5 BigQuery Dataset: "What tables or queries actually exist?"
- A6 Architecture Diagram: "How does the whole machine connect?"

Machine-readable index:

- [manifest.json](manifest.json)
- [PROMPT_FOR_AGENT.md](PROMPT_FOR_AGENT.md)

The actual evidence stays in:

- [README.md](../README.md)
- [ROADMAP.md](../ROADMAP.md)
- [data/quality/l1_checkpoint_report.json](../data/quality/l1_checkpoint_report.json)
- [data/derived/patient_identity_map.json](../data/derived/patient_identity_map.json)
- [A1_executive_dashboard/control_room_payload.json](A1_executive_dashboard/control_room_payload.json)
- [dbt-project/](../dbt-project/)
- [docs/contracts.md](../docs/contracts.md)
- [docs/dag.md](../docs/dag.md)
- [openapi_snapshot.json](../openapi_snapshot.json)
- [.github/workflows/quality.yml](../.github/workflows/quality.yml)
