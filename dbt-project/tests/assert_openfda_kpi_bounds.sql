-- KPI contract proof: rate KPIs must be bounded [0,1] and volume KPIs non-negative.
-- Returns offending rows; dbt test passes only when zero rows come back.
select 'drug serious_rate out of [0,1]' as violation, primary_drug as key
from {{ ref('mart_drug_safety_kpis') }}
where serious_rate < 0 or serious_rate > 1

union all
select 'drug serious_reports > total_reports', primary_drug
from {{ ref('mart_drug_safety_kpis') }}
where serious_reports > total_reports

union all
select 'reaction serious_share out of [0,1]', reaction_name
from {{ ref('mart_reaction_signals') }}
where serious_share < 0 or serious_share > 1

union all
select 'reaction report_share out of [0,1]', reaction_name
from {{ ref('mart_reaction_signals') }}
where report_share < 0 or report_share > 1
