"""
FastAPI wrapper around inference.predict() for the AI Gateway.

Runs standalone on port 8001 (SEPSIS_MODEL_URL in ai-gateway/.env).
Per CLAUDE.md convention: never raise an uncaught exception here —
always return JSON, since the gateway must still return partial
results if this model errors out.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import inference
from model import get_device

app = FastAPI(title="MediCore Sepsis Model", version="1.0")


class VitalsReading(BaseModel):
    hr: float | None = None
    o2sat: float | None = None
    temp: float | None = None
    sbp: float | None = None
    map: float | None = None
    dbp: float | None = None
    resp: float | None = None
    iculos: float = 0


class PredictRequest(BaseModel):
    vitals_readings: list[VitalsReading]
    encounter_id: str | None = None


@app.post("/predict")
def predict_sepsis(request: PredictRequest):
    if len(request.vitals_readings) < 2:
        return JSONResponse(
            status_code=400,
            content={"error": "Minimum 2 readings required", "code": "INSUFFICIENT_READINGS", "statusCode": 400},
        )
    try:
        readings = [r.model_dump() for r in request.vitals_readings]
        return inference.predict(readings)
    except Exception as exc:  # never raise uncaught — gateway needs partial results
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "code": "INFERENCE_ERROR", "statusCode": 500},
        )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": "time2vec-transformer-sepsis",
        "version": "1.0",
        "device": str(get_device()),
    }
