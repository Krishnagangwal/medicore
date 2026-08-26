"""
FedAvg strategy configuration for the sepsis federated simulation.

FedAvg (McMahan et al. 2017) aggregates client weight updates using a
weighted average by each client's local dataset size — the standard
first choice for federated averaging, and appropriate here since our
3 simulated hospitals are IID-ish partitions of the same source
distribution (not the more adversarial non-IID setting that motivates
fancier strategies like FedProx).
"""

import flwr as fl


class SavingFedAvg(fl.server.strategy.FedAvg):
    """FedAvg that remembers both the latest AND the best-by-val-AUROC
    aggregated parameters.

    A first run of this simulation (15 rounds, no early stopping)
    showed aggregated val AUROC peak at round 2 (0.74) and decline
    steadily to round 15 (0.65) — the same overfitting-past-the-peak
    pattern the centralized training run showed, but federated has no
    protection against it: blindly saving the LAST round's weights
    means saving the most-overfit checkpoint, not the best one. This
    tracks the best round's parameters (by the aggregated val AUROC
    each round's evaluate phase produces) so fl_train.py can save
    those instead, mirroring the checkpoint-on-improvement logic
    centralized train.py already uses.

    aggregate_fit (round N) produces round N's parameters; the
    evaluation of those SAME parameters happens afterward, in round
    N's aggregate_evaluate. So a round's candidate parameters are held
    in _pending_parameters until that round's evaluate confirms
    whether they're a new best.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.latest_parameters = None
        self.best_parameters = None
        self.best_auroc = -1.0
        self.best_round = None
        self._pending_parameters = None

    def aggregate_fit(self, server_round, results, failures):
        aggregated_parameters, metrics = super().aggregate_fit(server_round, results, failures)
        if aggregated_parameters is not None:
            self.latest_parameters = aggregated_parameters
            self._pending_parameters = aggregated_parameters
        return aggregated_parameters, metrics

    def aggregate_evaluate(self, server_round, results, failures):
        loss, metrics = super().aggregate_evaluate(server_round, results, failures)
        auroc = metrics.get("aggregated_val_auroc") if metrics else None
        if auroc is not None and auroc > self.best_auroc and self._pending_parameters is not None:
            self.best_auroc = auroc
            self.best_parameters = self._pending_parameters
            self.best_round = server_round
        return loss, metrics


def get_fedavg_strategy(initial_parameters) -> SavingFedAvg:
    """All 3 hospitals participate in every round (fraction_fit /
    fraction_evaluate = 1.0) — with only 3 simulated hospitals total,
    sub-sampling clients per round (the usual reason for fractions
    < 1.0 in cross-device FL with thousands of clients) has no purpose
    here; this is cross-silo FL, where every institution is expected
    to participate every round."""

    round_counter = {"n": 0}

    def fit_config(server_round: int):
        return {"round": server_round}

    def weighted_auroc_aggregation(metrics):
        """metrics: list of (num_examples, metrics_dict) from each
        hospital's evaluate(). Aggregated AUROC is weighted by each
        hospital's local validation set size, matching FedAvg's own
        weighting convention for training."""
        round_counter["n"] += 1
        total = sum(n for n, _ in metrics)
        aggregated = sum(n * m["val_auroc"] for n, m in metrics) / total

        by_hospital = sorted(metrics, key=lambda x: x[1]["hospital_id"])
        hospital_str = ", ".join(f"h{m['hospital_id']}: {m['val_auroc']:.2f}" for _, m in by_hospital)
        print(f"Round {round_counter['n']} | Aggregated Val AUROC: {aggregated:.4f} | Hospital AUROCs: [{hospital_str}]")

        result = {"aggregated_val_auroc": aggregated}
        for _, m in metrics:
            result[f"hospital_{m['hospital_id']}_auroc"] = m["val_auroc"]
        return result

    return SavingFedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=3,
        min_evaluate_clients=3,
        min_available_clients=3,
        initial_parameters=initial_parameters,
        on_fit_config_fn=fit_config,
        evaluate_metrics_aggregation_fn=weighted_auroc_aggregation,
    )
