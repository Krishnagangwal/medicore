"""Train Model 2 — Patient Deterioration (sepsis risk) classifier.

Run:
    python train.py

Inputs:
    PhysioNet 2019 Sepsis Challenge CSVs at ~/Downloads/22687585/

Outputs:
    artifacts/deterioration_model.pkl
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
import xgboost as xgb
import shap
import joblib

PHYSIONET_DIR = Path.home() / "Downloads" / "22687585"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

# PhysioNet 2019 vital feature columns
FEATURE_COLS = [
    "HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp",
    "BaseExcess", "HCO3", "FiO2", "pH", "PaCO2", "SaO2",
    "Glucose", "Lactate", "WBC", "Creatinine", "Bilirubin_total",
]
TARGET_COL = "SepsisLabel"


def load_physionet() -> pd.DataFrame:
    """Load and concatenate all PhysioNet PSV files."""
    files = list(PHYSIONET_DIR.rglob("*.psv"))
    if not files:
        raise FileNotFoundError(f"No PSV files found in {PHYSIONET_DIR}")
    dfs = [pd.read_csv(f, sep="|") for f in files[:500]]  # subset for dev
    return pd.concat(dfs, ignore_index=True)


def train() -> None:
    df = load_physionet()
    available = [c for c in FEATURE_COLS if c in df.columns]
    X = df[available].fillna(df[available].median()).values
    y = df[TARGET_COL].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.05,
        scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum(),
        eval_metric="aucpr",
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    print(f"ROC-AUC on test set: {auc:.4f}")

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test[:100])
    print(f"SHAP values shape: {np.array(shap_values).shape}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACTS_DIR / "deterioration_model.pkl")
    joblib.dump(available, ARTIFACTS_DIR / "feature_cols.pkl")
    print(f"Artifacts saved → {ARTIFACTS_DIR}")


if __name__ == "__main__":
    train()
