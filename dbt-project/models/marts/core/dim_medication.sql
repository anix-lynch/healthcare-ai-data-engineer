WITH int_encounters_enriched AS (
    SELECT DISTINCT medication
    FROM {{ ref('int_encounters_enriched') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['medication']) }} AS medication_key,
    medication AS medication_name,
    CURRENT_TIMESTAMP AS created_at,
    CURRENT_TIMESTAMP AS updated_at
FROM int_encounters_enriched