"""Model 5 — Readmission inference (stubbed)."""
from __future__ import annotations

from typing import Any


def predict(patient_id: str, encounter_id: str, context: dict[str, Any]) -> dict:
    """Return a mock 30-day readmission risk prediction."""
    return {
        "readmission_risk": "MEDIUM",
        "probability": 0.34,
        "confidence": 0.81,
        "risk_factors": ["prior_admission_90d", "multiple_comorbidities"],
        "shap_values": [
            {
                "feature": "num_prior_admissions_90d",
                "display_name": "Prior admissions (90 days)",
                "value": 2.0,
                "impact": 0.38,
                "direction": "increases_risk",
            },
            {
                "feature": "los_days",
                "display_name": "Length of stay (days)",
                "value": 5.0,
                "impact": 0.21,
                "direction": "increases_risk",
            },
            {
                "feature": "discharge_to_home",
                "display_name": "Discharged to home",
                "value": 1.0,
                "impact": -0.15,
                "direction": "decreases_risk",
            },
        ],
        "model_version": "5.0.0-stub",
    }
