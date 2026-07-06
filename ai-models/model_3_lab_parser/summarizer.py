"""Summarise parsed lab results into patient-facing and clinical strings."""
from __future__ import annotations

from parser import LabValue


def patient_summary(values: list[LabValue]) -> str:
    """Plain-language summary suitable for the patient portal."""
    if not values:
        return "No lab values could be extracted from this report."

    abnormal = [v for v in values if v.is_abnormal]
    critical = [v for v in values if v.is_critical]

    lines: list[str] = []
    if not abnormal:
        lines.append("All extracted lab values are within normal limits.")
    else:
        lines.append(
            f"{len(abnormal)} value(s) are outside the normal range: "
            + ", ".join(v.test_name for v in abnormal)
            + "."
        )
    if critical:
        lines.append(
            f"ATTENTION: {len(critical)} value(s) are critically abnormal: "
            + ", ".join(v.test_name for v in critical)
            + ". Please seek immediate medical attention."
        )
    return " ".join(lines)


def clinical_summary(values: list[LabValue]) -> str:
    """Concise clinical narrative for the doctor portal."""
    if not values:
        return "Lab report parsing yielded no extractable values."

    abnormal = [v for v in values if v.is_abnormal]
    critical = [v for v in values if v.is_critical]

    lines = [f"Extracted {len(values)} lab value(s)."]
    for v in abnormal:
        flag = "CRITICAL" if v.is_critical else "Abnormal"
        lines.append(
            f"[{flag}] {v.test_name}: {v.value} {v.unit} "
            f"(ref: {v.reference_range})"
        )
    if not abnormal:
        lines.append("No abnormal values detected.")
    return "\n".join(lines)
