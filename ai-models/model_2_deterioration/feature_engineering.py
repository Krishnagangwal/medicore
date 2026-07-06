"""Feature engineering for Model 2 — Patient Deterioration.

Features computed per time step:
  - Vitals at current hour:    HR, O2Sat, Temp, SBP, MAP, Resp
  - Rate of change (1h delta): delta_HR, delta_SBP, delta_Resp
  - 3-hour rolling mean:       roll_HR, roll_SBP, roll_O2Sat
  - Derived:                   shock_index, news2_score
  - Context:                   ICULOS, Age

Label leakage prevention: once SepsisLabel flips to 1 for a patient, all
subsequent rows are dropped — we keep only rows up to (and including) the
onset hour.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_COLS: list[str] = [
    "HR", "O2Sat", "Temp", "SBP", "MAP", "Resp",
    "delta_HR", "delta_SBP", "delta_Resp",
    "roll_HR", "roll_SBP", "roll_O2Sat",
    "shock_index", "news2_score",
    "ICULOS", "Age",
]

TARGET_COL = "SepsisLabel"


# ---------------------------------------------------------------------------
# Modified NEWS2 (vectorised, no avpu / supplemental O2)
# ---------------------------------------------------------------------------

def _news2_vectorised(resp: pd.Series, spo2: pd.Series, temp: pd.Series,
                      sbp: pd.Series, hr: pd.Series) -> pd.Series:
    score = pd.Series(0, index=resp.index, dtype=int)

    # Respiratory rate
    score += np.select(
        [resp <= 8, resp <= 11, resp <= 20, resp <= 24],
        [3,          1,          0,          2],
        default=3,
    )
    # SpO2
    score += np.select(
        [spo2 <= 91, spo2 <= 93, spo2 <= 95],
        [3,           2,           1],
        default=0,
    )
    # Temperature
    score += np.select(
        [temp <= 35.0, temp <= 36.0, temp <= 38.0, temp <= 39.0],
        [3,             1,             0,             1],
        default=2,
    )
    # Systolic BP
    score += np.select(
        [sbp <= 90,  sbp <= 100, sbp <= 110, sbp <= 219],
        [3,           2,           1,           0],
        default=3,
    )
    # Heart rate
    score += np.select(
        [hr <= 40,  hr <= 50,  hr <= 90,  hr <= 110, hr <= 130],
        [3,          1,          0,          1,          2],
        default=3,
    )
    return score


# ---------------------------------------------------------------------------
# Main feature builder
# ---------------------------------------------------------------------------

def build(df: pd.DataFrame) -> pd.DataFrame:
    """Return feature-engineered DataFrame with no post-onset rows.

    Modifies a copy of df — does not mutate the input.
    """
    df = df.sort_values(["Patient_ID", "ICULOS"]).reset_index(drop=True)

    # ── Label leakage prevention ──────────────────────────────────────────
    # For each sepsis patient: keep rows up to and including the first onset.
    onset = (
        df[df["SepsisLabel"] == 1]
        .groupby("Patient_ID")["ICULOS"]
        .min()
        .rename("onset_ICULOS")
    )
    df = df.merge(onset, on="Patient_ID", how="left")
    df = df[df["ICULOS"] <= df["onset_ICULOS"].fillna(float("inf"))].copy()
    df = df.drop(columns=["onset_ICULOS"]).reset_index(drop=True)

    print(f"After leakage prevention: {len(df):,} rows")
    print(f"Positive (sepsis) rows: {df['SepsisLabel'].sum():,} "
          f"({df['SepsisLabel'].mean():.2%})")

    # ── Delta features (rate of change within patient) ─────────────────────
    grp = df.groupby("Patient_ID", sort=False)
    df["delta_HR"]   = grp["HR"].diff().fillna(0)
    df["delta_SBP"]  = grp["SBP"].diff().fillna(0)
    df["delta_Resp"] = grp["Resp"].diff().fillna(0)

    # ── 3-hour rolling mean ────────────────────────────────────────────────
    for col, out in [("HR", "roll_HR"), ("SBP", "roll_SBP"), ("O2Sat", "roll_O2Sat")]:
        df[out] = grp[col].transform(lambda x: x.rolling(3, min_periods=1).mean())

    # ── Derived features ───────────────────────────────────────────────────
    df["shock_index"] = df["HR"] / df["SBP"].clip(lower=1.0)
    df["news2_score"] = _news2_vectorised(
        df["Resp"], df["O2Sat"], df["Temp"], df["SBP"], df["HR"]
    )

    return df


def get_feature_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Return (X, y) ready for training."""
    X = df[FEATURE_COLS].astype(float)
    y = df[TARGET_COL].astype(int)
    return X, y
