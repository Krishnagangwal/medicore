"""
Inference module for the Time-Aware Transformer sepsis model.

Model and artifacts are loaded once at import time (never per request)
so the AI Gateway can call predict() with low, consistent latency.

ASSUMPTIONS (stated explicitly, matching data_loader.py's conventions):
- Vitals not present in a reading are imputed with the training-set
  median stored in artifacts/normalisation.json (same statistic used
  for training-time imputation of never-recorded vitals).
- "trend" compares the current risk_score against the risk_score
  computed on the same readings minus the most recent one (i.e. "what
  did the model think one hour ago"). A small deadband (0.03) absorbs
  float noise so trend doesn't flip on negligible changes. Fewer than
  2 readings -> "insufficient_data".
- top_attended_hours reports RAW (pre-normalisation) vitals, since a
  clinician reading the explanation needs real units (hr=118), not the
  [0,1]-scaled values the model actually consumes.
"""

import json
import os

import torch

from data_loader import VITAL_COLS, WINDOW_SIZE
from model import SepsisTransformer, get_device

_ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
_KEY_MAP = {"hr": "HR", "o2sat": "O2Sat", "temp": "Temp", "sbp": "SBP", "map": "MAP", "dbp": "DBP", "resp": "Resp"}
_COL_TO_KEY = {v: k for k, v in _KEY_MAP.items()}

_ALERT_THRESHOLD = 0.65
_MODEL_VERSION = "1.0"

_device = get_device()
_model = SepsisTransformer().to(_device)

with open(os.path.join(_ARTIFACTS_DIR, "normalisation.json")) as f:
    _NORM = json.load(f)

_model_path = os.path.join(_ARTIFACTS_DIR, "model.pt")
if os.path.exists(_model_path):
    _model.load_state_dict(torch.load(_model_path, map_location=_device))
_model.eval()


def _risk_level(risk_score: float) -> str:
    if risk_score < 0.4:
        return "low"
    if risk_score <= 0.65:
        return "medium"
    return "high"


def _prepare_window(vitals_readings: list):
    """Build a left-padded (vitals, timestamps, mask) window plus the
    raw (pre-normalisation) reading dicts aligned to window position,
    for the last WINDOW_SIZE readings (chronologically sorted)."""
    readings = sorted(vitals_readings, key=lambda r: r.get("iculos", 0))[-WINDOW_SIZE:]
    n_real = len(readings)
    pad_len = WINDOW_SIZE - n_real

    vitals = torch.zeros(WINDOW_SIZE, len(VITAL_COLS), dtype=torch.float32)
    timestamps = torch.zeros(WINDOW_SIZE, dtype=torch.float32)
    mask = torch.zeros(WINDOW_SIZE, dtype=torch.bool)
    raw_aligned = [None] * WINDOW_SIZE

    for i, reading in enumerate(readings):
        pos = pad_len + i
        for j, col in enumerate(VITAL_COLS):
            value = reading.get(_COL_TO_KEY[col])
            if value is None:
                value = _NORM[col]["median"]
            lo, hi = _NORM[col]["min"], _NORM[col]["max"]
            span = hi - lo if hi > lo else 1.0
            vitals[pos, j] = max(0.0, min(1.0, (float(value) - lo) / span))
        timestamps[pos] = float(reading.get("iculos", 0))
        mask[pos] = True
        raw_aligned[pos] = reading

    return vitals, timestamps, mask, raw_aligned, n_real


@torch.no_grad()
def _forward(vitals: torch.Tensor, timestamps: torch.Tensor, mask: torch.Tensor):
    v = vitals.unsqueeze(0).to(_device)
    t = timestamps.unsqueeze(0).to(_device)
    m = mask.unsqueeze(0).to(_device)
    risk_logit, sofa_pred, importance = _model(v, t, m)
    risk_score = torch.sigmoid(risk_logit).item()
    sofa_score = max(0.0, sofa_pred.item())
    importance = importance.squeeze(0).cpu()
    total = importance.sum().item()
    if total > 1e-8:
        importance = importance / total
    return risk_score, sofa_score, importance


def predict(vitals_readings: list) -> dict:
    """Run the sepsis model on up to 24 hourly vital-sign readings.

    Args:
        vitals_readings: list of dicts, each with keys among
            {hr, o2sat, temp, sbp, map, dbp, resp, iculos}. Missing
            keys are imputed with the training-set median.

    Returns: dict matching the CLAUDE.md sepsis model output contract.
    """
    vitals, timestamps, mask, raw_aligned, n_real = _prepare_window(vitals_readings)
    risk_score, sofa_score, importance = _forward(vitals, timestamps, mask)

    if n_real >= 2:
        # Compare against the same readings minus the most recent one,
        # i.e. "what the model would have said one hour ago".
        readings_sorted = sorted(vitals_readings, key=lambda r: r.get("iculos", 0))
        prev_vitals, prev_ts, prev_mask, _, _ = _prepare_window(readings_sorted[:-1])
        prev_risk, _, _ = _forward(prev_vitals, prev_ts, prev_mask)
        delta = risk_score - prev_risk
        if delta > 0.03:
            trend = "worsening"
        elif delta < -0.03:
            trend = "improving"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"

    attn_list = importance.tolist()
    real_indices = [i for i in range(WINDOW_SIZE) if raw_aligned[i] is not None]
    ranked = sorted(real_indices, key=lambda i: attn_list[i], reverse=True)[:3]
    peak_hour = ranked[0] if ranked else int(torch.argmax(importance).item())

    top_attended_hours = []
    for idx in ranked:
        reading = raw_aligned[idx]
        top_attended_hours.append(
            {
                "hour_index": idx,
                "iculos_hour": reading.get("iculos"),
                "attention": attn_list[idx],
                "vitals": {
                    "hr": reading.get("hr"),
                    "o2sat": reading.get("o2sat"),
                    "temp": reading.get("temp"),
                    "sbp": reading.get("sbp"),
                    "resp": reading.get("resp"),
                },
            }
        )

    return {
        "risk_score": risk_score,
        "risk_level": _risk_level(risk_score),
        "alert": risk_score > _ALERT_THRESHOLD,
        "alert_threshold": _ALERT_THRESHOLD,
        "sofa_score": sofa_score,
        "sofa_rounded": round(sofa_score),
        "trend": trend,
        "attention_weights": attn_list,
        "attention_peak_hour": peak_hour,
        "top_attended_hours": top_attended_hours,
        "based_on_readings": n_real,
        "model": "time2vec-transformer",
        "model_version": _MODEL_VERSION,
    }
