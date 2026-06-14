# B5 BigQuery Dataset

Purpose

This is the warehouse view for the question:
"What tables or queries actually exist?"

What it proves

- the repo has a named table inventory
- the model layers are queryable and documented
- the data product is not just an API shell
- this portfolio view is a storytelling layer over root dbt/checkpoint assets

Proof files

- [dbt-project/models/staging/sources.yml](../../dbt-project/models/staging/sources.yml)
- [dbt-project/models/intermediate/int_encounters_enriched.sql](../../dbt-project/models/intermediate/int_encounters_enriched.sql)
- [dbt-project/models/marts/core/fact_patient_encounters.sql](../../dbt-project/models/marts/core/fact_patient_encounters.sql)
- [dbt-project/models/marts/core/schema.yml](../../dbt-project/models/marts/core/schema.yml)
- [data/quality/l1_checkpoint_report.json](../../data/quality/l1_checkpoint_report.json)
- [openapi_snapshot.json](../../openapi_snapshot.json)
- [warehouse_room_payload.json](warehouse_room_payload.json)

Backend endpoint

- `/api/warehouse-room`
- `/api/portfolio/b5`

Final visual proof

- [screenshots/bigquery_tables.png](screenshots/bigquery_tables.png)

ASCII mockup

- [bigquery_dataset_ascii.md](bigquery_dataset_ascii.md)

Tree-compatible files

- [table_inventory.md](table_inventory.md)
- [sample_queries.sql](sample_queries.sql)
