"""Train Model 4 — Drug-Drug Interaction severity classifier.

Run:
    python train.py

Inputs:
    ~/Downloads/ddis.csv          — interaction pairs with severity labels
    ~/Downloads/drug_smiles.csv   — SMILES strings for feature extraction

Outputs:
    artifacts/ddi_model.pkl
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
import xgboost as xgb
import shap
import joblib

from feature_extraction import load_smiles_dict, pair_features

DDIS_PATH = Path.home() / "Downloads" / "ddis.csv"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


def build_dataset(ddis_path: Path) -> tuple[np.ndarray, np.ndarray, LabelEncoder]:
    smiles_dict = load_smiles_dict()
    df = pd.read_csv(ddis_path)

    X_list, y_list = [], []
    for _, row in df.iterrows():
        a = str(row["drug_a"]).lower()
        b = str(row["drug_b"]).lower()
        if a in smiles_dict and b in smiles_dict:
            X_list.append(pair_features(smiles_dict[a], smiles_dict[b]))
            y_list.append(row["severity"])

    X = np.array(X_list, dtype=np.float32)
    le = LabelEncoder()
    y = le.fit_transform(y_list)
    return X, y, le


def train() -> None:
    X, y, le = build_dataset(DDIS_PATH)
    print(f"Dataset: {X.shape[0]} drug pairs, {len(le.classes_)} severity classes")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        eval_metric="mlogloss",
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test[:50])
    print(f"SHAP values shape: {np.array(shap_values).shape}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACTS_DIR / "ddi_model.pkl")
    joblib.dump(le, ARTIFACTS_DIR / "ddi_label_encoder.pkl")
    print(f"Artifacts saved → {ARTIFACTS_DIR}")


if __name__ == "__main__":
    train()
