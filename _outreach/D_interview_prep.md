# D — Interview Prep (5 likely questions, grounded in YOUR repo)

> Hiring managers and senior data engs will ask questions designed to
> test whether the repo reflects YOU or a tutorial. The answers below
> are scripted to be said in your voice, not memorized. Practice them
> out loud 3x each.
>
> **Cardinal rule:** every answer ties back to a SPECIFIC file or
> commit in your repo. Vague answers = "this person didn't really
> build it."

---

## Q1 — "Walk me through your medallion architecture and the decisions you made."

**Why they ask:** baseline competence + decision-making depth on data
modeling.

**Answer (90 seconds):**

```
Sure. The architecture is bronze → silver → gold over a 55K-row
synthetic EHR corpus, with one staging layer, two intermediate
models, and a star schema at the mart layer — one fact table
(fact_patient_encounters) and seven dims (patient, doctor, hospital,
diagnosis, medication, insurance, date).

Three decisions I'd call out:

ONE — I kept staging deliberately thin: just lowercase columns, cast
dates, hash PII names into patient_name_hash. No business logic. That
keeps the staging layer cheap to rebuild and the intermediate layer
free to evolve. The hashing is dbt-fabric flavor — `HASHBYTES('SHA2_256',
patient_name)` — and I documented multi-adapter equivalents inline
(DuckDB sha256, BigQuery to_hex(sha256), Snowflake sha2, Postgres
pgcrypto). The adapter note is a six-line comment block in stg_healthcare.sql
that tells the next engineer exactly what to wrap in a {{sha256}} macro
before the multi-warehouse swap.

TWO — the intermediate layer earns its existence. int_encounters_enriched
joins clinical narrative back to encounters; int_readmissions resolves
the readmission window logic. Pure SELECTs in marts would have made
those two models impossible to unit-test in isolation. Senior dbt
shops always have an int_ layer for exactly this reason.

THREE — schema.yml on the mart layer is non-negotiable. Eighteen
not_null tests on PKs and FKs, eight unique tests on natural keys, five
relationship tests linking fact to every dim, and three accepted_values
tests on clinical enums (admission_type, readmission flags, condition).
If any of those fail, the dbt run fails. The L1 checkpoint runs BEFORE
dbt — schema drift, PII, temporal sanity — so two layers of gating
before the marts hit the warehouse.

The repo's at github.com/anix-lynch/healthcare-ai-data-engineer if
you want to look at the actual SQL.
```

**Bait they'll set:**
- *"Why dbt and not Spark / Beam / Flink?"* → "dbt is the right fit
   for a star-schema medallion where the warehouse is the compute. If
   the workload were streaming or required Python UDFs at scale, I'd
   reach for Spark. For batch-medallion-into-warehouse, dbt is the
   cheaper and more testable path."
- *"Why a star schema instead of one-big-table?"* → "OBT optimizes
   for analyst query speed; star schema optimizes for downstream
   contract stability. The L2 RAG/agent layer imports against my
   gold marts — a star schema lets me evolve a single dim without
   rebuilding the fact. OBT would mean every dim change cascades."

---

## Q2 — "How do you ensure data quality at scale?"

**Why they ask:** this is THE data quality question. Where most
candidates fold. **You should LIGHT UP here — this is your moat.**

**Answer (75 seconds):**

```
Three layers, in order.

ONE — schema.yml in dbt enforces FK / unique / not_null / accepted_values
on every mart. dbt test runs on every PR via GitHub Actions. That's
the cheapest layer — it catches modeling-level breakage at PR time.

TWO — a custom L1 checkpoint (scripts/checkpoint.py) that runs BEFORE
dbt and catches the seven failure modes that dbt tests don't see:
schema drift in the source CSV (29 expected columns + 13 enriched),
critical nulls on PHI-adjacent fields, duplicate encounter keys (in
this synthetic dataset that's patient_name + admission_date — I
documented in the docstring that production would key on encounter_id /
visit_id), temporal sanity (discharge ≥ admission, LoS in [0, 365]),
PII patterns in narrative fields (SSN / phone / email / CC regex over
chief complaint / HPI / physician notes), patient identity resolvability
against the resolver map, and audit lineage column presence. Exits 1
on any critical failure. Wired into CI on every PR.

THREE — the L1 gate writes data/quality/l1_checkpoint_report.json
into git on every run. Committed. So a hirer or auditor can read the
full DQ state at any commit hash without spinning up the pipeline.
That's the "show your work" layer.

Honest scope: this is the floor. It's NOT Great Expectations
replacement and NOT HIPAA-compliant — I'm explicit about that in
the README's honest-scope table. For prod I'd layer GE or Soda for
distribution-level checks, add Monte Carlo or Bigeye for freshness
SLAs, and graduate from regex PII to Presidio or a clinical NER.

The point of the L1 gate is that it catches the dumb-but-pipeline-
killing failures (duplicate encounter ids, PII leaks into narrative,
discharge-before-admission, schema drift) at PR time, which is when
they're cheapest to fix. The fancier tools matter at the production
distribution-monitoring layer, not the gating layer.
```

**Bait they'll set:**
- *"Why not just use Great Expectations from day one?"* → "GE has
   a heavy install footprint and the YAML config IS the failure
   surface. For a portfolio repo and an L1 gate, 200 lines of pure
   Python is more legible and runs in 1.5 seconds in CI. GE makes
   more sense once you have multiple data products sharing
   expectation suites."
- *"How do you handle drift over time?"* → "The schema.yml is the
   contract. If a source-CSV column count changes, the schema_drift
   check fails immediately. If a dim's accepted_values expands, the
   dbt test fails and the PR has to explicitly update the enum.
   Silent drift is the failure mode I'm guarding against — explicit
   bumps are fine and expected."

---

## Q3 — "How did you scope and instrument the Vertex LLM enrichment?"

**Why they ask:** AI-data-engineer is a rare title because few people
have actually shipped LLM-into-pipeline work with cost discipline.
This question separates "I did a tutorial" from "I'd actually own
this in prod."

**Answer (90 seconds):**

```
The scope: enrich 497 encounters with chief complaint, HPI, vitals,
labs, and ESI tier — five structured fields, JSON-schema enforced.
The dataset is Kaggle synthetic, so the LLM is filling in clinical
narrative that the source rows lack.

Four decisions:

ONE — schema enforcement at the model boundary, not post-hoc validation.
Vertex gemini-2.5-flash supports response_schema natively, so I pass
the Pydantic-as-JSON-Schema in the request and let the model refuse
to return malformed JSON. Result: schema-fail rate is 0%, retry rate
is 3% (network only, not parse failures). If I'd validated post-hoc,
I'd be writing failed-rows.jsonl for parse errors — that file is
empty in my run.

TWO — x6 parallel workers via ThreadPoolExecutor with checkpoint-based
resume. Every successful row writes a checkpoint, so re-running the
script after a crash skips already-enriched rows. Idempotent + cheap.

THREE — retries log to stderr, not silently swallowed. Comet caught
this in a code review — silent backoff hides Vertex outages or quota
burn during long runs. Now every retry prints type(err).__name__ +
first 200 chars of the message to stderr.

FOUR — instrumented the run end-to-end and put the receipts in the
README. $0.25 total · $0.0005 per row · 789 seconds wallclock · ~37
rows/min sustained · p50 ~9s · p99 ~25s · 3% retry · 0% schema fail ·
100% success. Same pipeline scales to 55K ≈ $27 or 1M ≈ $500. The GCP
$900 credit absorbed the entire run.

For prod I'd add: per-row token-count logging, a daily cost-budget
guard that pages on anomaly, and a fallback to gemini-2.5-flash-lite
or a smaller adapter if cost-per-row drifts above tolerance.
```

**Bait they'll set:**
- *"Why gemini-2.5-flash and not Claude or GPT?"* → "Cost + native
   response_schema support + GCP free credits to absorb experimentation.
   I'd benchmark Claude Haiku and GPT-4o-mini against Gemini Flash on
   a held-out 50-row slice in prod — never pick a model without an
   A/B on YOUR dataset. The pipeline abstracts the provider, so the
   swap is one file."
- *"What's your max throughput?"* → "37 rows/min sustained at x6
   workers — bottlenecked on Vertex per-call latency, not local
   compute. x12 workers would roughly double it before quota
   throttling kicks in. For 1M rows I'd batch into async groups
   of 100 and use Vertex batch API instead of online API — order
   of magnitude cheaper for non-realtime work."

---

## Q4 — "Tell me about a data quality issue you caught and how you debugged it."

**Why they ask:** this is the "can you actually debug data" check.
Most candidates recite a generic answer. Pick a REAL one from your
repo.

**Answer (90 seconds — adapt to your actual story):**

```
[REAL EXAMPLE — pick ONE of these and rehearse it:]

A — audit_lineage "gracefully absent" false-pass. After my first L1
checkpoint ship, the audit_lineage check was reporting "gracefully
absent (Phase A — acceptable)" — which technically passed the gate
but signaled to any auditor or reviewer that the lineage columns
weren't actually there. Cowork audit caught that the README would
read as half-built to a hirer. Fix was to add four columns to every
gold-mart row: source_system, ingest_ts, row_hash, pii_redaction_status.
Then flip the check to status="complete". Now 7/7 truly green and
the JSON report and README agree. The lesson was: "graceful absence"
in a quality gate is just deferred technical debt with a polite name.

B — duplicate-encounter heuristic clarity. The L1 check_duplicate_encounters
function keys on (patient_name, admission_date) because the Kaggle
synthetic dataset has no encounter_id column. A reviewer pointed out
that without a docstring, this looks like I think (name + date) is
the correct production key. Added a four-line docstring that explicitly
says: "In a real EHR (Epic/Cerner/Athena) the gate would key on source
encounter_id / visit_id and flag (patient_id, encounter_id) duplicates
— the (name+date) heuristic is a synthetic-data stand-in for that
production check." Tiny change, big interview-defensibility win.

C — pandas-only API is fine until it isn't. The FastAPI layer loads
the 55K-row CSV into pandas at cold start. That's fine at 100K rows
but breaks at 1M. README now has a "Production swap path" section
that documents the DuckDB / warehouse alternatives and points at
api/app/schemas.py as the reference contracts that any backend
must honor. Lesson: document the scale boundary BEFORE someone asks
in an interview.

Pick A or B for a senior conversation — they show line-level care
and an ability to take cold review well. Pick C for a more architecture-
oriented conversation — it shows scale-thinking.
```

**Bait they'll set:**
- *"Did you write the audit_lineage columns into existing rows or
   just future rows?"* → BE HONEST. "I added the columns to the
   staging model so every gold-mart row going forward carries them.
   For existing historical rows in prod I'd run a one-time backfill
   migration with the same logic — but in the synthetic-data repo
   it's a fresh build every run, so backfill wasn't relevant."
- *"How would you have prevented the false-pass earlier?"* → "Better
   quality-gate semantics from day one — 'pass with warning' is a
   different status than 'pass'. The gate now distinguishes 'complete'
   from 'partial' from 'absent', so the README and JSON can't
   contradict each other."

---

## Q5 — "If we gave you 90 days to ship an AI-ready data backbone at our company, what would week 1 look like?"

**Why they ask:** can you scope, can you sequence, can you say no.

**Answer (90 seconds):**

```
Week 1 is NOT modeling or pipeline-building. Week 1 is the quality
contract — because every decision in week 2-12 needs a sharp number
to defend against.

DAY 1-2: meet the team, read existing dbt projects or data catalogs,
identify the ONE downstream consumer (RAG layer, ML training, BI
dashboard, internal API) whose pain is most acute. "All things to
all consumers" fails. Pick the highest-value, narrowest workflow.

DAY 3-4: define the L1 quality contract. What's the failure mode that
keeps the data team up at night? Schema drift? PII leak? Stale data?
Duplicate keys? Build a 5-10 check L1 gate that catches THOSE failure
modes, runs on every PR, and exits 1 on any critical break. Commit
the report JSON into git so the team's quality state is visible at
any commit hash.

DAY 5: stand up the simplest possible bronze → silver model in dbt
over the chosen source. NOT seven dims. NOT enrichment yet. Just
one staging model with FK + not_null tests and the L1 gate firing in
CI. Measure: does the team's first PR against this scaffold catch
something they'd have shipped otherwise?

WEEK 2-4: add the gold mart layer (star schema or wide table —
depends on downstream pattern), wire dbt test coverage to ≥80%
of marts.
WEEK 5-8: add LLM-augmented enrichment if the data needs it — with
cost/latency receipts from day one, never silent.
WEEK 9-12: add observability (freshness SLAs, lineage in DataHub
or Atlan), build the second mart, harden CI, document output
contracts for downstream consumers.

What I'd push BACK on in week 1: "let's pick our warehouse first"
"let's evaluate 5 data quality tools" "let's design the full data
model upfront." All of that is premature optimization without the
quality contract to tell us what's actually safe.
```

**Bait they'll set:**
- *"You're really not going to ship anything user-facing for 4
   weeks?"* → "I'm going to ship something team-facing on day 5 —
   one bronze→silver model with the gate running. Downstream consumers
   get a live, gated dataset they can build against. That's the
   artifact week 1 needs."
- *"What if leadership wants the AI features shipped fast?"* → "AI
   features amplify whatever your data foundation is. If the foundation
   is silently broken, the AI ships faster but the bugs ship faster
   too. I'd push for the quality gate first, then unblock the AI
   features in week 2-3 against gated data. It's actually faster
   total time-to-value because you spend zero time debugging
   garbage-in-garbage-out."

---

## Bonus — questions YOU should ask them

```
1. "How do you currently measure data quality? Walk me through what
    a data quality incident looks like in your dev loop — who's
    paged, how's it caught, how's it resolved."
    → Filters for teams that take DQ seriously. Their answer tells
      you EVERYTHING about engineering culture.

2. "What's the most recent prod data incident? How was it caught and
    resolved?"
    → Filters for teams with real observability vs hope-driven
      pipelines.

3. "Who owns the dbt project? Eng? Analytics? Data? How do model
    changes get reviewed and deployed?"
    → Filters for teams that have thought about the data-team-vs-eng
      ownership problem.

4. "What's the split between warehouse cost and ETL cost in your
    stack?"
    → Senior question. Tells you they care about unit economics.

5. "What would you want me to ship in my first 30 days that would
    make you say 'yes, that hire was right'?"
    → Classic, but powerful. Their answer gives you the playbook.

6. "What's your LLM-in-pipeline story today — any enrichment,
    classification, summarization? If yes, how do you control
    cost and quality?"
    → Differentiator question. AI Data Eng implies you'll own
      this layer. Their answer tells you if the role is real
      or aspirational.
```

---

## What NOT to do in interviews

```
❌ Don't memorize answers word-for-word — sounds robotic
❌ Don't oversell the repo ("production-grade" — it's not)
❌ Don't undersell ("just a side project" — it's not)
❌ Don't get defensive about the synthetic Kaggle data — the
   honest-scope table exists FOR this; lean into "patterns
   port, dataset doesn't"
❌ Don't bring up TC in the first call (recruiter handles that)
❌ Don't pretend to know tools you haven't used
❌ Don't say "I'm a fast learner" — every junior says that
❌ Don't bash legacy stacks ("Tableau is dead", "SSIS is gross")
   — the interviewer may have built it; stay neutral
❌ Don't say "data is the new oil" — instant signal-decay

✅ DO say "I don't know — here's how I'd find out"
✅ DO push back politely on bad architecture suggestions
✅ DO ask the questions above
✅ DO follow up with a 4-sentence thank-you within 24 hours
✅ DO send the repo link in the thank-you note as a reminder
✅ DO bring up the cost receipts unprompted — it's your most
   distinctive signal
```

---

## Post-interview thank-you template

```
Subject: thank you — <Role> conversation

Hi <Name>,

Thanks for the time today. The bit about <specific thing they
mentioned — their data quality setup, their warehouse swap, their
LLM enrichment plans, their next 6 months> was particularly
clarifying.

I'm doubly interested after the conversation. The repo is at
github.com/anix-lynch/healthcare-ai-data-engineer if you want to
share with the rest of the loop — the L1 quality gate report
and Vertex cost receipts are the two sections worth their 90
seconds.

Looking forward to the next step.

— Anix
```

**Send within 24 hours. Short. No padding. Reference one specific
thing they said.** Generic thank-yous get ignored.

---

## Take-home prep (data-eng-specific)

If they assign a take-home (common at Tier 2 — dbt Labs, Snowflake,
Monte Carlo style — and most healthcare data shops):

```
EXPECT one of these patterns:
  A) "Here's a messy CSV — model it into a star schema + write tests"
     → Lean HARD on your repo: staging+intermediate+marts split,
       FK tests, accepted_values, the L1 gate pattern. Don't reinvent.

  B) "Build a data quality framework around this dataset"
     → Lift your checkpoint.py pattern wholesale. Adapt the 7 checks
       to their domain. Commit the JSON report into the repo.

  C) "Here's an LLM API key — enrich this dataset"
     → This is your home turf. Schema-enforced response, parallel
       workers, retry-w-backoff, cost/latency receipts in the README,
       checkpoint-based resume. Show the receipts.

  D) "Design a data pipeline for X workflow"
     → Architecture doc + diagram (use your DAG markdown style).
       Don't write code. Show medallion thinking + quality gate
       + downstream contract.

RED FLAGS in take-homes that should make you decline:
  🚩 >8 hours of estimated work for a first-round screen
  🚩 They want you to use their proprietary data (= free consulting)
  🚩 No clear evaluation criteria stated
  🚩 They ask for production-ready code with no spec

GREEN FLAGS:
  ✅ <4 hours, clear scope, public dataset, written rubric
  ✅ They reference your repo in the prompt (= they read it)
  ✅ They pay for take-home work (rare but signal of seriousness)
```
