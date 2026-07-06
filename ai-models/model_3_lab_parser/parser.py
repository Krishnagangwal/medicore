"""Lab value extraction and reference-range comparison.

Uses regex to pull (test_name, value, unit) tuples from OCR text, then
compares them against the static reference ranges defined below.
No ML involved — purely rule-based.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Static reference ranges  (min_normal, max_normal, critical_low, critical_high)
# Source: standard clinical reference values
# ---------------------------------------------------------------------------
REFERENCE_RANGES: dict[str, dict] = {
    "haemoglobin":     {"unit": "g/dL",  "lo": 13.5, "hi": 17.5, "crit_lo": 7.0,  "crit_hi": 20.0},
    "hemoglobin":      {"unit": "g/dL",  "lo": 13.5, "hi": 17.5, "crit_lo": 7.0,  "crit_hi": 20.0},
    "wbc":             {"unit": "10³/µL","lo": 4.5,  "hi": 11.0, "crit_lo": 2.0,  "crit_hi": 30.0},
    "platelets":       {"unit": "10³/µL","lo": 150,  "hi": 400,  "crit_lo": 50,   "crit_hi": 1000},
    "glucose":         {"unit": "mg/dL", "lo": 70,   "hi": 100,  "crit_lo": 40,   "crit_hi": 500},
    "creatinine":      {"unit": "mg/dL", "lo": 0.6,  "hi": 1.2,  "crit_lo": 0.0,  "crit_hi": 10.0},
    "sodium":          {"unit": "mEq/L", "lo": 136,  "hi": 145,  "crit_lo": 120,  "crit_hi": 160},
    "potassium":       {"unit": "mEq/L", "lo": 3.5,  "hi": 5.0,  "crit_lo": 2.5,  "crit_hi": 6.5},
    "bilirubin":       {"unit": "mg/dL", "lo": 0.1,  "hi": 1.2,  "crit_lo": 0.0,  "crit_hi": 15.0},
    "alt":             {"unit": "U/L",   "lo": 7,    "hi": 56,   "crit_lo": 0,    "crit_hi": 1000},
    "ast":             {"unit": "U/L",   "lo": 10,   "hi": 40,   "crit_lo": 0,    "crit_hi": 1000},
    "tsh":             {"unit": "µIU/mL","lo": 0.4,  "hi": 4.0,  "crit_lo": 0.0,  "crit_hi": 20.0},
    "crp":             {"unit": "mg/L",  "lo": 0.0,  "hi": 10.0, "crit_lo": 0.0,  "crit_hi": 200.0},
}

# Regex: captures test name, numeric value, and optional unit from a line like
#   "Haemoglobin  9.2  g/dL"  or  "WBC: 11.5 10^3/uL"
_LAB_PATTERN = re.compile(
    r"([A-Za-z][A-Za-z0-9\s\-/]+?)\s*[:\-]?\s*"
    r"([\d]+\.?[\d]*)\s*"
    r"([A-Za-z%µ³/^0-9\-]+)?",
    re.MULTILINE,
)


@dataclass
class LabValue:
    test_name: str
    value: float
    unit: str
    reference_range: str
    is_abnormal: bool
    is_critical: bool


def parse_text(ocr_text: str) -> list[LabValue]:
    """Extract lab values from raw OCR text and flag abnormals."""
    results: list[LabValue] = []

    for match in _LAB_PATTERN.finditer(ocr_text):
        raw_name = match.group(1).strip().lower()
        try:
            value = float(match.group(2))
        except ValueError:
            continue
        unit = (match.group(3) or "").strip()

        ref = REFERENCE_RANGES.get(raw_name)
        if ref is None:
            continue

        is_abnormal = not (ref["lo"] <= value <= ref["hi"])
        is_critical = value <= ref["crit_lo"] or value >= ref["crit_hi"]
        ref_range_str = f"{ref['lo']}–{ref['hi']} {ref['unit']}"

        results.append(
            LabValue(
                test_name=raw_name.title(),
                value=value,
                unit=unit or ref["unit"],
                reference_range=ref_range_str,
                is_abnormal=is_abnormal,
                is_critical=is_critical,
            )
        )

    return results
