"""Model 6 — Differential Diagnosis inference (stubbed)."""
from __future__ import annotations

from typing import Any


def predict(patient_id: str, encounter_id: str, context: dict[str, Any]) -> dict:
    """Return a mock differential diagnosis result."""
    symptom_text: str = context.get("symptom_text", "")

    # Stub: base differentials on whether any fever/cough keywords appear
    has_respiratory = any(
        kw in symptom_text.lower() for kw in ("cough", "fever", "breath", "wheez")
    )

    differentials = (
        [
            {
                "condition": "Community-Acquired Pneumonia",
                "probability": 0.72,
                "evidence": ["fever", "cough", "elevated_wbc"],
            },
            {
                "condition": "COVID-19",
                "probability": 0.18,
                "evidence": ["fever", "cough"],
            },
            {
                "condition": "Influenza",
                "probability": 0.10,
                "evidence": ["fever"],
            },
        ]
        if has_respiratory
        else [
            {
                "condition": "Unspecified Acute Illness",
                "probability": 0.60,
                "evidence": [],
            },
            {
                "condition": "Viral Syndrome",
                "probability": 0.40,
                "evidence": [],
            },
        ]
    )

    return {
        "differentials": differentials,
        "top_diagnosis": differentials[0]["condition"],
        "confidence": differentials[0]["probability"],
        "shap_values": [
            {
                "feature": "symptom_fever",
                "display_name": "Fever",
                "value": 1.0,
                "impact": 0.45,
                "direction": "increases_risk",
            },
            {
                "feature": "symptom_cough",
                "display_name": "Cough",
                "value": 1.0,
                "impact": 0.33,
                "direction": "increases_risk",
            },
        ],
        "model_version": "6.0.0-stub",
    }
