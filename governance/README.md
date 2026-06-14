# Governance + access control (Bullet 4)

> "ไม่ใช่ทุกคนควรเห็นทุกอย่าง" — not everyone should see everything.

The analyst-facing surface is an **approved, PII-masked view**; the raw base
tables are off-limits. Least privilege is enforced by BigQuery's authorized-view
+ dataset-IAM model, not by trust.

```
 healthcare_analytics  (raw_ingest_clean, ...)        ← sensitive base, restricted
        ▲
        │ authorized view reads base ON THE CALLER'S BEHALF
        │
 healthcare_governed   (vw_encounters_safe)           ← name→sha256, billing→band
        ▲
        │ READER
        │
 restricted-reader-b4  ──► 200 on vw_encounters_safe   ✅ approved view
                       ──► 403 on raw_ingest_clean      🚫 base table denied
```

## What's enforced (verified)

| Control | How | Proof |
|---|---|---|
| **PII masking** | `vw_encounters_safe`: `name → SHA256`, `billing_amount → band` | `proof_governance.json` → masked sample |
| **Least-privilege grant** | `restricted-reader-b4` is READER on `healthcare_governed` only, **no** access to `healthcare_analytics` | dataset access entries |
| **Authorized view** | the view is authorized on the base dataset so the analyst never touches base | `setup_governance.py` step [3] |
| **Retention** | `quarantine_records` expires after 90 days | `ALTER TABLE ... expiration_timestamp` |
| **Data contract** | versioned consumer contracts | [`../docs/contracts.md`](../docs/contracts.md) |

## The observable 403 (one owner grant, then self-running)

The denial is already **guaranteed by policy** (the restricted SA has no grant on
the base dataset). To *observe* it, you authenticate AS the restricted SA and run
both queries — `governance/least_privilege_demo.py` does this and writes
`proof_least_privilege.json`.

The deploy SA cannot mint a token for another SA (no `tokenCreator`), so the
project owner runs this **once**:

```bash
gcloud iam service-accounts add-iam-policy-binding \
  restricted-reader-b4@bchan-genai-lab.iam.gserviceaccount.com \
  --member="serviceAccount:bchan-genai-deploy@bchan-genai-lab.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountTokenCreator" --project bchan-genai-lab

GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json \
  python governance/least_privilege_demo.py --impersonate
```

Expected: `approved_view_read = 200_ALLOWED`, `base_table_read = 403_DENIED`.

## Run

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json \
  python governance/setup_governance.py      # idempotent — build the apparatus
```
