"""
Great Expectations validation for the canonical openFDA view (Trust branch).

This is the REAL GE engine running against real openFDA FAERS data — not a
decorative suite file. v1 shipped a GE suite JSON that the engine never executed
(no committed validation result; gx/uncommitted/ was gitignored). Here GE 1.x
actually validates the 300 landed reports and we PRESERVE the result as proof.

Expectations are openFDA-specific (14 FAERS fields), derived from observed
distributions. Schema-drift is caught by expect_table_columns_to_match_set, so a
column dropped/renamed by the live API fails the suite.

Run:  .ge-venv/bin/python ingestion/ge_validate.py [--strict]
Proof: data/quality/openfda_ge_validation.json
Exits 1 with --strict if any expectation fails (fail-closed).
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

import pandas as pd
import great_expectations as gx
from great_expectations import expectations as gxe

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "ingestion"))
from openfda_gate import _load  # same canonical dedup as the gate — one source of truth

COLUMNS = [
    "safetyreportid", "receivedate", "serious", "seriousnessdeath", "occurcountry",
    "patient_sex", "patient_age", "primary_drug", "n_drugs", "reactions",
    "n_reactions", "source_system", "ingest_ts", "row_hash",
]


def build_suite():
    s = gx.ExpectationSuite(name="openfda_data_quality")
    add = s.add_expectation
    # schema drift — exact column set from the live API
    add(gxe.ExpectTableColumnsToMatchSet(column_set=COLUMNS))
    # keys: complete + unique
    add(gxe.ExpectColumnValuesToNotBeNull(column="safetyreportid"))
    add(gxe.ExpectColumnValuesToBeUnique(column="safetyreportid"))
    add(gxe.ExpectColumnValuesToNotBeNull(column="row_hash"))
    add(gxe.ExpectColumnValuesToBeUnique(column="row_hash"))
    # provenance / freshness fields complete
    add(gxe.ExpectColumnValuesToNotBeNull(column="source_system"))
    add(gxe.ExpectColumnValuesToBeInSet(column="source_system", value_set=["openfda_faers"]))
    add(gxe.ExpectColumnValuesToNotBeNull(column="receivedate"))
    add(gxe.ExpectColumnValueLengthsToEqual(column="receivedate", value=8))
    add(gxe.ExpectColumnValuesToNotBeNull(column="ingest_ts"))
    # value domains (nulls allowed in source — in_set ignores nulls by design)
    add(gxe.ExpectColumnValuesToBeInSet(column="serious", value_set=["1", "2"]))
    add(gxe.ExpectColumnValuesToBeInSet(column="seriousnessdeath", value_set=["1", "2"]))
    add(gxe.ExpectColumnValuesToBeInSet(column="patient_sex", value_set=["0", "1", "2"]))
    add(gxe.ExpectColumnValuesToBeBetween(column="n_drugs", min_value=1, max_value=100))
    add(gxe.ExpectColumnValuesToBeBetween(column="n_reactions", min_value=1, max_value=50))
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    rows, idem = _load(REPO / "data" / "raw" / "openfda")
    df = pd.DataFrame([{c: r.get(c) for c in COLUMNS} for r in rows])

    ctx = gx.get_context(mode="ephemeral")
    ds = ctx.data_sources.add_pandas("openfda")
    asset = ds.add_dataframe_asset(name="events")
    bd = asset.add_batch_definition_whole_dataframe("whole")
    suite = ctx.suites.add(build_suite())
    vd = ctx.validation_definitions.add(
        gx.ValidationDefinition(data=bd, suite=suite, name="openfda_vd")
    )
    res = vd.run(batch_parameters={"dataframe": df})

    rd = res.to_json_dict()
    n_total = len(rd["results"])
    n_pass = sum(1 for r in rd["results"] if r["success"])
    proof = {
        "engine": "great_expectations",
        "ge_version": gx.__version__,
        "suite": "openfda_data_quality",
        "n_rows": len(df),
        "expectations_total": n_total,
        "expectations_passed": n_pass,
        "success": res.success,
        "results": [
            {
                "expectation": r["expectation_config"]["type"],
                "column": r["expectation_config"]["kwargs"].get("column", "<table>"),
                "success": r["success"],
            }
            for r in rd["results"]
        ],
    }
    out = REPO / "data" / "quality" / "openfda_ge_validation.json"
    out.write_text(json.dumps(proof, indent=2))
    print(json.dumps({k: proof[k] for k in
          ("ge_version", "n_rows", "expectations_total", "expectations_passed", "success")}, indent=2))
    print(f"\n{'[ok] GE PASS' if res.success else '[FAIL] GE'} "
          f"{n_pass}/{n_total} on {len(df)} real openFDA reports -> {out.relative_to(REPO)}")
    return (0 if res.success else 1) if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
