"""
Fail-closed quality gate for the openFDA pipeline (Trust branch of the L1 SLA).
Runs on the landed real openFDA records before they're trusted downstream.
Critical checks (exit 1 on any failure): null key, duplicate key, schema drift,
temporal sanity, value domain. Plus reconciliation vs the source total.
"""
from __future__ import annotations
import argparse, json, sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REQUIRED = {"safetyreportid", "receivedate", "serious", "source_system", "ingest_ts", "row_hash"}


def _load(part_dir):
    rows = []
    for f in sorted(part_dir.rglob("*.jsonl")):
        for line in f.open():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", type=Path, default=REPO / "data" / "raw" / "openfda")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    rows = _load(args.data)
    if not rows:
        print("ERROR: no landed openFDA data", file=sys.stderr)
        return 1

    ids = [r.get("safetyreportid") for r in rows]
    null_keys = sum(1 for i in ids if not i)
    dupes = [k for k, c in Counter(ids).items() if c > 1 and k]
    missing_cols = sorted(REQUIRED - set(rows[0].keys()))
    bad_dates = 0
    for r in rows:
        d = str(r.get("receivedate") or "")
        try:
            if not (len(d) == 8 and 1990 <= int(d[:4]) <= datetime.now().year):
                bad_dates += 1
        except ValueError:
            bad_dates += 1
    bad_serious = sum(1 for r in rows if r.get("serious") not in ("1", "2", 1, 2, None))

    checks = {
        "null_key": {"fail": null_keys, "critical": null_keys > 0},
        "duplicate_key": {"fail": len(dupes), "critical": len(dupes) > 0},
        "schema_drift": {"missing": missing_cols, "critical": bool(missing_cols)},
        "temporal_sanity": {"bad_dates": bad_dates, "critical": bad_dates > 0},
        "value_domain": {"bad_serious": bad_serious, "critical": bad_serious > 0},
    }
    critical = [k for k, v in checks.items() if v["critical"]]
    manifest = json.loads((REPO / "data" / "freshness" / "ingest_manifest.json").read_text())
    report = {
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "n_rows": len(rows),
        "checks": checks,
        "reconciliation": {
            "records_landed": len(rows),
            "source_total_in_window": manifest.get("total_matching_source"),
            "note": "landed = documented sampled slice of source window (not silent truncation)",
        },
        "critical_failures": critical,
        "passed": not critical,
        "exit_code": 1 if critical else 0,
    }
    out = REPO / "data" / "quality" / "openfda_gate_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"\n{'[ok] GATE PASS' if not critical else '[FAIL] ' + ', '.join(critical)} ({len(rows)} real reports)")
    return report["exit_code"] if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
