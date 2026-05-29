WITH stg_healthcare AS (
    SELECT *
    FROM {{ ref('stg_healthcare') }}
)

SELECT
    *,
    -- length_of_stay_days (BigQuery DATE_DIFF: end, start, part)
    DATE_DIFF(discharge_date, admission_date, DAY) AS length_of_stay_days,

    -- cost_per_day
    CASE
        WHEN DATE_DIFF(discharge_date, admission_date, DAY) > 0
        THEN billing_amount / DATE_DIFF(discharge_date, admission_date, DAY)
        ELSE billing_amount  -- 0-day stays: bill counts as one day
    END AS cost_per_day,

    -- is_emergency flag (1/0)
    CASE WHEN admission_type = 'emergency' THEN 1 ELSE 0 END AS is_emergency,

    -- age_group
    CASE
        WHEN age BETWEEN 0 AND 17 THEN '0-17'
        WHEN age BETWEEN 18 AND 30 THEN '18-30'
        WHEN age BETWEEN 31 AND 50 THEN '31-50'
        WHEN age BETWEEN 51 AND 70 THEN '51-70'
        ELSE '70+'
    END AS age_group,

    -- season from admission month
    CASE
        WHEN EXTRACT(MONTH FROM admission_date) BETWEEN 3 AND 5  THEN 'spring'
        WHEN EXTRACT(MONTH FROM admission_date) BETWEEN 6 AND 8  THEN 'summer'
        WHEN EXTRACT(MONTH FROM admission_date) BETWEEN 9 AND 11 THEN 'autumn'
        ELSE 'winter'
    END AS season
FROM stg_healthcare
