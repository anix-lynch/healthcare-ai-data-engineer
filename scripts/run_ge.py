"""Great Expectations validation of the enriched L1 dataset.

Owns the STANDARD tabular contract — schema, nulls, value ranges, allowed sets,
uniqueness — and renders Data Docs (HTML) as the human-readable proof. The
domain-specific checks GE can't express (PII regex over free-text clinical
notes, encounter->patient identity resolution) stay in scripts/checkpoint.py.
That split is deliberate: GE for the standard column contract, custom code for
the healthcare-specific guards. See README "Data quality: two layers".

Run:  .ge-venv/bin/python scripts/run_ge.py   (or: make ge)
Out:  great_expectations/ (suite + config) + Data Docs HTML, exit 1 on failure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import great_expectations as gx

REPO = Path(__file__).resolve().parent.parent
# Relative on purpose — GX persists this string into great_expectations.yml, so an
# absolute /Users/... path would leak into the public repo. Resolved via chdir(REPO).
CSV = "data/raw/healthcare_dataset_enriched.csv"
GE_ROOT = REPO / "gx"
SUITE = "l1_data_quality"

# Ranges below are medically-valid bounds the real 497-row data sits inside —
# not fit to the data, so they'd actually catch drift if new rows broke them.
RANGES = {
    "Age": (0, 120),
    "bp_systolic": (50, 260),
    "bp_diastolic": (30, 160),
    "heart_rate": (30, 220),
    "respiratory_rate": (5, 60),
    "temperature_f": (94, 107),
    "spo2_pct": (70, 100),
    "Billing Amount": (0, 1_000_000),
}
NOT_NULL = ["Name", "Age", "Gender", "esi_tier_truth", "chief_complaint", "row_hash"]
ALLOWED = {
    "Gender": ["Female", "Male"],
    "esi_tier_truth": [1, 2, 3, 4, 5],
    "Test Results": ["Abnormal", "Inconclusive", "Normal"],
    "pii_redaction_status": ["cleared"],
}


def main() -> int:
    os.chdir(REPO)  # so the relative CSV path resolves AND gets stored relative
    context = gx.get_context(project_root_dir=str(REPO))
    ds = context.sources.add_or_update_pandas("healthcare_l1")
    asset = ds.add_csv_asset("enriched_encounters", filepath_or_buffer=CSV)
    context.add_or_update_expectation_suite(SUITE)
    validator = context.get_validator(
        batch_request=asset.build_batch_request(), expectation_suite_name=SUITE
    )

    # 33-column schema contract
    validator.expect_table_column_count_to_equal(33)
    # non-null critical columns
    for col in NOT_NULL:
        validator.expect_column_values_to_not_be_null(col)
    # numeric ranges (medically valid)
    for col, (lo, hi) in RANGES.items():
        validator.expect_column_values_to_be_between(col, min_value=lo, max_value=hi)
    # allowed categorical sets
    for col, vals in ALLOWED.items():
        validator.expect_column_values_to_be_in_set(col, vals)
    # esi tier is the clinical truth label — must be 1..5, never null
    validator.expect_column_values_to_be_between("esi_tier_truth", min_value=1, max_value=5)
    # every row carries a unique content hash (dedupe guarantee)
    validator.expect_column_values_to_be_unique("row_hash")

    validator.save_expectation_suite(discard_failed_expectations=False)

    checkpoint = context.add_or_update_checkpoint(name="l1_ge_checkpoint", validator=validator)
    result = checkpoint.run()
    context.build_data_docs()

    n = len(result.list_validation_results()[0]["results"])
    passed = result.success
    print(f"Great Expectations: {n} expectations, suite '{SUITE}' -> "
          f"{'PASS' if passed else 'FAIL'}")
    print(f"Data Docs: {GE_ROOT / 'uncommitted' / 'data_docs' / 'local_site' / 'index.html'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
