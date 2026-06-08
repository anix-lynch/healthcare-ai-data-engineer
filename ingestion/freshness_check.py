"""
Freshness gate for the openFDA pipeline (Freshness branch of the L1 SLA).

Three honest clocks (the old version had only #2, which let a 3-month-old FDA
record pulled today read "fresh 0h" — a lie):
  1. source freshness   — age of the NEWEST FDA record we hold (max receivedate).
                          openFDA is quarterly, so old is normal; we DISPLAY it,
                          and only warn if the source feed itself looks stalled.
  2. ingestion freshness — now - last_successful_ingest (did OUR pipeline run?).
                          This drives the stale alert / fail-closed exit.
  3. warehouse lag       — ingest_ts -> landed in BigQuery (from reconciliation report).

Run after every ingest. --strict exits non-zero when ingestion is stale. NB: the
stale flag + exit code + JSON report = DETECTION (an escalation artifact). It is
not an external notification — no email/Slack channel is wired.
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ingestion"))
from openfda_gate import _load

MANIFEST = REPO / "data" / "freshness" / "ingest_manifest.json"
RECON = REPO / "data" / "quality" / "openfda_reconciliation.json"
SLA = REPO / "config" / "freshness_sla.json"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    if not MANIFEST.exists():
        print("ERROR: no ingest manifest", file=sys.stderr)
        return 1
    m = json.loads(MANIFEST.read_text())
    sla = json.loads(SLA.read_text()) if SLA.exists() else {}
    warn = sla.get("warn_after_h", 24)
    err = sla.get("error_after_h", 48)
    source_warn_days = sla.get("source_warn_days", 120)  # quarterly feed + buffer
    now = datetime.now(timezone.utc)

    # clock 2 — ingestion freshness (pipeline health, drives the alert)
    last = datetime.strptime(m["last_successful_ingest"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    ingestion_latency_h = round((now - last).total_seconds() / 3600, 2)
    status = "fresh" if ingestion_latency_h < warn else ("warn" if ingestion_latency_h < err else "stale")

    # clock 1 — source freshness (age of NEWEST FDA record held; no more "fresh 0h" lie)
    rows, _ = _load(REPO / "data" / "raw" / "openfda")
    recv = [str(r.get("receivedate")) for r in rows if r.get("receivedate")]
    source = {}
    if recv:
        newest = max(recv)
        try:
            newest_dt = datetime.strptime(newest, "%Y%m%d").replace(tzinfo=timezone.utc)
            age_days = (now - newest_dt).days
            source = {"newest_record_receivedate": newest, "source_age_days": age_days,
                      "source_feed_status": "ok" if age_days <= source_warn_days else "feed_may_be_stalled"}
        except ValueError:
            source = {"newest_record_receivedate": newest, "source_age_days": None}

    # clock 3 — warehouse lag (ingest_ts -> BigQuery), from reconciliation report
    warehouse_lag_s = None
    if RECON.exists():
        warehouse_lag_s = json.loads(RECON.read_text()).get(
            "leg_b_accepted_to_warehouse", {}).get("warehouse_lag_seconds")

    report = {
        "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "clocks": {
            "source_freshness": source,
            "ingestion_freshness": {"last_successful_ingest": m["last_successful_ingest"],
                                    "ingestion_latency_hours": ingestion_latency_h,
                                    "sla": {"warn_after_h": warn, "error_after_h": err},
                                    "status": status},
            "warehouse_lag": {"warehouse_lag_seconds": warehouse_lag_s},
        },
        "records_landed": m.get("records_landed"),
        "sla_status": status,
        "stale_alert": status == "stale",
    }
    (REPO / "data" / "freshness" / "freshness_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if status == "stale":
        print(f"\n[STALE] pipeline data {ingestion_latency_h:.1f}h old (> {err}h SLA) -- detected; "
              f"escalation artifact freshness_report.json (no external notifier wired)", file=sys.stderr)
        if args.strict:
            return 1
    else:
        sa = source.get("source_age_days")
        print(f"\n[ok] {status.upper()}: ingestion {ingestion_latency_h:.1f}h old "
              f"(SLA warn {warn}h/err {err}h) | newest FDA record {sa}d old | "
              f"warehouse lag {warehouse_lag_s}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
