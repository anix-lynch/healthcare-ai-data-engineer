# C — LinkedIn Rewrite (positioned for AI Data Engineer · healthcare / AI-data)

> **Goal:** be findable + immediately credible to a hiring manager
> doing a 30-second skim of your profile. NOT to win an essay contest.
>
> **Positioning lock:** AI-ready data + quality gates + dbt medallion.
> Not "data engineer" alone (commodity, lower bands), not "ML engineer"
> (different track, harder pivot), not "analytics engineer" (lower
> ceiling than AI Data Eng). The narrower the position, the higher
> the offer.

---

## 1. Headline (220 char max — use all of it)

### Option A — feature-led (recommended)

```
AI Data Engineer · Healthcare medallion + L1 quality gates ·
dbt + Vertex LLM enrichment · open to mid-senior roles
```

**Why this works:**
- "AI Data Engineer" — exact title hirers search for (not just "Data Engineer")
- "Healthcare medallion" — domain + architecture anchor (filter signal)
- "L1 quality gates" — your unique moat (most data engs talk dbt tests,
   few talk PR-time CI quality gates)
- "Vertex LLM enrichment" — proves you bridge data + AI (rare combo)
- "open to mid-senior roles" — pulls inbound from recruiters at the
   right level

### Option B — benefit-led (use if you want more recruiter pull)

```
AI Data Engineer · I ship data the AI layer can trust ·
dbt medallion + L1 quality gates + LLM enrichment receipts ·
healthcare-ai-data-engineer repo on GitHub
```

**Why this works:**
- "Trust" framing = what every AI hiring manager is anxious about
- "Receipts" callout = pre-qualifies inbound (recruiters who skim
   GitHub repos = better recruiters)

### Option C — combo (high information density, slightly aggressive)

```
AI Data Engineer @ healthcare medallion · L1 quality gates in CI ·
Vertex LLM enrichment $0.0005/row · dbt FK+enum tests · DM > InMail
```

**Why this works:**
- "DM > InMail" — signals senior-ish confidence, filters serious replies
- The $0.0005/row number = single most distinctive data point in your
   headline (recruiters will save your profile just to remember it)

**My pick: A.** Cleanest. Use B if 2 weeks of A gets thin pull.

---

## 2. About section (3 paragraphs — keep it tight)

```
─────────────────────────────────────────────────────────────────────
I build the data layer the AI stack consumes without hallucinating
its way out of garbage input — dbt medallion, L1 quality gates in CI,
PII redaction at ingest, frozen output contracts, and LLM-augmented
enrichment with the cost/latency receipts to prove it works at scale.

Recent: healthcare AI data backbone — 55K-row synthetic EHR corpus
through staging → intermediate → gold marts with FK + accepted_values
+ not_null tests on a fact + 7 dims, a 7-check L1 quality gate that
blocks PRs on schema drift / PII leak / temporal-sanity violations,
and a Vertex gemini-2.5-flash enrichment pipeline that ran 497 rows
at $0.0005/row · 100% schema-success · scales to 1M ≈ $500. Multi-
adapter SQL (DuckDB / BigQuery / Snowflake / Fabric / Postgres) so
the pattern ports without rewriting.

→ github.com/anix-lynch/healthcare-ai-data-engineer

Open to mid-senior AI Data Engineer / Analytics Engineer / Data
Platform Engineer roles at clinical-data, AI-data-infra, or RAG-
needing-a-backbone shops. Not interested in legacy SSIS/Tableau-
wrangler work or "data engineer" roles that mean "build the dashboards."
DMs open.
─────────────────────────────────────────────────────────────────────
```

**Word count:** 158. Don't pad — every extra sentence dilutes signal.

**What this About does:**
- Para 1: positions you against the median data eng candidate
   (your moat = quality gates + LLM enrichment, not just dbt)
- Para 2: proof — the repo, with SPECIFIC numbers that prove
   technical depth ($0.0005/row, 7-check gate, 55K rows)
- Para 3: filter — pre-qualifies what conversations to skip vs open

---

## 3. Featured section (top of profile)

Pin EXACTLY 3 items:

```
1. GitHub repo card — healthcare-ai-data-engineer
   Caption: "Healthcare data backbone · L1 quality gate in CI ·
             Vertex enrichment receipts"

2. l1_checkpoint_report.json screenshot (the 7/7 ✅ block)
   OR the Vertex cost/latency table from README
   Caption: "Sample quality gate output + Vertex enrichment receipts"

3. A 1-paragraph "What I'm looking for" doc OR a blog post if
   you write one (suggested topic below)
   Caption: "AI Data Engineer · mid-senior · healthcare or AI-data infra"
```

**Order matters.** Repo first (proof), output second (proof),
positioning third.

---

## 4. Experience section — top entry rewrite template

```
─────────────────────────────────────────────────────────────────────
AI Data Engineer (independent / portfolio)            2025 – present

• Designed and shipped healthcare-ai-data-engineer: dbt medallion
  data backbone over 55K synthetic EHR encounters, resolving to
  40K unique patients via SHA256 short-id resolver
• Built 7-check L1 quality gate (schema drift · critical nulls ·
  duplicate encounters · temporal sanity · PII-in-narrative ·
  patient identity · audit lineage) wired into GitHub Actions —
  blocks PRs on any critical failure
• Shipped Vertex gemini-2.5-flash enrichment pipeline (chief
  complaint, HPI, vitals, labs, ESI ground-truth) at $0.0005/row
  with 100% schema success rate via Pydantic-via-JSON-Schema
  enforcement; x6 parallel workers, retry-with-backoff, stderr
  visibility on Vertex outages
• Built dbt schema tests on fact + 7 dims: 18 not_null · 8 unique
  · 5 FK relationships · 3 accepted_values for clinical enums
• Frozen output contracts (canonical / retrieval / feature /
  eval-holdout / audit-lineage) so downstream RAG/agent patterns
  import against stable surface
• Multi-adapter SQL (SQL Server / Fabric primary, with documented
  swap path to DuckDB / BigQuery / Snowflake / Postgres)
• FastAPI thin internal data API + auto-generated OpenAPI;
  CI runs pytest + L1 gate + gitleaks on every PR

Stack: Python · dbt · SQL Server · DuckDB · BigQuery · Vertex AI
       (gemini-2.5-flash) · FastAPI · Pydantic · pandas · pytest ·
       GitHub Actions · gitleaks

→ github.com/anix-lynch/healthcare-ai-data-engineer
─────────────────────────────────────────────────────────────────────
```

**Why this format works:**
- Active verbs first ("Designed", "Built", "Shipped")
- Specifics over adjectives ("7-check L1 gate" > "comprehensive DQ")
- Numbers everywhere ($0.0005/row · 55K · 40K · 18 not_null tests)
- Stack at the bottom = keyword bait for recruiters w/o burying story
- Link at the end = closes the loop

---

## 5. Skills section — pin these 3 to the top

```
1. Data Engineering
2. dbt (data build tool)
3. Data Quality
```

**Then in body:** SQL · Python · dbt · Data Modeling · Medallion
Architecture · Data Quality · ETL · ELT · Snowflake · BigQuery ·
DuckDB · Vertex AI · LLM-Augmented Data Pipelines · PII Detection ·
FastAPI · Pydantic · Pytest · GitHub Actions · Data Governance ·
Apache Airflow · Star Schema · CI/CD for Data

**Skip these (commodity / will dilute):** Machine Learning · AI ·
Software Development · Programming · Microsoft Office · Excel ·
Tableau · Power BI (UNLESS you're targeting analytics-eng band on
purpose — for AI Data Eng band, skip BI tools entirely)

---

## 6. Activity / posting cadence (the actual unlock)

```
1 post / week — pick ONE of these patterns:

PATTERN A — "I built X and learned Y"
  e.g., "Built a 7-check L1 data quality gate that blocks PRs on
        schema drift / PII leak / temporal sanity. Here's why
        Great Expectations was overkill, why per-row Pydantic was
        too slow, and how 200 lines of pure Python beat both for
        the bronze→silver hand-off. [thread]"

PATTERN B — "Cost receipts" (your unique muscle)
  e.g., "Enriched 497 clinical rows via Vertex gemini-2.5-flash at
        $0.0005/row, 100% schema-success, ~9s p50 latency. Scales
        to 1M ≈ $500. Most LLM-enrichment posts skip the receipts —
        here's how I budgeted, parallelized, and instrumented. [post]"

PATTERN C — "Hot take on a thing the field gets wrong"
  e.g., "Most data eng portfolios skip the quality gate entirely —
        they ship dbt tests and call it governance. Here's the CI-
        wired L1 gate setup I wish more candidates showed. [3 min]"

PATTERN D — "Working in public" updates
  e.g., "Shipped audit_lineage columns on every gold-mart row today:
        source_system + ingest_ts + row_hash + pii_redaction_status.
        Why I deferred this until phase 4 and what I learned. [link]"

CADENCE: 1 post / week is enough. 2 = overkill. 0 = invisible.
WHY:     LinkedIn algorithm rewards consistent posting more than
         viral posting. 1/week for 8 weeks > 1 viral post.
```

**Posting unlocks inbound that outreach can't.** Cost-receipts posts
(Pattern B) are your highest-signal asymmetric play — almost nobody
posts numbers, so they stand out.

---

## 7. Profile setup checklist

```
☐ Photo: clean, professional, smiling — not the AI-headshot style
☐ Banner: simple — your name + "AI Data Engineer · Healthcare +
   dbt + Quality Gates" + repo URL (no Canva spam)
☐ Headline: option A above
☐ About: paragraph block above
☐ Featured: 3 items pinned (see #3)
☐ Experience: top entry rewritten per template
☐ Skills: 3 pinned + others listed
☐ Open to Work: ON, but ONLY visible to recruiters (not public banner)
   ← public banner reads as desperate at mid-senior level
☐ Custom URL: linkedin.com/in/anixlynch (clean, no numbers)
☐ Featured GitHub link in contact info
☐ Verified email + phone
☐ Top-of-profile pronoun field if comfortable (signals inclusive eng
   team to filter for)
```

---

## What to DELETE from your current profile

```
❌ Buzzwords: "synergize", "transform", "leverage", "innovative",
   "data-driven" (data engs gag at this one), "passionate"
❌ Job titles older than 10 years (unless directly relevant)
❌ Generic certifications (Coursera, Udemy) — keep only top 2 if any
   (DataCamp / dbt Fundamentals / Snowflake SnowPro ARE worth keeping)
❌ Volunteer entries unless directly data/AI-related
❌ "Languages spoken" if it's just English
❌ Any post older than 6 months that doesn't represent current you
❌ ANY mention of "Tableau dashboards" or "PowerPoint reports" if
   you're chasing AI Data Eng band (signals analyst, not engineer)
```

---

## Bonus — your "why this company" template for applications

When applying directly through a JD form, paste this into "Why this
company":

```
I target clinical-data and AI-data-infra shops specifically because
data quality, AI-ready contracts, and LLM-augmented enrichment matter
more there than at general SaaS data teams. <Company> shows up in my
Tier-1 list because <ONE specific reason — their dbt usage, their
data quality blog post, their AI product>.

My healthcare AI data backbone repo is the long version of that
argument: github.com/anix-lynch/healthcare-ai-data-engineer
```

**3 sentences. No padding.** Hiring managers skim "Why this company"
and 99% of answers are generic.

---

## 8. Suggested first 3 LinkedIn posts (to seed the algorithm)

If you've been quiet on LinkedIn, post these in order over 3 weeks:

```
POST 1 (week 1) — Pattern B (cost receipts)
  Topic: "I enriched 497 clinical rows w/ Vertex at $0.0005/row.
          Here's the budget math + parallel-worker setup."
  CTA:   Link to README cost table section.

POST 2 (week 2) — Pattern C (hot take)
  Topic: "Most data eng portfolios ship dbt tests and call it
          governance. Here's the CI-wired L1 gate that actually
          blocks bad data at PR time."
  CTA:   Link to scripts/checkpoint.py.

POST 3 (week 3) — Pattern A (built X learned Y)
  Topic: "Resolved 55K encounters to 40K unique patients using a
          SHA256 short-id resolver. Honest about what name-hash
          MDM gives you vs what MRN-based MDM gives you. Trade-off
          breakdown."
  CTA:   Link to scripts/patient_identity.py.
```

These three posts together signal: cost discipline · quality
discipline · honest scope. That's the exact triangle hirers
listen for at the senior AI Data Eng band.
