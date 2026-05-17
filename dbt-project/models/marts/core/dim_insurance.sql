WITH int_encounters_enriched AS (
    SELECT DISTINCT insurance_provider
    FROM {{ ref('int_encounters_enriched') }}
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['insurance_provider']) }} AS insurance_key,
    insurance_provider AS insurance_provider_name,
    CURRENT_TIMESTAMP AS created_at,
    CURRENT_TIMESTAMP AS updated_at
FROM int_encounters_enriched