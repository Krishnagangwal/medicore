"""Model 3 — Lab Parser FastAPI microservice.

Start:
    uvicorn endpoint:app --port 8003

Accepts two input modes on POST /predict:
    Mode A - multipart/form-data: file upload (field "file") + optional "gender" field
    Mode B - application/json: {"file_base64": "...", "file_format": "pdf|jpg|png", "gender": "..."}
"""
from __future__ import annotations

import base64
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from inference import parse

app = FastAPI(title="MediCore Model 3 — Lab Parser", version="1.0.0")


class PredictJSONRequest(BaseModel):
    file_base64: str
    file_format: str
    gender: Optional[str] = "unknown"


class PredictResponse(BaseModel):
    ocr_status: str
    extracted_values: list[dict[str, Any]]
    abnormal_count: int
    critical_count: int
    patient_summary: Optional[str]
    clinical_summary: Optional[str]


def _infer_format(filename: Optional[str], content_type: Optional[str]) -> str:
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ("pdf", "jpg", "jpeg", "png"):
            return "pdf" if ext == "pdf" else ext
    if content_type:
        if "pdf" in content_type:
            return "pdf"
        if "png" in content_type:
            return "png"
        if "jpeg" in content_type or "jpg" in content_type:
            return "jpg"
    return "png"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": "lab_parser", "version": "1.0"}


@app.post("/predict", response_model=PredictResponse)
async def run_predict(request: Request) -> dict:
    content_type = request.headers.get("content-type", "")

    try:
        if "multipart/form-data" in content_type:
            form = await request.form()
            upload = form.get("file")
            if upload is None:
                raise HTTPException(status_code=400, detail="Missing 'file' in form data")
            gender = form.get("gender") or "unknown"
            file_bytes = await upload.read()
            file_format = _infer_format(upload.filename, upload.content_type)
        else:
            body = await request.json()
            payload = PredictJSONRequest(**body)
            file_bytes = base64.b64decode(payload.file_base64)
            file_format = payload.file_format
            gender = payload.gender or "unknown"
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {e}") from e

    return parse(file_bytes, file_format, gender=gender)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
