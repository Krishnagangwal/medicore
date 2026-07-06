"""Load and clean the PhysioNet 2019 Sepsis Challenge dataset.

Dataset: ~/Downloads/archive-2/Dataset.csv
  - 1.55M rows, 40,336 unique patients
  - One row per patient per ICU hour
  - SepsisLabel = 1 at the hour sepsis was diagnosed
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

DATASET_PATH = Path(os.getenv(
    "PHYSIONET_CSV",
    str(Path.home() / "Downloads" / "archive-2" / "Dataset.csv"),
))

# Columns used downstream — load only what we need for speed
LOAD_COLS = [
    "Patient_ID", "ICULOS", "SepsisLabel",
    "HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp",
    "Lactate", "WBC", "Creatinine",
    "Age", "Gender", "HospAdmTime",
]

VITAL_COLS = ["HR", "O2Sat", "Temp", "SBP", "MAP", "DBP", "Resp",
              "Lactate", "WBC", "Creatinine"]


def load(path: Path = DATASET_PATH) -> pd.DataFrame:
    """Load dataset, forward-fill within patient, then median-impute.

    Returns a clean DataFrame sorted by Patient_ID, ICULOS.
    """
    print(f"Loading {path} …")
    df = pd.read_csv(path, usecols=LOAD_COLS, low_memory=False)
    df = df.sort_values(["Patient_ID", "ICULOS"]).reset_index(drop=True)

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    numeric_cols = [c for c in numeric_cols if c not in ("Patient_ID", "SepsisLabel")]

    # Forward-fill within patient (propagates last known vital sign)
    print("Forward-filling missing values within patients …")
    df[numeric_cols] = df.groupby("Patient_ID")[numeric_cols].transform("ffill")

    # Global median imputation for remaining NaNs (first readings with no prior data)
    medians = df[numeric_cols].median()
    df[numeric_cols] = df[numeric_cols].fillna(medians)

    print(f"Loaded: {len(df):,} rows, {df['Patient_ID'].nunique():,} patients")
    print(f"Sepsis patients: {df.groupby('Patient_ID')['SepsisLabel'].max().sum():,}")
    return df
