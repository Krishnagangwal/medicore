"""Train Model 6 — Differential Diagnosis classifier.

Run:
    python train.py

Inputs:
    DDXPlus dataset (github.com/mila-iqia/ddxplus) or
    MIMIC-IV Demo discharge notes at ~/Downloads/mimic-iv-clinical-databas...emo-2.2/

Outputs:
    artifacts/diff_dx_model.pkl
    artifacts/diff_dx_label_encoder.pkl
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report
from sklearn.ensemble import RandomForestClassifier
import shap
import joblib

MIMIC_DIR = Path.home() / "Downloads"
_candidates = list(MIMIC_DIR.glob("mimic-iv-clinical-databas*"))
MIMIC_DEMO_DIR = _candidates[0] if _candidates else MIMIC_DIR / "mimic-iv-demo"

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


def load_discharge_notes() -> pd.DataFrame:
    """Load MIMIC-IV Demo discharge notes (stub — replace with DDXPlus when available)."""
    notes_path = MIMIC_DEMO_DIR / "note" / "discharge.csv.gz"
    if not notes_path.exists():
        raise FileNotFoundError(f"Discharge notes not found at {notes_path}")

    df = pd.read_csv(notes_path, compression="gzip")
    # Minimal columns: text (symptom description), diagnosis (label)
    df = df[["text"]].dropna()
    df["diagnosis"] = "Unspecified"  # placeholder — extract ICD labels in Phase 2
    return df


def train() -> None:
    df = load_discharge_notes()
    print(f"Loaded {len(df)} discharge notes")

    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    X = vectorizer.fit_transform(df["text"]).toarray()

    le = LabelEncoder()
    y = le.fit_transform(df["diagnosis"])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test[:20])
    print(f"SHAP values shape: {np.array(shap_values).shape}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACTS_DIR / "diff_dx_model.pkl")
    joblib.dump(le, ARTIFACTS_DIR / "diff_dx_label_encoder.pkl")
    joblib.dump(vectorizer, ARTIFACTS_DIR / "diff_dx_vectorizer.pkl")
    print(f"Artifacts saved → {ARTIFACTS_DIR}")


if __name__ == "__main__":
    train()
