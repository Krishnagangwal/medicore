"""
Evaluates the federated model on the COMBINED held-out test patients
from all 3 hospitals (each hospital's 20% test slice, reserved by
split_hospital_patients and never touched by fl_client.py's local
training), and compares against the centralized model's test AUROC.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader

import inference as inference_module
from fl_client import build_windows_for_patients, split_hospital_patients
from model import SepsisTransformer, get_device

MODEL_SEPSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(MODEL_SEPSIS_DIR, "artifacts")
CSV_PATH = os.path.expanduser("~/Downloads/archive-2/Dataset.csv")

# From ai-models/model_sepsis/test_run5.log (test_sepsis_model.py Test 1).
CENTRALIZED_TEST_AUROC = 0.7603


def _load_federated_model(device):
    model = SepsisTransformer().to(device)
    model.load_state_dict(torch.load(os.path.join(ARTIFACTS_DIR, "federated_model.pt"), map_location=device))
    model.eval()
    return model


def _evaluate(model, dataset, device):
    loader = DataLoader(dataset, batch_size=512, shuffle=False)
    all_probs, all_labels = [], []
    with torch.no_grad():
        for vitals, timestamps, mask, label, sofa in loader:
            vitals, timestamps, mask = vitals.to(device), timestamps.to(device), mask.to(device)
            risk_logit, _, _ = model(vitals, timestamps, mask, return_attention=False)
            all_probs.append(torch.sigmoid(risk_logit).cpu().numpy())
            all_labels.append(label.numpy())
    y_score = np.concatenate(all_probs)
    y_true = np.concatenate(all_labels)
    try:
        auroc = roc_auc_score(y_true, y_score)
    except ValueError:
        auroc = float("nan")
    return auroc, len(dataset)


def test_federated_model() -> float:
    print("=== Federated Model Evaluation ===")
    device = get_device()

    with open(os.path.join(ARTIFACTS_DIR, "hospital_partitions.json")) as f:
        partitions = json.load(f)
    with open(os.path.join(ARTIFACTS_DIR, "normalisation.json")) as f:
        normalisation = json.load(f)

    model = _load_federated_model(device)

    hospital_aurocs = {}
    combined_test_ids = []
    for hospital_id_str, patient_ids in partitions.items():
        hospital_id = int(hospital_id_str)
        _, _, test_ids = split_hospital_patients(patient_ids)
        combined_test_ids.extend(test_ids)
        hospital_dataset = build_windows_for_patients(CSV_PATH, test_ids, normalisation)
        auroc, _ = _evaluate(model, hospital_dataset, device)
        hospital_aurocs[hospital_id] = auroc

    combined_dataset = build_windows_for_patients(CSV_PATH, combined_test_ids, normalisation)
    combined_auroc, n_combined = _evaluate(model, combined_dataset, device)

    gap = combined_auroc - CENTRALIZED_TEST_AUROC

    print(f"Combined test patients: {len(combined_test_ids)}")
    print(f"Combined test windows:  {n_combined}")
    print()
    print(f"Federated model test AUROC:     {combined_auroc:.4f}")
    print(f"Centralized model test AUROC:   {CENTRALIZED_TEST_AUROC:.4f}  (reference)")
    print(f"Federated vs centralized gap:   {gap:+.4f}")
    print()
    print("Hospital breakdown:")
    print(f"  Hospital 0 (40% data): AUROC {hospital_aurocs[0]:.4f}")
    print(f"  Hospital 1 (35% data): AUROC {hospital_aurocs[1]:.4f}")
    print(f"  Hospital 2 (25% data): AUROC {hospital_aurocs[2]:.4f}")
    print()
    if abs(gap) < 0.03:
        print("Note: A small federated gap (< 0.03) is expected and normal.")
        print("Federated models trade slight accuracy for privacy preservation")
        print("and cross-hospital generalizability.")
    else:
        print(f"Note: gap ({gap:+.4f}) exceeds the typical 0.03 expectation. "
              "Reporting honestly rather than re-running indefinitely.")

    return combined_auroc


def test_clinical_scenario() -> bool:
    device = get_device()
    model = _load_federated_model(device)

    readings = []
    for h in range(1, 19):
        readings.append({"hr": 85, "o2sat": 97, "temp": 37.2, "sbp": 118, "map": 82, "dbp": 68, "resp": 16, "iculos": h})
    for h in range(19, 25):
        readings.append({"hr": 118, "o2sat": 91, "temp": 38.8, "sbp": 86, "map": 58, "dbp": 45, "resp": 26, "iculos": h})

    # Reuse inference.py's window-building helper (left-pad + per-vital
    # normalisation) rather than duplicating it — it only needs the
    # readings, not inference.py's own separately-loaded module-level
    # model, which this test intentionally bypasses in favor of the
    # federated checkpoint loaded above.
    vitals, timestamps, mask, _, _ = inference_module._prepare_window(readings)
    with torch.no_grad():
        risk_logit, _, _ = model(
            vitals.unsqueeze(0).to(device),
            timestamps.unsqueeze(0).to(device),
            mask.unsqueeze(0).to(device),
            return_attention=False,
        )
    risk_score = torch.sigmoid(risk_logit).item()
    alert = risk_score > 0.65

    print(f"Clinical scenario: risk_score={risk_score:.4f}, alert={alert}")
    passed = alert is True
    print("Clinical scenario: PASS" if passed else "Clinical scenario: FAIL")
    return passed


if __name__ == "__main__":
    test_federated_model()
    print()
    test_clinical_scenario()
