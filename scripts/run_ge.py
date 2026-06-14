"""Great Expectations release gates at two data-platform boundaries.

The source contract validates every one of the 55,500 incoming rows before
promotion. Exact duplicates are deliberately handled by quarantine and
reconciliation rather than treated as a source-contract failure.

The enriched contract validates the smaller AI-facing clinical enrichment
slice before downstream retrieval/classification consumers may use it.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import great_expectations as gx

REPO = Path(__file__).resolve().parent.parent
GE_ROOT = REPO / "gx"
PROOF = REPO / "data" / "quality" / "ge_release_gate_report.json"


def _source_contract(validator) -> None:
    validator.expect_table_column_count_to_equal(15)
    validator.expect_table_row_count_to_equal(55_500)

    for col in [
        "Name", "Age", "Gender", "Blood Type", "Medical Condition",
        "Date of Admission", "Doctor", "Hospital", "Insurance Provider",
        "Billing Amount", "Room Number", "Admission Type", "Discharge Date",
        "Medication", "Test Results",
    ]:
        validator.expect_column_values_to_not_be_null(col)

    for col, lo, hi in [
        ("Age", 0, 120),
        ("Room Number", 1, 10_000),
    ]:
        validator.expect_column_values_to_be_between(col, min_value=lo, max_value=hi)
    # Negative billing adjustments are rare but present in the source. Treat
    # them as a tolerated exception population to investigate, not as a reason
    # to silently drop the whole delivery. The report preserves the exact
    # unexpected count; reconciliation still must account for every row.
    validator.expect_column_values_to_be_between(
        "Billing Amount", min_value=0, max_value=1_000_000, mostly=0.995
    )

    for col, values in {
        "Gender": ["Female", "Male"],
        "Admission Type": ["Elective", "Emergency", "Urgent"],
        "Test Results": ["Abnormal", "Inconclusive", "Normal"],
        "Blood Type": ["A+", "A-", "AB+", "AB-", "B+", "B-", "O+", "O-"],
        "Medical Condition": ["Arthritis", "Asthma", "Cancer", "Diabetes", "Hypertension", "Obesity"],
        "Insurance Provider": ["Aetna", "Blue Cross", "Cigna", "Medicare", "UnitedHealthcare"],
        "Medication": ["Aspirin", "Ibuprofen", "Lipitor", "Paracetamol", "Penicillin"],
    }.items():
        validator.expect_column_values_to_be_in_set(col, values)


def _enriched_contract(validator) -> None:
    validator.expect_table_column_count_to_equal(33)
    for col in ["Name", "Age", "Gender", "esi_tier_truth", "chief_complaint", "row_hash"]:
        validator.expect_column_values_to_not_be_null(col)
    for col, lo, hi in [
        ("Age", 0, 120),
        ("bp_systolic", 50, 260),
        ("bp_diastolic", 30, 160),
        ("heart_rate", 30, 220),
        ("respiratory_rate", 5, 60),
        ("temperature_f", 94, 107),
        ("spo2_pct", 70, 100),
        ("Billing Amount", 0, 1_000_000),
    ]:
        validator.expect_column_values_to_be_between(col, min_value=lo, max_value=hi)
    for col, values in {
        "Gender": ["Female", "Male"],
        "esi_tier_truth": [1, 2, 3, 4, 5],
        "Test Results": ["Abnormal", "Inconclusive", "Normal"],
        "pii_redaction_status": ["cleared"],
    }.items():
        validator.expect_column_values_to_be_in_set(col, values)
    validator.expect_column_values_to_be_between("esi_tier_truth", min_value=1, max_value=5)
    validator.expect_column_values_to_be_unique("row_hash")


def _run_gate(context, datasource, *, asset_name: str, csv: str, suite: str, build, rows: int) -> dict:
    asset = datasource.add_csv_asset(asset_name, filepath_or_buffer=csv)
    context.add_or_update_expectation_suite(suite)
    validator = context.get_validator(
        batch_request=asset.build_batch_request(),
        expectation_suite_name=suite,
    )
    build(validator)
    validator.save_expectation_suite(discard_failed_expectations=False)
    result = context.add_or_update_checkpoint(name=f"{suite}_checkpoint", validator=validator).run()
    validation = result.list_validation_results()[0]
    results = validation["results"]
    exceptions = [
        {
            "expectation": item["expectation_config"]["expectation_type"],
            "column": item["expectation_config"]["kwargs"].get("column"),
            "unexpected_count": item["result"].get("unexpected_count", 0),
            "unexpected_percent": item["result"].get("unexpected_percent", 0),
        }
        for item in results
        if item["result"].get("unexpected_count", 0)
    ]
    return {
        "suite": suite,
        "asset": csv,
        "rows": rows,
        "expectations": len(results),
        "passed": sum(1 for item in results if item["success"]),
        "success": bool(result.success),
        "exceptions_observed": exceptions,
    }


def main() -> int:
    os.chdir(REPO)
    context = gx.get_context(project_root_dir=str(REPO))
    datasource = context.sources.add_or_update_pandas("healthcare_release_gates")

    gates = [
        _run_gate(
            context, datasource,
            asset_name="source_encounters",
            csv="data/raw/healthcare_dataset.csv",
            suite="source_release_contract",
            build=_source_contract,
            rows=55_500,
        ),
        _run_gate(
            context, datasource,
            asset_name="enriched_encounters",
            csv="data/raw/healthcare_dataset_enriched.csv",
            suite="enriched_ai_contract",
            build=_enriched_contract,
            rows=497,
        ),
    ]
    context.build_data_docs()

    proof = {
        "proof": "great_expectations_release_gate",
        "activity_bracket": [
            "ingest source",
            "validate source contract",
            "quarantine and reconcile",
            "dbt build and test",
            "validate AI-facing enrichment",
            "publish to downstream consumers",
        ],
        "gates": gates,
        "total_expectations": sum(gate["expectations"] for gate in gates),
        "passed_expectations": sum(gate["passed"] for gate in gates),
        "success": all(gate["success"] for gate in gates),
        "boundary": (
            "GE validates contracts at source and AI-facing release boundaries. "
            "Duplicate disposition and no-row-loss accounting are proven separately by reconciliation."
        ),
    }
    PROOF.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))
    return 0 if proof["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
