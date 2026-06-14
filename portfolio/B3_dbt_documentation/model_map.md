# Model Map

This is the warehouse-facing inventory behind the A3 data model explorer.

## Staging

- `stg_healthcare`: source cleanup, type casting, and passthrough audit fields.

## Intermediate

- `int_encounters_enriched`: derived encounter fields and enrichment-ready shape.
- `int_readmissions`: readmission logic and encounter sequencing.

## Marts

- `fact_patient_encounters`: encounter grain fact table.
- `dim_patient`: patient grain dimension.
- `dim_doctor`: doctor grain dimension.
- `dim_hospital`: hospital grain dimension.
- `dim_diagnosis`: diagnosis dimension.
- `dim_medication`: medication dimension.
- `dim_insurance`: insurance dimension.
- `dim_date`: calendar dimension.

## Mart Catalog

- `canonical_patient_context`: one row per encounter for grounding.
- `retrieval_corpus_view`: source for retrieval and leak-safe indexing.
- `feature_view`: downstream features for prediction and analytics.
- `eval_holdout_view`: held-out rows reserved for evaluation.
- `audit_lineage_view`: provenance and freshness metadata.

## Proof

- [docs/dag.md](../../docs/dag.md)
- [dbt-project/models/](../../dbt-project/models/)
- [dbt-project/tests/](../../dbt-project/tests/)
