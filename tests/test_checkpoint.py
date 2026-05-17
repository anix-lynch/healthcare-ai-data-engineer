"""Smoke the L1 data quality gate on the shipped enriched corpus."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT = REPO_ROOT / "data" / "quality" / "l1_checkpoint_report.json"


def test_checkpoint_runs_and_passes():
    """Checkpoint script exits 0 (no critical failures) on the enriched CSV."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "checkpoint.py"), "--quiet"],
        cwd=str(REPO_ROOT),
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"checkpoint failed: {result.stderr}"
    assert REPORT.exists(), f"report not written at {REPORT}"
    report = json.loads(REPORT.read_text())
    assert report["passed"] is True, f"critical_failures: {report['critical_failures']}"


def test_identity_map_has_expected_shape():
    """Patient identity map resolves the 55K corpus to ~40K unique patients."""
    m = json.loads((REPO_ROOT / "data" / "derived" / "patient_identity_map.json").read_text())
    s = m["stats"]
    assert s["n_encounters"] > 50000
    assert s["n_unique_patients"] > 30000
    assert s["max_encounters_per_patient"] > 5  # at least some repeaters
