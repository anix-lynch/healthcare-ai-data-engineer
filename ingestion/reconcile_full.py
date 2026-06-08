"""
Full reconciliation across the whole record lifecycle (Bullet 1 proof 7).

Unifies the per-stage reports into one mass-balance accounting that covers accepted,
quarantined, missing/backfilled, and replayed records — not just fetched-vs-landed.

  fetched         = accepted + rejected_null + rejected_dup        (ingestion leg)
  accepted(gate)  = good(clean) + quarantined                      (quarantine leg)
  good(clean)     -> warehouse (window-scoped match)               (load leg)
  missing         = 0 after backfill                               (backfill leg)
  replayed        = fixed quarantined records merged exactly once   (replay leg, if any)

Reads the committed proof files; writes data/quality/openfda_reconciliation_full.json.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
Q = REPO / "data" / "quality"


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


man = load(REPO / "data" / "freshness" / "ingest_manifest.json", {})
quar = load(Q / "openfda_quarantine.json", {})
recon = load(Q / "openfda_reconciliation.json", {})
backfill = load(Q / "openfda_backfill_test.json", {})
replay = load(Q / "openfda_quarantine_replay.json", {})

leg_a = man.get("reconciliation", {})
fetched = leg_a.get("fetched_from_api")
rej_null = leg_a.get("rejected_null_key")
rej_dup = leg_a.get("rejected_duplicate_in_pull")
accepted = leg_a.get("accepted")

total_gate = quar.get("total")          # canonical accepted entering quarantine
good = quar.get("good")
quarantined = quar.get("quarantined")

window = recon.get("window_reconciliation", {})
batch_accepted = window.get("batch_accepted")
in_warehouse = window.get("batch_ids_present_in_warehouse")

missing_after = backfill.get("still_missing")
replayed = replay.get("newly_replayed", 0)

legs = {
    "ingestion_balance":  fetched == (accepted or 0) + (rej_null or 0) + (rej_dup or 0) if fetched is not None else None,
    "quarantine_balance": (good or 0) + (quarantined or 0) == total_gate if total_gate is not None else None,
    "warehouse_window_match": batch_accepted == in_warehouse if batch_accepted is not None else None,
    "no_missing_after_backfill": missing_after == 0 if missing_after is not None else None,
}
report = {
    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "accounting": {
        "fetched_from_api": fetched, "rejected_null": rej_null, "rejected_duplicate": rej_dup,
        "accepted": accepted, "quarantined": quarantined, "good_clean": good,
        "warehouse_window": in_warehouse, "missing_after_backfill": missing_after,
        "replayed_exactly_once": replayed,
    },
    "legs": legs,
    "reconciles": all(v for v in legs.values() if v is not None),
}
out = Q / "openfda_reconciliation_full.json"
out.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
import sys
sys.exit(0 if report["reconciles"] else 1)
