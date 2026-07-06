"""Model 1 — Triage inference (real CatBoost + SHAP).

Model loads once at import time from artifacts/model.cbm.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np
from catboost import CatBoostClassifier, Pool

_BASE = Path(__file__).parent
_MODEL_PATH = _BASE / "artifacts" / "model.cbm"
_FEATURES_PATH = _BASE / "artifacts" / "features.json"

_DISPLAY_NAMES: dict[str, str] = {
    "heart_rate":           "Heart rate",
    "systolic_bp":          "Systolic blood pressure",
    "diastolic_bp":         "Diastolic blood pressure",
    "temperature":          "Temperature",
    "respiratory_rate":     "Respiratory rate",
    "spo2":                 "SpO₂",
    "pain_scale":           "Pain scale",
    "age":                  "Age",
    "chief_complaint_code": "Chief complaint",
    "shock_index":          "Shock index",
}

# ---------------------------------------------------------------------------
# Module-level model load (single load, not per request)
# ---------------------------------------------------------------------------
_t0 = time.monotonic()

_model = CatBoostClassifier()
_model.load_model(str(_MODEL_PATH))

with open(_FEATURES_PATH) as _f:
    _meta: dict = json.load(_f)

_FEATURE_COLS: list[str] = _meta["feature_cols"]
_MEDIANS: dict[str, float] = _meta["medians"]
_CATEGORY_ORDER: list[str] = _meta["category_order"]
_CHIEF_COMPLAINTS: list[str] = _meta["chief_complaints"]

_load_ms = int((time.monotonic() - _t0) * 1000)
print(f"[model_1_triage] Model loaded in {_load_ms} ms")
assert _load_ms < 3000, f"Model load exceeded 3 s ({_load_ms} ms)"


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------

def _build_feature_vector(vitals: dict[str, Any]) -> tuple[list[float], list[float]]:
    """Return (feature_values, medians_used_mask) — substituting medians for missing."""
    values: list[float] = []
    for feat in _FEATURE_COLS:
        raw = vitals.get(feat)
        if raw is None:
            raw = _MEDIANS[feat]
        values.append(float(raw))
    return values


def _explanation_text(category: str, top_feature: str, top_value: float, top_impact: float) -> str:
    median = _MEDIANS.get(top_feature, 0.0)
    if abs(top_value - median) < 0.01 * max(abs(median), 1.0):
        qualifier = "borderline"
    elif top_value > median:
        qualifier = "elevated"
    else:
        qualifier = "low"
    name = _DISPLAY_NAMES.get(top_feature, top_feature).lower()
    return (
        f"Triage classified as {category.replace('_', ' ').lower()} primarily due to "
        f"{qualifier} {name} ({round(top_value, 1)})."
    )


def predict(patient_id: str, encounter_id: str, context: dict[str, Any]) -> dict:
    """Run real CatBoost inference and return prediction with top-5 SHAP values."""
    vitals: dict = context.get("vitals", {})
    feature_values = _build_feature_vector(vitals)

    pool = Pool(data=[feature_values], feature_names=_FEATURE_COLS)

    # Probability over 4 classes
    proba = _model.predict_proba(pool)[0]          # shape: (4,)
    predicted_idx = int(np.argmax(proba))
    category = _CATEGORY_ORDER[predicted_idx]
    confidence = float(proba[predicted_idx])

    # SHAP — CatBoost native, shape: (n_samples, n_classes, n_features + 1) for multi-class
    shap_matrix = _model.get_feature_importance(pool, type="ShapValues")

    if shap_matrix.ndim == 3:
        # (1, n_classes, n_features + 1) — take predicted class, drop bias term
        shap_row = shap_matrix[0][predicted_idx][:-1]
    elif shap_matrix.ndim == 2:
        # Fallback for binary or older CatBoost
        shap_row = shap_matrix[0][:-1]
    else:
        shap_row = np.zeros(len(_FEATURE_COLS))

    # Top 5 features sorted by absolute impact
    ranked = sorted(
        zip(_FEATURE_COLS, feature_values, shap_row.tolist()),
        key=lambda x: abs(x[2]),
        reverse=True,
    )[:5]

    shap_values = []
    for feat, val, impact in ranked:
        display_val = val
        if feat == "chief_complaint_code":
            display_val = int(val)
        shap_values.append(
            {
                "feature": feat,
                "display_name": _DISPLAY_NAMES.get(feat, feat),
                "value": round(float(display_val), 2),
                "impact": round(float(impact), 4),
                "direction": "increases_risk" if impact > 0 else "decreases_risk",
            }
        )

    top_feat, top_val, top_impact = ranked[0]
    explanation = _explanation_text(category, top_feat, top_val, top_impact)

    return {
        "category": category,
        "category_code": predicted_idx,
        "confidence": round(confidence, 4),
        "shap_values": shap_values,
        "explanation_text": explanation,
    }
