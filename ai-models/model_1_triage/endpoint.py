"""Model 1 — Triage FastAPI microservice (real inference).

Start:
    uvicorn endpoint:app --port 8001

POST /predict body:
    {
        "patient_id": "uuid",
        "encounter_id": "uuid",
        "context": { ... },          // optional; vitals nested here too
        "vitals": {
            "heart_rate": 112,
            "systolic_bp": 95,
            ...                       // all optional; missing values use dataset medians
            "chief_complaint": "Chest pain"  // string — encoded to int internally
        }
    }
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

# Ensure local imports work when run as `uvicorn endpoint:app`
sys.path.insert(0, str(Path(__file__).parent))

from data_generation import CHIEF_COMPLAINTS
from inference import _meta, predict

app = FastAPI(title="MediCore Model 1 — Triage", version="1.0.0")

_CC_LOWER = {cc.lower(): i for i, cc in enumerate(CHIEF_COMPLAINTS)}


class VitalsInput(BaseModel):
    heart_rate:        Optional[float] = None
    systolic_bp:       Optional[float] = None
    diastolic_bp:      Optional[float] = None
    temperature:       Optional[float] = None
    respiratory_rate:  Optional[float] = None
    spo2:              Optional[float] = None
    pain_scale:        Optional[float] = None
    age:               Optional[float] = None
    chief_complaint:   Optional[str]   = None  # human-readable; encoded internally
    chief_complaint_code: Optional[int] = None  # accepted directly too
    shock_index:       Optional[float] = None   # computed if not provided

    @field_validator("heart_rate", "systolic_bp", "diastolic_bp",
                     "temperature", "respiratory_rate", "spo2",
                     "pain_scale", "age", "shock_index", mode="before")
    @classmethod
    def must_be_numeric(cls, v: Any) -> Any:
        if v is None:
            return v
        try:
            return float(v)
        except (TypeError, ValueError):
            raise ValueError(f"Vital value must be numeric, got {v!r}")

    def to_context_vitals(self) -> dict[str, Any]:
        """Return a flat vitals dict with encoded chief_complaint and derived shock_index."""
        d: dict[str, Any] = {}

        simple = [
            "heart_rate", "systolic_bp", "diastolic_bp",
            "temperature", "respiratory_rate", "spo2",
            "pain_scale", "age",
        ]
        for k in simple:
            v = getattr(self, k)
            if v is not None:
                d[k] = v

        # Encode chief_complaint string → int
        if self.chief_complaint_code is not None:
            d["chief_complaint_code"] = self.chief_complaint_code
        elif self.chief_complaint is not None:
            key = self.chief_complaint.strip().lower()
            code = _CC_LOWER.get(key)
            if code is None:
                d["chief_complaint_code"] = 9  # "Other"
            else:
                d["chief_complaint_code"] = code

        # Derive shock_index if not provided but both HR and SBP are available
        if "shock_index" not in d:
            hr  = d.get("heart_rate",  _meta["medians"]["heart_rate"])
            sbp = d.get("systolic_bp", _meta["medians"]["systolic_bp"])
            d["shock_index"] = round(float(hr) / max(float(sbp), 1.0), 4)
        else:
            d["shock_index"] = self.shock_index

        return d


class PredictRequest(BaseModel):
    patient_id:   str
    encounter_id: str
    context:      Dict[str, Any] = {}
    vitals:       Optional[VitalsInput] = None


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "model": "model_1_triage",
        "accuracy": _meta.get("overall_accuracy"),
    }


@app.post("/predict")
def run_predict(request: PredictRequest) -> dict:
    # Merge vitals: top-level VitalsInput takes precedence over context["vitals"]
    ctx = dict(request.context)
    if request.vitals is not None:
        ctx["vitals"] = request.vitals.to_context_vitals()
    elif "vitals" not in ctx:
        ctx["vitals"] = {}

    try:
        return predict(request.patient_id, request.encounter_id, ctx)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
