"""
Fail-closed end-to-end proof (Trust + resilience).

audit requirement: prove the pipeline STOPS (non-zero exit) on bad data, and runs
clean to success on good data. We exercise the real gate binary via subprocess so
the receipt reflects actual exit codes, not in-process asserts.

  Case A (corrupted fixture): within-pull duplicate id  -> gate --strict MUST exit != 0
  Case B (clean real data):   gate + GE --strict         -> MUST exit 0

Writes data/quality/openfda_failclose_test.json. Exits 1 unless A fails-closed AND B passes.
"""
from __future__ import annotations
import json, shutil, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REAL = REPO / "data" / "raw" / "openfda"
TMP = Path("/tmp/hcde_failclose_fixture/openfda")


def run(cmd, data=None):
    c = [sys.executable, str(REPO / "ingestion" / "openfda_gate.py"), "--strict"]
    if data:
        c += ["--data", str(data)]
    return subprocess.run(c, capture_output=True, text=True).returncode


def main():
    # Case A: build a corrupted fixture (duplicate one id WITHIN a single pull file)
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    src = sorted(REAL.rglob("*.jsonl"))[0]
    part = TMP / "ingest_date=2026-06-08"
    part.mkdir(parents=True)
    lines = src.read_text().splitlines()
    bad = part / "corrupt.jsonl"
    bad.write_text("\n".join(lines + [lines[0]]) + "\n")  # append dup of first row
    # manifest needed by the gate
    (REPO / "data" / "freshness").mkdir(parents=True, exist_ok=True)
    a_exit = run("gate", data=TMP)

    # Case B: clean real data through gate + GE
    b_gate = run("gate")
    b_ge = subprocess.run(
        [str(REPO / ".ge-venv" / "bin" / "python"), str(REPO / "ingestion" / "ge_validate.py"), "--strict"],
        capture_output=True, text=True).returncode

    shutil.rmtree(TMP, ignore_errors=True)

    checks = {
        "A_corrupt_fixture_fails_closed": a_exit != 0,
        "B_clean_gate_passes": b_gate == 0,
        "B_clean_ge_passes": b_ge == 0,
    }
    report = {"test": "fail_closed_end_to_end",
              "exit_codes": {"A_corrupt_gate": a_exit, "B_clean_gate": b_gate, "B_clean_ge": b_ge},
              "checks": checks, "passed": all(checks.values())}
    out = REPO / "data" / "quality" / "openfda_failclose_test.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
