SELECT
    encounter_id
FROM {{ ref('fact_patient_encounters') }}
-- is_readmission is INT 1/0 (consistent with accepted_values [0,1] + SUM-able)
WHERE is_readmission = 1 AND days_since_last_admission > 30