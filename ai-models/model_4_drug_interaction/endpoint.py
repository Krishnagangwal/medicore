"""Model 4 — Drug Interaction FastAPI microservice.

Start:
    uvicorn endpoint:app --port 8004
"""
from __future__ import annotations

from typing import Any, Dict

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from inference import predict

app = FastAPI(title="MediCore Model 4 — Drug Interaction", version="1.0.0-stub")


class PredictRequest(BaseModel):
    patient_id: str
    encounter_id: str
    context: Dict[str, Any] = {}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": "model_4_drug_interaction"}


@app.post("/predict")
def run_predict(request: PredictRequest) -> dict:
    return predict(request.patient_id, request.encounter_id, request.context)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
