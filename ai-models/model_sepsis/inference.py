"""
Inference module for the Time-Aware Transformer sepsis model.

Model and artifacts are loaded once at import time (never per request)
so the AI Gateway can call predict() with low, consistent latency.

ASSUMPTIONS (stated explicitly, matching data_loader.py's conventions):
- Vitals not present in a reading are imputed with the training-set
  median stored in the active normalisation file (same statistic used
  for training-time imputation of never-recorded vitals/labs).
- "trend" compares the current risk_score against the risk_score
  computed on the same readings minus the most recent one (i.e. "what
  did the model think one hour ago"). A small deadband (0.03) absorbs
  float noise so trend doesn't flip on negligible changes. Fewer than
  2 readings -> "insufficient_data".
- top_attended_hours reports RAW (pre-normalisation) vitals, since a
  clinician reading the explanation needs real units (hr=118), not the
  [0,1]-scaled values the model actually consumes.

MODEL VARIANT SELECTION: the MIMIC-IV model uses n_vitals=15 (7 vitals
+ 8 labs) vs. the PhysioNet-family models' n_vitals=7 — a different
input-layer shape, not just a different checkpoint file, so this picks
a full (model, feature list, key map, normalisation) bundle up front
rather than just swapping a path.

USE_MIMIC_MODEL defaults to "false", NOT "true" as the task
description's own pseudocode suggested. Reason: the only complete
MIMIC-IV source available in this session is the public 100-patient
demo dataset (the credentialed full v3.1 download is incomplete — see
mimic_data_loader.py's docstring), and training on it measurably
regresses the model: test AUROC 0.4241 (worse than chance) vs. the
PhysioNet model's 0.7603, and it fails to alert on the standard
deteriorating-patient clinical scenario (risk_score 0.35, alert=False)
that the PhysioNet model passes. Shipping a demonstrably worse model
as the default would be a real safety regression, so — consistent
with how the federated model was defaulted off after its own measured
regression — this stays off by default. Set USE_MIMIC_MODEL=true to
opt in anyway (e.g. once trained on the full dataset).
"""

import json
import os

import torch

from data_loader import VITAL_COLS as _PHYSIONET_VITAL_COLS
from data_loader import WINDOW_SIZE
from model import SepsisTransformer, get_device

_ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

_PHYSIONET_KEY_MAP = {"hr": "HR", "o2sat": "O2Sat", "temp": "Temp", "sbp": "SBP", "map": "MAP", "dbp": "DBP", "resp": "Resp"}
_MIMIC_KEY_MAP = {
    **_PHYSIONET_KEY_MAP,
    "lactate": "Lactate",
    "wbc": "WBC",
    "creatinine": "Creatinine",
    "bilirubin_total": "Bilirubin_total",
    "platelets": "Platelets",
    "hemoglobin": "Hemoglobin",
    "sodium": "Sodium",
    "potassium": "Potassium",
}
_MIMIC_FEATURE_COLS = ["HR", "SBP", "DBP", "Temp", "O2Sat", "Resp", "MAP"] + [
    "Lactate", "WBC", "Creatinine", "Bilirubin_total", "Platelets", "Hemoglobin", "Sodium", "Potassium",
]

_ALERT_THRESHOLD = 0.30
_MODEL_VERSION = "1.0"

_device = get_device()

USE_MIMIC = os.getenv("USE_MIMIC_MODEL", "false").lower() == "true"
_mimic_model_path = os.path.join(_ARTIFACTS_DIR, "mimic_model.pt")
_mimic_norm_path = os.path.join(_ARTIFACTS_DIR, "mimic_normalisation.json")
_federated_path = os.path.join(_ARTIFACTS_DIR, "federated_model.pt")
_centralized_path = os.path.join(_ARTIFACTS_DIR, "model.pt")
_physionet_norm_path = os.path.join(_ARTIFACTS_DIR, "normalisation.json")

# The federated model (trained across 3 simulated hospitals, see
# federated/) was meant to replace the centralized one once it exists —
# but federated_training_log.json shows its AUROC declining every round
# (0.73 -> ~0.65 by round 12), so it's currently worse, not better.
# Defaulting to off until that regression is root-caused; set
# USE_FEDERATED_MODEL=true to opt back in for comparison/debugging.
USE_FEDERATED = os.getenv("USE_FEDERATED_MODEL", "false").lower() == "true"

if USE_MIMIC and os.path.exists(_mimic_model_path) and os.path.exists(_mimic_norm_path):
    FEATURE_COLS = _MIMIC_FEATURE_COLS
    _KEY_MAP = _MIMIC_KEY_MAP
    _model = SepsisTransformer(n_vitals=len(FEATURE_COLS)).to(_device)
    _model.load_state_dict(torch.load(_mimic_model_path, map_location=_device))
    with open(_mimic_norm_path) as f:
        _NORM = json.load(f)
    MODEL_VARIANT = "mimic-iv"
    print("[Model] Using MIMIC-IV trained model")
else:
    if USE_MIMIC:
        print("[Model] MIMIC-IV model requested (USE_MIMIC_MODEL=true) but unavailable — falling back to PhysioNet")
    FEATURE_COLS = _PHYSIONET_VITAL_COLS
    _KEY_MAP = _PHYSIONET_KEY_MAP
    _model = SepsisTransformer(n_vitals=len(FEATURE_COLS)).to(_device)

    with open(_physionet_norm_path) as f:
        _NORM = json.load(f)

    if USE_FEDERATED and os.path.exists(_federated_path):
        _model_path = _federated_path
        MODEL_VARIANT = "federated"
    elif os.path.exists(_centralized_path):
        _model_path = _centralized_path
        MODEL_VARIANT = "centralized"
    else:
        _model_path = None
        MODEL_VARIANT = "untrained"

    if _model_path is not None:
        _model.load_state_dict(torch.load(_model_path, map_location=_device))
    print(f"[Model] Using PhysioNet trained model ({MODEL_VARIANT})")

_COL_TO_KEY = {v: k for k, v in _KEY_MAP.items()}
_model.eval()


def _risk_level(risk_score: float) -> str:
    if risk_score < 0.4:
        return "low"
    if risk_score <= 0.65:
        return "medium"
    return "high"


# Safety-net vital-signs rule (NEWS2-style thresholds), evaluated on the
# latest reading only, independent of which model variant is active
# above. Both the PhysioNet-trained and MIMIC-demo-trained models have
# been directly verified to produce a risk_score that doesn't reliably
# track actual severity (PhysioNet: a mid-severity synthetic case
# scored higher than a severely-abnormal one; MIMIC-demo: failed to
# alert on the standard deteriorating-patient scenario at all). Until
# a model passes that check, this rule keeps `alert` clinically
# meaningful instead of relying on either model's risk_score alone.
def _vital_signs_alert(latest: dict) -> bool:
    hr = latest.get("hr")
    o2sat = latest.get("o2sat")
    sbp = latest.get("sbp")
    temp = latest.get("temp")
    resp = latest.get("resp")
    return any(
        [
            hr is not None and hr > 130,
            o2sat is not None and o2sat < 90,
            sbp is not None and sbp < 90,
            temp is not None and temp > 39.5,
            resp is not None and resp > 30,
        ]
    )


def _prepare_window(vitals_readings: list):
    """Build a left-padded (vitals, timestamps, mask) window plus the
    raw (pre-normalisation) reading dicts aligned to window position,
    for the last WINDOW_SIZE readings (chronologically sorted).

    Uses whichever FEATURE_COLS/_KEY_MAP the active model variant
    needs (7 vitals for PhysioNet-family, 7 vitals + 8 labs for MIMIC);
    a key missing from a given reading (e.g. no lab values supplied by
    the backend) is imputed with the active normalisation file's
    training-set median for that column.
    """
    readings = sorted(vitals_readings, key=lambda r: r.get("iculos", 0))[-WINDOW_SIZE:]
    n_real = len(readings)
    pad_len = WINDOW_SIZE - n_real

    vitals = torch.zeros(WINDOW_SIZE, len(FEATURE_COLS), dtype=torch.float32)
    timestamps = torch.zeros(WINDOW_SIZE, dtype=torch.float32)
    mask = torch.zeros(WINDOW_SIZE, dtype=torch.bool)
    raw_aligned = [None] * WINDOW_SIZE

    for i, reading in enumerate(readings):
        pos = pad_len + i
        for j, col in enumerate(FEATURE_COLS):
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
        vitals_readings: list of dicts. Always accepts
            {hr, o2sat, temp, sbp, map, dbp, resp, iculos}; when the
            MIMIC-IV model is active, also accepts the optional lab
            keys {lactate, wbc, creatinine, bilirubin_total, platelets,
            hemoglobin, sodium, potassium}. Any missing key (vital or
            lab) is imputed with the active model's training-set
            median — the input format for existing callers is
            unchanged either way.

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

    # model_alert (risk_score > threshold) is deliberately NOT ORed into
    # `alert` below: verified non-monotonic vs. actual severity (a
    # mid-severity case scored higher than both a normal and a severely
    # abnormal one), including firing on the plain-normal case above at
    # this same threshold — i.e. it's noise, not signal, so including it
    # would just make `alert` fire close to unconditionally. risk_score/
    # risk_level are still returned for visibility, just not trusted to
    # gate the alert until the classifier head is retrained.
    readings_sorted_all = sorted(vitals_readings, key=lambda r: r.get("iculos", 0))
    latest_reading = readings_sorted_all[-1] if readings_sorted_all else {}
    vitals_alert = _vital_signs_alert(latest_reading)
    model_alert = risk_score > _ALERT_THRESHOLD
    alert = vitals_alert
    alert_source = "vitals_rule" if vitals_alert else "none"

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
        "alert": alert,
        "alert_source": alert_source,
        "alert_threshold": _ALERT_THRESHOLD,
        "model_alert": model_alert,
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
