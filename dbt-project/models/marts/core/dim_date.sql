{{ config(materialized='table') }}

-- Generate date dimension from 2019-01-01 to 2025-12-31
-- Using a cross join approach compatible with Fabric Warehouse
WITH numbers AS (
    SELECT ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
    FROM (VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) AS t1(n)
    CROSS JOIN (VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) AS t2(n)
    CROSS JOIN (VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) AS t3(n)
    CROSS JOIN (VALUES (0),(1),(2),(3),(4),(5),(6),(7),(8),(9)) AS t4(n)
)
SELECT TOP 2556
    DATEADD(day, n, CAST('2019-01-01' AS DATE)) AS date_day
FROM numbers
WHERE DATEADD(day, n, CAST('2019-01-01' AS DATE)) <= CAST('2025-12-31' AS DATE)
ORDER BY date_day
