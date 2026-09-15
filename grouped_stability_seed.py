from __future__ import annotations

import json
import os
from pathlib import Path

from realitygraph.grouped_empirical import grouped_real_datasets
from realitygraph.predictive import (
    certify_predictive_batch,
    field_from_matrix,
    sealed_group_split,
)
from realitygraph.residual import certify_residual_batch


def main():
    base_seed = os.environ["REALITYGRAPH_GROUP_STABILITY_SEED"]
    replay = int(os.environ["REALITYGRAPH_GROUP_REPLAY"])
    cache = Path(".cache/grouped-real")
    out_path = Path(os.environ.get(
        "REALITYGRAPH_GROUP_RESULT",
        f"results/grouped-stability-{replay}.json",
    ))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    result = {"replay": replay, "datasets": {}}

    for dataset in grouped_real_datasets(cache):
        field = field_from_matrix(
            dataset.probe_names,
            dataset.values,
            dataset.labels,
            dataset.groups,
        )
        split = sealed_group_split(
            dataset.groups,
            f"{base_seed}|{dataset.name}|{replay}",
        )
        test_groups = sorted({str(dataset.groups[i]) for i in split.test})

        certificate = certify_predictive_batch(
            field,
            split,
            max_probes=8,
            min_calibration_gain=1e-4,
            min_sealed_gain=1e-4,
            max_group_harm=0.0,
            min_support=4,
        )
        gain = (
            certificate.sealed_baseline_metrics.log_loss
            - certificate.sealed_metrics.log_loss
        )
        if certificate.accepted and certificate.sealed_metrics.max_group_harm > 1e-12:
            raise AssertionError(f"{dataset.name}: accepted with sealed group harm")

        train_positive = sum(dataset.labels[i] for i in split.train)
        prior = (train_positive + 1.0) / (len(split.train) + 2.0)
        baseline = [prior] * len(dataset.values)
        residual = certify_residual_batch(
            field,
            split,
            baseline,
            max_probes=8,
            min_calibration_gain=1e-4,
            min_sealed_gain=1e-4,
            max_group_harm=0.0,
            min_support=4,
        )
        residual_gain = (
            residual.sealed_baseline_metrics.log_loss
            - residual.sealed_metrics.log_loss
        )
        if residual.accepted and residual.sealed_metrics.max_group_harm > 1e-12:
            raise AssertionError(f"{dataset.name}: residual harmed sealed group")

        result["datasets"][dataset.name] = {
            "groups": dataset.group_count,
            "test_groups": test_groups,
            "accepted": certificate.accepted,
            "gain": gain,
            "group_harm": certificate.sealed_metrics.max_group_harm,
            "probes": [rule.probe_name for rule in certificate.plan.rules],
            "residual_accepted": residual.accepted,
            "residual_gain": residual_gain,
            "residual_group_harm": residual.sealed_metrics.max_group_harm,
            "residual_probes": [rule.probe_name for rule in residual.plan.rules],
        }

        print(
            f"{dataset.name} replay={replay:02d} "
            f"accepted={certificate.accepted} gain={gain:.6f} "
            f"residual={residual.accepted} residual_gain={residual_gain:.6f} "
            f"sealed_groups={len(test_groups)}"
        )

    out_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(f"GROUP_STABILITY_SEED_OK replay={replay} out={out_path}")


if __name__ == "__main__":
    main()
