"""
Split enriched dataset → use_397 + holdout_100 + save canonical files.

Holdout rules:
    - Random sample stratified by Medical Condition (so each condition has
      proportional holdout representation).
    - Deterministic via seed=42 — same split every run.
    - Tagged with "holdout": true field — visible in both halves merged.
    - Holdout NEVER feeds Rachel index, Traffic Light training, Crystal Ball
      tuning. Reserved exclusively for final eval (Recall@K, F1, RMSE).

Outputs written to data/raw/:
    healthcare_dataset_enriched.jsonl     all 497 with "holdout" flag
    healthcare_dataset_enriched.csv       same, CSV form for dbt
    enriched_use_397.jsonl                training/index side
    enriched_holdout_100.jsonl            eval side
"""
from __future__ import annotations
import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = Path("/tmp/enriched_500.jsonl")
RAW_DIR = REPO_ROOT / "data" / "raw"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", type=Path, default=DEFAULT_IN)
    ap.add_argument("--holdout-n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rows: list[dict] = []
    with args.inp.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    print(f"Loaded {len(rows)} enriched rows from {args.inp.name}")

    # Stratified holdout by condition (proportional)
    by_condition: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_condition[r.get("Medical Condition", "Unknown")].append(r)

    rng = random.Random(args.seed)
    holdout: list[dict] = []
    total = len(rows)
    for cond, members in by_condition.items():
        share = round(args.holdout_n * len(members) / total)
        share = min(share, len(members))
        rng.shuffle(members)
        holdout.extend(members[:share])

    # Top up if rounding undershoots
    if len(holdout) < args.holdout_n:
        used_keys = {id(r) for r in holdout}
        remaining = [r for r in rows if id(r) not in used_keys]
        rng.shuffle(remaining)
        holdout.extend(remaining[: args.holdout_n - len(holdout)])
    elif len(holdout) > args.holdout_n:
        rng.shuffle(holdout)
        holdout = holdout[: args.holdout_n]

    holdout_ids = {id(r) for r in holdout}
    use_rows = [r for r in rows if id(r) not in holdout_ids]

    # Tag holdout flag in-place (both halves get the field, just different value)
    for r in use_rows:
        r["holdout"] = False
    for r in holdout:
        r["holdout"] = True

    # Stitch back for canonical "all rows with flag" file
    all_tagged = use_rows + holdout
    rng.shuffle(all_tagged)  # don't let holdout cluster at the tail

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    canonical_jsonl = RAW_DIR / "healthcare_dataset_enriched.jsonl"
    canonical_csv = RAW_DIR / "healthcare_dataset_enriched.csv"
    use_jsonl = RAW_DIR / "enriched_use_397.jsonl"
    holdout_jsonl = RAW_DIR / "enriched_holdout_100.jsonl"

    # Write JSONL files
    with canonical_jsonl.open("w") as f:
        for r in all_tagged:
            f.write(json.dumps(r) + "\n")
    with use_jsonl.open("w") as f:
        for r in use_rows:
            f.write(json.dumps(r) + "\n")
    with holdout_jsonl.open("w") as f:
        for r in holdout:
            f.write(json.dumps(r) + "\n")

    # Write CSV variant for dbt
    if all_tagged:
        fieldnames = list(all_tagged[0].keys())
        with canonical_csv.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            for r in all_tagged:
                # serialize any nested dict/list to JSON string for CSV cell
                row = {
                    k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                    for k, v in r.items()
                }
                w.writerow(row)

    # Report
    print()
    print(f"✅ canonical (all + flag):  {canonical_jsonl}  ({len(all_tagged)} rows)")
    print(f"✅ canonical CSV (for dbt): {canonical_csv}")
    print(f"✅ training/index side:    {use_jsonl}      ({len(use_rows)} rows)")
    print(f"✅ holdout (eval only):     {holdout_jsonl}   ({len(holdout)} rows)")
    print()
    print("Holdout condition breakdown:")
    holdout_cond = defaultdict(int)
    for r in holdout:
        holdout_cond[r.get("Medical Condition", "?")] += 1
    for c, n in sorted(holdout_cond.items()):
        print(f"  {c:<14} {n}")


if __name__ == "__main__":
    main()
