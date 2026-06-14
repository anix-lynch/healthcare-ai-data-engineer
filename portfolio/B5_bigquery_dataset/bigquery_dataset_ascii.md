+----------------------------------------------------------+
| A5 BIGQUERY DATASET                                      |
| What tables or queries actually exist?                   |
+----------------------------------------------------------+
| staging                                                  |
|  stg_healthcare                                          |
|                                                          |
| intermediate                                             |
|  int_encounters_enriched                                 |
|  int_readmissions                                        |
|                                                          |
| gold marts                                               |
|  dim_patient                                             |
|  dim_doctor                                              |
|  dim_hospital                                            |
|  dim_diagnosis                                           |
|  dim_medication                                          |
|  dim_insurance                                           |
|  dim_date                                                |
|  fact_patient_encounters                                 |
+----------------------------------------------------------+
| Proof files                                              |
| - dbt-project/models/*                                   |
| - openapi_snapshot.json                                  |
| - api/app/main.py                                        |
+----------------------------------------------------------+
