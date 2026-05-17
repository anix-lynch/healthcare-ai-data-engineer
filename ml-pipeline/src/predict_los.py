"""
predict_los.py — Length-of-Stay regression model.

Real ML regression. Predicts LoS_days (1-30) from admission features.
Used downstream by ops-capacity-assistant to plan bed pressure / staffing.

Stack: sklearn GradientBoostingRegressor + joblib persistence + JSON metrics.
(MLflow tracking is queued — adding it = pip install mlflow in a venv.
 The metrics + artifact format here is MLflow-compatible at upgrade time.)

Run:
  cd layer1-data-backbone/ml-pipeline
  python src/predict_los.py
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "data" / "raw" / "healthcare_dataset.csv"
OUTPUT_DIR = REPO_ROOT / "ml-pipeline" / "outputs"
ARTIFACT_DIR = REPO_ROOT / "ml-pipeline" / "artifacts"


def load_and_engineer() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["Date of Admission"] = pd.to_datetime(df["Date of Admission"])
    df["Discharge Date"] = pd.to_datetime(df["Discharge Date"])
    df["LoS_days"] = (df["Discharge Date"] - df["Date of Admission"]).dt.days
    df = df[df["LoS_days"] > 0]
    return df


def preprocess(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    target = df["LoS_days"]
    drop_cols = [
        "Name", "Date of Admission", "Discharge Date", "Doctor",
        "Hospital", "Room Number", "Test Results", "LoS_days",
    ]
    X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    for col in X.select_dtypes(include=["object"]).columns:
        X[col] = LabelEncoder().fit_transform(X[col].astype(str))
    return X, target


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading {DATA_PATH}")
    df = load_and_engineer()
    print(f"Rows after LoS engineering: {len(df):,}")
    print(f"LoS distribution: mean={df['LoS_days'].mean():.2f} std={df['LoS_days'].std():.2f}")

    X, y = preprocess(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"Train: {X_train.shape}  Test: {X_test.shape}")

    params = {
        "n_estimators": 200,
        "max_depth": 5,
        "learning_rate": 0.1,
        "random_state": 42,
    }
    print(f"\nTraining GradientBoostingRegressor: {params}")
    model = GradientBoostingRegressor(**params)
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    print(f"\nMAE: {mae:.3f} days · R²: {r2:.3f}")

    # Persist artifact
    artifact_path = ARTIFACT_DIR / "predicted_los.joblib"
    joblib.dump(model, artifact_path)
    print(f"Saved artifact: {artifact_path}")

    # Metrics JSON (MLflow-compatible shape)
    metrics = {
        "model": "GradientBoostingRegressor",
        "params": params,
        "metrics": {"mae_days": round(mae, 4), "r2": round(r2, 4)},
        "n_train": len(X_train),
        "n_test": len(X_test),
        "target_range_days": [int(y.min()), int(y.max())],
        "trained_at": datetime.now().isoformat(),
        "features_used": list(X.columns),
    }
    metrics_path = OUTPUT_DIR / "predicted_los_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(f"Saved metrics: {metrics_path}")

    # Predictions on test set
    pred_df = X_test.assign(actual_los=y_test.values, predicted_los=preds.round(1))
    out_csv = OUTPUT_DIR / "predicted_los_predictions.csv"
    pred_df.to_csv(out_csv, index=False)
    print(f"Saved predictions ({len(pred_df):,} rows): {out_csv}")

    # Feature importance
    fi = pd.DataFrame({
        "feature": X.columns,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False)
    fi_path = OUTPUT_DIR / "predicted_los_feature_importance.csv"
    fi.to_csv(fi_path, index=False)
    print(f"\nTop 5 features:")
    print(fi.head().to_string(index=False))


if __name__ == "__main__":
    main()
