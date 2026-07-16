"""Train Model 4 — Drug-Drug Interaction severity classifier.

Run:
    python train.py

Dataset reality (found via exploration, see CLAUDE.md session notes):
ddis.csv has columns d1, d2, type, "Neg samples" — not drug_a/drug_b/
severity. `type` (0-962) is a per-pair side-effect-type index, not a
severity grade, and no severity or drug-name field exists anywhere in
the raw data. All 4,576,287 rows are restricted to the same 645 drugs
in drug_smiles.csv.

Since there is no ground-truth severity, this trains against a proxy
label: for each of the 63,472 known positive pairs, the number of
distinct `type` values recorded is quartile-binned into
Minor/Moderate/Major/Contraindicated (1-4); "clean" negative pairs
(drawn from the "Neg samples" column, filtered to exclude any pair that
is secretly a positive elsewhere) are labeled 0 (No interaction). This
heuristic is documented, not a clinical claim — see
feature_extraction.build_feature_matrix().

Inputs:
    ~/Downloads/ddis.csv          — interaction pairs (full file loaded;
                                     category dtypes keep it to ~40MB)
    ~/Downloads/drug_smiles.csv   — SMILES strings for feature extraction

Outputs:
    artifacts/model.cbm           — CatBoost multiclass model
    artifacts/metadata.json       — label map, feature names, drug index
    artifacts/graph_edges.json    — compact known-interaction edge list,
                                     used by graph.py and inference.py at
                                     runtime instead of re-scanning the
                                     195MB source CSV on every startup
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from feature_extraction import (
    FEATURE_NAMES,
    build_feature_matrix,
    display_name,
)

DDIS_PATH = Path.home() / "Downloads" / "ddis.csv"
SMILES_PATH = Path.home() / "Downloads" / "drug_smiles.csv"
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"

LABEL_MAP = {0: "none", 1: "minor", 2: "moderate", 3: "major", 4: "contraindicated"}
TARGET_NAMES = [LABEL_MAP[i] for i in range(5)]


def train() -> None:
    print("Loading ddis.csv (category dtypes for memory efficiency)...")
    ddis_df = pd.read_csv(
        DDIS_PATH,
        dtype={"d1": "category", "d2": "category", "type": "int16", "Neg samples": "category"},
    )
    print(f"  {ddis_df.shape[0]:,} rows loaded")

    smiles_df = pd.read_csv(SMILES_PATH)
    print(f"Loaded {smiles_df.shape[0]} drugs with SMILES")

    print("Building feature matrix (Morgan fingerprints + graph features)...")
    X, y, drug_pairs = build_feature_matrix(ddis_df, smiles_df)
    print(f"  X: {X.shape}, y: {y.shape}")
    print(f"  Class distribution: {dict(zip(*np.unique(y, return_counts=True)))}")

    X_train, X_test, y_train, y_test, pairs_train, pairs_test = train_test_split(
        X, y, drug_pairs, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train: {X_train.shape[0]:,} rows, Test: {X_test.shape[0]:,} rows")

    model = CatBoostClassifier(
        loss_function="MultiClass",
        iterations=400,
        depth=6,
        learning_rate=0.1,
        auto_class_weights="Balanced",
        random_seed=42,
        eval_metric="TotalF1",
        verbose=50,
    )
    model.fit(X_train, y_train, eval_set=(X_test, y_test))

    y_pred = model.predict(X_test).reshape(-1).astype(int)
    print("\n=== Classification report (test set) ===")
    report = classification_report(y_test, y_pred, target_names=TARGET_NAMES, digits=3, zero_division=0)
    print(report)

    print("=== Confusion matrix (rows=true, cols=pred) ===")
    cm = confusion_matrix(y_test, y_pred, labels=list(range(5)))
    print("classes:", TARGET_NAMES)
    print(cm)

    accuracy = float((y_pred == y_test).mean())
    print(f"\nOverall accuracy: {accuracy:.4f}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(ARTIFACTS_DIR / "model.cbm"))
    print(f"Saved model -> {ARTIFACTS_DIR / 'model.cbm'}")

    all_cids = sorted(set(smiles_df["drug_id"]))
    metadata = {
        "model_version": "4.0.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "label_map": LABEL_MAP,
        "feature_names": FEATURE_NAMES,
        "n_features": len(FEATURE_NAMES),
        "drug_index": all_cids,
        "n_drugs": len(all_cids),
        "n_positive_pairs": int((y != 0).sum()),
        "n_train": int(X_train.shape[0]),
        "n_test": int(X_test.shape[0]),
        "test_accuracy": accuracy,
    }
    with open(ARTIFACTS_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata -> {ARTIFACTS_DIR / 'metadata.json'}")

    # Compact known-interaction edge list for fast runtime loading (graph.py,
    # inference.py) instead of re-reading the 195MB ddis.csv on every start.
    edges = []
    for (a, b), label in zip(drug_pairs, y):
        if label == 0:
            continue
        edges.append(
            {
                "d1": a,
                "d2": b,
                "d1_name": display_name(a),
                "d2_name": display_name(b),
                "severity_code": int(label),
                "severity": LABEL_MAP[int(label)],
            }
        )
    with open(ARTIFACTS_DIR / "graph_edges.json", "w") as f:
        json.dump(edges, f, indent=2)
    print(f"Saved graph edges ({len(edges):,}) -> {ARTIFACTS_DIR / 'graph_edges.json'}")


if __name__ == "__main__":
    train()
