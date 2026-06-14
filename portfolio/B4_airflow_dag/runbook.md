# Runbook

If the pipeline is broken:

1. Check [data/quality/l1_checkpoint_report.json](../../data/quality/l1_checkpoint_report.json).
2. Re-run [scripts/checkpoint.py](../../scripts/checkpoint.py).
3. Inspect [.github/workflows/quality.yml](../../.github/workflows/quality.yml).
4. Verify the DBT models in [dbt-project/models/](../../dbt-project/models/).
5. Confirm the API surface still matches [openapi_snapshot.json](../../openapi_snapshot.json).

This repo does not expose a live Airflow deployment. The DAG here is the
execution shape, not a claim of production orchestration.
