from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from middleware import get_current_user
from orchestrator import orchestrate
from schemas import GatewayRequest, GatewayResponse

app = FastAPI(title="MediCore AI Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/gateway/predict", response_model=GatewayResponse)
async def predict(
    request: GatewayRequest,
    _user: dict = Depends(get_current_user),
) -> GatewayResponse:
    results = await orchestrate(request)
    return GatewayResponse(
        patient_id=request.patient_id,
        encounter_id=request.encounter_id,
        triage=results.get("triage"),
        deterioration=results.get("deterioration"),
        lab_parser=results.get("lab_parser"),
        drug_interaction=results.get("drug_interaction"),
        differential_dx=results.get("differential_dx"),
        readmission=results.get("readmission"),
    )
