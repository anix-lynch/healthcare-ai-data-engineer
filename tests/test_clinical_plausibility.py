"""Clinical plausibility gate — toddler+Viagra class failures."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from clinical_plausibility import check_row  # noqa: E402


def test_toddler_viagra_fails():
    row = {"Name": "test kid", "Age": "2", "Medication": "Viagra"}
    reasons = check_row(row)
    assert reasons, "age=2 + Viagra must fail clinical plausibility"
    assert any("clinical_plausibility_hard" in r for r in reasons)


def test_teen_lipitor_hard_fail():
    row = {"Name": "teen", "Age": "16", "Medication": "Lipitor"}
    reasons = check_row(row)
    assert reasons
    assert any("clinical_plausibility_hard" in r for r in reasons)


def test_adult_lipitor_passes():
    row = {"Name": "adult", "Age": "45", "Medication": "Lipitor"}
    assert check_row(row) == []


def test_child_penicillin_passes():
    row = {"Name": "kid", "Age": "8", "Medication": "Penicillin"}
    assert check_row(row) == []


def test_child_lipitor_fails():
    row = {"Age": 10, "medication": "lipitor"}
    reasons = check_row(row)
    assert any("clinical_plausibility_hard" in r for r in reasons)
