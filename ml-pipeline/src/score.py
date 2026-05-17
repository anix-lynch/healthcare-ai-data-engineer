"""
score.py — real inference loader for ML artifacts.

Loads a saved model from artifacts/ and runs predictions on a sample.
REPLACES the earlier placeholder version (which wrote hardcoded dummy CSV;
preserved as score.legacy.py).

Usage:
  python src/score.py predicted_los     # loads predicted_los.joblib
  python src/score.py readmission_risk  # loads readmission_risk.joblib
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.preprocessing import LabelEncoder

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "data" / "raw" / "healthcare_dataset.csv"
ARTIFACT_DIR = REPO_ROOT / "ml-pipeline" / "artifacts"


def load_sample(model_name: str, n: int = 5) -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH).head(n).copy()
    df["Date of Admission"] = pd.to_datetime(df["Date of Admission"])
    df["Discharge Date"] = pd.to_datetime(df["Discharge Date"])
    if model_name == "predicted_los":
        df["LoS_days"] = (df["Discharge Date"] - df["Date of Admission"]).dt.days
    drop_cols = [
        "Name", "Date of Admission", "Discharge Date", "Doctor", "Hospital",
        "Room Number", "Test Results", "LoS_days",
    ]
    X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    for col in X.select_dtypes(include=["object"]).columns:
        X[col] = LabelEncoder().fit_transform(X[col].astype(str))
    return X


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python src/score.py <model_name>")
        print("Available: predicted_los · readmission_risk")
        sys.exit(1)

    model_name = sys.argv[1]
    artifact = ARTIFACT_DIR / f"{model_name}.joblib"
    if not artifact.exists():
        train_script = "predict_los" if model_name == "predicted_los" else "predict_readmission"
        print(f"Artifact not found: {artifact}")
        print(f"Train it first: python src/{train_script}.py")
        sys.exit(1)

    print(f"Loading model: {artifact}")
    model = joblib.load(artifact)
    print(f"Model: {type(model).__name__}")

    X = load_sample(model_name, n=5)
    print(f"Input shape: {X.shape}")

    if model_name == "predicted_los":
        preds = model.predict(X)
        print("\nPredictions:")
        for i, p in enumerate(preds):
            print(f"  patient {i}: predicted LoS = {p:.1f} days")
    elif model_name == "readmission_risk":
        preds = model.predict(X)
        probs = model.predict_proba(X)[:, 1]
        print("\nPredictions:")
        for i, (p, prob) in enumerate(zip(preds, probs)):
            label = "READMISSION" if p == 1 else "no readmission"
            print(f"  patient {i}: {label} (risk={prob:.3f})")
    else:
        print(f"Unknown model: {model_name}")
        print("Available: predicted_los · readmission_risk")
        sys.exit(1)


if __name__ == "__main__":
    main()
