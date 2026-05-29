-- Proof queries aligned to real dbt core models in this repo.
-- A5 portfolio panel should point to these instead of synthetic placeholders.

select
  medical_condition,
  count(*) as encounters
from fact_patient_encounters
group by 1
order by encounters desc;

select
  patient_id,
  count(*) as encounter_count
from dim_patient
group by 1
order by encounter_count desc
limit 10;

select
  admission_type,
  avg(length_of_stay_days) as avg_los
from fact_patient_encounters
group by 1
order by avg_los desc;
