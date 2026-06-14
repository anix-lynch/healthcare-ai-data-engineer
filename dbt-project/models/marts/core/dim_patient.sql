-- Patient dimension: exactly one row per CANONICAL patient (patient_id), the
-- entity-resolution grain — case/spacing variants of the same name collapse to
-- one patient (55,500 encounters → 40,235 patients), matching the resolver
-- artifact byte-for-byte. Encounter-varying attributes (condition, insurance,
-- age) are collapsed to the most recent encounter so the dim key stays unique.
WITH ranked AS (
    SELECT
        patient_id,
        patient_name_hash,
        patient_name_cleaned,
        gender,
        age,
        blood_type,
        medical_condition,
        insurance_provider,
        ROW_NUMBER() OVER (
            PARTITION BY patient_id
            ORDER BY admission_date DESC
        ) AS rn
    FROM {{ ref('stg_healthcare') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['patient_id']) }} AS patient_key,
    patient_id,
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
