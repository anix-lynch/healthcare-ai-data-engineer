"""Validate the L1.25 Feast feature definitions load and are well-formed.

This is what makes the feature layer a *tested, reproducible* deliverable rather
than a file that merely exists: the definitions are constructed and asserted on
every `pytest tests/` run (no BigQuery / network needed — object construction is
offline). `feast apply` (which does need BigQuery) is the separate `make
feast-apply` target documented in feature-store/README.md.

Skips cleanly if `feast` is not installed in the active interpreter, so the core
API test suite still runs without the feature-store extra.
"""

import importlib.util
from pathlib import Path

import pytest

feast = pytest.importorskip("feast")  # skip if the feature-store extra isn't installed

FEATURES_PY = Path(__file__).resolve().parent.parent / "feature-store" / "features.py"


def _load():
    spec = importlib.util.spec_from_file_location("l125_features", FEATURES_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_definitions_construct():
    """The whole module executes — Entity, source, FeatureView, FeatureService."""
    m = _load()
    assert m.patient.join_key == "patient_key"
    assert m.patient_encounter_features.name == "patient_encounter_features"
    assert m.high_utilizer_signal_features.name == "high_utilizer_signal_features"


def test_feature_schema_is_complete():
    """The 6 machine-ready features the L1.5 signal layer consumes are all present."""
    m = _load()
    fields = {f.name for f in m.patient_encounter_features.schema}
    assert fields == {
        "prior_encounter_count",
        "days_since_last_admission",
        "los_days",
        "is_emergency",
        "is_readmission",
        "prior_avg_los",
    }


def test_point_in_time_correctness_is_declared():
    """An event timestamp must drive the PIT join, or features leak the future."""
    m = _load()
    assert m.encounter_pit_source.timestamp_field == "event_timestamp"
    # the prior-only aggregate must exclude the current row
    assert "1 PRECEDING" in m.encounter_pit_source.query


def test_service_bundles_the_view():
    """The FeatureService the signal layer requests must expose the encounter view."""
    m = _load()
    served = {fv.name for fv in m.high_utilizer_signal_features._features}
    assert "patient_encounter_features" in served
