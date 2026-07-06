"""Train Model 2 — Patient Deterioration (sepsis risk) classifier.

Run:
    python train.py

Outputs:
    artifacts/model.cbm
    artifacts/features.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.metrics import (
    classification_report,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

import data_loader
import feature_engineering as fe
from feature_engineering import FEATURE_COLS, TARGET_COL

ARTIFACTS_DIR = Path(__file__).parent / "artifacts"
ALERT_THRESHOLD = 0.65


def train() -> None:
    # ── Load & engineer features ──────────────────────────────────────────
    raw = data_loader.load()
    df  = fe.build(raw)

    # ── Patient-level train/test split ────────────────────────────────────
    all_patients = df["Patient_ID"].unique()
    train_pids, test_pids = train_test_split(
        all_patients, test_size=0.20, random_state=42
    )

    # Guard: confirm no patient appears in both sets
    overlap = set(train_pids) & set(test_pids)
    assert len(overlap) == 0, f"Patient leakage detected: {len(overlap)} shared patients"
    print(f"\nPatient-level split — train: {len(train_pids):,}, test: {len(test_pids):,}")
    print("Patient leakage check: PASSED ✓")

    train_mask = df["Patient_ID"].isin(train_pids)
    test_mask  = df["Patient_ID"].isin(test_pids)

    X_train, y_train = fe.get_feature_matrix(df[train_mask])
    X_test,  y_test  = fe.get_feature_matrix(df[test_mask])

    print(f"Train rows: {len(X_train):,}  |  Test rows: {len(X_test):,}")
    print(f"Train sepsis rate: {y_train.mean():.3%}")
    print(f"Test  sepsis rate: {y_test.mean():.3%}\n")

    # Class imbalance weight
    neg = (y_train == 0).sum()
    pos = (y_train == 1).sum()
    scale_pos_weight = float(neg / max(pos, 1))
    print(f"scale_pos_weight = {scale_pos_weight:.1f}")

    # ── Train CatBoost ────────────────────────────────────────────────────
    train_pool = Pool(X_train.values, y_train.values, feature_names=FEATURE_COLS)
    eval_pool  = Pool(X_test.values,  y_test.values,  feature_names=FEATURE_COLS)

    model = CatBoostClassifier(
        iterations=500,
        depth=8,
        learning_rate=0.08,
        loss_function="Logloss",
        scale_pos_weight=scale_pos_weight,
        eval_metric="AUC",
        od_type="Iter",
        od_wait=40,
        random_seed=42,
        verbose=50,
    )
    model.fit(train_pool, eval_set=eval_pool)

    # ── Evaluation ────────────────────────────────────────────────────────
    y_proba = model.predict_proba(X_test.values)[:, 1]
    auroc   = roc_auc_score(y_test, y_proba)
    y_pred  = (y_proba >= ALERT_THRESHOLD).astype(int)
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary", zero_division=0)

    print(f"\n{'='*50}")
    print(f"AUROC on test set:  {auroc:.4f}")
    print(f"Precision @ {ALERT_THRESHOLD}:   {prec:.4f}")
    print(f"Recall    @ {ALERT_THRESHOLD}:   {rec:.4f}")
    print(f"F1        @ {ALERT_THRESHOLD}:   {f1:.4f}")
    print(classification_report(y_test, y_pred, target_names=["no_sepsis", "sepsis"]))

    if auroc < 0.77:
        print(f"WARNING: AUROC {auroc:.4f} below target 0.77")
    else:
        print(f"PASS: AUROC {auroc:.4f} ≥ 0.77 ✓")

    # ── Save artifacts ────────────────────────────────────────────────────
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = ARTIFACTS_DIR / "model.cbm"
    model.save_model(str(model_path))
    print(f"Model saved → {model_path}")

    # Global medians from training data for inference imputation
    medians = {col: float(X_train[col].median()) for col in FEATURE_COLS}

    features_meta = {
        "feature_cols":     FEATURE_COLS,
        "medians":          medians,
        "alert_threshold":  ALERT_THRESHOLD,
        "auroc":            round(auroc, 4),
        "scale_pos_weight": round(scale_pos_weight, 2),
    }
    features_path = ARTIFACTS_DIR / "features.json"
    with open(features_path, "w") as f:
        json.dump(features_meta, f, indent=2)
    print(f"Features meta saved → {features_path}")


if __name__ == "__main__":
    train()
