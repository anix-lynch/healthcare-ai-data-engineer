SELECT
    encounter_id
FROM {{ ref('fact_patient_encounters') }}
WHERE is_readmission = TRUE AND days_since_last_admission > 30