WITH int_encounters_enriched AS (
    SELECT DISTINCT doctor_name
    FROM {{ ref('int_encounters_enriched') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['doctor_name']) }} AS doctor_key,
    doctor_name,
    CURRENT_TIMESTAMP AS created_at,
    CURRENT_TIMESTAMP AS updated_at
FROM int_encounters_enriched