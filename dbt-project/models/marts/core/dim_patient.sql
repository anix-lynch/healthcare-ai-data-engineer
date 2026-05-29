-- Patient dimension: exactly one row per patient (patient_name_hash).
-- Encounter-varying attributes (medical_condition, insurance, age) are
-- collapsed to the most recent encounter so the dim key stays unique.
WITH ranked AS (
    SELECT
        patient_name_hash,
        patient_name_cleaned,
        gender,
        age,
        blood_type,
        medical_condition,
        insurance_provider,
        ROW_NUMBER() OVER (
            PARTITION BY patient_name_hash
            ORDER BY admission_date DESC
        ) AS rn
    FROM {{ ref('stg_healthcare') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['patient_name_hash']) }} AS patient_key,
    patient_name_hash,
    patient_name_cleaned,
    gender,
    age,
    blood_type,
    medical_condition,
    insurance_provider,
    CURRENT_TIMESTAMP AS created_at,
    CURRENT_TIMESTAMP AS updated_at
FROM ranked
WHERE rn = 1
