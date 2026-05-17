WITH int_encounters_enriched AS (
    SELECT *
    FROM {{ ref('int_encounters_enriched') }}
)

SELECT
    *,
    -- Calculate days_since_last_admission
    DATEDIFF(day, LAG(admission_date) OVER (PARTITION BY patient_name_hash ORDER BY admission_date), admission_date) AS days_since_last_admission,
    
    -- Flag is_readmission
    CASE
        WHEN DATEDIFF(day, LAG(admission_date) OVER (PARTITION BY patient_name_hash ORDER BY admission_date), admission_date) <= 30 THEN CAST(1 AS BIT)
        ELSE CAST(0 AS BIT)
    END AS is_readmission,
    
    -- Calculate previous_admission_count per patient
    ROW_NUMBER() OVER (PARTITION BY patient_name_hash ORDER BY admission_date) - 1 AS previous_admission_count
FROM int_encounters_enriched