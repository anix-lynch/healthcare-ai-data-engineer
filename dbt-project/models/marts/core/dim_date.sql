{{ config(materialized='table') }}

-- Date dimension 2019-01-01 → 2025-12-31 (BigQuery GENERATE_DATE_ARRAY)
SELECT
    date_day,
    EXTRACT(YEAR    FROM date_day) AS year,
    EXTRACT(MONTH   FROM date_day) AS month,
    EXTRACT(DAY     FROM date_day) AS day,
    EXTRACT(QUARTER FROM date_day) AS quarter,
    FORMAT_DATE('%A', date_day)    AS day_name,
    EXTRACT(DAYOFWEEK FROM date_day) IN (1, 7) AS is_weekend
FROM UNNEST(GENERATE_DATE_ARRAY(DATE '2019-01-01', DATE '2025-12-31')) AS date_day
ORDER BY date_day
