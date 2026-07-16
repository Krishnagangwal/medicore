"""OCR extraction from lab report PDFs and images.

Requires system dependencies:
    brew install tesseract poppler          # macOS
    apt-get install tesseract-ocr poppler-utils  # Debian/Ubuntu

Never raises: any failure (missing binary, corrupt file, unsupported
format) is reported back through the returned dict instead of an
exception, so callers can always rely on getting a result.
"""
from __future__ import annotations

import io
from typing import Any


def _load_images(file_bytes: bytes, file_format: str) -> list:
    fmt = (file_format or "").strip().lower().lstrip(".")
    if fmt == "pdf":
        from pdf2image import convert_from_bytes  # noqa: PLC0415

        return convert_from_bytes(file_bytes)
    if fmt in {"jpg", "jpeg", "png", "tiff", "bmp"}:
        from PIL import Image  # noqa: PLC0415

        return [Image.open(io.BytesIO(file_bytes))]
    raise ValueError(f"Unsupported file format: {file_format}")


def _preprocess(image: Any) -> Any:
    """Grayscale + autocontrast + sharpen, used as a low-confidence retry pass."""
    from PIL import ImageFilter, ImageOps  # noqa: PLC0415

    gray = image.convert("L")
    contrasted = ImageOps.autocontrast(gray)
    return contrasted.filter(ImageFilter.SHARPEN)


def _ocr_images(images: list) -> tuple[str, float]:
    """Run pytesseract on each image, reconstructing line breaks from word geometry."""
    import pytesseract  # noqa: PLC0415

    lines: list[str] = []
    confidences: list[float] = []

    for image in images:
        data = pytesseract.image_to_data(image, config="--psm 6", output_type=pytesseract.Output.DICT)
        line_groups: dict[tuple[int, int, int], list[str]] = {}
        n = len(data.get("text", []))
        for i in range(n):
            word = data["text"][i]
            if not word or not word.strip():
                continue
            try:
                conf_val = float(data["conf"][i])
            except (TypeError, ValueError):
                conf_val = -1.0
            if conf_val <= 0:
                continue
            key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
            line_groups.setdefault(key, []).append(word)
            confidences.append(conf_val)

        for key in sorted(line_groups.keys()):
            lines.append(" ".join(line_groups[key]))

    text = "\n".join(lines)
    confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
    return text, confidence


def extract(file_bytes: bytes, file_format: str) -> dict:
    """Extract text from a lab report file.

    Returns {"text": str, "confidence": float, "method": str}. Never raises;
    on any failure returns an empty-text, zero-confidence result instead.
    """
    try:
        images = _load_images(file_bytes, file_format)
        if not images:
            return {"text": "", "confidence": 0.0, "method": "low_confidence"}

        text, confidence = _ocr_images(images)
        method = "pytesseract"

        if confidence < 0.60:
            try:
                enhanced_images = [_preprocess(image) for image in images]
                enhanced_text, enhanced_confidence = _ocr_images(enhanced_images)
                if enhanced_confidence > confidence:
                    text, confidence = enhanced_text, enhanced_confidence
            except Exception:
                pass
            method = "pytesseract_enhanced" if confidence >= 0.60 else "low_confidence"

        return {"text": text, "confidence": round(confidence, 4), "method": method}
    except Exception:
        return {"text": "", "confidence": 0.0, "method": "low_confidence"}
