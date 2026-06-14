# Self-monitoring orchestration (Bullet 2)

> "พังต้องรู้ / ซ่อมได้ต้องซ่อม / ซ่อมไม่ได้ต้องเรียกคน" —
> when it breaks you must know; fix what's fixable; page a human for what isn't.

A real Apache Airflow DAG (`data_platform`) that is **self-monitoring, not
silent**. Every clause below is run-verified, not a comment.

```
 ingest_source_a ─┐
                  ├─► transform ─► freshness_sla ─► quality_gate ─┬─► publish    (all_success)
 ingest_source_b ─┘                                              └─► escalate   (one_failed)
```

| Clause | Mechanism | Verified |
|---|---|---|
| **parallel ingest** | two independent ingest tasks fan out; `transform` joins them | `proof_orchestration.json` → 18 rows from 2 sources |
| **sequential transform** | depends on both ingests | run log |
| **data-freshness SLA** | computes newest-record lag vs as-of; raises if > 24h | `freshness: lag 0.00h < 24h` |
| **ML anomaly auto-quarantine** | IsolationForest over numeric features; outliers split out before publish | caught `L1-100016` (age 920000, billing 4.2M, LOS 365) |
| **LLM-explained failure** | one Gemini (Vertex) call turns the quarantine into a plain-language on-call note | `llm_explanation_real.json` → `vertex:gemini-2.5-flash` |
| **bounded recovery** | `quality_gate` retries (`retries=2`); on final failure `escalate` pages a human | `UP_FOR_RETRY` → `escalation.json` |

The real Gemini explanation pinned the planted outlier exactly:

> "A data entry error or unit mismatch for the `age` field is the most likely
> cause, as `920000` is an implausibly high value… Manually review the source
> data for `encounter_id L1-100016`."

## Run

```bash
python3.12 -m venv .airflow-venv
.airflow-venv/bin/pip install "apache-airflow==2.10.3" scikit-learn pandas google-cloud-aiplatform \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.3/constraints-3.12.txt"

export AIRFLOW_HOME=$PWD/.airflow_home
export AIRFLOW__CORE__DAGS_FOLDER=$PWD/orchestration/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
.airflow-venv/bin/airflow db migrate

# happy path — anomaly quarantined, 17 clean rows published
.airflow-venv/bin/airflow dags test data_platform 2024-07-12

# failure branch — force the gate to fail → bounded retries → escalate pages a human
QUARANTINE_FAIL_RATE=0.02 .airflow-venv/bin/airflow dags test data_platform 2024-07-11
```

No Cloud Composer (cost) — the DAG runs anywhere Airflow runs; the locked
architecture serves it via Cloud Scheduler / Airflow for batch.
