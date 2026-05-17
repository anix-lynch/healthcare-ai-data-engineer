"""
er_overload.py — ER overload signal (rule-based KPI, deliberately not ML).

Per Codex priority: this is an ops signal, not a model. Concurrent-admissions
heuristic per hospital per day, classified into normal/warning/overloaded.

Why rule-based:
  Ops signals run on thresholds because thresholds are auditable, explainable,
  and adjustable by hospital ops without ML retraining. ML here would be cargo cult.

Logic:
  For each (hospital, calendar day):
    concurrent_admissions = count of encounters with admission_date == day
    signal =
       overloaded  if concurrent >= OVERLOAD_THRESHOLD
       warning     if concurrent >= WARNING_THRESHOLD
       normal      otherwise

Output: hospital · day · concurrent_admissions · signal

Run:
  cd layer1-data-backbone/ml-pipeline
  python src/er_overload.py
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "data" / "raw" / "healthcare_dataset.csv"
OUTPUT_DIR = REPO_ROOT / "ml-pipeline" / "outputs"

# Thresholds — calibrated to dataset size (55K rows / ~5y / 100s of hospitals
# means most hospital-days have low single-digit admits).
WARNING_THRESHOLD = 3
OVERLOAD_THRESHOLD = 5


def classify(concurrent: int) -> str:
    if concurrent >= OVERLOAD_THRESHOLD:
        return "overloaded"
    if concurrent >= WARNING_THRESHOLD:
        return "warning"
    return "normal"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df["Date of Admission"] = pd.to_datetime(df["Date of Admission"])
    df["admission_day"] = df["Date of Admission"].dt.date

    daily = (
        df.groupby(["Hospital", "admission_day"])
        .size()
        .rename("concurrent_admissions")
        .reset_index()
    )
    daily["signal"] = daily["concurrent_admissions"].apply(classify)

    print(f"Hospital-day rows: {len(daily):,}")

    counts = daily["signal"].value_counts().to_dict()
    print(f"\nSignal distribution:")
    for sig in ["normal", "warning", "overloaded"]:
        c = counts.get(sig, 0)
        print(f"  {sig:12s} {c:,} ({100*c/len(daily):.2f}%)")

    out_csv = OUTPUT_DIR / "er_overload_daily.csv"
    daily.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv}")

    # Top 10 most-overloaded hospital-days for spot-check
    top = daily.nlargest(10, "concurrent_admissions")
    print(f"\nTop 10 hospital-days by concurrent admissions:")
    print(top.to_string(index=False))

    metrics = {
        "feature": "er_overload_signal",
        "type": "rule-based",
        "rule": (
            f"overloaded if concurrent_admissions ≥ {OVERLOAD_THRESHOLD}, "
            f"warning if ≥ {WARNING_THRESHOLD}, else normal"
        ),
        "thresholds": {
            "warning": WARNING_THRESHOLD,
            "overload": OVERLOAD_THRESHOLD,
        },
        "rationale": (
            "ER ops signals are threshold-based by design: explainable, "
            "auditable, ops-adjustable without ML retraining. Real production "
            "would join wait-time + bed-availability + staffing pressure — "
            "this synthetic dataset only has admission timestamps, so the "
            "concurrent-admit count is the available proxy."
        ),
        "n_hospital_days": len(daily),
        "signal_counts": {k: int(v) for k, v in counts.items()},
        "computed_at": datetime.now().isoformat(),
    }
    metrics_path = OUTPUT_DIR / "er_overload_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(f"\nSaved metrics: {metrics_path}")


if __name__ == "__main__":
    main()
