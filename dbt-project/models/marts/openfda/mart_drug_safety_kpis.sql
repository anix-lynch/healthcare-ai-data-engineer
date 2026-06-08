-- Business semantic mart, grain = one primary drug.
-- This is the analyst/BI "open the tap" surface for Bullet 3: every column is a
-- business-defined KPI, not a raw column. Power BI and the grounded AI read THIS,
-- not the star-schema internals. KPI definitions are documented in _semantic__marts.yml.
--
-- Volume KPIs are computed at REPORT grain (before the reaction explosion) and
-- reaction KPIs at the bridge grain, then joined — so a serious report with many
-- reactions is never double-counted (enforced by assert_openfda_kpi_bounds).
{{ config(materialized='table', cluster_by=['primary_drug']) }}

with report_kpis as (
    select
        primary_drug,
        count(distinct safetyreportid)                              as total_reports,
        countif(is_serious)                                         as serious_reports,
        safe_divide(countif(is_serious), count(distinct safetyreportid)) as serious_rate,
        count(distinct occurcountry)                                as countries_reporting,
        min(received_date)                                          as first_report_date,
        max(received_date)                                          as last_report_date,
        date_diff(max(received_date), min(received_date), day)      as reporting_window_days
    from {{ ref('fact_adverse_events') }}
    where primary_drug is not null
    group by primary_drug
),

reaction_kpis as (
    -- reaction events from the governed bridge, attributed to the report's primary drug
    select
        f.primary_drug,
        count(distinct b.reaction_id)                               as distinct_reactions,
        count(*)                                                    as total_reaction_events
    from {{ ref('bridge_report_reaction') }} b
    join {{ ref('fact_adverse_events') }} f using (safetyreportid)
    where f.primary_drug is not null
    group by f.primary_drug
)

select
    rk.primary_drug,
    rk.total_reports,
    rk.serious_reports,
    rk.serious_rate,
    coalesce(rx.distinct_reactions, 0)                              as distinct_reactions,
    coalesce(rx.total_reaction_events, 0)                           as total_reaction_events,
    safe_divide(rx.total_reaction_events, rk.total_reports)         as reactions_per_report,
    rk.countries_reporting,
    rk.first_report_date,
    rk.last_report_date,
    rk.reporting_window_days
from report_kpis rk
left join reaction_kpis rx using (primary_drug)
