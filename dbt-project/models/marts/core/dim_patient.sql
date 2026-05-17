WITH stg_healthcare AS (
    SELECT DISTINCT
        patient_name_hash,
        patient_name_cleaned,
        gender,
        age,
        blood_type,
        medical_condition,
        insurance_provider
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
FROM stg_healthcare