-- Reaction dimension — openFDA `reactions` is a real multi-valued list (";"-delimited,
-- n_reactions up to 15/report), so it genuinely normalizes. NOT a fabricated dimension.
{{ config(materialized='table') }}
with exploded as (
    select distinct trim(r) as reaction_name
    from {{ ref('fact_adverse_events') }}, unnest(split(reactions, ';')) as r
    where reactions is not null and trim(r) != ''
)
select to_hex(md5(reaction_name)) as reaction_id, reaction_name from exploded
