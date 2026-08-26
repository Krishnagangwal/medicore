"""
Rule-based sepsis alert text generator.

Qwen LLM replaces this in a later session — the generate_alert_text()
signature stays the same, only the implementation changes, so nothing
calling it needs to change when that happens.
"""

from __future__ import annotations


def generate_alert_text(sepsis_result: dict) -> str:
    """Generate a 1-2 sentence plain-English clinical alert.

    Called only when alert=True. Never raises — any malformed input
    (missing keys, wrong types) falls through to a safe fallback
    string so a bad model response never breaks the gateway response.
    """
    if isinstance(sepsis_result, dict) and sepsis_result.get("alert") is False:
        return ""

    try:
        risk_score = sepsis_result["risk_score"]

        if risk_score > 0.85:
            lead = "Critical sepsis risk detected."
        elif risk_score > 0.75:
            lead = "High sepsis risk detected."
        elif risk_score > 0.65:
            lead = "Elevated sepsis risk detected."
        else:
            lead = "Sepsis risk detected."

        driver_text = None
        top_hours = sepsis_result.get("top_attended_hours") or []
        if top_hours:
            vitals = top_hours[0].get("vitals", {}) or {}
            hr = vitals.get("hr")
            o2sat = vitals.get("o2sat")
            temp = vitals.get("temp")
            sbp = vitals.get("sbp")
            resp = vitals.get("resp")

            if hr is not None and hr > 100:
                driver_text = f"tachycardia (HR {hr})"
            elif o2sat is not None and o2sat < 94:
                driver_text = f"hypoxia (SpO2 {o2sat}%)"
            elif temp is not None and temp > 38.3:
                driver_text = f"fever ({temp}°C)"
            elif sbp is not None and sbp < 90:
                driver_text = f"hypotension (SBP {sbp}mmHg)"
            elif resp is not None and resp > 20:
                driver_text = f"tachypnoea (RR {resp})"

        parts = [lead]
        if driver_text:
            parts.append(f"Primary driver: {driver_text}.")

        sofa_rounded = sepsis_result.get("sofa_rounded")
        if sofa_rounded is not None and sofa_rounded >= 2:
            parts.append(f"SOFA score {sofa_rounded}.")

        if risk_score > 0.80:
            parts.append("Immediate clinical assessment required.")
        else:
            parts.append("Prompt assessment recommended.")

        return " ".join(parts)

    except Exception:
        risk_score = sepsis_result.get("risk_score") if isinstance(sepsis_result, dict) else None
        try:
            risk_score = float(risk_score)
        except (TypeError, ValueError):
            risk_score = 0.0
        return f"Sepsis alert: elevated risk score {risk_score:.2f}. Clinical assessment recommended."
