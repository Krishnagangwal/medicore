"""Model 3 — Lab Parser inference orchestration.

parse() chains ocr.extract() -> parser.parse_text() -> summarizer.summarize().
Never raises: any unexpected failure degrades to the same empty-result
shape the API returns for a failed OCR pass, so the gateway can always
count on getting back a well-formed dict.
"""
from __future__ import annotations

import ocr
import parser
import summarizer

MODEL_VERSION = "3.0.0"


def _empty_result(ocr_status: str) -> dict:
    return {
        "ocr_status": ocr_status,
        "extracted_values": [],
        "abnormal_count": 0,
        "critical_count": 0,
        "patient_summary": None,
        "clinical_summary": None,
    }


def parse(file_bytes: bytes, file_format: str, gender: str = "unknown") -> dict:
    """Run the full lab-report pipeline and return the gateway-schema lab_parser.result shape."""
    try:
        ocr_result = ocr.extract(file_bytes, file_format)
        confidence = ocr_result.get("confidence", 0.0) or 0.0
        text = ocr_result.get("text") or ""

        if confidence >= 0.70:
            ocr_status = "high_confidence"
        elif confidence >= 0.40:
            ocr_status = "low_confidence"
        else:
            ocr_status = "failed"

        if ocr_status == "failed" or not text.strip():
            return _empty_result("failed" if ocr_status == "failed" else ocr_status)

        values = parser.parse_text(text, gender=gender)
        abnormal_count = sum(1 for v in values if v["flag"] != "NORMAL")
        critical_count = sum(1 for v in values if v["flag"] in ("CRITICAL_LOW", "CRITICAL_HIGH"))

        summary = summarizer.summarize(values, gender=gender)

        return {
            "ocr_status": ocr_status,
            "extracted_values": values,
            "abnormal_count": abnormal_count,
            "critical_count": critical_count,
            "patient_summary": summary.get("patient_summary"),
            "clinical_summary": summary.get("clinical_summary"),
        }
    except Exception:
        return _empty_result("failed")
