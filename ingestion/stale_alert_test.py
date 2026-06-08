"""
Stale-alert proof (Freshness branch). Codex DOD: a stale fixture must make the
freshness gate fire an alert AND exit non-zero (fail-closed), not die silently.

  Case A (stale fixture): manifest ingest_ts forced 72h old (> 48h err SLA)
                          -> freshness_check --strict MUST exit != 0 and stale_alert=true
  Case B (fresh real):    real manifest -> MUST exit 0, stale_alert=false

Backs up/restores the real manifest. Writes data/quality/openfda_stale_alert_test.json.
"""
from __future__ import annotations
import json, subprocess, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MAN = REPO / "data" / "freshness" / "ingest_manifest.json"
RPT = REPO / "data" / "freshness" / "freshness_report.json"
FRESH = [sys.executable, str(REPO / "ingestion" / "freshness_check.py"), "--strict"]


def run():
    rc = subprocess.run(FRESH, capture_output=True, text=True).returncode
    alert = json.loads(RPT.read_text()).get("stale_alert") if RPT.exists() else None
    return rc, alert


def main():
    real = MAN.read_text()
    m = json.loads(real)

    # Case A — stale fixture (72h old)
    old = (datetime.now(timezone.utc) - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%SZ")
    m_stale = dict(m); m_stale["last_successful_ingest"] = old
    MAN.write_text(json.dumps(m_stale, indent=2))
    a_rc, a_alert = run()

    # Case B — restore real, must be fresh
    MAN.write_text(real)
    b_rc, b_alert = run()

    checks = {
        "stale_fixture_exits_nonzero": a_rc != 0,
        "stale_alert_fired": a_alert is True,
        "fresh_real_exits_zero": b_rc == 0,
        "fresh_no_false_alert": b_alert is False,
    }
    report = {"test": "stale_alert_fires", "exit_codes": {"A_stale": a_rc, "B_fresh": b_rc},
              "stale_alert": {"A_stale": a_alert, "B_fresh": b_alert},
              "checks": checks, "passed": all(checks.values())}
    out = REPO / "data" / "quality" / "openfda_stale_alert_test.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
