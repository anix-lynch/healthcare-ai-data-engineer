SELECT
    encounter_id
FROM {{ ref('fact_patient_encounters') }}
WHERE length_of_stay_days < 0