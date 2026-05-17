"""
predict_readmission.py — readmission_risk classifier (real target, not proxy).

REPLACES the proxy-target version in train.py. Uses the dbt-style readmission
definition: ≤30-day re-admission of the same patient = is_readmission=1.
This is the actual clinical definition (HEDIS / CMS readmission measure shape).

Stack: sklearn GradientBoostingClassifier + joblib + JSON metrics.

Run:
  cd layer1-data-backbone/ml-pipeline
  python src/predict_readmission.py
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "data" / "raw" / "healthcare_dataset.csv"
OUTPUT_DIR = REPO_ROOT / "ml-pipeline" / "outputs"
ARTIFACT_DIR = REPO_ROOT / "ml-pipeline" / "artifacts"


def engineer_readmission_target(df: pd.DataFrame) -> pd.DataFrame:
    """30-day readmission flag (matches dbt int_readmissions logic).

    For each patient, sort by admission date, compute days since prior visit,
    flag visit as readmission if prior visit was ≤30 days ago.
    """
    df = df.copy()
    df["Date of Admission"] = pd.to_datetime(df["Date of Admission"])
    df = df.sort_values(["Name", "Date of Admission"])
    df["days_since_prior"] = (
        df.groupby("Name")["Date of Admission"]
        .diff()
        .dt.days
    )
    df["is_readmission"] = (df["days_since_prior"] <= 30).astype(int)
    df.loc[df["days_since_prior"].isna(), "is_readmission"] = 0  # first visit can't be a readmit
    return df


def preprocess(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    target = df["is_readmission"]
    drop_cols = [
        "Name", "Date of Admission", "Discharge Date", "Doctor", "Hospital",
        "Room Number", "Test Results", "is_readmission", "days_since_prior",
    ]
    X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    for col in X.select_dtypes(include=["object"]).columns:
        X[col] = LabelEncoder().fit_transform(X[col].astype(str))
    return X, target


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df = engineer_readmission_target(df)

    n_readmit = int(df["is_readmission"].sum())
    n_total = len(df)
    print(f"Rows: {n_total:,}")
    print(f"Readmissions (≤30 day): {n_readmit:,} ({100*n_readmit/n_total:.2f}%)")

    if n_readmit < 50:
        print(
            f"\n⚠️  Only {n_readmit} positive cases — synthetic data is mostly "
            f"single-visit. Model will struggle. Honest result either way."
        )

    X, y = preprocess(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {X_train.shape}  Test: {X_test.shape}")

    params = {
        "n_estimators": 200,
        "max_depth": 4,
        "learning_rate": 0.1,
        "random_state": 42,
    }
    print(f"\nTraining GradientBoostingClassifier: {params}")
    model = GradientBoostingClassifier(**params)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    acc = accuracy_score(y_test, preds)
    try:
        auc = roc_auc_score(y_test, probs)
    except ValueError:
        auc = float("nan")  # only one class in y_test (extreme imbalance)

    print(f"\nAccuracy: {acc:.4f}")
    print(f"AUC-ROC: {auc:.4f}")
    print("\nConfusion matrix:")
    print(confusion_matrix(y_test, preds))
    print("\nClassification report:")
    print(classification_report(y_test, preds, zero_division=0))

    artifact_path = ARTIFACT_DIR / "readmission_risk.joblib"
    joblib.dump(model, artifact_path)
    print(f"Saved artifact: {artifact_path}")

    metrics = {
        "model": "GradientBoostingClassifier",
        "params": params,
        "target_definition": "30-day readmission (matches dbt int_readmissions)",
        "metrics": {
            "accuracy": round(acc, 4),
            "auc_roc": round(auc, 4) if not np.isnan(auc) else None,
        },
        "class_balance": {
            "positives": n_readmit,
            "negatives": n_total - n_readmit,
            "positive_rate": round(n_readmit / n_total, 4),
        },
        "n_train": len(X_train),
        "n_test": len(X_test),
        "trained_at": datetime.now().isoformat(),
        "features_used": list(X.columns),
        "honest_caveat": (
            "Synthetic dataset is mostly single-visit per patient. Real signal "
            "is sparse. Code is correct; metrics reflect data limitations, not "
            "model capability."
        ) if n_readmit < 200 else None,
    }
    metrics_path = OUTPUT_DIR / "readmission_risk_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(f"Saved metrics: {metrics_path}")

    pred_df = X_test.assign(
        actual_readmission=y_test.values,
        predicted_readmission=preds,
        risk_probability=probs.round(4),
    )
    out_csv = OUTPUT_DIR / "readmission_risk_predictions.csv"
    pred_df.to_csv(out_csv, index=False)
    print(f"Saved predictions ({len(pred_df):,} rows): {out_csv}")


if __name__ == "__main__":
    main()
