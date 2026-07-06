"""Model 3 — Lab Parser inference (stubbed).

When a real lab_report_id is provided, the live path will:
  1. Download the Cloudinary file
  2. Run ocr.extract_text()
  3. Run parser.parse_text()
  4. Run summarizer.patient_summary() + summarizer.clinical_summary()
"""
from __future__ import annotations

from typing import Any


def predict(patient_id: str, encounter_id: str, context: dict[str, Any]) -> dict:
    """Return a mock lab-parsing result."""
    return {
        "extracted_values": [
            {
                "test_name": "Haemoglobin",
                "value": 9.2,
                "unit": "g/dL",
                "reference_range": "13.5–17.5 g/dL",
                "is_abnormal": True,
                "is_critical": False,
            },
            {
                "test_name": "Wbc",
                "value": 12.4,
                "unit": "10³/µL",
                "reference_range": "4.5–11.0 10³/µL",
                "is_abnormal": True,
                "is_critical": False,
            },
        ],
        "abnormal_count": 2,
        "critical_count": 0,
        "patient_summary": "2 values are outside the normal range: Haemoglobin, Wbc.",
        "clinical_summary": (
            "Extracted 2 lab value(s).\n"
            "[Abnormal] Haemoglobin: 9.2 g/dL (ref: 13.5–17.5 g/dL)\n"
            "[Abnormal] Wbc: 12.4 10³/µL (ref: 4.5–11.0 10³/µL)"
        ),
        "model_version": "3.0.0-stub",
    }
