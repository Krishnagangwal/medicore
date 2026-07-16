"""Lab value extraction and reference-range comparison.

Line-by-line tokenized extraction of (test_name, value, unit, reference
range) from raw OCR text, normalized against reference_ranges.py and
flagged against normal/critical thresholds. No ML involved — purely
rule-based.

Tokenizing (splitting on whitespace) rather than one monolithic regex is
what lets this tell "HbA1c" (a name token that happens to contain a
digit) apart from "8.2" (the value token): a token is part of the name
as long as it starts with a letter; the first token that starts with a
digit is the value.

The trailing textual flag word some reports print ("LOW"/"HIGH"/"H"/"L")
is not relied upon — flag and severity are always computed from the
numeric value against the reference range, which is authoritative even
when the printed flag is missing, OCR-mangled, or absent from the format.
"""
from __future__ import annotations

import re

from reference_ranges import REFERENCE_RANGES, normalize_test_name, resolve_range

_VALUE_TOKEN_RE = re.compile(r"^(?P<num>\d+(?:[.,]\d+)?)(?P<suffix>.*)$")
_RANGE_RE = re.compile(r"(?P<low>\d+(?:[.,]\d+)?)\s*(?:-|–|to)\s*(?P<high>\d+(?:[.,]\d+)?)")
_UNIT_HINT_RE = re.compile(r"[A-Za-zµ%]")


def _to_float(raw: str) -> float:
    return float(raw.replace(",", "."))


def _compute_flag_severity(
    value: float, low: float, high: float, critical_low: float, critical_high: float
) -> tuple[str, str]:
    if low <= value <= high:
        return "NORMAL", "normal"

    if value <= critical_low:
        return "CRITICAL_LOW", "critical"
    if value >= critical_high:
        return "CRITICAL_HIGH", "critical"

    if value < low:
        deviation = (low - value) / low if low else 1.0
        return "LOW", "mild" if deviation < 0.20 else "moderate"

    deviation = (value - high) / high if high else 1.0
    return "HIGH", "mild" if deviation < 0.20 else "moderate"


def _parse_line(line: str, gender: str) -> dict | None:
    tokens = line.split()
    if not tokens:
        return None

    i = 0
    name_parts: list[str] = []
    while i < len(tokens) and tokens[i][0].isalpha():
        name_parts.append(tokens[i].strip(":-"))
        i += 1
    if not name_parts or i >= len(tokens):
        return None

    canonical = normalize_test_name(" ".join(name_parts))
    if canonical is None:
        return None

    value_match = _VALUE_TOKEN_RE.match(tokens[i])
    if not value_match:
        return None
    try:
        value = _to_float(value_match.group("num"))
    except ValueError:
        return None
    unit = value_match.group("suffix").strip()
    i += 1

    if not unit and i < len(tokens):
        candidate = tokens[i]
        stripped = candidate.strip("()[]")
        if _UNIT_HINT_RE.search(candidate) and not _RANGE_RE.fullmatch(stripped):
            unit = candidate
            i += 1

    defaults = resolve_range(canonical, gender)
    unit = unit or defaults["unit"]

    range_match = _RANGE_RE.search(" ".join(tokens[i:]))
    if range_match:
        try:
            low = _to_float(range_match.group("low"))
            high = _to_float(range_match.group("high"))
        except ValueError:
            low, high = defaults["low"], defaults["high"]
    else:
        low, high = defaults["low"], defaults["high"]

    flag, severity = _compute_flag_severity(value, low, high, defaults["critical_low"], defaults["critical_high"])

    return {
        "test": REFERENCE_RANGES[canonical]["display_name"],
        "value": value,
        "unit": unit,
        "reference_low": low,
        "reference_high": high,
        "flag": flag,
        "severity": severity,
    }


def parse_text(ocr_text: str, gender: str = "unknown") -> list[dict]:
    """Extract lab values from raw OCR text and flag abnormals.

    `gender` selects which normal range to fall back on when a line does
    not print its own reference range ("male"/"female"/"unknown").
    """
    results: list[dict] = []
    for raw_line in (ocr_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parsed = _parse_line(line, gender)
        if parsed is not None:
            results.append(parsed)
    return results
