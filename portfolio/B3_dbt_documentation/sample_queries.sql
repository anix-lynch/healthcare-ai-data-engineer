-- A3 mart explorer: three lineage-backed mart queries
-- lineage: stg_healthcare -> int_encounters_enriched -> fact_patient_encounters
SELECT
  encounter_id,
  patient_key,
  doctor_key,
  hospital_key,
  admission_date,
  discharge_date
FROM {{ ref('fact_patient_encounters') }}
LIMIT 20;

-- lineage: stg_healthcare -> dim_patient
SELECT
  patient_key,
  patient_age,
  patient_gender,
  patient_blood_type
FROM {{ ref('dim_patient') }}
LIMIT 20;

-- lineage: stg_healthcare -> dim_hospital
SELECT
  hospital_key,
  hospital_name,
  hospital_city,
  hospital_state
FROM {{ ref('dim_hospital') }}
LIMIT 20;
