"""ML anomaly detection for the quality gate.

An IsolationForest over the numeric encounter features flags rows that don't look
like the rest of the population (e.g. a billing amount or length-of-stay far off
the distribution). Flagged rows are auto-quarantined BEFORE they reach the
published marts — the gate is statistical, not just rule-based.
"""
from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest

NUMERIC_FEATURES = ["age", "billing_amount", "length_of_stay_days"]


def detect_anomalies(df: pd.DataFrame, contamination: float = 0.05) -> pd.DataFrame:
    """Return the input frame with `is_anomaly` (bool) + `anomaly_score` columns.

    contamination = expected outlier fraction; the model labels the most isolated
    rows as anomalies. Deterministic via fixed random_state so a DAG run is
    reproducible.
    """
    feats = [c for c in NUMERIC_FEATURES if c in df.columns]
    X = df[feats].fillna(df[feats].median())

    model = IsolationForest(contamination=contamination, random_state=42, n_estimators=200)
    labels = model.fit_predict(X)           # -1 = anomaly, 1 = normal
    scores = model.score_samples(X)          # lower = more anomalous

    out = df.copy()
    out["is_anomaly"] = labels == -1
    out["anomaly_score"] = scores
    return out


def quarantine_split(df: pd.DataFrame):
    """Split a scored frame into (clean, quarantined) by the anomaly flag."""
    scored = detect_anomalies(df)
    clean = scored[~scored["is_anomaly"]].copy()
    quarantined = scored[scored["is_anomaly"]].copy()
    return clean, quarantined
