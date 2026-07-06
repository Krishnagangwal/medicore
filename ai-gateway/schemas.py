from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ModelType(str, Enum):
    TRIAGE = "triage"
    DETERIORATION = "deterioration"
    LAB_PARSER = "lab_parser"
    DRUG_INTERACTION = "drug_interaction"
    DIFFERENTIAL_DX = "differential_dx"
    READMISSION = "readmission"


class ShapValue(BaseModel):
    feature: str
    display_name: str
    value: float
    impact: float
    direction: Literal["increases_risk", "decreases_risk", "neutral"]


class ModelBlock(BaseModel):
    status: Literal["success", "error", "timeout", "skipped"]
    latency_ms: int
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class GatewayContext(BaseModel):
    symptom_text: Optional[str] = None
    medications: List[str] = Field(default_factory=list)
    lab_report_id: Optional[str] = None
    vitals_last_n: int = Field(default=3, ge=1, le=20)


class GatewayRequest(BaseModel):
    patient_id: str
    encounter_id: str
    models: List[ModelType]
    context: GatewayContext


class GatewayResponse(BaseModel):
    patient_id: str
    encounter_id: str
    triage: Optional[ModelBlock] = None
    deterioration: Optional[ModelBlock] = None
    lab_parser: Optional[ModelBlock] = None
    drug_interaction: Optional[ModelBlock] = None
    differential_dx: Optional[ModelBlock] = None
    readmission: Optional[ModelBlock] = None
