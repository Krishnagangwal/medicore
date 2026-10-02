"""
MediCore AI Gateway — entry point.

Orchestrates parallel dispatch to the sepsis model (port 8001) and
drug interaction model (port 8004), returning one unified response
matching the CLAUDE.md contract. Called by the Node.js backend for
every patient scoring event.

Start: uvicorn main:app --port 8000
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

import httpx
import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from middleware import verify_token
from orchestrator import DRUG_MODEL_URL, SEPSIS_MODEL_URL, dispatch
from schemas import GatewayRequest, GatewayResponse

app = FastAPI(
    title="MediCore AI Gateway",
    description="Sepsis care platform — orchestrates AI model dispatch",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def check_model_health(base_url: str) -> bool:
    """Quick health check on a model endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{base_url}/health", timeout=3.0)
            return r.status_code == 200
    except Exception:  # noqa: BLE001 — an unreachable model reports "offline", not a 500
        return False


@app.get("/health")
async def health() -> dict:
    """Health check — used by UptimeRobot and Node.js backend."""
    sepsis_online = await check_model_health(SEPSIS_MODEL_URL)
    drug_online = await check_model_health(DRUG_MODEL_URL)

    return {
        "status": "ok",
        "service": "medicore-ai-gateway",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models": {
            "sepsis": "online" if sepsis_online else "offline",
            "drug_interaction": "online" if drug_online else "offline",
        },
        "version": "1.0.0",
    }


@app.post("/gateway/sepsis-assessment", response_model=GatewayResponse)
async def sepsis_assessment(request: GatewayRequest, user: dict = Depends(verify_token)) -> GatewayResponse:
    """Main clinical assessment endpoint.

    Called by the Node.js backend for every patient scoring event.
    Fires the sepsis and drug interaction models in parallel. Always
    returns — dispatch() handles all per-model failures internally,
    so a 500 here would mean a genuine, unexpected gateway bug.
    """
    try:
        return await dispatch(request)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Gateway internal error: {str(e)}")

@app.post("/gateway/predict", response_model=GatewayResponse)
async def predict_alias(
    request: GatewayRequest,
    user: dict = Depends(verify_token)
):
    return await sepsis_assessment(request, user)

@app.post("/gateway/sepsis-assessment/public", response_model=GatewayResponse)
async def sepsis_assessment_public(request: GatewayRequest) -> GatewayResponse:
    """Same as above but no auth required.

    Used for demo day testing and direct model testing. In production
    this would be removed.
    """
    return await dispatch(request)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)