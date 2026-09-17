"""
Training script for the Time-Aware Transformer sepsis model, on
MIMIC-IV instead of PhysioNet 2019.

Same model architecture as train.py (Time2Vec + causal Transformer +
dual heads), same core training loop fixes discovered during the
PhysioNet training session (LR warmup for this Post-LN Transformer,
gradient accumulation + clipping) — those aren't PhysioNet-specific,
they're architecture-specific, so they're kept here proactively rather
than rediscovered the hard way again. n_vitals=15 (7 vitals + 8 labs)
replaces PhysioNet's 7, everything else about the model is unchanged.

Saves to artifacts/mimic_model.pt (NOT artifacts/model.pt — the
PhysioNet-trained model stays as-is and untouched as a fallback).
"""

import json
import math
import os
import time

import numpy as np
import torch
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve
from torch.utils.data import DataLoader

from mimic_data_loader import FEATURE_COLS, WINDOW_SIZE, load_and_prepare_mimic_data
from model import SepsisTransformer, get_device

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

N_VITALS = len(FEATURE_COLS)  # 15: 7 vitals + 8 labs
EPOCHS = 50
BATCH_SIZE = 64
LR = 1e-3
WEIGHT_DECAY = 1e-4
PATIENCE = 10
LAMBDA_SOFA = 0.3
SEED = 42
GRAD_CLIP_NORM = 1.0

# MIMIC's ICD-based admission-level labeling gives a far milder
# positive rate (~15-20%) than PhysioNet's per-hour SepsisLabel
# (~2%), so the "batch has zero positives" gradient-variance failure
# mode that forced ACCUM_STEPS=8 on PhysioNet is not expected to be
# nearly as severe here. A small accumulation factor is kept anyway as
# a cheap safeguard, along with a short warmup — this is still the
# same Post-LN Transformer architecture that collapsed without one.
ACCUM_STEPS = 4
WARMUP_STEPS = 50


def main():
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    device = get_device()
    print(f"Device: {device}")

    print("Loading and preparing MIMIC-IV data...")
    t0 = time.time()
    train_ds, val_ds, test_ds, pos_weight = load_and_prepare_mimic_data(artifacts_dir=ARTIFACTS_DIR, seed=SEED)
    print(f"Data ready in {time.time() - t0:.1f}s")

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=512, shuffle=False, num_workers=0)

    model = SepsisTransformer(n_vitals=N_VITALS).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {n_params:,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    steps_per_epoch = max(1, math.ceil(len(train_loader) / ACCUM_STEPS))
    total_steps = EPOCHS * steps_per_epoch

    def lr_lambda(step):
        if step < WARMUP_STEPS:
            return step / max(1, WARMUP_STEPS)
        progress = (step - WARMUP_STEPS) / max(1, total_steps - WARMUP_STEPS)
        return 0.5 * (1 + math.cos(math.pi * min(progress, 1.0)))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    sepsis_criterion = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pos_weight, device=device))
    sofa_criterion = torch.nn.MSELoss()

    best_auroc = -1.0
    patience_counter = 0
    training_log = []
    model_path = os.path.join(ARTIFACTS_DIR, "mimic_model.pt")

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss_sum = 0.0
        sepsis_loss_sum = 0.0
        sofa_loss_sum = 0.0
        n_batches = 0

        optimizer.zero_grad()
        n_mini_batches = len(train_loader)
        for i, (vitals, timestamps, mask, label, sofa) in enumerate(train_loader):
            vitals = vitals.to(device)
            timestamps = timestamps.to(device)
            mask = mask.to(device)
            label = label.to(device)
            sofa = sofa.to(device)

            risk_logit, sofa_pred, _ = model(vitals, timestamps, mask, return_attention=False)

            sepsis_loss = sepsis_criterion(risk_logit, label)
            sofa_loss = sofa_criterion(sofa_pred, sofa)
            loss = sepsis_loss + LAMBDA_SOFA * sofa_loss

            (loss / ACCUM_STEPS).backward()

            is_last = i == n_mini_batches - 1
            if (i + 1) % ACCUM_STEPS == 0 or is_last:
                torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP_NORM)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

            total_loss_sum += loss.item()
            sepsis_loss_sum += sepsis_loss.item()
            sofa_loss_sum += sofa_loss.item()
            n_batches += 1

        model.eval()
        all_probs, all_labels = [], []
        with torch.no_grad():
            for vitals, timestamps, mask, label, sofa in val_loader:
                vitals = vitals.to(device)
                timestamps = timestamps.to(device)
                mask = mask.to(device)
                risk_logit, _, _ = model(vitals, timestamps, mask, return_attention=False)
                probs = torch.sigmoid(risk_logit).cpu().numpy()
                all_probs.append(probs)
                all_labels.append(label.numpy())
        all_probs = np.concatenate(all_probs) if all_probs else np.array([])
        all_labels = np.concatenate(all_labels) if all_labels else np.array([])
        try:
            val_auroc = roc_auc_score(all_labels, all_probs)
        except ValueError:
            val_auroc = 0.5

        train_loss = total_loss_sum / max(n_batches, 1)
        sepsis_loss_avg = sepsis_loss_sum / max(n_batches, 1)
        sofa_mse_avg = sofa_loss_sum / max(n_batches, 1)

        print(
            f"Epoch {epoch} | Train Loss: {train_loss:.3f} | Val AUROC: {val_auroc:.3f} | "
            f"Sepsis Loss: {sepsis_loss_avg:.3f} | SOFA MSE: {sofa_mse_avg:.3f}"
        )

        training_log.append(
            {"epoch": epoch, "train_loss": train_loss, "val_auroc": val_auroc, "sepsis_loss": sepsis_loss_avg, "sofa_mse": sofa_mse_avg}
        )
        with open(os.path.join(ARTIFACTS_DIR, "mimic_training_log.json"), "w") as f:
            json.dump(training_log, f, indent=2)

        if val_auroc > best_auroc:
            best_auroc = val_auroc
            patience_counter = 0
            torch.save(model.state_dict(), model_path)
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                print(f"Early stopping at epoch {epoch} (no improvement for {PATIENCE} epochs)")
                break

    print(f"Training complete. Best validation AUROC: {best_auroc:.4f}")
    print(f"Best model saved to {model_path}")

    # ---- Self-test (Step 5) ----
    print("\n" + "=" * 70)
    print("SELF TEST")
    print("=" * 70)

    print("\nDataset stats:")
    print(f"  Train windows: {len(train_ds)}, Val windows: {len(val_ds)}, Test windows: {len(test_ds)}")

    best_model = SepsisTransformer(n_vitals=N_VITALS).to(device)
    best_model.load_state_dict(torch.load(model_path, map_location=device))
    best_model.eval()

    test_loader = DataLoader(test_ds, batch_size=512, shuffle=False)
    all_probs, all_labels = [], []
    with torch.no_grad():
        for vitals, timestamps, mask, label, sofa in test_loader:
            vitals, timestamps, mask = vitals.to(device), timestamps.to(device), mask.to(device)
            risk_logit, _, _ = best_model(vitals, timestamps, mask, return_attention=False)
            all_probs.append(torch.sigmoid(risk_logit).cpu().numpy())
            all_labels.append(label.numpy())
    y_score = np.concatenate(all_probs) if all_probs else np.array([])
    y_true = np.concatenate(all_labels) if all_labels else np.array([])

    print("\nModel performance:")
    if len(np.unique(y_true)) < 2:
        print("  Test set has only one class present — AUROC/AUPRC undefined. Reporting honestly, not fabricating a number.")
        test_auroc = float("nan")
    else:
        test_auroc = roc_auc_score(y_true, y_score)
        test_auprc = average_precision_score(y_true, y_score)
        fpr, tpr, _ = roc_curve(y_true, y_score)
        specificity = 1 - fpr
        valid = np.where(specificity >= 0.8)[0]
        sens_at_80_spec = tpr[valid[-1]] if len(valid) > 0 else float("nan")
        print(f"  Test AUROC: {test_auroc:.4f} (target > 0.77, ideally > 0.83)")
        print(f"  Test AUPRC: {test_auprc:.4f}")
        print(f"  Sensitivity at 80% specificity: {sens_at_80_spec:.4f}")

    print("\nClinical scenario test (same deteriorating patient):")
    readings = []
    for h in range(1, 19):
        readings.append({"hr": 85, "o2sat": 97, "temp": 37.2, "sbp": 118, "map": 82, "dbp": 68, "resp": 16, "iculos": h})
    for h in range(19, 25):
        readings.append({"hr": 118, "o2sat": 91, "temp": 38.9, "sbp": 86, "map": 58, "dbp": 45, "resp": 26, "iculos": h})

    normalisation_path = os.path.join(ARTIFACTS_DIR, "mimic_normalisation.json")
    with open(normalisation_path) as f:
        norm = json.load(f)

    vitals_t = torch.zeros(WINDOW_SIZE, N_VITALS, dtype=torch.float32)
    timestamps_t = torch.zeros(WINDOW_SIZE, dtype=torch.float32)
    mask_t = torch.ones(WINDOW_SIZE, dtype=torch.bool)
    key_map = {"HR": "hr", "SBP": "sbp", "DBP": "dbp", "Temp": "temp", "O2Sat": "o2sat", "Resp": "resp", "MAP": "map"}
    for i, reading in enumerate(readings):
        for j, col in enumerate(FEATURE_COLS):
            key = key_map.get(col)
            value = reading.get(key) if key else None
            if value is None:
                value = norm[col]["median"]
            lo, hi = norm[col]["min"], norm[col]["max"]
            span = hi - lo if hi > lo else 1.0
            vitals_t[i, j] = max(0.0, min(1.0, (float(value) - lo) / span))
        timestamps_t[i] = float(reading["iculos"])

    with torch.no_grad():
        risk_logit, sofa_pred, importance = best_model(
            vitals_t.unsqueeze(0).to(device), timestamps_t.unsqueeze(0).to(device), mask_t.unsqueeze(0).to(device)
        )
    risk_score = torch.sigmoid(risk_logit).item()
    alert = risk_score > 0.65
    peak_hour = int(torch.argmax(importance.squeeze(0)).item())
    print(f"  risk_score: {risk_score:.4f}")
    print(f"  alert: {alert}")
    print(f"  attention_peak_hour: {peak_hour}")
    print(f"  sofa_score: {max(0.0, sofa_pred.item()):.4f}")


if __name__ == "__main__":
    main()
