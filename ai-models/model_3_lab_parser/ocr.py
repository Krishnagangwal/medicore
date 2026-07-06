"""OCR extraction from lab report PDFs and images.

Requires system dependencies:
    brew install tesseract poppler  # macOS
    apt-get install tesseract-ocr poppler-utils  # Debian/Ubuntu
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def extract_text_from_image(image_path: str) -> str:
    """Run Tesseract OCR on a single image file and return extracted text."""
    import pytesseract  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    img = Image.open(image_path)
    return pytesseract.image_to_string(img, config="--psm 6")


def extract_text_from_pdf(pdf_path: str, dpi: int = 300) -> str:
    """Convert each PDF page to an image and run OCR; return concatenated text."""
    from pdf2image import convert_from_path  # noqa: PLC0415
    import pytesseract  # noqa: PLC0415

    pages = convert_from_path(pdf_path, dpi=dpi)
    return "\n".join(pytesseract.image_to_string(page, config="--psm 6") for page in pages)


def extract_text(source: str) -> str:
    """Dispatch OCR to the correct handler based on file extension."""
    path = Path(source)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(source)
    if ext in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
        return extract_text_from_image(source)
    raise ValueError(f"Unsupported file type: {ext}")
