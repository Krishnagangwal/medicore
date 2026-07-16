"""Model 4 — Drug Interaction inference.

Loads the trained CatBoost model at import time. For every combinatorial
pair of input medications: extract_features() -> predict_proba() ->
severity class + confidence -> SHAP via CatBoost's native
get_feature_importance(type="ShapValues"). Only pairs predicted as
severity > 0 are returned.
"""
from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any

import numpy as np
from catboost import CatBoostClassifier, Pool

import feature_extraction as fe
import graph as graph_module

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "model.cbm"

LABEL_MAP = {0: "none", 1: "minor", 2: "moderate", 3: "major", 4: "contraindicated"}

RECOMMENDATIONS = {
    1: "Minor interaction — no action typically required; monitor as clinically indicated.",
    2: "Moderate interaction — monitor patient for adverse effects; dose adjustment may be needed.",
    3: "Major interaction — monitor closely or consider an alternative agent.",
    4: "Contraindicated — avoid this combination; select an alternative therapy.",
}

FALLBACK_MECHANISM = "Interaction detected via molecular feature analysis"
TOP_K_SHAP = 5

_model: CatBoostClassifier | None = None


def _get_model() -> CatBoostClassifier:
    global _model
    if _model is None:
        model = CatBoostClassifier()
        model.load_model(str(MODEL_PATH))
        _model = model
    return _model


try:
    _get_model()
except Exception:
    pass  # model may not be trained yet; predict() will raise a clear error on first use


def _mechanism_for_pair(cid_a: str, cid_b: str) -> str:
    interaction = graph_module.get_graph().get_interaction(cid_a, cid_b)
    if interaction is None:
        return FALLBACK_MECHANISM
    return "Documented interaction in the reference drug-interaction database"


def _shap_for_class(shap_row: np.ndarray, predicted_class: int, n_features: int) -> np.ndarray:
    """Normalize CatBoost's ShapValues output to a flat (n_features,) array
    of per-feature SHAP contributions toward `predicted_class`.

    CatBoost's get_feature_importance(type="ShapValues") on a multiclass
    model returns shape (n_samples, n_classes, n_features + 1) — the last
    column of each class slice is the expected-value bias term, dropped
    here since only per-feature attributions are needed.
    """
    row = np.asarray(shap_row)
    if row.ndim == 2:  # (n_classes, n_features + 1)
        class_row = row[predicted_class]
    else:  # already flat for this class: (n_features + 1,)
        class_row = row
    return class_row[:n_features]


def _top_shap_values(feature_values: np.ndarray, feature_names: list[str], top_k: int) -> list[dict]:
    order = np.argsort(-np.abs(feature_values))[:top_k]
    results = []
    for idx in order:
        impact = float(feature_values[idx])
        if impact == 0.0:
            continue
        feature = feature_names[idx]
        results.append(
            {
                "feature": feature,
                "display_name": fe.feature_display_name(feature),
                "impact": round(impact, 4),
                "direction": "increases_risk" if impact > 0 else "decreases_risk",
            }
        )
    return results


def predict(medications: list[str]) -> dict:
    """Check all pairwise combinations of `medications` for interactions."""
    model = _get_model()
    feature_names = fe.FEATURE_NAMES
    n_features = len(feature_names)

    pairs = list(itertools.combinations(medications, 2))
    total_pairs_checked = len(pairs)

    interactions: list[dict] = []

    if pairs:
        X = np.array([fe.extract_features(a, b) for a, b in pairs], dtype=np.float32)
        pool = Pool(X)
        proba = model.predict_proba(X)
        shap_values = model.get_feature_importance(pool, type="ShapValues")

        for i, (drug_a, drug_b) in enumerate(pairs):
            class_probs = proba[i]
            predicted_class = int(np.argmax(class_probs))
            confidence = float(class_probs[predicted_class])

            if predicted_class == 0:
                continue

            cid_a = fe.resolve_drug_id(drug_a)
            cid_b = fe.resolve_drug_id(drug_b)
            mechanism = (
                _mechanism_for_pair(cid_a, cid_b) if cid_a and cid_b else FALLBACK_MECHANISM
            )

            shap_row = _shap_for_class(shap_values[i], predicted_class, n_features)

            interactions.append(
                {
                    "drug_a": drug_a,
                    "drug_b": drug_b,
                    "severity": LABEL_MAP[predicted_class],
                    "severity_code": predicted_class,
                    "confidence": round(confidence, 4),
                    "mechanism": mechanism,
                    "recommendation": RECOMMENDATIONS[predicted_class],
                    "shap_values": _top_shap_values(shap_row, feature_names, TOP_K_SHAP),
                }
            )

    interactions.sort(key=lambda x: x["severity_code"], reverse=True)

    return {
        "total_pairs_checked": total_pairs_checked,
        "interaction_count": len(interactions),
        "interactions": interactions,
        "graph": graph_module.to_json(medications),
    }
