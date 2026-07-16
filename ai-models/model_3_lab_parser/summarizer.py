"""Summarize parsed lab results into patient-facing and clinical strings.

Patient summary: plain English, capped near 5 sentences. Every abnormal
test is named; critical findings each get their own callout, mild/moderate
findings are grouped by direction (low vs high) into shared sentences so
the total length stays readable regardless of how many values are abnormal.

Clinical summary: medical terminology, capped near 6 sentences, most
severe finding first, each abnormal gets one line pairing the deviation
with the reference_ranges clinical_low/clinical_high note.
"""
from __future__ import annotations

from reference_ranges import REFERENCE_RANGES

_SEVERITY_RANK = {"critical": 0, "moderate": 1, "mild": 2, "normal": 3}


def _plain_direction_word(flag: str) -> str:
    return "low" if flag in ("LOW", "CRITICAL_LOW") else "high"


def summarize(extracted_values: list[dict], gender: str = "unknown") -> dict:
    """Build patient_summary and clinical_summary from parser.parse_text() output."""
    if not extracted_values:
        return {
            "patient_summary": "No lab values could be identified in this report.",
            "clinical_summary": "Lab report parsing yielded no extractable values.",
        }

    abnormal = [v for v in extracted_values if v["flag"] != "NORMAL"]

    if not abnormal:
        return {
            "patient_summary": "All your test results are within the normal range. No immediate concerns.",
            "clinical_summary": "All extracted values are within normal limits. No immediate action required.",
        }

    patient_summary = _build_patient_summary(abnormal)
    clinical_summary = _build_clinical_summary(abnormal)
    return {"patient_summary": patient_summary, "clinical_summary": clinical_summary}


def _entry_for(test_display_name: str) -> dict:
    for entry in REFERENCE_RANGES.values():
        if entry["display_name"] == test_display_name:
            return entry
    return {}


def _build_patient_summary(abnormal: list[dict]) -> str:
    sentences = [f"Your blood test results show {len(abnormal)} value(s) outside the normal range."]

    critical = [v for v in abnormal if v["severity"] == "critical"]
    non_critical = [v for v in abnormal if v["severity"] != "critical"]

    for v in critical:
        entry = _entry_for(v["test"])
        word = _plain_direction_word(v["flag"])
        plain_text = entry.get("plain_low") if word == "low" else entry.get("plain_high")
        plain_text = plain_text or f"{word} {v['test'].lower()}"
        sentences.append(
            f"Your {v['test']} is significantly {word} at {v['value']} {v['unit']} — "
            f"{plain_text} — and this needs urgent medical attention."
        )

    low_names = [v["test"] for v in non_critical if v["flag"] == "LOW"]
    high_names = [v["test"] for v in non_critical if v["flag"] == "HIGH"]
    if low_names:
        verb = "is" if len(low_names) == 1 else "are"
        sentences.append(f"Your {', '.join(low_names)} {verb} slightly low.")
    if high_names:
        verb = "is" if len(high_names) == 1 else "are"
        sentences.append(f"Your {', '.join(high_names)} {verb} slightly high.")

    sentences.append("Please discuss these results with your doctor at your earliest convenience.")
    return " ".join(sentences)


def _build_clinical_summary(abnormal: list[dict]) -> str:
    ordered = sorted(abnormal, key=lambda v: _SEVERITY_RANK.get(v["severity"], 3))

    max_detail = 5
    shown, remainder = ordered[:max_detail], ordered[max_detail:]

    lines: list[str] = []
    for v in shown:
        entry = _entry_for(v["test"])
        direction = "below" if v["flag"] in ("LOW", "CRITICAL_LOW") else "above"
        boundary_word = "lower" if direction == "below" else "upper"
        boundary_value = v["reference_low"] if direction == "below" else v["reference_high"]
        deviation_pct = round(abs(v["value"] - boundary_value) / boundary_value * 100) if boundary_value else 0
        clinical_note = entry.get("clinical_low") if direction == "below" else entry.get("clinical_high")
        clinical_note = clinical_note or "Correlate clinically"
        lines.append(
            f"{v['test']}: {v['value']} {v['unit']} ({deviation_pct}% {direction} {boundary_word} limit) — "
            f"{clinical_note}."
        )

    if remainder:
        lines.append(f"...and {len(remainder)} more abnormal value(s) requiring review.")

    lines.append(
        "Recommended: correlate clinically and consider further work-up "
        "(repeat testing, targeted investigations, or specialist referral) based on the abnormalities above."
    )
    return " ".join(lines)
