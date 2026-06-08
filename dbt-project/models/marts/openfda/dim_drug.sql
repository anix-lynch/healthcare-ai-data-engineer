-- Primary-drug dimension (single primary_drug per report → fact carries the FK).
{{ config(materialized='table') }}
select distinct to_hex(md5(primary_drug)) as drug_id, primary_drug as drug_name
from {{ ref('fact_adverse_events') }}
where primary_drug is not null
