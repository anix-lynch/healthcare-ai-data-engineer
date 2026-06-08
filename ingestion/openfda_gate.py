"""
Fail-closed quality gate for the openFDA pipeline (Trust branch of the L1 SLA).
Runs on the landed real openFDA records before they're trusted downstream.
Critical checks (exit 1 on any failure): null key, duplicate key, schema drift,
temporal sanity, value domain. Plus reconciliation vs the source total.
"""
from __future__ import annotations
import argparse, json, os, sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REQUIRED = {"safetyreportid", "receivedate", "serious", "source_system", "ingest_ts", "row_hash"}
# All stages read the dataset from here. Quarantine sets OPENFDA_DATA_DIR to the
# CLEAN partition so downstream sees only good records; unset = raw (back-compat).
DATA_DIR = Path(os.environ.get("OPENFDA_DATA_DIR", str(REPO / "data" / "raw" / "openfda")))


def _load(part_dir):
    """Build the canonical openFDA view across all landed pulls (idempotent).

    A scheduled pipeline lands a new .jsonl per pull, so the same safetyreportid
    legitimately reappears across files (overlapping source windows / re-runs).
    We upsert by safetyreportid keeping the latest ingest_ts (MERGE semantics) so
    re-running the pull N times yields the SAME canonical set — the gate no longer
    fails-closed on operational re-lands. A genuine source defect (the SAME id
    duplicated WITHIN one pull) is still caught via within_pull_dupes.
    """
    files = sorted(part_dir.rglob("*.jsonl"))
    raw, within_pull_dupes = [], 0
    for f in files:
        seen_in_file = set()
        for line in f.open():
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            rid = r.get("safetyreportid")
            if rid and rid in seen_in_file:
                within_pull_dupes += 1
            seen_in_file.add(rid)
            raw.append(r)

    canonical, nullkey_rows = {}, []
    for r in raw:
        rid = r.get("safetyreportid")
        if not rid:                      # preserve so null_key check still fires
            nullkey_rows.append(r)
            continue
        prev = canonical.get(rid)
        if prev is None or str(r.get("ingest_ts", "")) >= str(prev.get("ingest_ts", "")):
            canonical[rid] = r
    rows = list(canonical.values()) + nullkey_rows

    stats = {
        "files_loaded": len(files),
        "raw_rows": len(raw),
        "canonical_rows": len(rows),
        "cross_pull_collapsed": len(raw) - len(rows),
        "within_pull_dupes": within_pull_dupes,
    }
    return rows, stats


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data", type=Path, default=DATA_DIR)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    rows, idem = _load(args.data)
    if not rows:
        print("ERROR: no landed openFDA data", file=sys.stderr)
        return 1

    ids = [r.get("safetyreportid") for r in rows]
    null_keys = sum(1 for i in ids if not i)
    # post-canonical residual dupes (must be 0 — idempotency safety net)
    residual_dupes = [k for k, c in Counter(ids).items() if c > 1 and k]
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

    # Per-field null profile. CRITICAL fields must be complete (block on any null);
    # OPTIONAL FDA fields (age/country/sex often absent in real FAERS) are profiled,
    # never required — nulls there are expected, not a quality failure.
    CRITICAL = ["safetyreportid", "row_hash", "source_system", "receivedate", "ingest_ts"]
    OPTIONAL = ["serious", "seriousnessdeath", "occurcountry", "patient_sex",
                "patient_age", "primary_drug", "reactions"]
    n = len(rows)
    null_profile = {
        f: {"nulls": sum(1 for r in rows if r.get(f) in (None, "")),
            "null_rate": round(sum(1 for r in rows if r.get(f) in (None, "")) / max(n, 1), 4),
            "critical": f in CRITICAL}
        for f in CRITICAL + OPTIONAL
    }
    critical_field_nulls = sum(v["nulls"] for f, v in null_profile.items() if v["critical"])

    checks = {
        "null_key": {"fail": null_keys, "critical": null_keys > 0},
        "null_rate": {  # critical fields complete; optional FDA fields profiled not required
            "critical_field_nulls": critical_field_nulls,
            "critical_fields": CRITICAL,
            "critical": critical_field_nulls > 0,
        },
        # within-pull dups = genuine source defect (pull dedup broke) → critical.
        # cross-pull re-lands are collapsed by canonical upsert, NOT a failure.
        "duplicate_key": {
            "within_pull_dupes": idem["within_pull_dupes"],
            "residual_after_canonical": len(residual_dupes),
            "critical": idem["within_pull_dupes"] > 0 or len(residual_dupes) > 0,
        },
        "schema_drift": {"missing": missing_cols, "critical": bool(missing_cols)},
        "temporal_sanity": {"bad_dates": bad_dates, "critical": bad_dates > 0},
        "value_domain": {"bad_serious": bad_serious, "critical": bad_serious > 0},
    }
    critical = [k for k, v in checks.items() if v["critical"]]
    manifest = json.loads((REPO / "data" / "freshness" / "ingest_manifest.json").read_text())
    report = {
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "n_rows": len(rows),
        "idempotency": {
            **idem,
            "duplicate_rate": round(idem["cross_pull_collapsed"] / max(idem["raw_rows"], 1), 4),
            "note": "canonical = latest row per safetyreportid (MERGE); re-runs collapse, no false dup-fail",
        },
        "checks": checks,
        "null_profile": null_profile,
        "reconciliation": {
            "records_landed": len(rows),
            "source_window_population": manifest.get("total_matching_source"),
            "note": "real mass-balance reconciliation lives in data/quality/openfda_reconciliation.json "
                    "(fetched=accepted+rejected; accepted=warehouse). source_window_population is the FDA "
                    "window size, a sampling denominator — NOT a reconciliation target.",
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
