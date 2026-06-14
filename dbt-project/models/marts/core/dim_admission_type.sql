WITH admissions AS (
    SELECT DISTINCT admission_type
    FROM {{ ref('int_encounters_enriched') }}
    WHERE admission_type IS NOT NULL
)

SELECT
    TO_HEX(SHA256(admission_type)) AS admission_type_key,
    admission_type
FROM admissions
