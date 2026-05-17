WITH source_data AS (
    -- Source: healthcare_dataset_enriched.csv (55,500 rows; 497 with enriched
    -- clinical narrative + vitals + labs + ESI ground-truth. Other rows have
    -- NULLs in the enriched columns.)
    -- Loaded via dbt seed command.
    SELECT
        -- Original 15 columns
        "Name" AS patient_name,
        "Date of Admission" AS date_of_admission,
        "Discharge Date" AS discharge_date,
        "Age" AS age,
        "Gender" AS gender,
        "Blood Type" AS blood_type,
        "Medical Condition" AS medical_condition,
        "Medication" AS medication,
        "Test Results" AS test_results,
        "Admission Type" AS admission_type,
        "Doctor" AS doctor,
        "Hospital" AS hospital,
        "Insurance Provider" AS insurance_provider,
        "Billing Amount" AS billing_amount,
        "Room Number" AS room_number,
        "Date of Admission" AS admission_date_raw,

        -- Enriched columns (LLM-generated, NULL for non-enriched rows)
        "chief_complaint" AS chief_complaint,
        "hpi" AS hpi,
        "physician_note" AS physician_note,
        "bp_systolic" AS bp_systolic,
        "bp_diastolic" AS bp_diastolic,
        "heart_rate" AS heart_rate,
        "respiratory_rate" AS respiratory_rate,
        "temperature_f" AS temperature_f,
        "spo2_pct" AS spo2_pct,
        "lab_panel_json" AS lab_panel_json,
        "lab_flags" AS lab_flags,
        "esi_tier_truth" AS esi_tier_truth,
        "acuity_red_flags" AS acuity_red_flags,
        "case_type" AS case_type,
        "scenario_hint" AS scenario_hint,
        "holdout" AS holdout
    FROM {{ source('healthcare', 'raw_healthcare_data') }}
)

SELECT
    -- Generate surrogate key for encounter
    {{ dbt_utils.generate_surrogate_key(['patient_name', 'date_of_admission']) }} AS encounter_id,
    
    -- Hash PII for patient name (using SQL Server HASHBYTES)
    CONVERT(VARCHAR(64), HASHBYTES('SHA2_256', patient_name), 2) AS patient_name_hash,

    -- Clean column names and type cast dates
    REPLACE(LOWER(patient_name), ' ', '_') AS patient_name_cleaned,
    CAST(date_of_admission AS DATE) AS admission_date,
    CAST(discharge_date AS DATE) AS discharge_date,
    age,
    gender,
    REPLACE(LOWER(blood_type), ' ', '_') AS blood_type,
    REPLACE(LOWER(medical_condition), ' ', '_') AS medical_condition,
    REPLACE(LOWER(medication), ' ', '_') AS medication,
    REPLACE(LOWER(test_results), ' ', '_') AS test_results,
    REPLACE(LOWER(admission_type), ' ', '_') AS admission_type,
    REPLACE(LOWER(doctor), ' ', '_') AS doctor_name,
    REPLACE(LOWER(hospital), ' ', '_') AS hospital_name,
    REPLACE(LOWER(insurance_provider), ' ', '_') AS insurance_provider,
    billing_amount,
    room_number,

    -- Pass-through of enriched columns (NULL-safe — downstream marts decide
    -- whether to filter to enriched-only via WHERE chief_complaint IS NOT NULL)
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
    case_type,
    scenario_hint,
    holdout
FROM source_data