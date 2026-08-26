"""
Main entry point for the federated sepsis training simulation.

Runs entirely locally via Flower's Ray-based simulation — no network
involved, but the 3 "hospitals" never see each other's rows, which is
the property that actually matters for the privacy story.

ray_init_args={"num_cpus": 1} deliberately caps Ray's total worker
pool at 1, forcing all 3 hospital clients to run strictly one at a
time even though the machine has more cores. Apple's MPS backend does
not support safe concurrent access to the same GPU from multiple
processes (the exact "MPS conflicts" the assignment brief warns
about); serializing clients avoids that entirely while still letting
each client use the fast MPS device (rather than falling back to CPU
for everyone, which would be safe but much slower).
"""

import json
import os
import sys

_MODEL_SEPSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FEDERATED_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _MODEL_SEPSIS_DIR)
sys.path.insert(0, _FEDERATED_DIR)

# Flower's Ray-based simulation runs each client's fit()/evaluate() in
# a SEPARATE worker process, not a thread — sys.path mutations made
# above only affect this driver process and are invisible to those
# workers. When Ray tries to unpickle a SepsisClient instance in a
# worker, it needs `import fl_client` to succeed there too, which
# requires PYTHONPATH (an environment variable, which DOES propagate
# to child processes) rather than sys.path. This must be set before
# flwr/ray initialize any workers.
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
_new_paths = os.pathsep.join([_MODEL_SEPSIS_DIR, _FEDERATED_DIR])
os.environ["PYTHONPATH"] = f"{_new_paths}{os.pathsep}{_existing_pythonpath}" if _existing_pythonpath else _new_paths

import flwr as fl
import torch

from model import SepsisTransformer, get_device
from fl_client import SepsisClient
from fl_partition import create_hospital_partitions
from fl_server import get_fedavg_strategy

CSV_PATH = os.path.expanduser("~/Downloads/archive-2/Dataset.csv")
MODEL_SEPSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(MODEL_SEPSIS_DIR, "artifacts")
NUM_ROUNDS = 15
SEED = 42


def main():
    device = get_device()
    print(f"Device: {device}")

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    print("Creating hospital partitions...")
    partitions = create_hospital_partitions(CSV_PATH, n_hospitals=3, seed=SEED)
    with open(os.path.join(ARTIFACTS_DIR, "hospital_partitions.json"), "w") as f:
        json.dump({str(k): v for k, v in partitions.items()}, f)

    normalisation_path = os.path.join(ARTIFACTS_DIR, "normalisation.json")
    class_weight_path = os.path.join(ARTIFACTS_DIR, "class_weights.json")
    if not (os.path.exists(normalisation_path) and os.path.exists(class_weight_path)):
        raise FileNotFoundError(
            "artifacts/normalisation.json and artifacts/class_weights.json "
            "are required (produced by the centralized ai-models/model_sepsis/"
            "train.py run) so federated hospitals share the same preprocessing "
            "contract. Run centralized training first."
        )

    # Start federated training from a FRESH random model, never from
    # the centralized model.pt — the whole point of this run is to
    # prove the federated procedure itself converges, not to warm-start
    # from a model that already saw all the data centrally.
    global_model = SepsisTransformer()
    initial_parameters = fl.common.ndarrays_to_parameters(
        [val.cpu().numpy() for val in global_model.state_dict().values() if val.dtype != torch.bool]
    )

    def client_fn(context):
        hospital_id = int(context.node_config["partition-id"])
        return SepsisClient(
            hospital_id=hospital_id,
            patient_ids=partitions[hospital_id],
            csv_path=CSV_PATH,
            normalisation_path=normalisation_path,
            class_weight_path=class_weight_path,
            device=device,
        ).to_client()

    strategy = get_fedavg_strategy(initial_parameters)

    print(f"Starting federated training: {NUM_ROUNDS} rounds, 3 hospitals")
    print(f"Hospital sizes: {[len(v) for v in partitions.values()]} patients")

    history = fl.simulation.start_simulation(
        client_fn=client_fn,
        num_clients=3,
        config=fl.server.ServerConfig(num_rounds=NUM_ROUNDS),
        strategy=strategy,
        client_resources={"num_cpus": 1, "num_gpus": 0},
        ray_init_args={"num_cpus": 1},
    )

    # Save the BEST round's parameters, not necessarily the last round's.
    # An earlier run showed val AUROC peak early (round 2) and decline
    # steadily thereafter — the same overfitting-past-the-peak pattern
    # centralized training showed, but federated has no early stopping.
    # Falls back to latest_parameters only if evaluation somehow never
    # produced a best (e.g. all rounds failed evaluation).
    best_parameters = strategy.best_parameters or strategy.latest_parameters
    if best_parameters is None:
        raise RuntimeError("Federated training produced no aggregated parameters (all rounds failed).")

    final_ndarrays = fl.common.parameters_to_ndarrays(best_parameters)
    final_model = SepsisTransformer()
    state_dict = final_model.state_dict()
    float_keys = [k for k, v in state_dict.items() if v.dtype != torch.bool]
    for key, array in zip(float_keys, final_ndarrays):
        state_dict[key] = torch.tensor(array, dtype=state_dict[key].dtype)
    final_model.load_state_dict(state_dict)

    model_path = os.path.join(ARTIFACTS_DIR, "federated_model.pt")
    torch.save(final_model.state_dict(), model_path)

    print("\n=== Federated Training Complete ===")
    print(f"Rounds completed: {NUM_ROUNDS}")
    if strategy.best_round is not None:
        print(f"Best round: {strategy.best_round} | Best aggregated Val AUROC: {strategy.best_auroc:.4f}")
    else:
        print("No round improved on the initial -1.0 baseline; saved the final round's parameters instead.")
    print(f"Saved: {model_path}")

    # history.metrics_distributed["aggregated_val_auroc"] is a list of
    # (round_number, value) tuples, one entry per completed round.
    auroc_history = history.metrics_distributed.get("aggregated_val_auroc", [])

    hospital_auroc_by_round = {}
    for hospital_id in range(3):
        for round_num, auroc in history.metrics_distributed.get(f"hospital_{hospital_id}_auroc", []):
            hospital_auroc_by_round.setdefault(round_num, {})[hospital_id] = auroc

    training_log = {
        str(round_num): {
            "aggregated_auroc": auroc,
            "hospital_aurocs": [hospital_auroc_by_round.get(round_num, {}).get(h) for h in range(3)],
        }
        for round_num, auroc in auroc_history
    }
    log_path = os.path.join(ARTIFACTS_DIR, "federated_training_log.json")
    with open(log_path, "w") as f:
        json.dump(training_log, f, indent=2)
    print(f"Training history saved to {log_path}")


if __name__ == "__main__":
    main()
