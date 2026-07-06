"""Generate synthetic triage training data.

Pipeline:
  1. Load PhysioNet 2019 Sepsis Challenge CSVs to derive vital-sign distributions.
  2. Sample N synthetic patients from those distributions.
  3. Apply NEWS2 scoring to each sample.
  4. Map NEWS2 score → MTS triage category label.
  5. Save dataset/triage_train.csv for train.py.

Dataset path: ~/Downloads/22687585/
"""
from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Optional

PHYSIONET_DIR = Path(os.path.expanduser("~/Downloads/22687585"))
OUT_DIR = Path(__file__).parent / "dataset"


# ---------------------------------------------------------------------------
# NEWS2 scoring
# ---------------------------------------------------------------------------

def news2_score(
    resp_rate: float,
    spo2: float,
    supplemental_o2: bool,
    temp: float,
    systolic_bp: float,
    heart_rate: float,
    avpu: int = 0,
) -> int:
    """Calculate NEWS2 early-warning score (0–20+).

    avpu: 0=Alert, 3=Voice/Pain/Unresponsive (any non-Alert AVPU = 3 points).
    """
    score = 0

    # Respiratory rate
    if resp_rate <= 8:
        score += 3
    elif resp_rate <= 11:
        score += 1
    elif resp_rate <= 20:
        score += 0
    elif resp_rate <= 24:
        score += 2
    else:
        score += 3

    # SpO2
    if spo2 <= 91:
        score += 3
    elif spo2 <= 93:
        score += 2
    elif spo2 <= 95:
        score += 1

    # Supplemental O2
    if supplemental_o2:
        score += 2

    # Temperature
    if temp <= 35.0:
        score += 3
    elif temp <= 36.0:
        score += 1
    elif temp <= 38.0:
        score += 0
    elif temp <= 39.0:
        score += 1
    else:
        score += 2

    # Systolic BP
    if systolic_bp <= 90:
        score += 3
    elif systolic_bp <= 100:
        score += 2
    elif systolic_bp <= 110:
        score += 1
    elif systolic_bp <= 219:
        score += 0
    else:
        score += 3

    # Heart rate
    if heart_rate <= 40:
        score += 3
    elif heart_rate <= 50:
        score += 1
    elif heart_rate <= 90:
        score += 0
    elif heart_rate <= 110:
        score += 1
    elif heart_rate <= 130:
        score += 2
    else:
        score += 3

    # Consciousness
    score += avpu

    return score


def news2_to_triage(score: int) -> str:
    """Map NEWS2 score to MTS triage category."""
    if score >= 7:
        return "CRITICAL"
    if score >= 5:
        return "URGENT"
    if score >= 1:
        return "SEMI_URGENT"
    return "NON_URGENT"


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------

# Approximate PhysioNet vital-sign distributions (mean, std) — updated during
# Phase 2 when we fit the actual distributions from the raw CSVs.
_VITAL_DISTRIBUTIONS = {
    "resp_rate":    (18.0, 5.0),
    "spo2":         (97.0, 3.0),
    "temp":         (37.1, 0.8),
    "systolic_bp":  (120.0, 20.0),
    "heart_rate":   (80.0, 18.0),
}


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _sample_vitals(rng: random.Random) -> dict:
    def gauss(mu: float, sigma: float) -> float:
        return rng.gauss(mu, sigma)

    return {
        "resp_rate":    _clamp(gauss(*_VITAL_DISTRIBUTIONS["resp_rate"]), 4, 60),
        "spo2":         _clamp(gauss(*_VITAL_DISTRIBUTIONS["spo2"]), 70, 100),
        "supplemental_o2": rng.random() < 0.15,
        "temp":         _clamp(gauss(*_VITAL_DISTRIBUTIONS["temp"]), 33.0, 42.0),
        "systolic_bp":  _clamp(gauss(*_VITAL_DISTRIBUTIONS["systolic_bp"]), 60, 250),
        "heart_rate":   _clamp(gauss(*_VITAL_DISTRIBUTIONS["heart_rate"]), 20, 200),
        "avpu":         rng.choices([0, 3], weights=[0.9, 0.1])[0],
    }


def generate(n_samples: int = 10_000, seed: int = 42) -> list[dict]:
    """Return a list of labelled vital-sign records."""
    rng = random.Random(seed)
    records = []
    for _ in range(n_samples):
        vitals = _sample_vitals(rng)
        score = news2_score(**vitals)
        records.append(
            {
                **vitals,
                "news2_score": score,
                "triage_category": news2_to_triage(score),
            }
        )
    return records


def save_csv(records: list[dict], path: Optional[Path] = None) -> Path:
    """Save generated records to CSV. Requires pandas."""
    import pandas as pd  # noqa: PLC0415

    out = path or OUT_DIR / "triage_train.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(out, index=False)
    print(f"Saved {len(records)} rows → {out}")
    return out


if __name__ == "__main__":
    print(f"PhysioNet dir: {PHYSIONET_DIR} (exists={PHYSIONET_DIR.exists()})")
    records = generate(n_samples=20_000)
    save_csv(records)
