"""
Gateway tests — run after starting the gateway (models optional).

Tests the gateway logic directly (no HTTP layer): alert text
generation and dispatch()'s parallel orchestration against mocked
model responses, so these run without the real model endpoints up.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from alert_generator import generate_alert_text
from orchestrator import DRUG_MODEL_URL, SEPSIS_MODEL_URL, dispatch
from schemas import GatewayRequest, VitalReading


def test_alert_generator() -> None:
    """Test rule-based alert text generation."""

    # High risk with tachycardia
    result1 = {
        "risk_score": 0.87,
        "sofa_rounded": 7,
        "alert": True,
        "top_attended_hours": [{"hour_index": 22, "attention": 0.31, "vitals": {"hr": 118, "o2sat": 91, "sbp": 88}}],
    }
    text1 = generate_alert_text(result1)
    assert "118" in text1 or "tachycardia" in text1.lower() or "hypox" in text1.lower()
    assert len(text1) > 20
    print(f"Alert text 1: {text1}")

    # Medium risk with hypoxia
    result2 = {
        "risk_score": 0.71,
        "sofa_rounded": 3,
        "alert": True,
        "top_attended_hours": [{"hour_index": 18, "attention": 0.28, "vitals": {"hr": 95, "o2sat": 91, "sbp": 100}}],
    }
    text2 = generate_alert_text(result2)
    assert len(text2) > 0
    print(f"Alert text 2: {text2}")

    # Error handling — bad input
    text3 = generate_alert_text({})
    assert len(text3) > 0  # fallback should always work
    print(f"Fallback text: {text3}")

    print("Alert generator: all tests passed")


async def test_dispatch_with_mock() -> None:
    """Test dispatch() without real model endpoints running.

    Patches httpx.AsyncClient.post with an async function that
    dispatches on the request URL, so it works correctly under
    asyncio.gather regardless of which of the two calls resolves
    first.
    """
    mock_sepsis_response = {
        "risk_score": 0.82,
        "risk_level": "high",
        "alert": True,
        "alert_threshold": 0.65,
        "sofa_score": 7.1,
        "sofa_rounded": 7,
        "trend": "worsening",
        "attention_weights": [0.02] * 21 + [0.18, 0.24, 0.31],
        "attention_peak_hour": 23,
        "top_attended_hours": [
            {"hour_index": 23, "iculos_hour": 24, "attention": 0.31, "vitals": {"hr": 118, "o2sat": 91}}
        ],
        "based_on_readings": 6,
        "model": "time2vec-transformer",
    }

    mock_drug_response = {
        "total_pairs_checked": 1,
        "interaction_count": 1,
        "interactions": [
            {
                "drug_a": "Vancomycin",
                "drug_b": "Piperacillin-Tazobactam",
                "severity": "major",
                "severity_code": 3,
                "mechanism": "Combined nephrotoxicity risk",
                "recommendation": "Monitor renal function closely",
                "shap_values": [],
            }
        ],
    }

    request = GatewayRequest(
        patient_id="test-patient-001",
        encounter_id="test-encounter-001",
        vitals_readings=[
            VitalReading(hr=85 + i * 5, o2sat=97 - i, temp=37.2 + i * 0.3, sbp=118 - i * 5, resp=16 + i, iculos=i + 1)
            for i in range(6)
        ],
        medications=["Vancomycin", "Piperacillin-Tazobactam"],
    )

    async def fake_post(url, json=None, timeout=None):
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock(return_value=None)
        if url.startswith(SEPSIS_MODEL_URL):
            response.json = MagicMock(return_value=mock_sepsis_response)
        elif url.startswith(DRUG_MODEL_URL):
            response.json = MagicMock(return_value=mock_drug_response)
        else:
            raise AssertionError(f"unexpected URL in mocked post: {url}")
        return response

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=fake_post)):
        response = await dispatch(request)

    assert response.patient_id == "test-patient-001"
    assert response.sepsis.status == "success"
    assert response.drug_interaction.status == "success"
    assert response.sepsis.result["alert"] is True
    assert response.sepsis.result["alert_text"] != ""
    assert response.drug_interaction.result["interaction_count"] == 1

    print("Dispatch test passed")
    print(f"Sepsis status: {response.sepsis.status}")
    print(f"Risk score: {response.sepsis.result['risk_score']}")
    print(f"Alert text: {response.sepsis.result['alert_text']}")
    print(f"Drug interactions: {response.drug_interaction.result['interaction_count']}")
    print(f"Request ID: {response.request_id}")


async def test_dispatch_skips_drug_model_under_two_meds() -> None:
    """drug_interaction.status must be 'skipped' with fewer than 2 medications."""
    mock_sepsis_response = {
        "risk_score": 0.3,
        "risk_level": "low",
        "alert": False,
        "alert_threshold": 0.65,
        "sofa_score": 0.5,
        "sofa_rounded": 0,
        "trend": "stable",
        "attention_weights": [1 / 24] * 24,
        "attention_peak_hour": 0,
        "top_attended_hours": [],
        "based_on_readings": 2,
        "model": "time2vec-transformer",
    }

    request = GatewayRequest(
        patient_id="test-patient-002",
        encounter_id="test-encounter-002",
        vitals_readings=[VitalReading(hr=80, o2sat=98, iculos=1), VitalReading(hr=82, o2sat=98, iculos=2)],
        medications=["Vancomycin"],
    )

    async def fake_post(url, json=None, timeout=None):
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock(return_value=None)
        response.json = MagicMock(return_value=mock_sepsis_response)
        return response

    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=fake_post)):
        response = await dispatch(request)

    assert response.drug_interaction.status == "skipped"
    assert response.sepsis.result["alert_text"] == ""
    print("Skip-drug-model test passed")


if __name__ == "__main__":
    print("=== Testing Alert Generator ===")
    test_alert_generator()

    print("\n=== Testing Dispatch (mock models) ===")
    asyncio.run(test_dispatch_with_mock())

    print("\n=== Testing Dispatch (drug model skipped) ===")
    asyncio.run(test_dispatch_skips_drug_model_under_two_meds())

    print("\n=== All gateway tests passed ===")
