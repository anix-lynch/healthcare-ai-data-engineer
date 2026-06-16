-- Staging: clean + standardize the raw healthcare load.
-- ADAPTER: BigQuery (Standard SQL). Raw table is loaded by
-- scripts/load_bigquery.py with snake_case columns; dates arrive as DATE.
WITH source_data AS (
    SELECT
        name                AS patient_name,
        date_of_admission,
        discharge_date,
        age,
        gender,
        blood_type,
        medical_condition,
        medication,
        test_results,
        admission_type,
        doctor,
        hospital,
        insurance_provider,
        billing_amount,
        room_number,

        -- Enriched columns (LLM-generated; NULL for non-enriched rows)
        chief_complaint,
        hpi,
        physician_note,
        bp_systolic,
        bp_diastolic,
        heart_rate,
        respiratory_rate,
        temperature_f,
        spo2_pct,
        lab_panel_json,
        lab_flags,
        esi_tier_truth,
        acuity_red_flags,
        holdout
    FROM {{ source('healthcare', 'raw_healthcare_data') }}
)

SELECT
    -- Surrogate key for the encounter
    {{ dbt_utils.generate_surrogate_key(['patient_name', 'date_of_admission']) }} AS encounter_id,

    -- Hash PII for patient name (BigQuery: TO_HEX(SHA256(...)))
    TO_HEX(SHA256(patient_name)) AS patient_name_hash,

    -- Canonical patient identity — collapses case/spacing variants of the SAME
    -- name into one patient, byte-for-byte identical to scripts/patient_identity.py
    -- (`P-` + first 10 hex of SHA256 of the lower-cased, space-normalized name).
    -- Entity resolver in SQL: encounters → canonical patients (matches patient_identity.py).
    CONCAT('P-', SUBSTR(TO_HEX(SHA256(REPLACE(REPLACE(LOWER(patient_name), ' ', '_'), '_', ' '))), 1, 10)) AS patient_id,

    -- Clean column values
    REPLACE(LOWER(patient_name), ' ', '_')        AS patient_name_cleaned,
    date_of_admission                              AS admission_date,
    discharge_date                                 AS discharge_date,
    age,
    gender,
    REPLACE(LOWER(blood_type), ' ', '_')          AS blood_type,
    REPLACE(LOWER(medical_condition), ' ', '_')   AS medical_condition,
    REPLACE(LOWER(medication), ' ', '_')          AS medication,
    REPLACE(LOWER(test_results), ' ', '_')        AS test_results,
    REPLACE(LOWER(admission_type), ' ', '_')      AS admission_type,
    REPLACE(LOWER(doctor), ' ', '_')              AS doctor_name,
    REPLACE(LOWER(hospital), ' ', '_')            AS hospital_name,
    REPLACE(LOWER(insurance_provider), ' ', '_')  AS insurance_provider,
    billing_amount,
    room_number,

    -- Enriched pass-through (NULL-safe; marts filter to enriched-only as needed)
    chief_complaint,
    hpi,
    physician_note,
    bp_systolic,
    bp_diastolic,
    heart_rate,
    respiratory_rate,
    temperature_f,
    spo2_pct,
    lab_panel_json,
    lab_flags,
    esi_tier_truth,
    acuity_red_flags,
    holdout
FROM source_data
-- Encounter grain = one row per (patient, admission date). Bulk load quarantines
-- exact duplicates before landing; QUALIFY keeps the richest row if any slip through.
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY patient_name, date_of_admission
    ORDER BY discharge_date DESC, chief_complaint
) = 1
