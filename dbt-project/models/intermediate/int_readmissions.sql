WITH int_encounters_enriched AS (
    SELECT *
    FROM {{ ref('int_encounters_enriched') }}
)

SELECT
    *,
    -- days since this patient's previous admission (BigQuery DATE_DIFF: end, start, part)
    DATE_DIFF(
        admission_date,
        LAG(admission_date) OVER (PARTITION BY patient_name_hash ORDER BY admission_date),
        DAY
    ) AS days_since_last_admission,

    -- is_readmission: within 30 days of a prior admission (1/0)
    CASE
        WHEN DATE_DIFF(
                admission_date,
                LAG(admission_date) OVER (PARTITION BY patient_name_hash ORDER BY admission_date),
                DAY
             ) <= 30
        THEN 1 ELSE 0
    END AS is_readmission,

    -- previous_admission_count per patient
    ROW_NUMBER() OVER (PARTITION BY patient_name_hash ORDER BY admission_date) - 1 AS previous_admission_count
FROM int_encounters_enriched
