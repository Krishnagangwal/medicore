from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict

import httpx

from schemas import GatewayRequest, ModelBlock, ModelType

MODEL_URLS: Dict[str, str] = {
    ModelType.TRIAGE.value: os.getenv("MODEL_1_URL", "http://localhost:8001"),
    ModelType.DETERIORATION.value: os.getenv("MODEL_2_URL", "http://localhost:8002"),
    ModelType.LAB_PARSER.value: os.getenv("MODEL_3_URL", "http://localhost:8003"),
    ModelType.DRUG_INTERACTION.value: os.getenv("MODEL_4_URL", "http://localhost:8004"),
    ModelType.READMISSION.value: os.getenv("MODEL_5_URL", "http://localhost:8005"),
    ModelType.DIFFERENTIAL_DX.value: os.getenv("MODEL_6_URL", "http://localhost:8006"),
}

TIMEOUT_SECONDS: float = float(os.getenv("MODEL_TIMEOUT_SECONDS", "10"))


async def _call_model(
    client: httpx.AsyncClient,
    model_name: str,
    payload: Dict[str, Any],
) -> ModelBlock:
    url = MODEL_URLS.get(model_name)
    if not url:
        return ModelBlock(
            status="skipped",
            latency_ms=0,
            error_message=f"No URL configured for {model_name}",
        )

    t0 = time.monotonic()
    try:
        response = await client.post(
            f"{url}/predict",
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        if response.status_code == 200:
            return ModelBlock(status="success", latency_ms=latency_ms, result=response.json())
        return ModelBlock(
            status="error",
            latency_ms=latency_ms,
            error_message=f"HTTP {response.status_code}: {response.text[:200]}",
        )
    except httpx.TimeoutException:
        return ModelBlock(
            status="timeout",
            latency_ms=int((time.monotonic() - t0) * 1000),
            error_message="Model timed out",
        )
    except Exception as exc:  # noqa: BLE001
        return ModelBlock(
            status="error",
            latency_ms=int((time.monotonic() - t0) * 1000),
            error_message=str(exc),
        )


async def orchestrate(request: GatewayRequest) -> Dict[str, ModelBlock]:
    """Call all requested models in parallel; always return partial results."""
    payload: Dict[str, Any] = {
        "patient_id": request.patient_id,
        "encounter_id": request.encounter_id,
        "context": request.context.model_dump(),
    }

    async with httpx.AsyncClient() as client:
        model_names = [m.value for m in request.models]
        coros = [_call_model(client, name, payload) for name in model_names]
        settled = await asyncio.gather(*coros, return_exceptions=True)

    output: Dict[str, ModelBlock] = {}
    for name, result in zip(model_names, settled):
        if isinstance(result, Exception):
            output[name] = ModelBlock(status="error", latency_ms=0, error_message=str(result))
        else:
            output[name] = result
    return output
