-- Incremental staging (only new/changed rows; late/re-sent reports upserted).
{{ config(materialized='incremental', unique_key='safetyreportid',
          incremental_strategy='merge', on_schema_change='append_new_columns') }}
with src as (
    select
        safetyreportid,
        parse_date('%Y%m%d', cast(receivedate as string)) as received_date,
        cast(serious as string)                           as serious_flag,
        primary_drug, reactions, n_drugs, n_reactions, occurcountry,
        cast(ingest_ts as timestamp)                      as ingest_ts,
        row_hash
    from {{ source('openfda', 'raw_openfda_events') }}
    where safetyreportid is not null
)
select * from src
{% if is_incremental() %}
  where ingest_ts > (select coalesce(max(ingest_ts), timestamp('1970-01-01')) from {{ this }})
{% endif %}
