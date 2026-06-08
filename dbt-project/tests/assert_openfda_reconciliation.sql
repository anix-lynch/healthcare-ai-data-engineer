-- Reconciliation (Trust): no report dropped/duplicated between stage and fact.
with staged as (select count(distinct safetyreportid) n from {{ ref('stg_openfda_events') }}),
     fact   as (select count(*) n, count(distinct safetyreportid) d from {{ ref('fact_adverse_events') }})
select 'reconciliation_mismatch' as failure
from staged, fact
where staged.n != fact.n or fact.n != fact.d
