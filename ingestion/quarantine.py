"""
Record-level quarantine (Bullet 1 — process malformed records safely).

Before this, ONE malformed record fail-closed the whole batch. That's safe but not
resilient. Quarantine isolates the bad records, lets the GOOD records flow to the
warehouse, and only escalates (fail-closed) when malformed data is WIDESPREAD —
because a widespread break is an unsafe condition a human should see, not auto-pass.

malformed = breaks the data CONTRACT: a required field missing/empty, or an
unparseable receivedate. (Duplicates and value-domain are handled by the gate.)

  good      -> data/clean/openfda_clean.jsonl   (flows to bq_load)
  bad       -> data/quarantine/quarantine.jsonl (isolated, reason-tagged, replayable)
  report    -> data/quality/openfda_quarantine.json
  escalate  -> exit 1 if quarantine_rate > threshold (widespread = unsafe)

good + quarantined == total  (mass balance, machine-checked).
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ingestion"))
from openfda_gate import _load

REQUIRED = ["safetyreportid", "row_hash", "source_system", "receivedate", "ingest_ts"]
CLEAN_DIR = REPO / "data" / "clean"          # downstream stages read this via OPENFDA_DATA_DIR
CLEAN = CLEAN_DIR / "openfda_clean.jsonl"
QUAR = REPO / "data" / "quarantine" / "quarantine.jsonl"
RPT = REPO / "data" / "quality" / "openfda_quarantine.json"


def classify(r):
    """Return a reason string if the record is malformed, else None."""
    for f in REQUIRED:
        if r.get(f) in (None, ""):
            return f"missing_required:{f}"
    d = str(r.get("receivedate"))
    if not (len(d) == 8 and d.isdigit()):
        return "unparseable_receivedate"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=REPO / "data" / "raw" / "openfda")
    ap.add_argument("--threshold", type=float, default=0.10, help="escalate if quarantine rate exceeds this")
    args = ap.parse_args()

    rows, _ = _load(args.data)
    good, bad = [], []
    for r in rows:
        reason = classify(r)
        (bad if reason else good).append({**r, "_quarantine_reason": reason} if reason else r)

    total = len(rows)
    rate = round(len(bad) / max(total, 1), 4)
    CLEAN.parent.mkdir(parents=True, exist_ok=True)
    QUAR.parent.mkdir(parents=True, exist_ok=True)
    CLEAN.write_text("\n".join(json.dumps(r) for r in good) + ("\n" if good else ""))
    QUAR.write_text("\n".join(json.dumps(r) for r in bad) + ("\n" if bad else ""))

    widespread = rate > args.threshold
    report = {
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "total": total, "good": len(good), "quarantined": len(bad),
        "quarantine_rate": rate, "threshold": args.threshold,
        "balances": len(good) + len(bad) == total,
        "reasons": _count_reasons(bad),
        "widespread_escalation": widespread,
        "decision": "escalate_fail_closed" if widespread else "isolate_and_continue",
    }
    RPT.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if widespread:
        print(f"\n[ESCALATE] quarantine rate {rate} > {args.threshold} — widespread malformed, "
              f"fail-closed (good records NOT loaded)", file=sys.stderr)
        return 1
    print(f"\n[ok] quarantined {len(bad)}/{total} ({rate}); {len(good)} good records continue")
    return 0


def _count_reasons(bad):
    from collections import Counter
    return dict(Counter(r["_quarantine_reason"] for r in bad))


if __name__ == "__main__":
    sys.exit(main())
