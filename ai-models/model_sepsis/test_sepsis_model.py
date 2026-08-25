"""
Post-training validation for the sepsis model.

Test 1 checks aggregate discrimination performance on the held-out
test set and re-confirms the patient-level split has zero leakage.
Test 2 simulates a single deteriorating ICU patient end-to-end through
inference.predict() and checks the explainability output actually
points at the hours that worsened.
"""

import os

import numpy as np
import torch
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve
from torch.utils.data import DataLoader

from data_loader import load_and_prepare_data
from model import SepsisTransformer, get_device

CSV_PATH = os.path.expanduser("~/Downloads/archive-2/Dataset.csv")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


def test_model_performance():
    print("=" * 70)
    print("TEST 1 — Model performance on held-out test set")
    print("=" * 70)

    device = get_device()

    # load_and_prepare_data asserts internally that fit/val patient IDs
    # are disjoint from test patient IDs (patient-level split); if this
    # call succeeds without raising, that assertion already passed.
    train_ds, val_ds, test_ds, _ = load_and_prepare_data(CSV_PATH, artifacts_dir=ARTIFACTS_DIR)
    print("Patient-level split verified: 0 overlap")

    model = SepsisTransformer().to(device)
    model.load_state_dict(torch.load(os.path.join(ARTIFACTS_DIR, "model.pt"), map_location=device))
    model.eval()

    n_params = sum(p.numel() for p in model.parameters())
    print(f"Number of parameters in model: {n_params:,}")

    loader = DataLoader(test_ds, batch_size=512, shuffle=False)
    all_probs, all_labels = [], []
    with torch.no_grad():
        for vitals, timestamps, mask, label, _ in loader:
            vitals, timestamps, mask = vitals.to(device), timestamps.to(device), mask.to(device)
            risk_logit, _, _ = model(vitals, timestamps, mask, return_attention=False)
            all_probs.append(torch.sigmoid(risk_logit).cpu().numpy())
            all_labels.append(label.numpy())
    y_score = np.concatenate(all_probs)
    y_true = np.concatenate(all_labels)

    auroc = roc_auc_score(y_true, y_score)
    auprc = average_precision_score(y_true, y_score)

    fpr, tpr, _ = roc_curve(y_true, y_score)
    specificity = 1 - fpr
    valid = np.where(specificity >= 0.8)[0]
    sens_at_80_spec = tpr[valid[-1]] if len(valid) > 0 else float("nan")

    print(f"AUROC on test set: {auroc:.4f} (target: > 0.77)")
    print(f"AUPRC on test set: {auprc:.4f}")
    print(f"Sensitivity at 80% specificity: {sens_at_80_spec:.4f}")

    if auroc > 0.77:
        print("PASS: AUROC exceeds 0.77 target")
    else:
        print("FAIL: AUROC below 0.77 target")

    return auroc


def test_clinical_scenario():
    print("=" * 70)
    print("TEST 2 — Clinical scenario: deteriorating ICU patient")
    print("=" * 70)

    import inference  # imported here so it loads the freshly-trained model.pt

    readings = []
    for h in range(1, 19):
        readings.append({"hr": 85, "o2sat": 97, "temp": 37.2, "sbp": 118, "map": 82, "dbp": 68, "resp": 16, "iculos": h})
    for h in range(19, 25):
        readings.append({"hr": 118, "o2sat": 91, "temp": 38.8, "sbp": 86, "map": 58, "dbp": 45, "resp": 26, "iculos": h})

    result = inference.predict(readings)

    import json
    print(json.dumps(result, indent=2))

    failures = []
    if result["alert"] is not True:
        failures.append(f"alert == {result['alert']}, expected True")
    if result["attention_peak_hour"] < 18:
        failures.append(f"attention_peak_hour == {result['attention_peak_hour']}, expected >= 18")
    if result["risk_level"] != "high":
        failures.append(f"risk_level == {result['risk_level']!r}, expected 'high'")
    if result["sofa_rounded"] < 2:
        failures.append(f"sofa_rounded == {result['sofa_rounded']}, expected >= 2")

    if not failures:
        print("All clinical scenario assertions PASSED")
    else:
        print("Clinical scenario assertions FAILED:")
        for f in failures:
            print(f"  - {f}")

    return len(failures) == 0


if __name__ == "__main__":
    auroc = test_model_performance()
    scenario_passed = test_clinical_scenario()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"AUROC > 0.77: {'PASS' if auroc > 0.77 else 'FAIL'} ({auroc:.4f})")
    print(f"Clinical scenario: {'PASS' if scenario_passed else 'FAIL'}")
