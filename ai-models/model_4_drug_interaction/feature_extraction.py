"""SMILES-based molecular feature extraction for drug pairs.

Requires: rdkit (install via `pip install rdkit`)
Dataset: ~/Downloads/drug_smiles.csv
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

DRUG_SMILES_PATH = Path.home() / "Downloads" / "drug_smiles.csv"


def load_smiles_dict(csv_path: Path = DRUG_SMILES_PATH) -> dict[str, str]:
    """Return {drug_name_lower: smiles_string} from the SMILES CSV."""
    import pandas as pd  # noqa: PLC0415

    df = pd.read_csv(csv_path)
    # Expect columns: drug_name, smiles
    return {row["drug_name"].lower(): row["smiles"] for _, row in df.iterrows()}


def morgan_fingerprint(smiles: str, radius: int = 2, n_bits: int = 1024) -> np.ndarray:
    """Generate a Morgan (ECFP) fingerprint for a SMILES string."""
    from rdkit import Chem  # noqa: PLC0415
    from rdkit.Chem import AllChem  # noqa: PLC0415

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return np.zeros(n_bits, dtype=np.float32)
    fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
    return np.array(fp, dtype=np.float32)


def pair_features(smiles_a: str, smiles_b: str) -> np.ndarray:
    """Concatenate fingerprints of two drugs to form a pair feature vector."""
    fp_a = morgan_fingerprint(smiles_a)
    fp_b = morgan_fingerprint(smiles_b)
    return np.concatenate([fp_a, fp_b])  # shape: (2048,)
