-- Star-schema fact, grain = one adverse-event report.
{{ config(materialized='table') }}
select
    safetyreportid, received_date, primary_drug,
    case when serious_flag = '1' then true else false end as is_serious,
    n_drugs, n_reactions, reactions, occurcountry, ingest_ts
from {{ ref('stg_openfda_events') }}
