# A3 Data Model Explorer

Purpose

This is the lineage view for the question:
"Where did this number come from?"

What it proves

- the mart catalog is easy to inspect
- lineage is explicit from raw to staging to facts/dims to marts
- contracts and query surfaces are published for consumers

Proof files

- [docs/dag.md](../../docs/dag.md)
- [dbt-project/dbt_project.yml](../../dbt-project/dbt_project.yml)
- [dbt-project/models/staging/sources.yml](../../dbt-project/models/staging/sources.yml)
- [dbt-project/models/marts/core/schema.yml](../../dbt-project/models/marts/core/schema.yml)
- [dbt-project/tests/assert_valid_readmission_logic.sql](../../dbt-project/tests/assert_valid_readmission_logic.sql)
- [sample_queries.sql](sample_queries.sql)

Final visual proof

- [screenshots/mart_catalog.png](screenshots/mart_catalog.png)

ASCII mockups

- [mart_catalog_ascii.md](mart_catalog_ascii.md)
- [lineage_ascii.md](lineage_ascii.md)

Tree-compatible files

- [model_map.md](model_map.md)
