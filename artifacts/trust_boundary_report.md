# Trust Boundary Report
> Generated: 2026-06-16
> Trust posture: TRUSTED
> Contracts: 6/7 blocking

## What is a truth layer?

A collection of checks runs when you remember to run it.
A truth layer makes contracts first-class platform objects:
- Named, versioned, owned
- Lineage-tracked (what breaks downstream if this fails)
- Severity-classified (BLOCKING vs WARNING)
- Last-evaluated with proof artifacts

## Contract registry

| ID | Name | Type | Severity | Last Result |
|---|---|---|---|---|
| C-001 | source_release_contract | SOURCE_INTEGRITY | BLOCKING | PASS |
| C-002 | l1_data_quality_contract | SCHEMA_STABILITY | BLOCKING | PASS |
| C-003 | clinical_plausibility_hard_block | SEMANTIC_CORRECTNESS | BLOCKING | PASS -- 0 hard violations in enriched corpus |
| C-004 | enriched_ai_contract | ENRICHMENT_READINESS | BLOCKING | PASS -- 0 exceptions |
| C-005 | patient_identity_contract | ENTITY_RESOLUTION | WARNING | PASS -- 40,235 canonical patients; 47 unresol |
| C-006 | source_to_warehouse_reconciliation | RECONCILIATION | BLOCKING | PASS -- 55,500 == 49,986 + 5,514; all_pass=tr |
| C-007 | ai_safety_no_bad_data | AI_SAFETY | BLOCKING | PASS -- stale_data_incidents=0 across 1,000 f |

## Trust chain

```
CSV (55,500 rows)
  C-001: source_release_contract        [BLOCKING]
    C-003: clinical_plausibility         [BLOCKING] <- semantic layer (not expressible in GE)
      C-004: enriched_ai_contract        [BLOCKING]
        C-007: ai_safety_gate            [BLOCKING] <- terminal gate; stale_data_incidents=0
    C-005: patient_identity              [WARNING]
      C-006: reconciliation              [BLOCKING]
    C-002: schema_stability              [BLOCKING]
```

## Known soft exceptions (transparent, not hidden)

| Contract | Exception | Action |
|---|---|---|
| C-001 | Billing Amount 108 rows (0.19%) via mostly:0.995 | Tracked; not promoted to hard block |
| C-005 | 47 unresolved patients (0.12%) | WARN band; tracked in l1_checkpoint_report.json |

## What a Staff Engineer at Anthropic would call a truth layer

Contracts are platform policy, not test code. They have owners, versions, and lineage.
A break in any contract must trace to a downstream impact.
The system must answer "what breaks if this contract fails?" -- not just "did it pass today?"
