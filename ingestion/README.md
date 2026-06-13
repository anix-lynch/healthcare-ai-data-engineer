# Event-driven ingestion + record-level quarantine (Bullet 1)

The batch loader (`scripts/load_bigquery.py`, `WRITE_TRUNCATE`) proves the *bulk*
path. This module proves the **streaming** path and the **data-quality resilience**
that Bullet 1 claims: messy records arrive one at a time, good rows land, bad rows
are isolated *with a reason*, and re-running never duplicates.

## What it does

```
stream_source.jsonl  ──►  validate.py  ──►  ┌─ accepted ─► MERGE ─► raw_ingest_clean
 (20 rows, deliberately   (one shared        │  (upsert on natural key = name|admission_date)
  messy: see below)        rule set)         └─ bad ─────► quarantine_records (+ reasons)
                                │
POST /api/ingest ──────────────┘   (same validator over HTTP — the Cloud Run event face)
```

Five messy modes, all exercised by the 20-row stream:

| mode | example row | decision |
|---|---|---|
| duplicate | `amy archer` re-sent, same key+ts | 🚫 quarantine `duplicate` |
| malformed | `age:"abc"`, `gender:"Robot"` | 🚫 quarantine `malformed_age` / `bad_gender` |
| missing | empty `name` / empty `date_of_admission` | 🚫 quarantine `missing_required` |
| late-arriving | `carla diaz` replay with older ts | 🚫 quarantine `late_arriving` |
| revised | `ben cole` re-sent with newer ts + new billing | ♻️ `accepted_revised` (supersedes) |

## Two entry points, one rule set

```
                    ┌─ validate.py ─┐   (pure rules, no DB — shared)
batch replay  ──────┤               ├──► sink.py ──► BigQuery
ingest.py           │               │    (idempotent MERGE + quarantine)
                    │               │
Pub/Sub topic ──────┘               │
  encounter-events                  │
   → push subscription              │
   → Cloud Run /pubsub/push ────────┘
```

The **streaming leg is real Pub/Sub**, not a file pretending to be a stream:
a message published to the `encounter-events` topic is pushed to the live
Cloud Run `/pubsub/push` endpoint, validated, and persisted — proof of a true
`Pub/Sub → Cloud Run → BigQuery` flow is in [`proof_streaming.json`](proof_streaming.json).

## Run

```bash
# offline — prints the decision ledger + writes proof_ingestion.json, no BigQuery
python ingestion/ingest.py --dry-run

# batch — MERGE the file replay into bchan-genai-lab.healthcare_analytics.{raw_ingest_clean, quarantine_records}
GOOGLE_APPLICATION_CREDENTIALS=~/.config/secrets/bchan-genai-deploy.json python ingestion/ingest.py

# streaming — publish ONE real event through the live Pub/Sub → Cloud Run → BigQuery leg
GOOGLE_APPLICATION_CREDENTIALS=~/.config/secrets/bchan-genai-deploy.json python ingestion/publish_event.py --demo
```

## Entity resolution (same Bullet 1 claim)

Idempotency here collapses *re-sent encounters* on the natural key. The
**patient-level** resolver (`scripts/patient_identity.py`) is the other half of
the bullet: it folds **55,500 encounters → 40,235 canonical patients**
(`data/derived/patient_identity_map.json`), so one สมศรี is one patient even
when the source spells her four ways.

## Proof (`proof_ingestion.json`)

20 streamed → **13 new + 1 revised + 6 quarantined**, reconciles exactly
(`accepted + quarantined = 20`). Running it twice leaves `raw_ingest_clean` at
**13 rows** — the MERGE is idempotent. `ben cole`'s billing ends at the revised
`14500`, proving newer-supersedes.

## Why it's split this way

`validate.py` is pure (no DB) so the **API endpoint and the batch stream share one
rule set** — the accept/quarantine verdict can't drift between them. The ingester
owns persistence (MERGE + quarantine append); the endpoint just classifies.
