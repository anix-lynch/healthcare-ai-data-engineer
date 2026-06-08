"""
Freshness gate for the openFDA pipeline (Freshness branch of the L1 SLA).
Reads the ingest manifest + SLA config, computes data latency, SLA status
(fresh/warn/stale), and fires a stale-table alert. Run after every ingest.
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "data" / "freshness" / "ingest_manifest.json"
SLA = REPO / "config" / "freshness_sla.json"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    if not MANIFEST.exists():
        print("ERROR: no ingest manifest", file=sys.stderr)
        return 1
    m = json.loads(MANIFEST.read_text())
    sla = json.loads(SLA.read_text()) if SLA.exists() else {"warn_after_h": 24, "error_after_h": 48}
    last = datetime.strptime(m["last_successful_ingest"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    latency_h = (datetime.now(timezone.utc) - last).total_seconds() / 3600
    warn, err = sla["warn_after_h"], sla["error_after_h"]
    status = "fresh" if latency_h < warn else ("warn" if latency_h < err else "stale")
    report = {
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "last_successful_ingest": m["last_successful_ingest"],
        "data_latency_hours": round(latency_h, 2),
        "sla": {"warn_after_h": warn, "error_after_h": err},
        "sla_status": status,
        "records_landed": m.get("records_landed"),
        "stale_alert": status == "stale",
    }
    (REPO / "data" / "freshness" / "freshness_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if status == "stale":
        print(f"\n[STALE] data {latency_h:.1f}h old (> {err}h SLA) -- alert fired", file=sys.stderr)
        if args.strict:
            return 1
    else:
        print(f"\n[ok] {status.upper()}: data {latency_h:.1f}h old (SLA warn {warn}h / err {err}h)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
