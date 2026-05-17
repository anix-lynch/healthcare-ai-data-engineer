"""
high_utilizer.py — high-utilizer flag (rule-based, deliberately not ML).

Per Codex priority: don't over-ML this. Enterprise systems run on simple rules.

Rule:
  high_utilizer_flag = TRUE if patient has >= MIN_VISITS encounters in dataset
  (representing ≥12mo of hospital activity)

Default MIN_VISITS=2 (this synthetic dataset is mostly single-visit; only
1 patient has ≥3 visits, so 3-visit threshold flags nobody. Real production
data would use ≥3 in a 12-month window per CMS guidance.)

Run:
  cd layer1-data-backbone/ml-pipeline
  python src/high_utilizer.py
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "data" / "raw" / "healthcare_dataset.csv"
OUTPUT_DIR = REPO_ROOT / "ml-pipeline" / "outputs"

MIN_VISITS = 2  # see docstring re: synthetic-data adaptation


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)

    visit_counts = df.groupby("Name").size().rename("visit_count").reset_index()
    visit_counts["high_utilizer_flag"] = visit_counts["visit_count"] >= MIN_VISITS

    n_flagged = int(visit_counts["high_utilizer_flag"].sum())
    n_total = len(visit_counts)
    print(f"Patients: {n_total:,}")
    print(f"Flagged high-utilizer (visits ≥ {MIN_VISITS}): {n_flagged:,} ({100*n_flagged/n_total:.2f}%)")

    # Per-patient feature output
    out_csv = OUTPUT_DIR / "high_utilizer_flags.csv"
    visit_counts.to_csv(out_csv, index=False)
    print(f"Saved per-patient flags: {out_csv}")

    # Distribution of visit counts
    distribution = (
        visit_counts["visit_count"]
        .value_counts()
        .sort_index()
        .to_dict()
    )

    metrics = {
        "feature": "high_utilizer_flag",
        "type": "rule-based",
        "rule": f"visit_count >= {MIN_VISITS}",
        "rationale": (
            "Real production: ≥3 visits in 12 months (CMS high-utilizer definition). "
            "This synthetic dataset has only 1 patient with ≥3 visits, so threshold "
            "lowered to ≥2 to produce non-empty signal. Threshold is config-driven."
        ),
        "n_total_patients": n_total,
        "n_flagged": n_flagged,
        "flag_rate": round(n_flagged / n_total, 4),
        "visit_count_distribution": {str(k): int(v) for k, v in distribution.items()},
        "computed_at": datetime.now().isoformat(),
    }
    metrics_path = OUTPUT_DIR / "high_utilizer_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(f"Saved metrics: {metrics_path}")

    print("\nVisit-count distribution:")
    for k, v in sorted(distribution.items()):
        print(f"  {k} visits: {v:,} patients")


if __name__ == "__main__":
    main()
