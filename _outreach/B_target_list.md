# B — Target Company List (Plan-A: mid AI Data Engineer · healthcare-first, AI-data-second)

> **Filter criteria:**
> - Series B–E OR public + data-platform-native (not legacy w/ "data team" bolt-on)
> - Healthcare data, AI-data infra, or RAG-needing-a-backbone (where your repo lands cleanly)
> - Known to NOT run FAANG-style algo gauntlets (data eng interviews skew SQL/modeling)
> - Hiring AI Data Engineer / Analytics Engineer / Data Platform Engineer titles as of 2026
>
> **Knowledge cutoff caveat:** Reachable bands and "actively hiring" flags
> based on May 2025 state. Re-verify each target on Levels.fyi + their careers
> page before sending. Some 2025 funding rounds may have shifted the comp band.
> Companies marked ⚠️ had recent layoffs or restructuring — verify viability.

---

## TIER 1 — clinical data platforms (strongest repo fit — your moat is healthcare + dbt + quality)

```
COMPANY              SPACE                       SIGNAL              BAND*
─────────────────────────────────────────────────────────────────────────
Truveta              RWE / EHR aggregation       AI-eng hiring,      $150-200K
                                                  dbt-friendly
Komodo Health        real-world evidence         Series E, large    $150-200K
                                                  data platform
Datavant             health data exchange        established AI     $150-210K
                                                  data plat
Innovaccer           healthcare data platform    Series E, India+US $140-190K
Tempus AI            precision medicine          public, AI-native  $160-220K
Atropos Health       synthetic RCTs / RWE        clinical data eng  $150-200K
Flatiron Health      oncology RWE (Roche)        established health $160-210K
                                                  data shop
Pieces Tech          clinical AI summary         hospital data      $140-190K
                                                  pipelines
Notable Health       admin AI + data             Series B           $140-190K
Particle Health      patient data API            FHIR-heavy         $150-200K
Health Gorilla       interop / data platform     Series C           $150-200K
Cohere Health        utilization mgmt + data     Series C           $140-190K
```

---

## TIER 2 — AI-data infrastructure (your dbt/quality muscle ports directly)

```
COMPANY              SPACE                       SIGNAL              BAND
─────────────────────────────────────────────────────────────────────────
dbt Labs             dbt cloud + adapters        you SHIP dbt       $150-220K
                                                  daily — direct fit
Snowflake            warehouse + AI features     huge AI-data org   $170-240K
Databricks           lakehouse + LLM tooling     direct overlap     $180-260K
Fivetran             ELT + AI-data prep         data eng-heavy     $150-210K
Confluent            streaming + data quality    Kafka + governance $160-220K
Monte Carlo          data observability         LOVES quality      $150-210K
                                                  gates — direct fit
Soda                 data quality platform       direct overlap     $140-200K
Great Expectations   data quality OSS + Cloud   direct overlap     $130-190K
                     (now GX Cloud)
Bigeye               data observability         $140-190K
Datafold             data quality / CI for data  PR-time quality    $140-200K
                                                  ← your moat exactly
Acryl Data           DataHub / data catalog      governance focus   $140-200K
Atlan                data catalog + lineage      growth stage       $140-200K
Castor (Coalesce.ai) catalog + AI               $130-180K
```

---

## TIER 3 — RAG/GenAI shops that NEED a data backbone (your sweet spot for cross-pollination)

```
COMPANY              SPACE                       WHY IT FITS
─────────────────────────────────────────────────────────────────────────
Pinecone             vector DB                   they want eng who
                                                 understand the DATA
                                                 going in, not just
                                                 the index
Weaviate             vector DB                   same — data prep
                                                 +schema matters
Vectara              RAG platform                small + RAG-obsessed,
                                                 grounding = your story
LlamaIndex           RAG framework               applied data eng
                                                 around RAG ingestion
Arize AI             ML/LLM observability        regression gate
                                                 thinking transfers
Patronus AI          eval startup                eval ↔ data quality
                                                 overlap is huge
Galileo              eval / observability        same energy
Snorkel AI           data labeling + eval        labeling pipelines
                                                 = data eng work
Tecton               feature store / MLOps       feature_view contract
                                                 in your repo ports
Hex                  notebook + data tools       Series C analytics
                                                 eng adjacent
Mode (Thoughtspot)   BI + AI                     analytics eng band
```

---

## TIER 4 — adjacent non-healthcare (worth a swing — your patterns are domain-agnostic)

```
COMPANY              SPACE                       BAND
─────────────────────────────────────────────────────────────────────────
Notion               productivity + AI           Series E, AI hiring  $150-220K
Linear               project mgmt + AI           data eng growth     $150-200K
Vercel               edge / observability        platform data       $160-220K
Retool               internal tools + data       growth stage        $150-210K
PostHog              product analytics OSS       data-heavy          $140-200K
Plaid                fintech data infra          mature data org     $170-230K
Mercury              fintech + data              Series B            $150-200K
Ramp                 fintech + AI                growth, data-heavy  $160-220K
Brex                 fintech                     data eng demand     $160-220K
Affirm               fintech                     ML+data infra       $170-230K
Stripe Atlas / Tax   fintech data products       always hiring       $170-240K
Discord              consumer + data infra       analytics eng band  $160-220K
Hugging Face         model hub + data            data eng around     $140-200K
                                                  datasets library
Together AI          inference + RAG infra       data prep matters
```

---

## How to use this list

```
WEEK 1  pick 10 from Tier 1 → research each → send personalized outreach
        Healthcare-first because your repo is named "healthcare-*" and
        your moat compounds when domain matches

WEEK 2  10 more from Tier 1+2 → measure reply rate

WEEK 3  decide: double-down on what's converting, or pivot to Tier 3
        (RAG-needing-a-backbone is your hidden sweet spot — they pay
        GenAI bands but interview you as data eng)

WEEK 4  follow-ups + 10 more sends from Tier 4

DO NOT  blast all 50+ in one week. Quality > quantity for senior roles.
        25 personalized sends > 200 generic sends.

NOTE    Tier 2 has the highest baseline pay BUT toughest screen
        (dbt Labs/Snowflake/Databricks engineers are sharp).
        Tier 1 has best repo-fit + faster offers.
        Tier 3 is the asymmetric upside bet.
```

---

## Research checklist per target (5 min/company)

```
☐ Read their /careers — is AI Data Engineer / Analytics Eng /
   Data Platform Eng actually open?
☐ Levels.fyi or Glassdoor — confirm band for "Data Engineer" or
   "Senior Data Engineer" (NOT just "Software Engineer")
☐ Find hiring manager OR senior data eng on LinkedIn (NOT recruiter)
☐ Read 1 recent eng blog post from their team — bonus if it's about
   dbt, data quality, lineage, or LLM enrichment
☐ Note ONE specific thing in your cold message
☐ Check Layoffs.fyi for any 2025-2026 cuts
☐ Verify funding status (Crunchbase or PitchBook)
☐ Check if they're on dbt Hub / Snowflake / BigQuery / Databricks
   — anchor your "swap path" pitch to their warehouse
```

---

## Red flags to skip a target

```
🚩 No engineering blog (low technical culture)
🚩 Recent layoffs >20% in past 6 months
🚩 JD says "10+ years experience required" + asks for PhD
   (= they want staff+, not mid-senior)
🚩 JD lists 15+ tools (= scattered team, will burn out new hires)
🚩 JD says "data engineer" but only lists Tableau/PowerBI/Looker
   (= they want an analyst, your skills will rust)
🚩 No mention of dbt, Airflow, Dagster, Prefect, OR any modern
   warehouse (= you're walking into legacy SSIS hell)
🚩 Stack is pure Spark + Scala (= different skill tree, slower
   to ramp + lower comp than the dbt/Snowflake/BQ track)
🚩 Posts brag about "petabyte scale" but no quality/governance
   mention (= they treat data eng as plumbing, your moat invisible)
```

---

## Bonus — companies to AVOID for AI Data Eng specifically

```
🚫 Pure FAANG data infra teams — algo gauntlet, your repo
   doesn't help you skip it
🚫 Banks / insurance giants — slow hiring, low ceiling, dress code
🚫 Consulting (McKinsey QuantumBlack, BCG GAMMA, Bain Vector,
   Accenture AI) — billable hours model, you'll lose your tech edge
🚫 Crypto data plays — burnt 70%+ of devs in last cycle, illiquid
🚫 Anything where the JD says "data wrangling" — that's analyst
   work at engineer bands, run away
```

*Bands are May 2025 estimates for mid-to-senior AI Data Eng with
healthcare or modern-stack experience. Verify on Levels.fyi.
Top quartile bands assume 5+ YoE + strong portfolio (your repo
qualifies for top-half of range).
