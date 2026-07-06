"""Model 4 — Drug Interaction inference (stubbed)."""
from __future__ import annotations

from typing import Any


def predict(patient_id: str, encounter_id: str, context: dict[str, Any]) -> dict:
    """Return a mock drug-interaction result."""
    medications: list[str] = context.get("medications", [])

    # Stub: flag a mock interaction if ≥ 2 medications are provided
    has_interaction = len(medications) >= 2
    interactions = []
    if has_interaction:
        interactions.append(
            {
                "drug_a": medications[0] if medications else "Drug A",
                "drug_b": medications[1] if len(medications) > 1 else "Drug B",
                "severity": "MODERATE",
                "description": "May increase plasma concentration of Drug B.",
                "recommendation": "Monitor for adverse effects; consider dose adjustment.",
            }
        )

    return {
        "interactions": interactions,
        "has_critical_interaction": False,
        "interaction_count": len(interactions),
        "shap_values": [
            {
                "feature": "drug_pair_similarity",
                "display_name": "Drug pair molecular similarity",
                "value": 0.62,
                "impact": 0.29,
                "direction": "increases_risk",
            }
        ],
        "model_version": "4.0.0-stub",
    }
