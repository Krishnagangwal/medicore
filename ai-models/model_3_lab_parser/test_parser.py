"""Self-test for Model 3 — Lab Parser. Run directly:

    python test_parser.py

Exercises parser.parse_text() on a synthetic lab report (no OCR/file
needed) and verifies the flags/severities the acceptance criteria call
for, then runs the full inference.parse() summary text through the same
checks.
"""
from __future__ import annotations

import json

import parser
import summarizer

TEST_TEXT = """
COMPLETE BLOOD COUNT
Hemoglobin:     7.8 g/dL      Reference: 12.0-17.0   LOW
WBC:            14.2 x10/uL   Reference: 4.0-11.0    HIGH
Platelets:      450 10^3/uL   Reference: 150-400      HIGH

LIVER FUNCTION
ALT:            85 U/L        Reference: 7-45         HIGH
Total Bilirubin: 0.8 mg/dL   Reference: 0.2-1.2      NORMAL

GLUCOSE
HbA1c:          8.2%          Reference: 4.5-6.4      HIGH
"""


def _find(values: list[dict], test_name: str) -> dict:
    for v in values:
        if v["test"].lower() == test_name.lower():
            return v
    raise AssertionError(f"{test_name} not found in extracted values: {values}")


def main() -> None:
    values = parser.parse_text(TEST_TEXT)
    print("Extracted values:")
    print(json.dumps(values, indent=2))

    assert len(values) == 6, f"expected 6 extracted values, got {len(values)}"

    hemoglobin = _find(values, "Hemoglobin")
    assert hemoglobin["flag"] == "CRITICAL_LOW", hemoglobin
    assert hemoglobin["severity"] == "critical", hemoglobin

    wbc = _find(values, "WBC")
    assert wbc["flag"] == "HIGH", wbc

    platelets = _find(values, "Platelets")
    assert platelets["flag"] == "HIGH", platelets

    alt = _find(values, "ALT")
    assert alt["flag"] == "HIGH", alt

    bilirubin = _find(values, "Total Bilirubin")
    assert bilirubin["flag"] == "NORMAL", bilirubin

    hba1c = _find(values, "HbA1c")
    assert hba1c["flag"] == "HIGH", hba1c

    print("\nAll flag assertions passed.")

    summary = summarizer.summarize(values)
    print("\nPatient summary:")
    print(summary["patient_summary"])
    print("\nClinical summary:")
    print(summary["clinical_summary"])

    patient_lower = summary["patient_summary"].lower()
    assert "hemoglobin" in patient_lower and "low" in patient_lower and "urgent" in patient_lower, (
        "patient_summary must mention hemoglobin critically low"
    )
    assert "hba1c" in patient_lower and "high" in patient_lower, (
        "patient_summary must mention HbA1c high"
    )

    clinical_lower = summary["clinical_summary"].lower()
    assert "anemia" in clinical_lower, "clinical_summary must use the term 'anemia'"
    assert "glycemic control" in clinical_lower, "clinical_summary must mention 'glycemic control'"

    print("\nAll summary content assertions passed.")


if __name__ == "__main__":
    main()
