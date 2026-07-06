"""Model 2 — Patient Deterioration inference (real CatBoost model).

Input:  list of vital-sign dicts (most recent last).
Output: risk score, level, alert, SHAP top-5, trend.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from catboost import CatBoostClassifier, Pool

_BASE = Path(__file__).parent
_MODEL_PATH    = _BASE / "artifacts" / "model.cbm"
_FEATURES_PATH = _BASE / "artifacts" / "features.json"

_DISPLAY_NAMES: dict[str, str] = {
    "HR":          "Heart rate",
    "O2Sat":       "SpO₂",
    "Temp":        "Temperature",
    "SBP":         "Systolic BP",
    "MAP":         "Mean arterial pressure",
    "Resp":        "Respiratory rate",
    "delta_HR":    "Heart rate change (1h)",
    "delta_SBP":   "Systolic BP change (1h)",
    "delta_Resp":  "Respiratory rate change (1h)",
    "roll_HR":     "Heart rate (3h mean)",
    "roll_SBP":    "Systolic BP (3h mean)",
    "roll_O2Sat":  "SpO₂ (3h mean)",
    "shock_index": "Shock index",
    "news2_score": "NEWS2 score",
    "ICULOS":      "Hours in ICU",
    "Age":         "Age",
}

# ── Module-level model load ───────────────────────────────────────────────
_t0 = time.monotonic()

_model = CatBoostClassifier()
_model.load_model(str(_MODEL_PATH))

with open(_FEATURES_PATH) as _f:
    _meta: dict = json.load(_f)

_FEATURE_COLS: list[str]    = _meta["feature_cols"]
_MEDIANS: dict[str, float]  = _meta["medians"]
_ALERT_THRESHOLD: float     = _meta["alert_threshold"]

_load_ms = int((time.monotonic() - _t0) * 1000)
print(f"[model_2_deterioration] Model loaded in {_load_ms} ms")
assert _load_ms < 3000, f"Model load exceeded 3 s ({_load_ms} ms)"


# ── NEWS2 (scalar) ────────────────────────────────────────────────────────

def _news2(resp: float, spo2: float, temp: float, sbp: float, hr: float) -> int:
    score = 0
    if   resp <= 8:   score += 3
    elif resp <= 11:  score += 1
    elif resp <= 24:  score += 2 if resp > 20 else 0
    else:             score += 3
    if   spo2 <= 91:  score += 3
    elif spo2 <= 93:  score += 2
    elif spo2 <= 95:  score += 1
    if   temp <= 35:  score += 3
    elif temp <= 36:  score += 1
    elif temp <= 39:  score += 0 if temp <= 38 else 1
    else:             score += 2
    if   sbp <= 90:   score += 3
    elif sbp <= 100:  score += 2
    elif sbp <= 110:  score += 1
    elif sbp > 219:   score += 3
    if   hr <= 40:    score += 3
    elif hr <= 50:    score += 1
    elif hr <= 90:    score += 0
    elif hr <= 110:   score += 1
    elif hr <= 130:   score += 2
    else:             score += 3
    return score


def _g(d: dict, key: str) -> float:
    """Get a value from dict, falling back to the training median."""
    v = d.get(key)
    return float(v) if v is not None else _MEDIANS.get(key, 0.0)


def _build_features(readings: list[dict]) -> list[float]:
    """Build a 16-element feature vector from a list of vital readings."""
    cur  = readings[-1]
    prev = readings[-2] if len(readings) >= 2 else None
    last3 = readings[-3:] if len(readings) >= 3 else readings

    hr   = _g(cur, "HR");    sbp  = _g(cur, "SBP")
    spo2 = _g(cur, "O2Sat"); resp = _g(cur, "Resp")
    temp = _g(cur, "Temp");  map_ = _g(cur, "MAP")

    delta_HR   = hr   - _g(prev, "HR")   if prev else 0.0
    delta_SBP  = sbp  - _g(prev, "SBP")  if prev else 0.0
    delta_Resp = resp - _g(prev, "Resp")  if prev else 0.0

    roll_HR   = float(np.mean([_g(r, "HR")    for r in last3]))
    roll_SBP  = float(np.mean([_g(r, "SBP")   for r in last3]))
    roll_O2Sat = float(np.mean([_g(r, "O2Sat") for r in last3]))

    shock_index = hr / max(sbp, 1.0)
    news2       = _news2(resp, spo2, temp, sbp, hr)

    iculos = _g(cur, "ICULOS")
    age    = _g(cur, "Age") if _g(cur, "Age") > 0 else _MEDIANS.get("Age", 55.0)

    return [
        hr, spo2, temp, sbp, map_, resp,
        delta_HR, delta_SBP, delta_Resp,
        roll_HR, roll_SBP, roll_O2Sat,
        shock_index, float(news2),
        iculos, age,
    ]


def _score(readings: list[dict]) -> float:
    """Return raw risk probability for the given reading list."""
    fv = _build_features(readings)
    pool = Pool([fv], feature_names=_FEATURE_COLS)
    return float(_model.predict_proba(pool)[0][1])


def _risk_level(score: float) -> str:
    if score > _ALERT_THRESHOLD:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def predict(vitals_list: list[dict[str, Any]], encounter_id: str = "") -> dict:
    """Full inference with SHAP, trend, and structured output.

    vitals_list: list of dicts (most recent last).
      Each dict: {HR, O2Sat, Temp, SBP, MAP, Resp, ICULOS, Age, ...}
    """
    n = len(vitals_list)
    if n == 0:
        raise ValueError("vitals_list must contain at least one reading")

    # Current risk
    fv   = _build_features(vitals_list)
    pool = Pool([fv], feature_names=_FEATURE_COLS)

    proba      = _model.predict_proba(pool)[0]
    risk_score = float(proba[1])

    # Trend
    if n < 2:
        trend = "insufficient_data"
    else:
        prev_score = _score(vitals_list[:-1])
        diff = risk_score - prev_score
        if diff > 0.04:
            trend = "worsening"
        elif diff < -0.04:
            trend = "improving"
        else:
            trend = "stable"

    # SHAP — binary Logloss → shape (n_samples, n_features + 1)
    shap_matrix = _model.get_feature_importance(pool, type="ShapValues")
    if shap_matrix.ndim == 3:
        shap_row = shap_matrix[0][1][:-1]   # class=1 (sepsis)
    else:
        shap_row = shap_matrix[0][:-1]       # binary — single row

    ranked = sorted(
        zip(_FEATURE_COLS, fv, shap_row.tolist()),
        key=lambda x: abs(x[2]),
        reverse=True,
    )[:5]

    shap_values = [
        {
            "feature":      feat,
            "display_name": _DISPLAY_NAMES.get(feat, feat),
            "value":        round(float(val), 3),
            "impact":       round(float(imp), 4),
            "direction":    "increases_risk" if imp > 0 else "decreases_risk",
        }
        for feat, val, imp in ranked
    ]

    # Timestamp
    cur = vitals_list[-1]
    last_vitals_at = cur.get("timestamp") or datetime.now(timezone.utc).isoformat()

    return {
        "risk_score":       round(risk_score, 4),
        "risk_level":       _risk_level(risk_score),
        "alert":            risk_score > _ALERT_THRESHOLD,
        "alert_threshold":  _ALERT_THRESHOLD,
        "shap_values":      shap_values,
        "trend":            trend,
        "based_on_readings": n,
        "last_vitals_at":   last_vitals_at,
    }
