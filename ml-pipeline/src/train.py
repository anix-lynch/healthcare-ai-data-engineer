import pandas as pd
import numpy as np
import xgboost as xgb
import mlflow
import mlflow.xgboost
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
import os
import warnings
warnings.filterwarnings('ignore')

# Set experiment
mlflow.set_experiment("healthcare-readmission-prediction")

def load_data(path):
    """Load healthcare dataset from CSV"""
    print(f"Loading data from {path}...")
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    return pd.read_csv(path)

def engineer_readmission_target(df):
    """
    Engineer readmission target from the dataset.
    Strategy: Use 'Test Results' as proxy for readmission risk
    - Abnormal = High risk (1)
    - Normal/Inconclusive = Low risk (0)
    """
    if 'Test Results' in df.columns:
        df['target'] = (df['Test Results'] == 'Abnormal').astype(int)
        print(f"Created target from 'Test Results': {df['target'].value_counts().to_dict()}")
    else:
        # Fallback: create synthetic target based on age and condition
        print("Creating synthetic readmission target...")
        df['target'] = ((df['Age'] > 60) & 
                       (df['Medical Condition'].isin(['Diabetes', 'Hypertension', 'Cancer']))).astype(int)
    
    return df

def preprocess(df):
    """Preprocess healthcare data for ML"""
    print("Preprocessing data...")
    print(f"Initial shape: {df.shape}")
    
    # Create target before dropping columns
    df = engineer_readmission_target(df)
    
    # Drop PII and non-predictive columns
    drop_cols = ['Name', 'Date of Admission', 'Discharge Date', 'Doctor', 'Hospital', 
                 'Room Number', 'Test Results']
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')
    
    # Encode categorical variables
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    print(f"Encoding categorical columns: {cat_cols}")
    
    for col in cat_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
    
    print(f"Final shape: {df.shape}")
    print(f"Target distribution: {df['target'].value_counts().to_dict()}")
    
    return df

def train():
    """Train XGBoost readmission prediction model"""
    data_path = "../../data/raw/healthcare_dataset.csv"
    
    # Load and preprocess data
    if not os.path.exists(data_path):
        print(f"ERROR: Data file not found at {data_path}")
        print("Please ensure healthcare_dataset.csv exists in data/raw/")
        return
    
    df = load_data(data_path)
    df = preprocess(df)
    
    # Split features and target
    X = df.drop('target', axis=1)
    y = df['target']
    
    print(f"\nFeatures: {X.columns.tolist()}")
    print(f"Feature shape: {X.shape}")
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\nTrain set: {X_train.shape}, Test set: {X_test.shape}")
    
    # Start MLflow run
    with mlflow.start_run():
        # XGBoost parameters - removed base_score to use default
        params = {
            "objective": "binary:logistic",
            "max_depth": 4,
            "learning_rate": 0.1,
            "n_estimators": 100,
            "random_state": 42,
            "eval_metric": "logloss"
        }
        
        print(f"\nTraining XGBoost with params: {params}")
        mlflow.log_params(params)
        
        # Train model
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, verbose=False)
        
        # Predictions
        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]
        
        # Metrics
        acc = accuracy_score(y_test, preds)
        auc = roc_auc_score(y_test, probs)
        
        print(f"\n{'='*50}")
        print(f"MODEL PERFORMANCE")
        print(f"{'='*50}")
        print(f"Accuracy: {acc:.4f}")
        print(f"AUC-ROC: {auc:.4f}")
        print(f"\nConfusion Matrix:")
        print(confusion_matrix(y_test, preds))
        print(f"\nClassification Report:")
        print(classification_report(y_test, preds))
        
        # Log metrics to MLflow
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("auc_roc", auc)
        
        # Log model
        mlflow.xgboost.log_model(model, "model")
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(f"\nTop 10 Important Features:")
        print(feature_importance.head(10))
        
        print(f"\n{'='*50}")
        print(f"✅ Model training complete!")
        print(f"✅ Model saved to MLflow")
        print(f"{'='*50}")

if __name__ == "__main__":
    train()
