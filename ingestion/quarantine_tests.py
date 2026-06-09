"""
Quarantine + replay proof suite (Bullet 1 proofs 1, 2, and widespread-escalation).

A isolate-and-continue : malformed records quarantined, valid records continue (mass balance)
B replay-exactly-once  : fix a quarantined record -> replay merges it ONCE; re-run = no-op
C widespread-escalate  : malformed rate over threshold -> fail-closed, nothing proceeds
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys
from pathlib import Path
from google.cloud import bigquery

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable
FIX = Path("/tmp/hcde_quar_fixture/openfda")
QUAR = REPO / "data" / "quarantine" / "quarantine.jsonl"
LEDGER = REPO / "data" / "quarantine" / "replayed_ledger.json"
QRPT = REPO / "data" / "quality" / "openfda_quarantine.json"
TID = "TEST_QUAR_0001"
ENV = {**os.environ, "GCP_PROJECT_ID": "PROJECT", "BQ_DATASET": "healthcare_analytics", "BQ_LOCATION": "US"}


def make_fixture(n_bad, n_total=12):
    if FIX.exists():
        shutil.rmtree(FIX)
    part = FIX / "ingest_date=2026-06-08"; part.mkdir(parents=True)
    src = sorted((REPO / "data" / "raw" / "openfda").rglob("*.jsonl"))[0]
    recs = [json.loads(l) for l in src.read_text().splitlines() if l.strip()][:n_total]
    for i in range(n_bad):
        recs[i].pop("row_hash", None)            # malformed: missing required field
    (part / "f.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")


def run_quar(threshold):
    rc = subprocess.run([PY, "ingestion/quarantine.py", "--data", str(FIX),
                         "--threshold", str(threshold)], cwd=REPO, env=ENV,
                        capture_output=True, text=True).returncode
    return rc, json.loads(QRPT.read_text())


def test_A():
    make_fixture(n_bad=2, n_total=12)
    rc, r = run_quar(0.5)
    clean = REPO / "data" / "clean" / "openfda_clean.jsonl"
    n_clean = len([l for l in clean.read_text().splitlines() if l.strip()]) if clean.exists() else -1
    return {"exit": rc, "total": r["total"], "good": r["good"], "quarantined": r["quarantined"],
            "clean_file_rows": n_clean, "balances": r["balances"], "decision": r["decision"],
            "pass": (rc == 0 and r["good"] == 10 and r["quarantined"] == 2 and r["balances"]
                     and n_clean == 10 and r["decision"] == "isolate_and_continue")}


def test_B():
    c = bigquery.Client(project="PROJECT")
    jc = bigquery.QueryJobConfig(maximum_bytes_billed=100 * 1024 * 1024)
    def cnt(): return list(c.query(f"SELECT COUNT(*) n FROM healthcare_analytics.raw_openfda_events WHERE safetyreportid='{TID}'", job_config=jc).result())[0].n
    c.query(f"DELETE FROM healthcare_analytics.raw_openfda_events WHERE safetyreportid='{TID}'", job_config=jc).result()
    if LEDGER.exists(): LEDGER.unlink()
    fixed = {"safetyreportid": TID, "receivedate": "20260101", "serious": "1", "seriousnessdeath": None,
             "occurcountry": "US", "patient_sex": "1", "patient_age": None, "primary_drug": "TESTDRUG",
             "n_drugs": 1, "reactions": "Headache", "n_reactions": 1, "source_system": "openfda_faers",
             "ingest_ts": "2026-06-08T10:00:00Z", "row_hash": "fixedhash_TID"}
    QUAR.parent.mkdir(parents=True, exist_ok=True)
    QUAR.write_text(json.dumps(fixed) + "\n")          # a now-FIXED quarantined record
    r1 = subprocess.run([PY, "ingestion/quarantine_replay.py"], cwd=REPO, env=ENV, capture_output=True, text=True)
    rep1 = json.loads((REPO / "data" / "quality" / "openfda_quarantine_replay.json").read_text())
    after1 = cnt()
    # replay AGAIN — must be a no-op (exactly once)
    QUAR.write_text(json.dumps(fixed) + "\n")          # even if it reappears, ledger blocks re-merge
    subprocess.run([PY, "ingestion/quarantine_replay.py"], cwd=REPO, env=ENV, capture_output=True, text=True)
    rep2 = json.loads((REPO / "data" / "quality" / "openfda_quarantine_replay.json").read_text())
    after2 = cnt()
    c.query(f"DELETE FROM healthcare_analytics.raw_openfda_events WHERE safetyreportid='{TID}'", job_config=jc).result()
    return {"replay1_newly": rep1["newly_replayed"], "bq_after1": after1,
            "replay2_newly": rep2["newly_replayed"], "bq_after2": after2,
            "pass": (rep1["newly_replayed"] == 1 and after1 == 1 and rep1["exactly_once"]
                     and rep2["newly_replayed"] == 0 and after2 == 1)}


def test_C():
    make_fixture(n_bad=6, n_total=10)                   # 60% malformed > 10% threshold
    rc, r = run_quar(0.10)
    return {"exit": rc, "quarantine_rate": r["quarantine_rate"], "decision": r["decision"],
            "pass": (rc != 0 and r["widespread_escalation"] and r["decision"] == "escalate_fail_closed")}


def main():
    res = {"A_isolate_and_continue": test_A(), "B_replay_exactly_once": test_B(),
           "C_widespread_escalate": test_C()}
    shutil.rmtree(FIX, ignore_errors=True)
    # restore real clean/quarantine from real raw
    subprocess.run([PY, "ingestion/quarantine.py"], cwd=REPO, env=ENV, capture_output=True, text=True)
    all_pass = all(v["pass"] for v in res.values())
    report = {"suite": "quarantine_replay", "scenarios": res, "all_pass": all_pass,
              "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()}
    (REPO / "data" / "quality" / "openfda_quarantine_tests.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v["pass"] for k, v in res.items()}, indent=2))
    print("all_pass:", all_pass)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
