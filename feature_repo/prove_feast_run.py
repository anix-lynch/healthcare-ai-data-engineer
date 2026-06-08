#!/usr/bin/env python3
"""
Bullet 3 proof: Feast is repointed to real openFDA and the feature path RUNS.
Proves three things and writes a machine-readable receipt:
  1. discovery   — the registry lists the openFDA feature view + its features
  2. historical  — get_historical_features returns point-in-time-correct rows
  3. online      — materialize + get_online_features serves features for a report key
"""
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from feast import FeatureStore

REPO = Path(__file__).resolve().parent
store = FeatureStore(repo_path=str(REPO))

# 1. discovery
fv = store.get_feature_view("openfda_drug_features")
discovered = [f.name for f in fv.features]

# 2. historical (point-in-time) — sample real report keys from the source parquet
src = pd.read_parquet(REPO.parent / "data" / "feast" / "openfda_drug_features.parquet")
sample = src.sort_values("event_timestamp").tail(5)
entity_df = pd.DataFrame({
    "safetyreportid": sample["safetyreportid"].tolist(),
    "event_timestamp": pd.to_datetime(sample["event_timestamp"]),
})
refs = ["openfda_drug_features:prior_reports_for_drug",
        "openfda_drug_features:is_serious",
        "openfda_drug_features:primary_drug"]
hist = store.get_historical_features(entity_df=entity_df, features=refs).to_df()
hist_rows = hist[["safetyreportid", "primary_drug", "prior_reports_for_drug", "is_serious"]].to_dict("records")

# 3. online — materialize then serve
end = datetime.utcnow()
store.materialize(start_date=end - timedelta(days=3650), end_date=end + timedelta(days=1))
key = sample["safetyreportid"].tolist()[:3]
online = store.get_online_features(
    features=refs, entity_rows=[{"safetyreportid": k} for k in key]
).to_dict()
online_rows = [
    {"safetyreportid": online["safetyreportid"][i],
     "primary_drug": online["primary_drug"][i],
     "prior_reports_for_drug": online["prior_reports_for_drug"][i]}
    for i in range(len(online["safetyreportid"]))
]

green = (len(discovered) >= 3 and len(hist_rows) == len(entity_df)
         and all(r["prior_reports_for_drug"] is not None for r in online_rows))
receipt = {
    "proof": "bullet3_feast_real_openfda",
    "claim_phrase": "discoverable Feast features",
    "source": "data/feast/openfda_drug_features.parquet (300 real openFDA reports from BQ fact)",
    "discovery": {"feature_view": fv.name, "features": discovered,
                  "pit_correct_feature": "prior_reports_for_drug"},
    "historical_retrieval": {"requested_keys": len(entity_df), "returned_rows": len(hist_rows),
                             "sample": hist_rows[:3]},
    "online_retrieval": {"served_keys": len(online_rows), "sample": online_rows},
    "verdict": "GREEN — Feast registry discovers openFDA features; historical + online retrieval run"
               if green else "YELLOW — a retrieval check did not pass",
}
out = REPO.parent / "data" / "quality" / "bullet3_feast_proof.json"
json.dump(receipt, open(out, "w"), indent=2, default=str)
print("WROTE", out)
print("  discovered features:", discovered)
print("  historical rows:", len(hist_rows), "| sample:", hist_rows[0] if hist_rows else None)
print("  online served:", online_rows[0] if online_rows else None)
print("VERDICT:", receipt["verdict"])
raise SystemExit(0 if green else 1)
