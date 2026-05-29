+----------------------------------------------------------+
| A3 DATA MODEL EXPLORER                                   |
| What can I use?                                          |
+----------------------------------------------------------+
| MART CATALOG                                             |
|  facts                                                   |
|   - fact_patient_encounters                              |
|                                                          |
|  dimensions                                              |
|   - dim_patient                                          |
|   - dim_doctor                                           |
|   - dim_hospital                                         |
|   - dim_diagnosis                                        |
|   - dim_medication                                       |
|   - dim_insurance                                        |
|   - dim_date                                             |
|                                                          |
|  contracts                                               |
|   - canonical_patient_context                            |
|   - retrieval_corpus_view                                |
|   - feature_view                                         |
|   - eval_holdout_view                                    |
|   - audit_lineage_view                                   |
|                                                          |
|  query mart examples                                     |
|   - SELECT * FROM fact_patient_encounters                |
|   - SELECT * FROM dim_patient                             |
|   - SELECT * FROM dim_hospital                            |
+----------------------------------------------------------+
