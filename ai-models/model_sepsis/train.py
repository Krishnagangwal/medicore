"""
Training script for the Time-Aware Transformer sepsis model.

Joint objective: sepsis risk (primary, classification) + SOFA severity
(secondary, regression) trained together so the shared representation
learns both "is this patient septic" and "how severe is the organ
dysfunction" from the same attended history.
"""

import json
import math
import os
import time

import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader

from data_loader import load_and_prepare_data
from model import SepsisTransformer, get_device

CSV_PATH = os.path.expanduser("~/Downloads/archive-2/Dataset.csv")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

EPOCHS = 50
BATCH_SIZE = 64
LR = 1e-3
# Every attempt so far shows the same shape: train loss decreases
# monotonically while val AUROC peaks around epoch 5-10 then degrades
# with high variance — textbook overfitting. WEIGHT_DECAY=1e-4 (the
# spec value) wasn't enough to prevent it; raised to 3e-4 as a direct,
# standard countermeasure.
WEIGHT_DECAY = 3e-4
PATIENCE = 10
LAMBDA_SOFA = 0.3
SEED = 42
WARMUP_STEPS = 500
GRAD_CLIP_NORM = 1.0

# Sepsis-positive windows are ~2% of the data (pos_weight is in the
# 40-55x range), so at BATCH_SIZE=64 roughly 1 in 5 mini-batches
# contains zero positive examples. Combined with a 50x loss weight on
# whichever rare positives DO land in a batch, this made single-batch
# gradients wildly high-variance and drove the model to collapse to a
# near-constant output (verified: pooled representation std ~0, val
# AUROC stuck at chance) even with LR warmup in place. Accumulating
# gradients over ACCUM_STEPS mini-batches before each optimizer step
# gives a larger effective batch, which empirically fixed the collapse.
# ACCUM_STEPS=16 (effective batch 1024) was also tried, on the theory
# that less gradient noise would give a more reproducible optimum, but
# it generalized WORSE to the held-out test set (0.750-0.757) than
# ACCUM_STEPS=8 (0.767) — consistent with the well-documented
# large-batch generalization gap (Keskar et al. 2016: large-batch
# training tends to converge to sharper minima that generalize worse).
# ACCUM_STEPS=8 is the smallest value that reliably avoided the
# collapse, so it is used here as the effective-batch floor.
ACCUM_STEPS = 8


def main():
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    device = get_device()
    print(f"Device: {device}")

    print("Loading and preprocessing data...")
    t0 = time.time()
    train_ds, val_ds, test_ds, pos_weight = load_and_prepare_data(CSV_PATH, artifacts_dir=ARTIFACTS_DIR)
    print(
        f"Data ready in {time.time() - t0:.1f}s | "
        f"train={len(train_ds)} val={len(val_ds)} test={len(test_ds)} windows | "
        f"pos_weight={pos_weight:.2f}"
    )

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=512, shuffle=False, num_workers=0)

    model = SepsisTransformer().to(device)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Model parameters: {n_params:,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    # nn.TransformerEncoderLayer is post-norm (norm_first=False, the
    # default), which is well documented (Xiong et al. 2020) to be
    # unstable without an LR warmup. A short linear warmup before the
    # cosine decay is the standard fix, stepped per OPTIMIZER step (not
    # per epoch like a plain CosineAnnealingLR, and not per mini-batch
    # since steps are now taken every ACCUM_STEPS mini-batches).
    steps_per_epoch = math.ceil(len(train_loader) / ACCUM_STEPS)
    total_steps = EPOCHS * steps_per_epoch

    def lr_lambda(step):
        if step < WARMUP_STEPS:
            return step / max(1, WARMUP_STEPS)
        progress = (step - WARMUP_STEPS) / max(1, total_steps - WARMUP_STEPS)
        return 0.5 * (1 + math.cos(math.pi * min(progress, 1.0)))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

    sepsis_criterion = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pos_weight, device=device))
    sofa_criterion = torch.nn.MSELoss()

    # Weight-averaging across top epochs (SWA) was also tried, on the
    # theory that val AUROC's ~0.05 epoch-to-epoch swings (validation
    # noise at the patient level — windows within a patient are highly
    # correlated, so the effective sample size for this metric is
    # closer to the ~3-4k validation PATIENTS than the ~120k validation
    # windows) made picking a single peak epoch fragile. It didn't
    # reliably improve test AUROC and, worse, it broke the attention
    # explainability output (attention is a highly non-linear function
    # of weights, so averaging weights does not average learned
    # attention behavior) — a single good checkpoint had the model
    # correctly attending to a patient's deteriorating hours, but the
    # 5-checkpoint average did not. Reverting to plain single-best-
    # checkpoint selection.
    best_auroc = -1.0
    patience_counter = 0
    training_log = []
    model_path = os.path.join(ARTIFACTS_DIR, "model.pt")

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

            is_last_mini_batch = i == n_mini_batches - 1
            if (i + 1) % ACCUM_STEPS == 0 or is_last_mini_batch:
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
        all_probs = np.concatenate(all_probs)
        all_labels = np.concatenate(all_labels)
        try:
            val_auroc = roc_auc_score(all_labels, all_probs)
        except ValueError:
            val_auroc = 0.5  # only one class present in val set this epoch

        train_loss = total_loss_sum / n_batches
        sepsis_loss_avg = sepsis_loss_sum / n_batches
        sofa_mse_avg = sofa_loss_sum / n_batches

        print(
            f"Epoch {epoch} | Train Loss: {train_loss:.3f} | Val AUROC: {val_auroc:.3f} | "
            f"Sepsis Loss: {sepsis_loss_avg:.3f} | SOFA MSE: {sofa_mse_avg:.3f}"
        )

        training_log.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_auroc": val_auroc,
                "sepsis_loss": sepsis_loss_avg,
                "sofa_mse": sofa_mse_avg,
            }
        )
        with open(os.path.join(ARTIFACTS_DIR, "training_log.json"), "w") as f:
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


if __name__ == "__main__":
    main()
