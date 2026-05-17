"""Unit tests for the patient identity resolver.

scripts/patient_identity.py is the canonical encounter → patient_id bridge.
These tests cover the deterministic-hash + name-normalization contract.
"""
from __future__ import annotations
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from patient_identity import normalize_name, patient_id_from_name, encounter_id_from_row_idx


def test_normalize_name_lowercases_and_collapses():
    assert normalize_name("Bobby JacksOn") == "bobby jackson"
    assert normalize_name("  EXTRA   spaces  ") == "extra spaces"
    assert normalize_name("") == ""


def test_patient_id_is_deterministic():
    """Same name → same patient_id, always."""
    a = patient_id_from_name("Bobby Jackson")
    b = patient_id_from_name("BOBBY  jackson")  # different casing + extra space
    c = patient_id_from_name("bobby jackson")
    assert a == b == c, f"expected same, got {a}, {b}, {c}"


def test_patient_id_changes_with_different_name():
    """Different names → different ids (high probability, SHA256 collision space)."""
    a = patient_id_from_name("Bobby Jackson")
    b = patient_id_from_name("Alice Smith")
    assert a != b


def test_patient_id_format():
    """Expected shape: P-{10-char hex}."""
    pid = patient_id_from_name("Test Patient")
    assert pid.startswith("P-")
    assert len(pid) == 12  # "P-" + 10 chars
    # All hex
    assert all(c in "0123456789abcdef" for c in pid[2:])


def test_empty_name_returns_unknown():
    assert patient_id_from_name("") == "P-unknown"
    assert patient_id_from_name("   ") == "P-unknown"


def test_encounter_id_format():
    """L1-NNNNNN zero-padded."""
    assert encounter_id_from_row_idx(0) == "L1-000000"
    assert encounter_id_from_row_idx(42) == "L1-000042"
    assert encounter_id_from_row_idx(99999) == "L1-099999"
