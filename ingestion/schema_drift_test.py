"""
Schema-drift negative test + honest scope (Trust / audit QA gap #2).

HONEST SCOPE: the gate validates the NORMALIZED openFDA data contract — the fixed
field set our ingestion produces (REQUIRED columns). It catches a required field
going missing or the output shape breaking. It is NOT comprehensive live-FDA-API
drift detection: openfda_pull.py normalizes raw FAERS into a fixed schema, so a
change to an FDA *optional* / nested field upstream may pass unseen. Claim it as
"normalized openFDA contract validation", never "detects all live API schema drift".

This test proves the contract check actually bites:
  drop a REQUIRED column from a fixture -> gate --strict MUST exit !=0 (schema_drift critical).
Writes data/quality/openfda_schema_drift_test.json.
"""
from __future__ import annotations
import json, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REAL = REPO / "data" / "raw" / "openfda"
TMP = Path("/tmp/hcde_schema_fixture/openfda")
GATE = [sys.executable, str(REPO / "ingestion" / "openfda_gate.py"), "--strict"]
DROP = "row_hash"  # a REQUIRED contract column


def main():
    if TMP.exists():
        shutil.rmtree(TMP)
    part = TMP / "ingest_date=2026-06-08"
    part.mkdir(parents=True)
    src = sorted(REAL.rglob("*.jsonl"))[0]
    # build a fixture with the required column dropped from every row
    out = []
    for line in src.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        r.pop(DROP, None)
        out.append(json.dumps(r))
    (part / "drift.jsonl").write_text("\n".join(out) + "\n")

    rc = subprocess.run(GATE + ["--data", str(TMP)], capture_output=True, text=True).returncode
    # confirm it was specifically schema_drift that fired
    rpt = json.loads((REPO / "data" / "quality" / "openfda_gate_report.json").read_text())
    drift_critical = rpt["checks"]["schema_drift"]["critical"]
    missing = rpt["checks"]["schema_drift"]["missing"]
    shutil.rmtree(TMP, ignore_errors=True)
    subprocess.run(GATE, capture_output=True, text=True)  # restore real report

    checks = {"dropped_required_col_exits_nonzero": rc != 0,
              "schema_drift_flagged_critical": bool(drift_critical),
              "missing_col_identified": DROP in missing}
    report = {"test": "schema_drift_negative", "dropped_column": DROP, "gate_exit": rc,
              "missing_reported": missing, "checks": checks, "passed": all(checks.values()),
              "scope": "normalized openFDA contract validation (NOT comprehensive live-API drift detection)"}
    out_f = REPO / "data" / "quality" / "openfda_schema_drift_test.json"
    out_f.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
