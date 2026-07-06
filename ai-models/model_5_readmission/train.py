"""Train Model 5 — 30-day Readmission risk classifier.

Run:
    python train.py

Inputs:
    MIMIC-IV Demo at ~/Downloads/mimic-iv-clinical-databas...emo-2.2/

Outputs:
    artifacts/readmission_model.pkl
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

MIMIC_DIR = Path.home() / "Downloads"
# Resolve the actual MIMIC demo directory regardless of exact name suffix
_candidates = list(MIMIC_DIR.glob("mimic-iv-clinical-databas*"))
MIMIC_DEMO_DIR = _candidates[0] if _candidates else MIMIC_DIR / "mimic-iv-demo"

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

FEATURE_COLS = [
    "age",
    "num_prior_admissions_90d",
    "los_days",
    "num_diagnoses",
    "num_procedures",
    "num_medications",
    "has_diabetes",
    "has_heart_failure",
    "has_copd",
    "discharge_to_home",
]


def load_mimic() -> pd.DataFrame:
    """Build a readmission dataset from MIMIC-IV Demo tables."""
    admissions_path = MIMIC_DEMO_DIR / "hosp" / "admissions.csv.gz"
    patients_path = MIMIC_DEMO_DIR / "hosp" / "patients.csv.gz"

    if not admissions_path.exists():
        raise FileNotFoundError(f"MIMIC admissions not found at {admissions_path}")

    adm = pd.read_csv(admissions_path, compression="gzip")
    patients = pd.read_csv(patients_path, compression="gzip")
    # Stub feature engineering — replace with real feature engineering
    adm = adm.merge(patients[["subject_id", "anchor_age"]], on="subject_id", how="left")
    adm["age"] = adm["anchor_age"].fillna(60)
    adm["los_days"] = 3.0
    adm["num_prior_admissions_90d"] = 0
    adm["num_diagnoses"] = 5
    adm["num_procedures"] = 2
    adm["num_medications"] = 4
    adm["has_diabetes"] = 0
    adm["has_heart_failure"] = 0
    adm["has_copd"] = 0
    adm["discharge_to_home"] = 1
    adm["readmitted_30d"] = 0  # placeholder label
    return adm


def train() -> None:
    df = load_mimic()
    X = df[FEATURE_COLS].fillna(0).values.astype(np.float32)
    y = df["readmitted_30d"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        eval_metric="aucpr",
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    print(f"ROC-AUC: {auc:.4f}")

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test[:50])
    print(f"SHAP values shape: {np.array(shap_values).shape}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACTS_DIR / "readmission_model.pkl")
    print(f"Artifacts saved → {ARTIFACTS_DIR}")


if __name__ == "__main__":
    train()
