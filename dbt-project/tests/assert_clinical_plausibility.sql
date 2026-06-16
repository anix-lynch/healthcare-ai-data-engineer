-- Gate 3: hard-block semantically implausible age × medication (e.g. toddler + Lipitor/Viagra).
-- hard_min_age=18 from data/quality/clinical_plausibility.yaml
SELECT
    encounter_id,
    age,
    medication
FROM {{ ref('stg_healthcare') }}
WHERE age < 18
  AND LOWER(REPLACE(medication, ' ', '_')) IN (
    'lipitor', 'atorvastatin', 'viagra', 'sildenafil', 'cialis', 'tadalafil'
  )
