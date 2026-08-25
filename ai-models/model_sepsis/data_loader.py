"""
Data pipeline for the Time-Aware Transformer sepsis model.

Converts the PhysioNet 2019 challenge CSV (one row per patient-hour,
irregular sampling) into fixed-length 24-hour windows suitable for
Transformer input, with patient-level train/val/test splits to avoid
leakage.

ASSUMPTIONS (stated explicitly since the source dataset and the
CLAUDE.md contract leave a few points underspecified):

1. Model input vitals are exactly the 7 fields the AI Gateway contract
   sends per reading: HR, O2Sat, Temp, SBP, MAP, DBP, Resp. Lab values
   (Lactate, Creatinine, WBC, ...) are present in the raw CSV but are
   NOT part of the gateway's `vitals_readings` payload, so they are
   dropped here to keep training input identical to what inference.py
   receives in production.
2. "Normalise each vital to [0,1]" is taken literally as min-max
   scaling (not z-score). normalisation.json therefore stores
   per-vital {min, max}, not mean/std.
3. Normalisation and imputation statistics (median, min, max) are
   computed from the 80% training-patient pool only, never from the
   held-out 20% test patients, to avoid statistical leakage.
4. SOFA is computed from raw (post-impute, pre-normalisation) vitals
   using fixed clinical thresholds, since those thresholds are defined
   in physiological units, not normalised ones.
5. Partial SOFA only: this dataset lacks GCS, bilirubin, creatinine,
   and platelets, so only the respiratory (SpO2-based) and
   cardiovascular (SBP/MAP-based) components are computed. Range is
   therefore 0-7, not the full 0-24 SOFA range.
6. Windows are built with STEP_SIZE=1 by sliding a 24-hour lookback
   over every real hour a patient has: for a patient with N real
   hours, this produces exactly N windows (one ending at each hour),
   left-padded with zeros when fewer than 24 hours of history exist
   yet. This matches how the model will be called in production
   (predict using up to 24h of history ending "now").
"""

import json
import os

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

WINDOW_SIZE = 24
RANDOM_SEED = 42

VITAL_COLS = ["HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp"]
ID_COL = "Patient_ID"
TIME_COL = "ICULOS"
LABEL_COL = "SepsisLabel"


def compute_sofa(o2sat: np.ndarray, sbp: np.ndarray, map_: np.ndarray) -> np.ndarray:
    """Compute partial SOFA (respiratory + cardiovascular only).

    Full SOFA also needs GCS, bilirubin, creatinine, and platelets,
    none of which are reliably available in this dataset. Respiratory
    and cardiovascular are used because they are directly observable
    from vitals and are the two components most tied to sepsis-driven
    hemodynamic and respiratory collapse.

    Cardiovascular thresholds in the source spec overlap (e.g. SBP<65
    also satisfies SBP<90 and often MAP<70). Rather than pick an
    arbitrary priority order, each criterion's score is computed
    independently and the maximum (i.e. most clinically severe) is
    taken — standard SOFA convention is "worst applicable value wins".
    """
    o2sat = np.asarray(o2sat, dtype=np.float32)
    sbp = np.asarray(sbp, dtype=np.float32)
    map_ = np.asarray(map_, dtype=np.float32)

    sofa_resp = np.select(
        [o2sat < 80, o2sat < 85, o2sat < 90, o2sat < 95],
        [4, 3, 2, 1],
        default=0,
    ).astype(np.float32)

    sbp_component = np.select([sbp < 65, sbp < 90], [4, 3], default=0).astype(np.float32)
    map_component = np.where(map_ < 70, 2, 0).astype(np.float32)
    sofa_cardio = np.maximum(sbp_component, map_component)

    return sofa_resp + sofa_cardio


def _build_patient_windows(vitals: np.ndarray, timestamps: np.ndarray, labels: np.ndarray, sofa: np.ndarray):
    """Vectorised sliding-window construction for a single patient.

    vitals: (n_hours, n_vitals) already imputed + normalised
    timestamps: (n_hours,) raw ICULOS values
    labels: (n_hours,) SepsisLabel per hour
    sofa: (n_hours,) SOFA per hour

    Returns n_hours windows, each covering the 24 hours ending at that
    hour (left-padded with zeros / mask=0 if fewer than 24 hours of
    history exist yet). Label/SOFA targets are the values AT the last
    (real) hour of each window, i.e. simply the per-hour arrays
    unchanged — no windowing needed for scalars.
    """
    n_hours, n_vitals = vitals.shape
    pad_len = WINDOW_SIZE - 1

    padded_vitals = np.vstack([np.zeros((pad_len, n_vitals), dtype=np.float32), vitals])
    windows = np.lib.stride_tricks.sliding_window_view(padded_vitals, WINDOW_SIZE, axis=0)
    windows = windows.transpose(0, 2, 1)  # (n_hours, WINDOW_SIZE, n_vitals)

    padded_ts = np.concatenate([np.zeros(pad_len, dtype=np.float32), timestamps.astype(np.float32)])
    ts_windows = np.lib.stride_tricks.sliding_window_view(padded_ts, WINDOW_SIZE)  # (n_hours, WINDOW_SIZE)

    real_flags = np.concatenate([np.zeros(pad_len, dtype=bool), np.ones(n_hours, dtype=bool)])
    mask_windows = np.lib.stride_tricks.sliding_window_view(real_flags, WINDOW_SIZE)  # (n_hours, WINDOW_SIZE)

    return windows.astype(np.float32), ts_windows.astype(np.float32), mask_windows.astype(bool), labels.astype(np.float32), sofa.astype(np.float32)


class SepsisDataset(Dataset):
    """Fixed-length windowed view over preprocessed patient-hour data.

    Wraps already-windowed numpy arrays (built once, up front, by
    `load_and_prepare_data`) so `__getitem__` is a cheap index lookup
    rather than re-running pandas groupby logic per sample.
    """

    def __init__(self, vitals: np.ndarray, timestamps: np.ndarray, mask: np.ndarray, labels: np.ndarray, sofa: np.ndarray):
        self.vitals = vitals
        self.timestamps = timestamps
        self.mask = mask
        self.labels = labels
        self.sofa = sofa

    def __len__(self) -> int:
        return self.vitals.shape[0]

    def __getitem__(self, idx: int):
        return (
            torch.from_numpy(self.vitals[idx]).float(),
            torch.from_numpy(self.timestamps[idx]).float(),
            torch.from_numpy(self.mask[idx]).bool(),
            torch.tensor(self.labels[idx], dtype=torch.float32),
            torch.tensor(self.sofa[idx], dtype=torch.float32),
        )


def load_and_prepare_data(
    csv_path: str,
    artifacts_dir: str = "artifacts",
    test_fraction: float = 0.2,
    val_fraction: float = 0.1,
    seed: int = RANDOM_SEED,
):
    """Load the raw CSV and produce train/val/test SepsisDataset objects.

    Also writes artifacts/normalisation.json and
    artifacts/class_weights.json, which inference.py depends on at
    serve time.

    Returns:
        train_dataset, val_dataset, test_dataset, pos_weight (float)
    """
    os.makedirs(artifacts_dir, exist_ok=True)

    usecols = [ID_COL, TIME_COL, LABEL_COL] + VITAL_COLS
    df = pd.read_csv(csv_path, usecols=usecols)
    df = df.sort_values([ID_COL, TIME_COL])

    # Clinical standard: forward-fill within each patient only (never
    # borrow from another patient, never look into the future).
    df[VITAL_COLS] = df.groupby(ID_COL)[VITAL_COLS].ffill()

    patient_ids = df[ID_COL].unique()
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(patient_ids)
    n_test = int(len(shuffled) * test_fraction)
    test_ids = shuffled[:n_test]
    train_pool_ids = shuffled[n_test:]

    n_val = int(len(train_pool_ids) * val_fraction)
    val_ids = train_pool_ids[:n_val]
    fit_ids = train_pool_ids[n_val:]

    assert set(fit_ids).isdisjoint(set(test_ids))
    assert set(val_ids).isdisjoint(set(test_ids))

    train_pool_mask = df[ID_COL].isin(train_pool_ids)

    # Global median imputation for remaining NaNs (leading hours before
    # any real reading, or vitals never recorded for a patient).
    # Computed on the training pool only to avoid leakage into test.
    medians = df.loc[train_pool_mask, VITAL_COLS].median()
    df[VITAL_COLS] = df[VITAL_COLS].fillna(medians)

    # SOFA is computed on raw (post-impute) physiological units, before
    # min-max normalisation, since its thresholds are clinical values.
    df["sofa"] = compute_sofa(df["O2Sat"].values, df["SBP"].values, df["MAP"].values)

    # Min-max normalisation to [0, 1] using training-pool statistics.
    # Median is also stored here (rather than only min/max) because
    # inference.py needs it to impute vitals missing from a live
    # request, using the same training-pool statistic as training-time
    # imputation.
    mins = df.loc[train_pool_mask, VITAL_COLS].min()
    maxs = df.loc[train_pool_mask, VITAL_COLS].max()
    normalisation = {
        col: {"min": float(mins[col]), "max": float(maxs[col]), "median": float(medians[col])}
        for col in VITAL_COLS
    }
    with open(os.path.join(artifacts_dir, "normalisation.json"), "w") as f:
        json.dump(normalisation, f, indent=2)

    for col in VITAL_COLS:
        lo, hi = normalisation[col]["min"], normalisation[col]["max"]
        span = hi - lo if hi > lo else 1.0
        df[col] = ((df[col] - lo) / span).clip(0.0, 1.0)

    def build_split(ids):
        vitals_list, ts_list, mask_list, label_list, sofa_list = [], [], [], [], []
        for pid, group in df[df[ID_COL].isin(ids)].groupby(ID_COL, sort=False):
            v = group[VITAL_COLS].to_numpy(dtype=np.float32)
            t = group[TIME_COL].to_numpy(dtype=np.float32)
            y = group[LABEL_COL].to_numpy(dtype=np.float32)
            s = group["sofa"].to_numpy(dtype=np.float32)
            vw, tw, mw, yw, sw = _build_patient_windows(v, t, y, s)
            vitals_list.append(vw)
            ts_list.append(tw)
            mask_list.append(mw)
            label_list.append(yw)
            sofa_list.append(sw)
        return (
            np.concatenate(vitals_list, axis=0),
            np.concatenate(ts_list, axis=0),
            np.concatenate(mask_list, axis=0),
            np.concatenate(label_list, axis=0),
            np.concatenate(sofa_list, axis=0),
        )

    fit_arrays = build_split(fit_ids)
    val_arrays = build_split(val_ids)
    test_arrays = build_split(test_ids)

    n_pos = float(fit_arrays[3].sum())
    n_neg = float(len(fit_arrays[3]) - n_pos)
    pos_weight = n_neg / max(n_pos, 1.0)
    with open(os.path.join(artifacts_dir, "class_weights.json"), "w") as f:
        json.dump({"pos_weight": pos_weight, "n_pos": n_pos, "n_neg": n_neg}, f, indent=2)

    train_dataset = SepsisDataset(*fit_arrays)
    val_dataset = SepsisDataset(*val_arrays)
    test_dataset = SepsisDataset(*test_arrays)

    # Patient-level split verification (train.py's acceptance criteria
    # also re-checks this at test time; verified again here at source).
    assert set(fit_ids).isdisjoint(set(test_ids)), "fit/test patient overlap detected"
    assert set(val_ids).isdisjoint(set(test_ids)), "val/test patient overlap detected"

    return train_dataset, val_dataset, test_dataset, pos_weight
