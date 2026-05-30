# L1.25 — Feature Store (Feast on BigQuery)

The **machine-ready feature layer** that sits between the L1 gold marts and the
L1.5 signal layer.

```
L1  Trust Engine      dbt → BigQuery gold marts          fact_patient_encounters, dim_patient
        │             (55 tests green, the truth)
        ▼
L1.25  Feature layer  Feast on BigQuery  ◄── YOU ARE HERE
        │             point-in-time-correct features,
        │             one definition reused offline (train) + online (serve)
        ▼
L1.5  Signal layer    anomaly / cluster / classify       consumes the FeatureService
```

## What this is

A real Feast feature store whose **offline store is BigQuery**
(project `bchan-genai-lab`, dataset `healthcare_analytics`) and whose **online
store** is a local SQLite file. It registers:

| Object | Name | Notes |
|---|---|---|
| Entity | `patient` | join key `patient_key` (gold `dim_patient` surrogate key) |
| FeatureView | `patient_encounter_features` | 6 features, PIT-correct |
| FeatureService | `high_utilizer_signal_features` | the bundle L1.5 requests |

### Features (all point-in-time correct)

| Feature | Source | PIT guarantee |
|---|---|---|
| `prior_encounter_count` | `previous_admission_count` (gold) | counts admissions strictly **before** this encounter |
| `days_since_last_admission` | gold mart | gap to previous admission |
| `prior_avg_los` | window over `length_of_stay_days` | `ROWS UNBOUNDED PRECEDING .. 1 PRECEDING` → excludes current row |
| `los_days` | this encounter | row-level fact |
| `is_emergency` | this encounter | row-level fact |
| `is_readmission` | this encounter | row-level fact |

The offline source is a **query against the L1 gold fact** `fact_patient_encounters`
that emits a real *event* timestamp (`TIMESTAMP(admission_date_key)`). Every
aggregate looks only at rows strictly before that timestamp, so a Feast
point-in-time join (`get_historical_features`) does **not** leak the future.
No extra table/view is created — Feast reads the query at retrieval time, so
read-only access to the dataset is sufficient for `apply`.

## How it was built (real, reproducible)

```bash
python3 -m venv .feast-venv          # venv lives at repo root, NOT inside
.feast-venv/bin/pip install 'feast[gcp]'   # gcp extra = BigQuery offline store
cd feature-store
GOOGLE_CLOUD_PROJECT=bchan-genai-lab ../.feast-venv/bin/feast apply
```

### `feast apply` output (captured)

```
No project found in the repository. Using project name healthcare_l125 defined in feature_store.yaml
Applying changes for project healthcare_l125
Deploying infrastructure for patient_encounter_features
```

Registry artifacts written: `registry.db` (5130 bytes), `online_store.db`.

```
$ feast feature-views list
NAME                        ENTITIES     TYPE
patient_encounter_features  {'patient'}  FeatureView

$ feast entities list
NAME     DESCRIPTION                                                TYPE
patient  A de-identified patient (gold dim_patient surrogate key).  ValueType.STRING

$ feast feature-services list
NAME                           FEATURES
high_utilizer_signal_features  patient_encounter_features:prior_encounter_count, ... (6 features)
```

## Honest scope note

`feast apply` (the deliverable: register feature definitions) ran **clean** with
read-only access — it only writes the local registry, never queries BigQuery.

A live offline retrieval (`get_historical_features`) additionally needs
`bigquery.dataEditor` on the dataset, because Feast uploads the entity spine to a
**temp join table** in BigQuery to run the point-in-time join. The runtime
deploy SA (`bchan-genai-deploy`) is read-only on `healthcare_analytics`, so the
live join is a one-line local step for the dataset owner:

```bash
gcloud auth application-default login   # as alynch@gozeroshot.dev (dataset OWNER)
```

This is **not** required for the apply/registry deliverable above.
