# Looker Studio — the L1 BI face

## 🖱️ ONE-CLICK START (BigQuery source pre-loaded)

Click this — it opens a new Looker Studio report with the gold fact table already
wired as the data source (no manual connector steps), signed in as the Google
account you're using in the browser:

**[▶︎ Open Looker Studio with fact_patient_encounters pre-loaded](https://lookerstudio.google.com/reporting/create?c.reportId=&ds.ds0.connector=bigQuery&ds.ds0.type=TABLE&ds.ds0.projectId=bchan-genai-lab&ds.ds0.datasetId=healthcare_analytics&ds.ds0.tableId=fact_patient_encounters)**

(blend in `dim_patient` on `patient_key` once inside if you want patient attributes).
After it opens, drop the 6 charts in the spec below → publish → copy the share URL.
That's the whole b-turn, ~3 min. Everything else (the data) is done.

---

The L1 gold marts already live in BigQuery and are **query-ready**. Looker Studio
report creation is **browser-only** (no good CLI / API for building a report), so
this file is the exact click-path.

## Status: data is ready (proof)

`bq` against the deploy SA (read-only) returns clean rows from the gold fact:

```
$ bq query 'SELECT COUNT(*) encounters, COUNT(DISTINCT patient_key) patients,
            ROUND(AVG(length_of_stay_days),1) avg_los, SUM(is_emergency) emergencies
            FROM `bchan-genai-lab.healthcare_analytics.fact_patient_encounters`'

 encounters | patients | avg_los | emergencies
      50000 |    49992 |    15.5 |       16389
```

### Connect Looker directly to the gold mart

Point the BigQuery connector straight at the existing gold view — **no new view
needed**. (A dedicated dashboard view was optional; creating one is blocked
because the runtime deploy SA is read-only on the dataset, and the human owner
token needs a browser reauth. The existing marts are clean enough to dashboard
as-is.)

Recommended source tables (all in `bchan-genai-lab.healthcare_analytics`):

| Table / view | Use |
|---|---|
| `fact_patient_encounters` | primary fact — LOS, billing, emergency, readmission, age_group, season |
| `dim_patient` | patient attributes — gender, age, medical_condition, insurance_provider |
| `feature_patient_pit` *(if owner creates it later)* | optional PIT feature view (see `feature-store/README.md`) |

## Exact click-path (~5 min)

1. Go to **https://lookerstudio.google.com** → sign in as **alynch@gozeroshot.dev**.
2. Top-left **Create** → **Report**.
3. In *Add data to report* → choose the **BigQuery** connector.
4. **MY PROJECTS** → project **`bchan-genai-lab`** → dataset **`healthcare_analytics`**
   → table **`fact_patient_encounters`** → **Add**.
5. (Optional join) **Add data** again → same dataset → **`dim_patient`**, then
   **Resource → Manage blends** → blend on `patient_key` to bring in
   `medical_condition`, `gender`, `insurance_provider`.

### Charts to drop in

| Chart | Type | Dimension | Metric |
|---|---|---|---|
| Scorecards (top row) | Scorecard | — | `Record Count` (encounters), `COUNT_DISTINCT patient_key`, `AVG length_of_stay_days`, `SUM is_emergency` |
| LOS by condition | Bar | `medical_condition` (blended) | `AVG length_of_stay_days` |
| Admissions over time | Time series | `admission_date_key` | `Record Count` |
| Emergency mix | Pie / Donut | `is_emergency` | `Record Count` |
| Billing by insurance | Bar | `insurance_provider` (blended) | `SUM billing_amount` |
| Age-group heat | Table w/ heatmap | `age_group` | `AVG length_of_stay_days`, `Record Count` |

6. **Share** (top-right) → set link access for the audience → copy the report URL.

That URL is the **L1 dashboard** face — the human-readable view of the same gold
marts the L1.25 Feast layer and L1.5 signals consume.
