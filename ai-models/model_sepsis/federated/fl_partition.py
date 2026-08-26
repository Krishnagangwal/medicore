"""
Splits PhysioNet patients into non-overlapping hospital partitions.

Real hospitals never share raw patient records with each other
(HIPAA / India's DPDP Act). Federated learning's premise depends on
this being a hard partition — no patient's data may appear at more
than one simulated "hospital" — so the disjointness assertions here
are the crux of the whole simulation being an honest one.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from data_loader import ID_COL


def create_hospital_partitions(csv_path: str, n_hospitals: int = 3, seed: int = 42) -> dict:
    """Partition unique patient IDs into `n_hospitals` non-overlapping groups.

    For the standard 3-hospital case, sizes are deliberately uneven
    (40/35/25%) to simulate a large academic center, a mid-size
    hospital, and a small community hospital — real hospital networks
    are never equally sized, and FedAvg's weighting by each client's
    dataset size is only meaningful to test if the partitions actually
    differ in size.

    Returns: {hospital_id: [patient_id, ...]}
    """
    df = pd.read_csv(csv_path, usecols=[ID_COL])
    patient_ids = df[ID_COL].unique()

    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(patient_ids)
    n = len(shuffled)

    if n_hospitals == 3:
        fractions = [0.40, 0.35, 0.25]
    else:
        fractions = [1.0 / n_hospitals] * n_hospitals

    partitions = {}
    start = 0
    for i, frac in enumerate(fractions):
        end = n if i == len(fractions) - 1 else start + int(round(n * frac))
        partitions[i] = shuffled[start:end].tolist()
        start = end

    all_ids = set()
    for ids in partitions.values():
        assert all_ids.isdisjoint(ids), "patient ID assigned to more than one hospital partition"
        all_ids.update(ids)
    assert all_ids == set(shuffled.tolist()), "partition union does not cover all patients"

    for hospital_id, ids in partitions.items():
        print(f"Hospital {hospital_id}: {len(ids)} patients ({100 * len(ids) / n:.1f}%)")

    return partitions


if __name__ == "__main__":
    CSV_PATH = os.path.expanduser("~/Downloads/archive-2/Dataset.csv")
    ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts")
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    partitions = create_hospital_partitions(CSV_PATH)
    with open(os.path.join(ARTIFACTS_DIR, "hospital_partitions.json"), "w") as f:
        json.dump({str(k): v for k, v in partitions.items()}, f)
    print(f"Saved partitions to {os.path.join(ARTIFACTS_DIR, 'hospital_partitions.json')}")
