"""Self-test for Model 4 — Drug Interaction Safety Engine. Run directly:

    python test_interactions.py

Lisinopril is not present in the 645-drug reference dataset (confirmed
during dataset exploration — see train.py docstring), so it is
substituted with Losartan, the closest available drug: both are
renin-angiotensin-system antihypertensives (Lisinopril = ACE inhibitor,
Losartan = ARB), commonly co-prescribed for the same indications.
"""
from __future__ import annotations

import json

import inference

REQUESTED = ["Warfarin", "Aspirin", "Metformin", "Lisinopril"]
SUBSTITUTED = {"Lisinopril": "Losartan"}
MEDICATIONS = [SUBSTITUTED.get(m, m) for m in REQUESTED]


def main() -> None:
    print(f"Requested medications: {REQUESTED}")
    print(f"Substitutions applied (drug not in reference dataset): {SUBSTITUTED}")
    print(f"Actual medications checked: {MEDICATIONS}\n")

    result = inference.predict(MEDICATIONS)

    print(f"Total pairs checked: {result['total_pairs_checked']}")
    print(f"Interactions found: {result['interaction_count']}\n")

    for interaction in result["interactions"]:
        print(
            f"  {interaction['drug_a']} + {interaction['drug_b']}: "
            f"{interaction['severity']} (code={interaction['severity_code']}, "
            f"confidence={interaction['confidence']})"
        )
        print(f"    mechanism: {interaction['mechanism']}")
        print(f"    recommendation: {interaction['recommendation']}")

    assert result["interaction_count"] >= 1, "expected at least one interaction to be detected"

    highest = max(result["interactions"], key=lambda x: x["severity_code"])
    print(f"\nHighest-severity interaction: {highest['drug_a']} + {highest['drug_b']} ({highest['severity']})")
    print("SHAP values for highest-severity interaction:")
    print(json.dumps(highest["shap_values"], indent=2))
    assert len(highest["shap_values"]) > 0, "expected non-empty shap_values on the top interaction"

    for interaction in result["interactions"]:
        assert "shap_values" in interaction and len(interaction["shap_values"]) > 0, (
            f"missing shap_values for {interaction['drug_a']} + {interaction['drug_b']}"
        )

    print("\nGraph (3-drug subset check):")
    graph = inference.graph_module.to_json(MEDICATIONS[:3])
    print(json.dumps(graph, indent=2))
    assert len(graph["nodes"]) == 3

    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()
