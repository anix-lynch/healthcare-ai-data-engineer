# AI Data Flywheel Summary
> Generated: 2026-06-16 | Status: ACTIVE

## The loop
```
quarantine events -> pattern mining (flywheel.py)
      -> rule candidates (suggested_rules.json)
      -> engineering review + adoption
      -> validator update (validate.py / clinical_plausibility.yaml)
      -> quarantine rate decreases (proven in quality trend)
      -> repeat
```

## Flywheel metrics

| Metric | Value |
|---|---|
| Quarantine events analyzed | 5,521 |
| Distinct failure patterns | 7 |
| Rules suggested | 6 |
| Rules adopted | 3 (50.0%) |
| Flywheel turns completed | 3 |
| Clinical violations epoch 0 -> 3 | 24 -> 0 |
| Agent-facing corpus violations | 0 |

## Adopted rules

| Rule ID | Type | Adopted In |
|---|---|---|
| DEDUP-001 | IDEMPOTENCY | ingestion/sink.py MERGE on natural_key |
| CLINICAL-001 | SEMANTIC_CORRECTNESS | data/quality/clinical_plausibility.yaml |
| SCHEMA-001 | TYPE_COERCION | ingestion/validate.py age int-cast + range |

## Pending rules (next turn)
- SCHEMA-002: gender enum expansion (PENDING_REVIEW)
- COMPLETE-001: upstream null-check probe (PENDING_REVIEW)
- TEMPORAL-001: late-arriving window config (CANDIDATE)

## Why this is a flywheel, not just a gate

CLINICAL-001 was triggered by 24 pattern-mining hits -> adopted -> 0 violations in agent corpus.
That is one complete turn of the flywheel. The quarantine history IS the training signal.
