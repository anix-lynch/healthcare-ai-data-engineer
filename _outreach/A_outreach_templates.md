# A — Outreach Templates (AI Data Engineer, mid healthcare / AI-data)

> Hook stack (in order of strength):
> 1. **L1 quality gate that blocks merges on schema drift / PII leak / temporal sanity** ← rarest signal
> 2. **Vertex LLM enrichment with $0.0005/row + 100% schema success receipts** ← second rarest
> 3. **dbt medallion + schema tests (FK + accepted_values + not_null on every dim)** ← solid baseline
> 4. **Healthcare domain** ← only mention if target is health-tech (skip for general data infra shops)
>
> Always lead with #1 or #2. Everyone has #3. Healthcare is your moat for clinical-data shops, your liability for general infra (skip in that case).

---

## 1. Cold email — hiring manager (NOT recruiter)

**Subject:** AI data eng w/ quality-gate + LLM-enrichment receipts — for `<TEAM/COMPANY>`

```
Hi <Name>,

Saw <Company> is building <specific product / role / public post>.
I'm a data engineer focused on the layer most candidates skip —
quality gates that block bad data BEFORE it reaches the AI layer,
LLM-augmented enrichment with cost/latency receipts, and dbt
medallion tests that catch FK breaks at PR time.

Built a healthcare AI data backbone that:
  • runs 7-check L1 quality gate in CI (schema drift, PII, dup keys,
    temporal sanity — fails the merge on any critical break)
  • enriches 497 clinical rows via Vertex gemini-2.5-flash at
    $0.0005/row · 100% schema success · scales to 1M @ ~$500
  • dbt medallion (bronze→silver→gold) w/ FK + accepted_values
    tests on 7 dims + fact table
  • frozen output contracts the L2 RAG/agent stack imports against
    without hallucinating its way out of garbage input

Repo + committed quality report:
  https://github.com/anix-lynch/healthcare-ai-data-engineer

Worth a 20-min chat about your <data quality / AI-ready data /
medallion> setup?

— Anix
```

**Length:** 6 sentences. Under 130 words. Don't pad.

**Personalization slots** (mandatory — 2 min of LinkedIn skim per target):
- `<specific product / role / public post>` ← something that signals you actually looked
- swap the bullet list to match what THEIR JD emphasizes (don't list things they don't care about)
- end with `<data quality / AI-ready data / medallion>` matched to their stack

---

## 2. LinkedIn DM — short (under 300 char, mobile-friendly)

```
Hey <Name> — saw <Company> is hiring for <Role>. I build the data
quality layer most candidates skip: 7-check L1 gate in CI, Vertex
LLM enrichment w/ receipts ($0.0005/row), dbt medallion. Repo w/
live numbers: github.com/anix-lynch/healthcare-ai-data-engineer

Open to a 20-min chat?
```

**Where to send:** hiring manager OR a senior data eng on the team (NOT the recruiter — they filter on keywords, hiring managers filter on signal).

---

## 3. LinkedIn DM — longer (when you've engaged with their content first)

```
Hi <Name>,

Your post on <topic> last week resonated — I've been thinking about
<specific angle they raised>.

Quick context on why I'm reaching out: <Company> is one of ~15 places
I'm targeting for AI data engineer roles in 2026, specifically because
you all seem to care about <data quality / governance / AI-ready data /
medallion architecture — pick the one that's true>.

I just shipped a healthcare data backbone that I think shows the kind
of thinking you'd value:
  - 7-check L1 quality gate (schema drift · PII · temporal · dup keys)
    wired into CI on every PR
  - Vertex LLM-augmented enrichment at $0.0005/row with 100% schema
    success rate (full cost + p50/p99 latency in README)
  - dbt medallion w/ FK + accepted_values tests on fact + 7 dims
  - frozen output contracts so L2 GenAI patterns import against
    a stable surface (not a moving target)

→ https://github.com/anix-lynch/healthcare-ai-data-engineer

Would a 20-min chat about <their team / their stack> make sense?
Happy to share more depth on the quality-gate methodology specifically.

— Anix
```

**Use when:** you've liked/commented on 2-3 of their posts in the prior week. Don't send cold.

---

## 4. Referral ask — when you have a warm intro

```
Hey <Mutual>,

Quick ask — would you be open to a soft intro to <Name> at <Company>?
I'm targeting AI data engineer roles at clinical-data or AI-native
infra shops where data quality + AI-readiness matter more than
take-home algo gauntlets.

Just shipped a repo that I think speaks for itself:
  github.com/anix-lynch/healthcare-ai-data-engineer
  (dbt medallion · 7-check L1 gate in CI · Vertex enrichment w/ receipts)

Happy to draft the intro paragraph for you — just need a yes and
I'll send a one-liner you can forward.

Thanks 🙏
— Anix
```

**Critical:** offer to write the intro paragraph. Removes the friction. ~3x conversion vs "would you intro me?"

---

## Send cadence — what actually works

```
WEEK 1   25 targeted messages   ← personalize each, no spray-and-pray
WEEK 2   25 more + 5 follow-ups on Week 1
WEEK 3   25 more + 10 follow-ups
WEEK 4   review what's working, double down on best-converting hook

EXPECTED REPLY RATE  10-20% on personalized outreach
EXPECTED MEETING RATE  3-5% (1-2 calls / week from 25 sends)
EXPECTED OFFER RATE  1 offer per ~40-70 quality conversations
                     (data eng has higher convert than GenAI — less crowded)
```

---

## Follow-up template (Day 5-7 after no reply)

```
Hi <Name> — bumping this in case it got buried.

The 90-second TL;DR: I build the data quality + AI-readiness layer
that most candidates can't talk about. Repo:
github.com/anix-lynch/healthcare-ai-data-engineer

If now's not the right time, totally understand — happy to circle
back in Q3.

— Anix
```

**Single follow-up. Then move on.** Don't be that person who sends 4 follow-ups.

---

## What NOT to do

```
❌ Don't mention TC expectations in the cold message
❌ Don't list every tool you've ever used
❌ Don't open with "I'm passionate about data"
❌ Don't send the same message to 50 people verbatim
❌ Don't apologize for "interrupting" — they signed up for InMail
❌ Don't attach a resume in the first message
❌ Don't say "I'd love to discuss opportunities at your company"
   ← recruiter-speak, hiring managers gag
❌ Don't lead with "I know Python and SQL" — commodity, dilutes signal
❌ Don't pitch yourself as "full-stack data" — too broad, lower bands

✅ DO send to hiring managers + senior data engs
✅ DO personalize the first line (proves you looked)
✅ DO link the repo, not a resume
✅ DO close with a specific ask (20-min chat)
✅ DO follow up exactly once
✅ DO lead with the quality gate — it's your rarest signal
```

---

## Channel-specific tweaks

```
SUBSTACK / MEDIUM AUTHORS    Reference their post in line 1, then pivot
                              to "the cost/latency receipts in my repo
                              would interest you" — they appreciate numbers

CONFERENCE SPEAKERS          "Saw your <Datacouncil / Coalesce / dbt
                              Coalesce> talk on <topic>" — be specific
                              about which slide or quote moved you

OPEN-SOURCE MAINTAINERS      Open a thoughtful issue or PR on their repo
                              BEFORE the DM. The DM then references the
                              PR. Conversion ~5x vs cold.

EX-COLLEAGUES OF FOUNDERS    Find a mutual on LinkedIn, send the referral
                              template above. Warmest path.
```
