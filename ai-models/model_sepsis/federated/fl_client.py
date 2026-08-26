"""
Flower NumPyClient — one instance simulates one hospital.

Each client only ever loads the patient_ids belonging to its own
partition and never sees another hospital's rows. What crosses the
"network" between client and server is exclusively model weights
(via get_parameters/set_parameters) and scalar metrics — never a
single raw vital-sign value. That boundary is the entire point of the
simulation: it is what would let hospitals collaborate on model
quality without a data-sharing agreement in the real deployment.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flwr as fl
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader

from data_loader import (
    ID_COL,
    LABEL_COL,
    TIME_COL,
    VITAL_COLS,
    SepsisDataset,
    _build_patient_windows,
    compute_sofa,
)
from model import SepsisTransformer

LOCAL_EPOCHS = 3
LOCAL_LR = 5e-4
LOCAL_WEIGHT_DECAY = 1e-4
ACCUM_STEPS = 8
BATCH_SIZE = 64
LAMBDA_SOFA = 0.3
# The centralized run showed this exact Post-LN Transformer collapses
# to a near-constant output within one epoch at a high LR without
# warmup. Round 1 starts every hospital from the same freshly
# initialised (random) global model, which is exactly the fragile
# regime that caused that collapse — so a short warmup is applied only
# in round 1. From round 2 onward, clients are fine-tuning already
# federated-averaged, already-trained weights, where warmup buys
# nothing and would just waste optimisation steps.
ROUND1_WARMUP_STEPS = 100


def split_hospital_patients(patient_ids: list, test_fraction: float = 0.2, val_fraction: float = 0.2, seed: int = 42):
    """Deterministically split one hospital's patients into
    train/val/test, given only the patient list + a fixed seed.

    fl_client.py calls this and only ever trains/validates on
    train_ids/val_ids. fl_test.py calls this SAME function (same
    patient list, same seed) to independently reproduce the identical
    test_ids without any extra state needing to be persisted — the
    test set is a partition federated training never sees, exactly
    like the centralized run's held-out test set.
    """
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(np.array(list(patient_ids)))
    n_test = int(len(shuffled) * test_fraction)
    test_ids = shuffled[:n_test]
    trainval_ids = shuffled[n_test:]
    n_val = int(len(trainval_ids) * val_fraction)
    val_ids = trainval_ids[:n_val]
    train_ids = trainval_ids[n_val:]
    return train_ids.tolist(), val_ids.tolist(), test_ids.tolist()


def build_windows_for_patients(csv_path: str, patient_ids: list, normalisation: dict) -> SepsisDataset:
    """Build a SepsisDataset covering exactly the given patients.

    Mirrors data_loader.load_and_prepare_data's preprocessing exactly
    (forward-fill, median impute, SOFA, min-max normalise, sliding
    windows) but scoped to a given patient subset and using the
    ALREADY-COMPUTED centralized normalisation/median stats rather
    than recomputing them locally. Hospitals sharing a normalisation
    contract (agreed measurement ranges) without sharing raw records
    is standard practice in federated clinical AI — it is a much
    smaller information leak than sharing data, and one every FL
    deployment in practice has to accept somewhere (units, coding
    conventions, etc. must be agreed centrally).
    """
    usecols = [ID_COL, TIME_COL, LABEL_COL] + VITAL_COLS
    df = pd.read_csv(csv_path, usecols=usecols)
    df = df[df[ID_COL].isin(patient_ids)].sort_values([ID_COL, TIME_COL])

    df[VITAL_COLS] = df.groupby(ID_COL)[VITAL_COLS].ffill()

    medians = {col: normalisation[col]["median"] for col in VITAL_COLS}
    df[VITAL_COLS] = df[VITAL_COLS].fillna(medians)

    df["sofa"] = compute_sofa(df["O2Sat"].values, df["SBP"].values, df["MAP"].values)

    for col in VITAL_COLS:
        lo, hi = normalisation[col]["min"], normalisation[col]["max"]
        span = hi - lo if hi > lo else 1.0
        df[col] = ((df[col] - lo) / span).clip(0.0, 1.0)

    vitals_list, ts_list, mask_list, label_list, sofa_list = [], [], [], [], []
    for pid, group in df.groupby(ID_COL, sort=False):
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

    return SepsisDataset(
        np.concatenate(vitals_list, axis=0),
        np.concatenate(ts_list, axis=0),
        np.concatenate(mask_list, axis=0),
        np.concatenate(label_list, axis=0),
        np.concatenate(sofa_list, axis=0),
    )


def build_hospital_dataset(csv_path: str, patient_ids: list, normalisation: dict, seed: int = 42):
    """Build local train/val SepsisDataset objects for one hospital's
    TRAIN/VAL patients only — the 20% test slice from
    split_hospital_patients is deliberately excluded here so it stays
    unseen by federated training, for fl_test.py to evaluate later."""
    train_ids, val_ids, _test_ids = split_hospital_patients(patient_ids, seed=seed)
    return (
        build_windows_for_patients(csv_path, train_ids, normalisation),
        build_windows_for_patients(csv_path, val_ids, normalisation),
    )


class SepsisClient(fl.client.NumPyClient):
    """One simulated hospital's local training/evaluation."""

    def __init__(self, hospital_id: int, patient_ids: list, csv_path: str, normalisation_path: str, class_weight_path: str, device: torch.device):
        self.hospital_id = hospital_id
        self.device = device

        with open(normalisation_path) as f:
            normalisation = json.load(f)
        with open(class_weight_path) as f:
            class_weights = json.load(f)
        self.pos_weight = class_weights["pos_weight"]

        self.train_dataset, self.val_dataset = build_hospital_dataset(csv_path, patient_ids, normalisation)
        self.model = SepsisTransformer().to(device)

    def get_parameters(self, config):
        """Only floating-point tensors are transmitted. causal_mask is
        a bool buffer derived purely from window_size (an architecture
        constant, not a learned value) — identical on every hospital
        by construction, so there is nothing to federate about it."""
        return [val.cpu().numpy() for val in self.model.state_dict().values() if val.dtype != torch.bool]

    def set_parameters(self, parameters):
        state_dict = self.model.state_dict()
        float_keys = [k for k, v in state_dict.items() if v.dtype != torch.bool]
        for key, array in zip(float_keys, parameters):
            state_dict[key] = torch.tensor(array, dtype=state_dict[key].dtype, device=self.device)
        self.model.load_state_dict(state_dict)

    def fit(self, parameters, config):
        self.set_parameters(parameters)
        self.model.train()

        round_num = config.get("round", 1)
        warmup_steps = ROUND1_WARMUP_STEPS if round_num == 1 else 0

        optimizer = torch.optim.AdamW(self.model.parameters(), lr=LOCAL_LR, weight_decay=LOCAL_WEIGHT_DECAY)
        loader = DataLoader(self.train_dataset, batch_size=BATCH_SIZE, shuffle=True)

        sepsis_criterion = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(self.pos_weight, device=self.device))
        sofa_criterion = torch.nn.MSELoss()

        total_loss_sum = 0.0
        n_batches = 0
        step = 0
        optimizer.zero_grad()

        for _ in range(LOCAL_EPOCHS):
            n_mini_batches = len(loader)
            for i, (vitals, timestamps, mask, label, sofa) in enumerate(loader):
                vitals = vitals.to(self.device)
                timestamps = timestamps.to(self.device)
                mask = mask.to(self.device)
                label = label.to(self.device)
                sofa = sofa.to(self.device)

                if warmup_steps and step < warmup_steps:
                    scale = (step + 1) / warmup_steps
                    for g in optimizer.param_groups:
                        g["lr"] = LOCAL_LR * scale
                elif warmup_steps:
                    for g in optimizer.param_groups:
                        g["lr"] = LOCAL_LR

                risk_logit, sofa_pred, _ = self.model(vitals, timestamps, mask, return_attention=False)
                sepsis_loss = sepsis_criterion(risk_logit, label)
                sofa_loss = sofa_criterion(sofa_pred, sofa)
                loss = sepsis_loss + LAMBDA_SOFA * sofa_loss

                (loss / ACCUM_STEPS).backward()

                is_last = i == n_mini_batches - 1
                if (i + 1) % ACCUM_STEPS == 0 or is_last:
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    optimizer.step()
                    optimizer.zero_grad()

                total_loss_sum += loss.item()
                n_batches += 1
                step += 1

        train_loss = total_loss_sum / max(n_batches, 1)
        print(f"[Hospital {self.hospital_id}] round {round_num} | local train loss: {train_loss:.4f}")

        return self.get_parameters({}), len(self.train_dataset), {"train_loss": train_loss, "hospital_id": self.hospital_id}

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        self.model.eval()

        loader = DataLoader(self.val_dataset, batch_size=512, shuffle=False)
        sepsis_criterion = torch.nn.BCEWithLogitsLoss(pos_weight=torch.tensor(self.pos_weight, device=self.device))

        all_probs, all_labels = [], []
        loss_sum = 0.0
        n_batches = 0
        with torch.no_grad():
            for vitals, timestamps, mask, label, sofa in loader:
                vitals = vitals.to(self.device)
                timestamps = timestamps.to(self.device)
                mask = mask.to(self.device)
                label = label.to(self.device)

                risk_logit, _, _ = self.model(vitals, timestamps, mask, return_attention=False)
                loss_sum += sepsis_criterion(risk_logit, label).item()
                n_batches += 1
                all_probs.append(torch.sigmoid(risk_logit).cpu().numpy())
                all_labels.append(label.cpu().numpy())

        y_score = np.concatenate(all_probs)
        y_true = np.concatenate(all_labels)
        try:
            val_auroc = roc_auc_score(y_true, y_score)
        except ValueError:
            val_auroc = 0.5

        val_loss = loss_sum / max(n_batches, 1)
        return val_loss, len(self.val_dataset), {"val_auroc": val_auroc, "hospital_id": self.hospital_id}
