"""
openFDA FAERS ingestion — real, messy, scheduled (replaces synthetic Kaggle load).

Pulls live FDA adverse-event reports (api.fda.gov, free, no key), normalizes the
fields the warehouse cares about, and lands them with real audit lineage:
  - ingest_ts      ISO timestamp this batch landed (varies per run -> real freshness)
  - source_system  openfda_faers
  - row_hash       sha256 of canonical content (change detection / dedup)

Incremental by receivedate window so each run only pulls new/changed reports.

Usage:
  python ingestion/openfda_pull.py --since 20260101 --max 500
"""
from __future__ import annotations
import argparse, hashlib, json, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
API = "https://api.fda.gov/drug/event.json"
SOURCE = "openfda_faers"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch(since, until, skip, limit):
    url = f"{API}?search=receivedate:[{since}+TO+{until}]&limit={limit}&skip={skip}"
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.load(r)
    return d.get("results", []), d.get("meta", {}).get("results", {}).get("total", 0)


def _normalize(rec, ingest_ts):
    patient = rec.get("patient", {}) or {}
    drugs = patient.get("drug", []) or []
    reactions = patient.get("reaction", []) or []
    row = {
        "safetyreportid": rec.get("safetyreportid"),
        "receivedate": rec.get("receivedate"),
        "serious": rec.get("serious"),
        "seriousnessdeath": rec.get("seriousnessdeath"),
        "occurcountry": rec.get("occurcountry"),
        "patient_sex": patient.get("patientsex"),
        "patient_age": patient.get("patientonsetage"),
        "primary_drug": (drugs[0].get("medicinalproduct") if drugs else None),
        "n_drugs": len(drugs),
        "reactions": ";".join(r.get("reactionmeddrapt", "") for r in reactions if r.get("reactionmeddrapt")) or None,
        "n_reactions": len(reactions),
        "source_system": SOURCE,
        "ingest_ts": ingest_ts,
    }
    canonical = json.dumps({k: v for k, v in row.items() if k != "ingest_ts"}, sort_keys=True)
    row["row_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--since", default="20260101")
    ap.add_argument("--until", default=datetime.now(timezone.utc).strftime("%Y%m%d"))
    ap.add_argument("--max", type=int, default=500)
    ap.add_argument("--out", type=Path, default=REPO / "data" / "raw" / "openfda")
    args = ap.parse_args()

    ingest_ts = _utc_now()
    args.out.mkdir(parents=True, exist_ok=True)
    (REPO / "data" / "freshness").mkdir(parents=True, exist_ok=True)

    # reconciliation counters (mass balance: fetched = accepted + rejected)
    rows, seen, skip, limit, total = [], set(), 0, min(100, args.max), 0
    fetched = dedup_dropped = null_rejected = 0
    t0 = time.time()
    while len(rows) < args.max:
        batch, total = _fetch(args.since, args.until, skip, min(limit, args.max - len(rows)))
        if not batch:
            break
        for rec in batch:
            fetched += 1
            rid = rec.get("safetyreportid")
            if not rid:                 # rejected: null key (documented rejection rule)
                null_rejected += 1
                continue
            if rid in seen:             # rejected: duplicate id within this pull window
                dedup_dropped += 1
                continue
            seen.add(rid)
            rows.append(_normalize(rec, ingest_ts))
        skip += len(batch)
        if len(batch) < limit or skip >= 25000:
            break
    accepted = len(rows)

    part = args.out / f"ingest_date={ingest_ts[:10]}"
    part.mkdir(parents=True, exist_ok=True)
    out_file = part / f"openfda_{ingest_ts.replace(':', '').replace('-', '')}.jsonl"
    with out_file.open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    null_rate = null_rejected / max(fetched, 1)
    manifest = {
        "source_system": SOURCE,
        "source_url": API,
        "last_successful_ingest": ingest_ts,
        "window": {"since": args.since, "until": args.until},
        "reconciliation": {                       # leg a→b: API fetch → accepted after rules
            "fetched_from_api": fetched,
            "rejected_null_key": null_rejected,
            "rejected_duplicate_in_pull": dedup_dropped,
            "accepted": accepted,
            "balances": fetched == accepted + null_rejected + dedup_dropped,
        },
        "records_landed": accepted,
        "total_matching_source": total,
        "null_key_rate": round(null_rate, 4),
        "ingest_latency_seconds": round(time.time() - t0, 1),
        "output": str(out_file.relative_to(REPO)),
    }
    (REPO / "data" / "freshness" / "ingest_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    print(f"\n[ok] landed {len(rows)} real openFDA reports -> {out_file.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
