"""
Pydantic models for the AI Gateway, matching the CLAUDE.md
sepsis-assessment contract exactly.

ModelBlock.result is deliberately a generic dict rather than
SepsisResult/DrugResult specifically: the gateway passes through
whatever each model actually returns (which may include extra,
model-specific fields — e.g. the drug interaction model also returns
a `graph` field) without re-validating or stripping it. SepsisResult
and DrugResult below document the expected shape for reference.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator


class VitalReading(BaseModel):
    hr: Optional[float] = None
    o2sat: Optional[float] = None
    temp: Optional[float] = None
    sbp: Optional[float] = None
    map: Optional[float] = None
    dbp: Optional[float] = None
    resp: Optional[float] = None
    iculos: Optional[float] = None


class GatewayRequest(BaseModel):
    patient_id: str
    encounter_id: str
    vitals_readings: list[VitalReading]
    medications: list[str] = []

    @field_validator("vitals_readings")
    @classmethod
    def must_have_readings(cls, v: list[VitalReading]) -> list[VitalReading]:
        if len(v) < 2:
            raise ValueError("Minimum 2 vital readings required")
        return v


class ShapValue(BaseModel):
    feature: str
    display_name: str
    impact: float
    direction: str


class AttendedHour(BaseModel):
    hour_index: int
    iculos_hour: Optional[float] = None
    attention: float
    vitals: dict


class SepsisResult(BaseModel):
    risk_score: float
    risk_level: str
    alert: bool
    alert_threshold: float
    sofa_score: float
    sofa_rounded: int
    trend: str
    attention_weights: list[float]
    attention_peak_hour: int
    top_attended_hours: list[AttendedHour]
    alert_text: str
    based_on_readings: int
    model: str


class DrugInteraction(BaseModel):
    drug_a: str
    drug_b: str
    severity: str
    severity_code: int
    mechanism: str
    recommendation: str
    shap_values: list[dict] = []


class DrugResult(BaseModel):
    total_pairs_checked: int
    interaction_count: int
    interactions: list[DrugInteraction]


class ModelBlock(BaseModel):
    status: str  # "success" | "error" | "timeout" | "skipped"
    latency_ms: Optional[int] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None


class GatewayResponse(BaseModel):
    request_id: str
    patient_id: str
    encounter_id: str
    requested_at: str
    completed_at: str
    sepsis: ModelBlock
    drug_interaction: ModelBlock
