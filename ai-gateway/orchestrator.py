"""
Core of the AI Gateway: parallel model dispatch.

asyncio.gather fires the sepsis and drug-interaction calls
simultaneously — not sequentially — so the gateway's total latency is
roughly max(sepsis_latency, drug_latency) instead of their sum. Each
call is wrapped in its own try/except so one model failing (timeout,
connection refused, bad response) never prevents the other's result
from coming back.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from datetime import datetime, timezone

import httpx

from alert_generator import generate_alert_text
from schemas import GatewayRequest, GatewayResponse, ModelBlock

SEPSIS_MODEL_URL = os.getenv("SEPSIS_MODEL_URL", "http://localhost:8001")
DRUG_MODEL_URL = os.getenv("DRUG_MODEL_URL", "http://localhost:8004")
MODEL_TIMEOUT = float(os.getenv("MODEL_TIMEOUT_SECONDS", "10"))


async def call_sepsis_model(
    client: httpx.AsyncClient,
    vitals_readings: list[dict],
    encounter_id: str,
) -> tuple[str, dict]:
    """Call the Time2Vec Transformer endpoint.

    Returns: ("success"|"error"|"timeout", result_dict)
    """
    start = time.time()
    try:
        response = await client.post(
            f"{SEPSIS_MODEL_URL}/predict",
            json={"vitals_readings": vitals_readings, "encounter_id": encounter_id},
            timeout=MODEL_TIMEOUT,
        )
        latency = int((time.time() - start) * 1000)
        response.raise_for_status()
        return "success", {"data": response.json(), "latency_ms": latency}
    except httpx.TimeoutException:
        return "timeout", {"error": f"Model timeout after {MODEL_TIMEOUT}s"}
    except Exception as e:  # noqa: BLE001 — one model's failure must never break the other
        return "error", {"error": str(e)}


async def call_drug_model(
    client: httpx.AsyncClient,
    medications: list[str],
    encounter_id: str,
) -> tuple[str, dict]:
    """Call the drug interaction endpoint.

    Returns: ("success"|"error"|"timeout"|"skipped", result_dict)
    If medications has fewer than 2 items there are no pairs to check,
    so the model is skipped rather than called.
    """
    if len(medications) < 2:
        return "skipped", {"reason": "Fewer than 2 medications — no pairs to check"}

    start = time.time()
    try:
        response = await client.post(
            f"{DRUG_MODEL_URL}/predict",
            json={"medications": medications},
            timeout=MODEL_TIMEOUT,
        )
        latency = int((time.time() - start) * 1000)
        response.raise_for_status()
        return "success", {"data": response.json(), "latency_ms": latency}
    except httpx.TimeoutException:
        return "timeout", {"error": f"Model timeout after {MODEL_TIMEOUT}s"}
    except Exception as e:  # noqa: BLE001
        return "error", {"error": str(e)}


async def dispatch(request: GatewayRequest) -> GatewayResponse:
    """Main orchestration function.

    Fires both models simultaneously. Never raises — always returns a
    GatewayResponse, with per-model status reflecting whatever
    actually happened to that model's call.
    """
    requested_at = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())

    vitals_list = [
        {k: v for k, v in reading.model_dump().items() if v is not None}
        for reading in request.vitals_readings
    ]

    async with httpx.AsyncClient() as client:
        sepsis_task = call_sepsis_model(client, vitals_list, request.encounter_id)
        drug_task = call_drug_model(client, request.medications, request.encounter_id)

        (sepsis_status, sepsis_raw), (drug_status, drug_raw) = await asyncio.gather(sepsis_task, drug_task)

    completed_at = datetime.now(timezone.utc).isoformat()

    if sepsis_status == "success":
        result = sepsis_raw["data"]
        # The model returns raw numbers only; the human-readable
        # sentence is a gateway concern, added here rather than by
        # the model itself so alert wording can change (e.g. to an
        # LLM later) without retraining or redeploying the model.
        result["alert_text"] = generate_alert_text(result) if result.get("alert") else ""

        sepsis_block = ModelBlock(
            status="success",
            latency_ms=sepsis_raw["latency_ms"],
            result=result,
            error_message=None,
        )
    else:
        sepsis_block = ModelBlock(
            status=sepsis_status,
            latency_ms=None,
            result=None,
            error_message=sepsis_raw.get("error"),
        )

    if drug_status == "success":
        drug_block = ModelBlock(
            status="success",
            latency_ms=drug_raw["latency_ms"],
            result=drug_raw["data"],
            error_message=None,
        )
    elif drug_status == "skipped":
        drug_block = ModelBlock(
            status="skipped",
            latency_ms=None,
            result={
                "total_pairs_checked": 0,
                "interaction_count": 0,
                "interactions": [],
                "reason": drug_raw["reason"],
            },
            error_message=None,
        )
    else:
        drug_block = ModelBlock(
            status=drug_status,
            latency_ms=None,
            result=None,
            error_message=drug_raw.get("error"),
        )

    return GatewayResponse(
        request_id=request_id,
        patient_id=request.patient_id,
        encounter_id=request.encounter_id,
        requested_at=requested_at,
        completed_at=completed_at,
        sepsis=sepsis_block,
        drug_interaction=drug_block,
    )
