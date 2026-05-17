"""
Stratified sampler for Layer 1 enrichment.

Goal: ensure the 500-row enriched subset covers all 7 patterns' eval needs,
NOT just whatever happens to be over-represented in the raw 55K registry.

Strata cube (post-filter, real combos only):
    condition  × admission_type × age_band × gender
    (6)        × (3)            × (4)      × (2)   = 144 cells max

We aim for at least 2-3 random samples per real cell, plus the edge-case
seed list for scenarios that aren't well-represented in raw data
(sepsis, MI, stroke, neutropenic fever, pediatric, etc.).

Usage:
    from stratified_sampler import build_500_row_plan
    plan = build_500_row_plan(raw_csv, edge_cases_json)
    # plan = list of dicts ready to feed to enrich_clinical_narrative.enrich_row()
"""
from __future__ import annotations
import csv
import json
import random
from collections import defaultdict
from pathlib import Path


# ── Age bands (match downstream conventions) ───────────────────────────────
def _age_band(age_str: str) -> str:
    try:
        age = int(float(age_str))
    except (ValueError, TypeError):
        return "unknown"
    if age < 18: return "0-17"
    if age < 35: return "18-34"
    if age < 55: return "35-54"
    if age < 75: return "55-74"
    return "75+"


def _stratum_key(row: dict) -> tuple[str, str, str, str]:
    return (
        row.get("Medical Condition", "Unknown"),
        row.get("Admission Type", "Unknown"),
        _age_band(row.get("Age", "0")),
        row.get("Gender", "Unknown"),
    )


# ── Plan builder ───────────────────────────────────────────────────────────
def build_500_row_plan(
    raw_csv: Path,
    edge_cases_json: Path,
    *,
    total_rows: int = 500,
    edge_cases_target: int = 50,
    samples_per_stratum: int = 3,
    seed: int = 42,
) -> tuple[list[dict], dict]:
    """
    Return (rows_to_enrich, coverage_report).

    rows_to_enrich = list of source rows (15 cols) optionally with a
    'scenario_hint' field for edge cases. Caller hands these to the
    enrichment LLM one row at a time.

    coverage_report = dict describing stratum fill counts + edge slot fill.
    """
    rng = random.Random(seed)

    # 1) load raw 55K rows
    raw_rows: list[dict] = list(csv.DictReader(raw_csv.open(newline="")))
    print(f"[sampler] loaded {len(raw_rows)} raw rows from {raw_csv.name}")

    # 2) load edge case seeds
    with edge_cases_json.open() as f:
        edge_cases: list[dict] = json.load(f)
    print(f"[sampler] loaded {len(edge_cases)} edge-case seeds")

    # 3) bucket raw rows by stratum
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for r in raw_rows:
        buckets[_stratum_key(r)].append(r)
    print(f"[sampler] {len(buckets)} unique strata in raw data")

    # 4) sample N per stratum (or all, if stratum smaller)
    sampled: list[dict] = []
    stratum_fill: dict[str, int] = {}
    for key, members in buckets.items():
        n_target = min(samples_per_stratum, len(members))
        picks = rng.sample(members, n_target)
        sampled.extend(picks)
        stratum_fill[str(key)] = n_target

    # 5) if oversample → trim, if undersample → top up with random extra rows
    target_random = total_rows - edge_cases_target
    if len(sampled) > target_random:
        rng.shuffle(sampled)
        sampled = sampled[:target_random]
    elif len(sampled) < target_random:
        # top up with random raw rows not yet picked
        sampled_ids = {(r.get("Name"), r.get("Date of Admission")) for r in sampled}
        extras = [r for r in raw_rows
                  if (r.get("Name"), r.get("Date of Admission")) not in sampled_ids]
        rng.shuffle(extras)
        sampled.extend(extras[:target_random - len(sampled)])

    print(f"[sampler] stratified sampled: {len(sampled)} rows")

    # 6) add edge cases (truncate or take as-is)
    if len(edge_cases) > edge_cases_target:
        edge_picks = rng.sample(edge_cases, edge_cases_target)
    else:
        edge_picks = edge_cases
    print(f"[sampler] edge-case rows: {len(edge_picks)}")

    # 7) final plan = stratified + edge cases (edge cases LAST so checkpoint
    #     hits stratified coverage first if run is interrupted)
    plan = sampled + edge_picks
    rng.shuffle(plan)  # mix them so failures don't bunch up at one tail

    # 8) coverage report
    final_buckets: dict[str, int] = defaultdict(int)
    edge_types: dict[str, int] = defaultdict(int)
    for r in plan:
        if r.get("scenario_hint"):
            edge_types[r.get("case_type", "unknown_edge")] += 1
        final_buckets[str(_stratum_key(r))] += 1

    report = {
        "n_total": len(plan),
        "n_stratified": len(sampled),
        "n_edge_cases": len(edge_picks),
        "n_strata_covered": len(final_buckets),
        "edge_case_types": dict(edge_types),
        "stratum_fill_top20": dict(sorted(final_buckets.items(), key=lambda kv: -kv[1])[:20]),
        "stratum_fill_underfilled": {k: v for k, v in final_buckets.items() if v < 2},
    }

    return plan, report


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-csv", type=Path,
                    default=Path(__file__).parent.parent / "data" / "raw" / "healthcare_dataset.csv")
    ap.add_argument("--edge-cases", type=Path,
                    default=Path(__file__).parent / "edge_cases.json")
    ap.add_argument("--out-plan", type=Path, default=Path("/tmp/enrich_plan_500.jsonl"))
    ap.add_argument("--out-report", type=Path, default=Path("/tmp/enrich_plan_500_report.json"))
    ap.add_argument("--total", type=int, default=500)
    ap.add_argument("--edge-target", type=int, default=50)
    args = ap.parse_args()

    plan, report = build_500_row_plan(
        args.raw_csv,
        args.edge_cases,
        total_rows=args.total,
        edge_cases_target=args.edge_target,
    )

    with args.out_plan.open("w") as f:
        for row in plan:
            f.write(json.dumps(row) + "\n")
    with args.out_report.open("w") as f:
        json.dump(report, f, indent=2)

    print(f"\nWrote {len(plan)} rows → {args.out_plan}")
    print(f"Wrote coverage report → {args.out_report}")
    print(f"\nCoverage summary:")
    print(f"  strata covered: {report['n_strata_covered']}")
    print(f"  edge cases: {report['n_edge_cases']}")
    print(f"  edge types: {len(report['edge_case_types'])}")
    print(f"  underfilled strata (n<2): {len(report['stratum_fill_underfilled'])}")
