-- Many-to-many bridge: one report ↔ many reactions. Every row MUST have a parent in
-- fact_adverse_events AND in dim_reaction → enforced by relationships tests (referential integrity).
{{ config(materialized='table') }}
select distinct
    f.safetyreportid,
    to_hex(md5(trim(r))) as reaction_id
from {{ ref('fact_adverse_events') }} f, unnest(split(f.reactions, ';')) as r
where f.reactions is not null and trim(r) != ''
