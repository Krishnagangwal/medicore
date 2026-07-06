"""Model 2 — Deterioration inference (stubbed)."""
from __future__ import annotations

from typing import Any


def predict(patient_id: str, encounter_id: str, context: dict[str, Any]) -> dict:
    """Return a mock deterioration risk prediction."""
    return {
        "risk_level": "MEDIUM",
        "risk_score": 0.48,
        "confidence": 0.79,
        "time_to_event_hours": 12,
        "shap_values": [
            {
                "feature": "lactate",
                "display_name": "Lactate",
                "value": 2.1,
                "impact": 0.35,
                "direction": "increases_risk",
            },
            {
                "feature": "resp_rate",
                "display_name": "Respiratory rate",
                "value": 21.0,
                "impact": 0.22,
                "direction": "increases_risk",
            },
            {
                "feature": "spo2",
                "display_name": "SpO₂",
                "value": 97.0,
                "impact": -0.18,
                "direction": "decreases_risk",
            },
        ],
        "model_version": "2.0.0-stub",
    }
