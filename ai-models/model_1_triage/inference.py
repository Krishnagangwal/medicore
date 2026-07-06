"""Model 1 — Triage inference (stubbed).

Returns a hardcoded mock prediction matching the gateway-schema.md shape.
Replace _mock_predict with a real model load + SHAP call after training.
"""
from __future__ import annotations

from typing import Any


def predict(patient_id: str, encounter_id: str, context: dict[str, Any]) -> dict:
    """Return a mock triage prediction."""
    return {
        "triage_category": "URGENT",
        "triage_score": 0.73,
        "confidence": 0.85,
        "news2_score": 6,
        "shap_values": [
            {
                "feature": "heart_rate",
                "display_name": "Heart rate",
                "value": 112.0,
                "impact": 0.41,
                "direction": "increases_risk",
            },
            {
                "feature": "resp_rate",
                "display_name": "Respiratory rate",
                "value": 22.0,
                "impact": 0.28,
                "direction": "increases_risk",
            },
            {
                "feature": "spo2",
                "display_name": "SpO₂",
                "value": 96.0,
                "impact": -0.12,
                "direction": "decreases_risk",
            },
        ],
        "model_version": "1.0.0-stub",
    }
