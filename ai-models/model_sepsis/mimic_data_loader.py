"""
MIMIC-IV data pipeline for the Time-Aware Transformer sepsis model.

Replaces data_loader.py for TRAINING only — data_loader.py stays and
is still used for inference (patient vitals arrive from the backend
at serve time, not from MIMIC).

ASSUMPTIONS (stated explicitly, since MIMIC's structure differs from
PhysioNet's in ways the task's own simplification doesn't fully spell
out):

1. Root directory auto-detection: searches common locations and picks
   whichever candidate has the most of the 8 required files present,
   tie-broken by total file size (see find_mimic_root()). The
   credentialed full MIMIC-IV v3.1 download at
   ~/medicore/physionet.org/files/mimiciv/3.1 finished after an
   earlier session found it incomplete; it now has all required files
   (364,627 patients, 94,458 ICU stays) and is what gets used — the
   size tiebreaker exists specifically because the full dataset and
   the public 100-patient "clinical-database-demo-2.2" in ~/Downloads
   both satisfy the file-presence check once both are complete, and a
   presence-only check can't tell a 5.5MB demo chartevents.csv.gz
   apart from a 3.5GB full one.
2. Sepsis label is per ADMISSION (hadm_id), from ICD-9/10 diagnosis
   codes, per the task's own simplified Sepsis-3 approximation. MIMIC's
   diagnoses_icd table carries no onset timestamp, so — unlike
   PhysioNet's hour-level SepsisLabel — there is no way to tell which
   hour within a positive stay sepsis was actually recognized. Every
   24-hour window from a sepsis-positive stay is therefore labeled 1,
   and every window from a negative stay is labeled 0. This is coarser
   than PhysioNet's onset-level labeling; it is a direct, unavoidable
   consequence of the task's own chosen simplification, not an
   additional simplification introduced here.
3. Vitals are hour-binned from chartevents by flooring
   (charttime - stay_intime) to an integer hour and averaging multiple
   readings that land in the same hour (real ICU charting is often
   more frequent than hourly). Labs are attributed to whichever ICU
   stay's [intime, outtime] window contains the lab's charttime (via
   hadm_id -> candidate stays), then hour-binned the same way.
4. SOFA: resp/cardio use the exact same thresholds as data_loader.py's
   compute_sofa (kept identical for comparability); renal and liver
   are new, computed per the task's explicit creatinine/bilirubin
   thresholds. sofa_total sums whatever components are available for a
   given patient at a given hour (still partial SOFA — GCS and platelet
   count aren't used here either, consistent with the existing model's
   partial-SOFA precedent).
"""

import glob
import json
import os

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

WINDOW_SIZE = 24
RANDOM_SEED = 42

VITAL_COLS = ["HR", "SBP", "DBP", "Temp", "O2Sat", "Resp", "MAP"]
LAB_COLS = ["Lactate", "WBC", "Creatinine", "Bilirubin_total", "Platelets", "Hemoglobin", "Sodium", "Potassium"]
FEATURE_COLS = VITAL_COLS + LAB_COLS  # 15 features total

VITAL_ITEMIDS = {
    "HR": 220045,
    "SBP": 220179,
    "DBP": 220180,
    "Temp": 223762,
    "O2Sat": 220277,
    "Resp": 220210,
    "MAP": 220052,
}
LAB_ITEMIDS = {
    "Lactate": 50813,
    "WBC": 51301,
    "Creatinine": 50912,
    "Bilirubin_total": 50885,
    "Platelets": 51265,
    "Hemoglobin": 51222,
    "Sodium": 50983,
    "Potassium": 50971,
}

REQUIRED_FILES = [
    "hosp/patients.csv.gz",
    "hosp/admissions.csv.gz",
    "hosp/labevents.csv.gz",
    "hosp/diagnoses_icd.csv.gz",
    "hosp/d_icd_diagnoses.csv.gz",
    "icu/icustays.csv.gz",
    "icu/chartevents.csv.gz",
    "icu/d_items.csv.gz",
]


def find_mimic_root() -> str:
    """Search common locations for a usable MIMIC-IV directory,
    preferring whichever candidate has the most required files present
    (i.e. prefers a complete full dataset over the demo, but falls
    back to the demo — or any other partially-complete source — since
    that's what's actually usable today).

    Once the full dataset finished downloading it tied the demo
    dataset on file-presence count (8/8 each) — both are "complete" by
    that check alone, but wildly different in scale (demo chartevents
    is 5.5MB; full is 3.5GB). A plain file-count comparison can't tell
    them apart, and ties broke on Python's unordered set iteration,
    which silently picked the demo in practice. Total byte size of the
    required files is used as a tiebreaker for exactly this reason —
    it's a cheap, robust proxy for "how much real data is here" that a
    presence-only check can't provide.
    """
    search_patterns = [
        os.path.expanduser("~/medicore/physionet.org/files/mimiciv/*"),
        os.path.expanduser("~/medicore/physionet/**/mimiciv*"),
        os.path.expanduser("~/Downloads/mimic-iv*"),
        os.path.expanduser("~/Downloads/**/mimic-iv*"),
    ]
    candidates = set()
    for pattern in search_patterns:
        for path in glob.glob(pattern, recursive=True):
            if os.path.isdir(path):
                candidates.add(os.path.abspath(path))

    def completeness(root: str) -> tuple:
        present = [rel for rel in REQUIRED_FILES if os.path.exists(os.path.join(root, rel))]
        total_bytes = sum(os.path.getsize(os.path.join(root, rel)) for rel in present)
        return len(present), total_bytes

    scored = [(completeness(c), c) for c in candidates]
    scored = [(score, c) for score, c in scored if score[0] > 0]
    if not scored:
        raise FileNotFoundError(
            "No usable MIMIC-IV directory found under ~/medicore/physionet.org or "
            "~/Downloads (need a hosp/ + icu/ layout with at least one of: "
            f"{REQUIRED_FILES})."
        )
    scored.sort(key=lambda x: x[0], reverse=True)
    (best_n_files, best_bytes), best_root = scored[0]
    print(
        f"[mimic_data_loader] Using MIMIC-IV root: {best_root} "
        f"({best_n_files}/{len(REQUIRED_FILES)} required files present, {best_bytes / 1e9:.2f} GB)"
    )
    if len(scored) > 1:
        for (n_files, n_bytes), root in scored[1:]:
            print(f"[mimic_data_loader]   (not chosen: {root} — {n_files}/{len(REQUIRED_FILES)} files, {n_bytes / 1e9:.2f} GB)")
    if best_n_files < len(REQUIRED_FILES):
        missing = [rel for rel in REQUIRED_FILES if not os.path.exists(os.path.join(best_root, rel))]
        print(f"[mimic_data_loader] WARNING: missing files at this root: {missing}")
    return best_root


CHUNKSIZE_THRESHOLD_BYTES = 500_000_000  # 500MB compressed
CHUNKSIZE_ROWS = 1_000_000


def _read_gz(root: str, rel_path: str, **kwargs) -> pd.DataFrame:
    return pd.read_csv(os.path.join(root, rel_path), compression="gzip", **kwargs)


def _read_gz_filtered_by_itemid(root: str, rel_path: str, itemids: set, usecols: list) -> pd.DataFrame:
    """Read a (possibly huge) MIMIC events file, keeping only rows whose
    itemid is in `itemids`. Chunked when the compressed file exceeds
    CHUNKSIZE_THRESHOLD_BYTES — chartevents.csv.gz and labevents.csv.gz
    are 3.5GB / 2.6GB on the full dataset, and only ~15 of the many
    hundreds of possible itemids are ever needed here, so filtering
    chunk-by-chunk keeps memory bounded to one chunk instead of loading
    the entire file (which is what made the ~140-row demo dataset take
    the same code path safely, but would not scale to the full one)."""
    path = os.path.join(root, rel_path)
    size = os.path.getsize(path)
    if size < CHUNKSIZE_THRESHOLD_BYTES:
        df = pd.read_csv(path, compression="gzip", usecols=usecols)
        return df[df["itemid"].isin(itemids)]

    print(f"[mimic_data_loader] {rel_path} is {size / 1e9:.2f} GB — reading in {CHUNKSIZE_ROWS:,}-row chunks")
    kept_chunks = []
    rows_seen = 0
    for chunk in pd.read_csv(path, compression="gzip", usecols=usecols, chunksize=CHUNKSIZE_ROWS):
        rows_seen += len(chunk)
        filtered = chunk[chunk["itemid"].isin(itemids)]
        if len(filtered):
            kept_chunks.append(filtered)
        if rows_seen % (CHUNKSIZE_ROWS * 10) == 0:
            kept_so_far = sum(len(c) for c in kept_chunks)
            print(f"[mimic_data_loader]   ...{rows_seen:,} rows scanned, {kept_so_far:,} kept")
    kept_total = sum(len(c) for c in kept_chunks)
    print(f"[mimic_data_loader] {rel_path}: {rows_seen:,} rows scanned, {kept_total:,} matched target itemids")
    if not kept_chunks:
        return pd.DataFrame(columns=usecols)
    return pd.concat(kept_chunks, ignore_index=True)


def compute_sofa_mimic(o2sat: np.ndarray, sbp: np.ndarray, map_: np.ndarray, creatinine: np.ndarray, bilirubin: np.ndarray) -> np.ndarray:
    """Partial SOFA: respiratory + cardiovascular (identical formula to
    data_loader.compute_sofa, kept consistent for comparability) plus
    renal (creatinine) and liver (bilirubin), newly available from
    MIMIC's lab data. Still partial — no GCS, no platelet component."""
    o2sat = np.asarray(o2sat, dtype=np.float32)
    sbp = np.asarray(sbp, dtype=np.float32)
    map_ = np.asarray(map_, dtype=np.float32)
    creatinine = np.asarray(creatinine, dtype=np.float32)
    bilirubin = np.asarray(bilirubin, dtype=np.float32)

    sofa_resp = np.select([o2sat < 80, o2sat < 85, o2sat < 90, o2sat < 95], [4, 3, 2, 1], default=0).astype(np.float32)

    sbp_component = np.select([sbp < 65, sbp < 90], [4, 3], default=0).astype(np.float32)
    map_component = np.where(map_ < 70, 2, 0).astype(np.float32)
    sofa_cardio = np.maximum(sbp_component, map_component)

    sofa_renal = np.select(
        [creatinine >= 5.0, creatinine >= 3.5, creatinine >= 2.0, creatinine >= 1.2],
        [4, 3, 2, 1],
        default=0,
    ).astype(np.float32)

    sofa_liver = np.select(
        [bilirubin >= 12.0, bilirubin >= 6.0, bilirubin >= 2.0, bilirubin >= 1.2],
        [4, 3, 2, 1],
        default=0,
    ).astype(np.float32)

    return sofa_resp + sofa_cardio + sofa_renal + sofa_liver


def _build_sepsis_positive_hadm_ids(root: str) -> set:
    diagnoses = _read_gz(root, "hosp/diagnoses_icd.csv.gz", dtype={"icd_code": "string"})
    d_diag = _read_gz(root, "hosp/d_icd_diagnoses.csv.gz", dtype={"icd_code": "string"})
    merged = diagnoses.merge(d_diag, on=["icd_code", "icd_version"], how="left")

    code = merged["icd_code"].astype(str)
    desc = merged["long_title"].fillna("")
    is_sepsis = (
        code.str.match(r"^A41")
        | code.str.match(r"^A40")
        | code.isin(["R6520", "R6521"])
        | desc.str.contains("sepsis", case=False, na=False)
    )
    return set(merged.loc[is_sepsis, "hadm_id"].unique().tolist())


def _hour_bin(charttime: pd.Series, intime: pd.Series) -> np.ndarray:
    delta_hours = (pd.to_datetime(charttime) - pd.to_datetime(intime)).dt.total_seconds() / 3600.0
    return np.floor(delta_hours).astype(np.int64)


def _load_vitals_wide(root: str, icustays: pd.DataFrame) -> pd.DataFrame:
    """Hour-binned vitals, one row per (stay_id, hour), columns = VITAL_COLS."""
    itemid_to_col = {v: k for k, v in VITAL_ITEMIDS.items()}
    usecols = ["stay_id", "charttime", "itemid", "valuenum"]
    chartevents = _read_gz_filtered_by_itemid(root, "icu/chartevents.csv.gz", set(itemid_to_col.keys()), usecols)
    chartevents = chartevents.dropna(subset=["valuenum"])
    chartevents["vital"] = chartevents["itemid"].map(itemid_to_col)

    chartevents = chartevents.merge(icustays[["stay_id", "intime"]], on="stay_id", how="inner")
    chartevents["hour"] = _hour_bin(chartevents["charttime"], chartevents["intime"])
    chartevents = chartevents[chartevents["hour"] >= 0]

    grouped = chartevents.groupby(["stay_id", "hour", "vital"])["valuenum"].mean().reset_index()
    wide = grouped.pivot_table(index=["stay_id", "hour"], columns="vital", values="valuenum").reset_index()
    for col in VITAL_COLS:
        if col not in wide.columns:
            wide[col] = np.nan
    return wide[["stay_id", "hour"] + VITAL_COLS]


def _load_labs_wide(root: str, icustays: pd.DataFrame) -> pd.DataFrame:
    """Hour-binned labs, one row per (stay_id, hour), columns = LAB_COLS.

    labevents has no stay_id; a lab is attributed to whichever of that
    admission's ICU stays has [intime, outtime] containing the lab's
    charttime (an admission can have multiple ICU stays).
    """
    itemid_to_col = {v: k for k, v in LAB_ITEMIDS.items()}
    usecols = ["hadm_id", "charttime", "itemid", "valuenum"]
    labevents = _read_gz_filtered_by_itemid(root, "hosp/labevents.csv.gz", set(itemid_to_col.keys()), usecols)
    labevents = labevents.dropna(subset=["valuenum", "hadm_id"])
    labevents["lab"] = labevents["itemid"].map(itemid_to_col)
    labevents["hadm_id"] = labevents["hadm_id"].astype(icustays["hadm_id"].dtype)

    merged = labevents.merge(icustays[["stay_id", "hadm_id", "intime", "outtime"]], on="hadm_id", how="inner")
    ct = pd.to_datetime(merged["charttime"])
    in_stay = (ct >= pd.to_datetime(merged["intime"])) & (ct <= pd.to_datetime(merged["outtime"]))
    merged = merged[in_stay]

    merged["hour"] = _hour_bin(merged["charttime"], merged["intime"])
    merged = merged[merged["hour"] >= 0]

    grouped = merged.groupby(["stay_id", "hour", "lab"])["valuenum"].mean().reset_index()
    wide = grouped.pivot_table(index=["stay_id", "hour"], columns="lab", values="valuenum").reset_index()
    for col in LAB_COLS:
        if col not in wide.columns:
            wide[col] = np.nan
    return wide[["stay_id", "hour"] + LAB_COLS]


def _build_patient_windows(vitals: np.ndarray, timestamps: np.ndarray, label: int, sofa: np.ndarray):
    """Same vectorised sliding-window construction as data_loader.py's
    _build_patient_windows, adapted for a single per-stay label (MIMIC
    has no hour-level SepsisLabel — see module docstring) applied to
    every window from that stay."""
    n_hours, n_features = vitals.shape
    pad_len = WINDOW_SIZE - 1

    padded_vitals = np.vstack([np.zeros((pad_len, n_features), dtype=np.float32), vitals])
    windows = np.lib.stride_tricks.sliding_window_view(padded_vitals, WINDOW_SIZE, axis=0)
    windows = windows.transpose(0, 2, 1)

    padded_ts = np.concatenate([np.zeros(pad_len, dtype=np.float32), timestamps.astype(np.float32)])
    ts_windows = np.lib.stride_tricks.sliding_window_view(padded_ts, WINDOW_SIZE)

    real_flags = np.concatenate([np.zeros(pad_len, dtype=bool), np.ones(n_hours, dtype=bool)])
    mask_windows = np.lib.stride_tricks.sliding_window_view(real_flags, WINDOW_SIZE)

    labels = np.full(n_hours, float(label), dtype=np.float32)

    return windows.astype(np.float32), ts_windows.astype(np.float32), mask_windows.astype(bool), labels, sofa.astype(np.float32)


class MimicSepsisDataset(Dataset):
    """Same shape contract as data_loader.SepsisDataset, generalised to
    n_features=15 (7 vitals + 8 labs) instead of 7."""

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


def load_and_prepare_mimic_data(
    artifacts_dir: str = "artifacts",
    test_fraction: float = 0.2,
    val_fraction: float = 0.1,
    seed: int = RANDOM_SEED,
    mimic_root: str = None,
):
    """Load MIMIC-IV, build patient-level splits and 24-hour windows.

    Returns: train_dataset, val_dataset, test_dataset, pos_weight (float)
    Also writes artifacts/mimic_normalisation.json.
    """
    os.makedirs(artifacts_dir, exist_ok=True)
    root = mimic_root or find_mimic_root()

    patients = _read_gz(root, "hosp/patients.csv.gz")
    icustays = _read_gz(root, "icu/icustays.csv.gz")

    adults = patients.loc[patients["anchor_age"] >= 18, "subject_id"]
    icustays = icustays[icustays["subject_id"].isin(adults)].reset_index(drop=True)
    print(f"Adult ICU stays: {len(icustays)}")

    positive_hadm_ids = _build_sepsis_positive_hadm_ids(root)
    icustays["sepsis_label"] = icustays["hadm_id"].isin(positive_hadm_ids).astype(int)
    n_pos_stays = int(icustays["sepsis_label"].sum())
    print(f"Sepsis-positive stays: {n_pos_stays} ({100 * n_pos_stays / len(icustays):.1f}%)")

    print("Loading and hour-binning vitals from chartevents...")
    vitals_wide = _load_vitals_wide(root, icustays)
    print("Loading and hour-binning labs from labevents...")
    labs_wide = _load_labs_wide(root, icustays)

    merged = pd.merge(vitals_wide, labs_wide, on=["stay_id", "hour"], how="outer")
    merged = merged.merge(icustays[["stay_id", "subject_id", "sepsis_label"]], on="stay_id", how="inner")
    merged = merged.sort_values(["stay_id", "hour"])

    # Patient-level split (by subject_id, not stay_id, so no patient's
    # data crosses the train/test boundary even if they had >1 stay).
    patient_ids = merged["subject_id"].unique()
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(patient_ids)
    n_test = max(1, int(len(shuffled) * test_fraction))
    test_ids = set(shuffled[:n_test].tolist())
    train_pool_ids = shuffled[n_test:]
    n_val = max(1, int(len(train_pool_ids) * val_fraction))
    val_ids = set(train_pool_ids[:n_val].tolist())
    fit_ids = set(train_pool_ids[n_val:].tolist())

    assert fit_ids.isdisjoint(test_ids), "fit/test patient overlap detected"
    assert val_ids.isdisjoint(test_ids), "val/test patient overlap detected"
    assert fit_ids.isdisjoint(val_ids), "fit/val patient overlap detected"

    train_pool_mask = merged["subject_id"].isin(set(train_pool_ids.tolist()))

    # Forward-fill within each stay (clinical standard), then
    # training-pool-only median imputation for anything still missing.
    merged[FEATURE_COLS] = merged.groupby("stay_id")[FEATURE_COLS].ffill()
    medians = merged.loc[train_pool_mask, FEATURE_COLS].median()
    merged[FEATURE_COLS] = merged[FEATURE_COLS].fillna(medians)

    merged["sofa"] = compute_sofa_mimic(
        merged["O2Sat"].values, merged["SBP"].values, merged["MAP"].values,
        merged["Creatinine"].values, merged["Bilirubin_total"].values,
    )

    mins = merged.loc[train_pool_mask, FEATURE_COLS].min()
    maxs = merged.loc[train_pool_mask, FEATURE_COLS].max()
    normalisation = {
        col: {"min": float(mins[col]), "max": float(maxs[col]), "median": float(medians[col])}
        for col in FEATURE_COLS
    }
    with open(os.path.join(artifacts_dir, "mimic_normalisation.json"), "w") as f:
        json.dump(normalisation, f, indent=2)

    for col in FEATURE_COLS:
        lo, hi = normalisation[col]["min"], normalisation[col]["max"]
        span = hi - lo if hi > lo else 1.0
        merged[col] = ((merged[col] - lo) / span).clip(0.0, 1.0)

    def build_split(subject_id_set):
        vitals_list, ts_list, mask_list, label_list, sofa_list = [], [], [], [], []
        subset = merged[merged["subject_id"].isin(subject_id_set)]
        for stay_id, group in subset.groupby("stay_id", sort=False):
            group = group.sort_values("hour")
            v = group[FEATURE_COLS].to_numpy(dtype=np.float32)
            t = group["hour"].to_numpy(dtype=np.float32)
            s = group["sofa"].to_numpy(dtype=np.float32)
            label = int(group["sepsis_label"].iloc[0])
            if len(group) == 0:
                continue
            vw, tw, mw, yw, sw = _build_patient_windows(v, t, label, s)
            vitals_list.append(vw)
            ts_list.append(tw)
            mask_list.append(mw)
            label_list.append(yw)
            sofa_list.append(sw)
        if not vitals_list:
            empty_v = np.zeros((0, WINDOW_SIZE, len(FEATURE_COLS)), dtype=np.float32)
            empty_t = np.zeros((0, WINDOW_SIZE), dtype=np.float32)
            empty_m = np.zeros((0, WINDOW_SIZE), dtype=bool)
            empty_y = np.zeros((0,), dtype=np.float32)
            empty_s = np.zeros((0,), dtype=np.float32)
            return empty_v, empty_t, empty_m, empty_y, empty_s
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

    print(f"Train patients: {len(fit_ids)}, Val patients: {len(val_ids)}, Test patients: {len(test_ids)}")
    print(f"Patient overlap (fit/test): {len(fit_ids & test_ids)}")
    print(f"Patient overlap (val/test): {len(val_ids & test_ids)}")
    print(f"Windows — train: {len(fit_arrays[3])}, val: {len(val_arrays[3])}, test: {len(test_arrays[3])}")
    print(f"pos_weight: {pos_weight:.2f}")

    return (
        MimicSepsisDataset(*fit_arrays),
        MimicSepsisDataset(*val_arrays),
        MimicSepsisDataset(*test_arrays),
        pos_weight,
    )
