-- Business semantic mart, grain = one reaction (MedDRA preferred-term level).
-- Powers "which adverse reactions are most reported / most serious" — the signal
-- view the Signal Platform (Bullet 5) and Power BI both consume. KPI definitions in
-- _semantic__marts.yml. A lightweight disproportionality proxy (report_share) is
-- included; it is NOT a validated PRR/ROR — labeled honestly as a screening proxy.
{{ config(materialized='table', cluster_by=['reaction_name']) }}

with bridged as (
    select b.reaction_id, b.safetyreportid, f.is_serious, f.primary_drug
    from {{ ref('bridge_report_reaction') }} b
    join {{ ref('fact_adverse_events') }} f using (safetyreportid)
),

total_reports as (
    select count(distinct safetyreportid) as n from {{ ref('fact_adverse_events') }}
)

select
    d.reaction_name,

    -- volume KPIs
    count(distinct b.safetyreportid)                               as reports_with_reaction,
    countif(b.is_serious)                                          as serious_reports_with_reaction,
    safe_divide(countif(b.is_serious), count(distinct b.safetyreportid)) as serious_share,

    -- breadth KPI: how many distinct drugs implicate this reaction
    count(distinct b.primary_drug)                                as distinct_drugs,

    -- screening proxy KPI (NOT validated PRR/ROR): this reaction's share of all reports
    safe_divide(count(distinct b.safetyreportid), max(t.n))       as report_share

from bridged b
join {{ ref('dim_reaction') }} d using (reaction_id)
cross join total_reports t
group by d.reaction_name
