# A4 Airflow DAG

Purpose

This is the runtime flow view for the question:
"What runs first? What depends on what? What breaks downstream?"

What it proves

- freshness: data arrives and refreshes on schedule
- reliability: tasks run in dependency order
- recovery: failed jobs retry or block publish safely
- blast radius: you know what breaks downstream

Proof files

- [data/raw/](../../data/raw/)
- [scripts/enrich_parallel.py](../../scripts/enrich_parallel.py)
- [scripts/patient_identity.py](../../scripts/patient_identity.py)
- [scripts/checkpoint.py](../../scripts/checkpoint.py)
- [dbt-project/](../../dbt-project/)
- [api/app/main.py](../../api/app/main.py)
- [.github/workflows/quality.yml](../../.github/workflows/quality.yml)
- [demo/quickstart.sh](../../demo/quickstart.sh)
- [Makefile](../../Makefile)

Final visual proof

- [screenshots/airflow_dag.png](screenshots/airflow_dag.png)

ASCII mockup

- [dag_ascii.md](dag_ascii.md)

Tree-compatible files

- [runbook.md](runbook.md)
