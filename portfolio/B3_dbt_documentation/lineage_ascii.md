+----------------------------------------------------------+
| A3 DATA MODEL EXPLORER                                   |
| Where did this number come from?                         |
+----------------------------------------------------------+
| raw                                                      |
|  raw healthcare CSV                                      |
|        |                                                 |
|        v                                                 |
| staging                                                  |
|  stg_healthcare                                          |
|        |                                                 |
|        v                                                 |
| facts + dims                                             |
|  int_encounters_enriched                                 |
|  int_readmissions                                        |
|  dim_patient                                             |
|  dim_doctor                                              |
|  dim_hospital                                            |
|  dim_diagnosis                                           |
|  dim_medication                                          |
|  dim_insurance                                           |
|  dim_date                                                |
|  fact_patient_encounters                                 |
+----------------------------------------------------------+
