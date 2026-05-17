SELECT
    encounter_id
FROM {{ ref('fact_patient_encounters') }}
WHERE discharge_date_key < admission_date_key