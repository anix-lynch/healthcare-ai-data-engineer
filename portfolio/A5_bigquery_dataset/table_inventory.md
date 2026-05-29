# Table Inventory

This is the warehouse-shaped inventory for the repo's marts.

| Table | Grain | Role |
| --- | --- | --- |
| `stg_healthcare` | source row | staging cleanup and casting |
| `int_encounters_enriched` | encounter row | derived encounter features |
| `int_readmissions` | encounter row | readmission sequencing |
| `fact_patient_encounters` | encounter row | central fact table |
| `dim_patient` | patient row | identity and demographics |
| `dim_doctor` | doctor row | provider lookup |
| `dim_hospital` | hospital row | facility lookup |
| `dim_diagnosis` | diagnosis row | condition dimension |
| `dim_medication` | medication row | medication dimension |
| `dim_insurance` | insurance row | payer dimension |
| `dim_date` | date row | calendar dimension |

Proof:

- [dbt-project/models/](../../dbt-project/models/)
- [docs/dag.md](../../docs/dag.md)
