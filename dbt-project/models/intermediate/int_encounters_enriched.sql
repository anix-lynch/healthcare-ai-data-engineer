WITH stg_healthcare AS (
    SELECT *
    FROM {{ ref('stg_healthcare') }}
)

SELECT
    *,
    -- Calculate length_of_stay_days
    DATEDIFF(day, admission_date, discharge_date) AS length_of_stay_days,
    
    -- Calculate cost_per_day
    CASE
        WHEN DATEDIFF(day, admission_date, discharge_date) > 0
        THEN billing_amount / DATEDIFF(day, admission_date, discharge_date)
        ELSE billing_amount -- Or 0, depending on business rule for 0-day stays
    END AS cost_per_day,
    
    -- Flag is_emergency
    CASE
        WHEN admission_type = 'emergency' THEN CAST(1 AS BIT)
        ELSE CAST(0 AS BIT)
    END AS is_emergency,
    
    -- Derive age_group
    CASE
        WHEN age BETWEEN 0 AND 17 THEN '0-17'
        WHEN age BETWEEN 18 AND 30 THEN '18-30'
        WHEN age BETWEEN 31 AND 50 THEN '31-50'
        WHEN age BETWEEN 51 AND 70 THEN '51-70'
        ELSE '70+'
    END AS age_group,
    
    -- Derive season from admission date
    CASE
        WHEN MONTH(admission_date) BETWEEN 3 AND 5 THEN 'spring'
        WHEN MONTH(admission_date) BETWEEN 6 AND 8 THEN 'summer'
        WHEN MONTH(admission_date) BETWEEN 9 AND 11 THEN 'autumn'
        ELSE 'winter'
    END AS season
FROM stg_healthcare