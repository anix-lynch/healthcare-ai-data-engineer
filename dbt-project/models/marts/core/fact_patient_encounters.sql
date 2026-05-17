WITH int_readmissions AS (
    SELECT *
    FROM {{ ref('int_readmissions') }}
),

dim_patient AS (
    SELECT *
    FROM {{ ref('dim_patient') }}
),

dim_date AS (
    SELECT *
    FROM {{ ref('dim_date') }}
),

dim_doctor AS (
    SELECT *
    FROM {{ ref('dim_doctor') }}
),

dim_hospital AS (
    SELECT *
    FROM {{ ref('dim_hospital') }}
),

dim_diagnosis AS (
    SELECT *
    FROM {{ ref('dim_diagnosis') }}
),

dim_medication AS (
    SELECT *
    FROM {{ ref('dim_medication') }}
),

dim_insurance AS (
    SELECT *
    FROM {{ ref('dim_insurance') }}
)

SELECT
    ir.encounter_id,
    dp.patient_key,
    dd_admission.date_day AS admission_date_key,
    dd_discharge.date_day AS discharge_date_key,
    ddoc.doctor_key,
    dh.hospital_key,
    ddi.diagnosis_key,
    dmed.medication_key,
    di.insurance_key,
    ir.billing_amount,
    ir.length_of_stay_days,
    ir.cost_per_day,
    ir.is_emergency,
    ir.is_readmission,
    ir.previous_admission_count,
    ir.age_group,
    ir.season,
    ir.room_number,
    CURRENT_TIMESTAMP AS created_at,
    CURRENT_TIMESTAMP AS updated_at
FROM int_readmissions ir
LEFT JOIN dim_patient dp
    ON ir.patient_name_hash = dp.patient_name_hash
LEFT JOIN dim_date dd_admission
    ON ir.admission_date = dd_admission.date_day
LEFT JOIN dim_date dd_discharge
    ON ir.discharge_date = dd_discharge.date_day
LEFT JOIN dim_doctor ddoc
    ON ir.doctor_name = ddoc.doctor_name
LEFT JOIN dim_hospital dh
    ON ir.hospital_name = dh.hospital_name
LEFT JOIN dim_diagnosis ddi
    ON ir.medical_condition = ddi.diagnosis_name
LEFT JOIN dim_medication dmed
    ON ir.medication = dmed.medication_name
LEFT JOIN dim_insurance di
    ON ir.insurance_provider = di.insurance_provider_name