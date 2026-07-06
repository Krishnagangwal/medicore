"""Model 2 — Patient Deterioration FastAPI microservice.

Start:
    uvicorn endpoint:app --port 8002
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

sys.path.insert(0, str(Path(__file__).parent))

from inference import _meta, predict

app = FastAPI(title="MediCore Model 2 — Patient Deterioration", version="1.0.0")


class VitalReading(BaseModel):
    HR:       Optional[float] = None
    O2Sat:    Optional[float] = None
    Temp:     Optional[float] = None
    SBP:      Optional[float] = None
    MAP:      Optional[float] = None
    Resp:     Optional[float] = None
    ICULOS:   Optional[float] = None
    Age:      Optional[float] = None
    timestamp: Optional[str]  = None

    @field_validator("HR", "O2Sat", "Temp", "SBP", "MAP", "Resp", "ICULOS", "Age",
                     mode="before")
    @classmethod
    def must_be_numeric(cls, v: Any) -> Any:
        if v is None:
            return v
        try:
            return float(v)
        except (TypeError, ValueError):
            raise ValueError(f"Vital value must be numeric, got {v!r}")


class PredictRequest(BaseModel):
    encounter_id:    str
    vitals_readings: List[VitalReading]
    context:         Dict[str, Any] = {}

    @field_validator("vitals_readings")
    @classmethod
    def at_least_one(cls, v: list) -> list:
        if not v:
            raise ValueError("vitals_readings must contain at least one entry")
        return v


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": "model_2_deterioration",
        "auroc": _meta.get("auroc"),
        "alert_threshold": _meta.get("alert_threshold"),
    }


@app.post("/predict")
def run_predict(request: PredictRequest) -> dict:
    readings = [r.model_dump(exclude_none=False) for r in request.vitals_readings]
    try:
        return predict(vitals_list=readings, encounter_id=request.encounter_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
