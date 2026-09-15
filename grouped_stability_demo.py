from __future__ import annotations

import os
from collections import Counter, defaultdict
from pathlib import Path

from realitygraph.grouped_empirical import grouped_real_datasets
from realitygraph.predictive import (
    certify_predictive_batch,
    field_from_matrix,
    sealed_group_split,
)
from realitygraph.residual import certify_residual_batch


def main():
    base_seed = os.environ.get("REALITYGRAPH_GROUP_STABILITY_SEED", "group-stability")
    cache = Path(".cache/grouped-real")
    repetitions = 16

    print("REALITYGRAPH / NATURAL-GROUP STABILITY")
    print("-------------------------------------")
    print(f"repetitions={repetitions}")
    print("authority: held-out people/days; zero sealed group harm required")
    print()

    for dataset in grouped_real_datasets(cache):
        field = field_from_matrix(
            dataset.probe_names,
            dataset.values,
            dataset.labels,
            dataset.groups,
        )

        accepted = 0
        residual_accepted = 0
        probe_counts = Counter()
        residual_probe_counts = Counter()
        gains = []
        residual_gains = []
        tested_group_occurrences = Counter()

        for replay in range(repetitions):
            split = sealed_group_split(
                dataset.groups,
                f"{base_seed}|{dataset.name}|{replay}",
            )
            test_groups = {dataset.groups[i] for i in split.test}
            for group in test_groups:
                tested_group_occurrences[str(group)] += 1

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
            if certificate.accepted:
                accepted += 1
                gains.append(gain)
                if certificate.sealed_metrics.max_group_harm > 1e-12:
                    raise AssertionError(
                        f"{dataset.name}: replay {replay} accepted with group harm"
                    )
                for rule in certificate.plan.rules:
                    probe_counts[rule.probe_name] += 1

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
            if residual.accepted:
                residual_accepted += 1
                residual_gains.append(residual_gain)
                if residual.sealed_metrics.max_group_harm > 1e-12:
                    raise AssertionError(
                        f"{dataset.name}: residual replay {replay} harmed a group"
                    )
                for rule in residual.plan.rules:
                    residual_probe_counts[rule.probe_name] += 1

            print(
                f"{dataset.name} replay={replay:02d} "
                f"accepted={certificate.accepted} gain={gain:.6f} "
                f"residual={residual.accepted} residual_gain={residual_gain:.6f} "
                f"sealed_groups={len(test_groups)}"
            )

        stable_probes = [
            (name, count)
            for name, count in probe_counts.most_common()
            if accepted and count / accepted >= 0.75
        ]
        stable_residual_probes = [
            (name, count)
            for name, count in residual_probe_counts.most_common()
            if residual_accepted and count / residual_accepted >= 0.75
        ]

        print()
        print(dataset.name)
        print(
            f"  grouped_acceptance={accepted}/{repetitions} "
            f"residual_acceptance={residual_accepted}/{repetitions}"
        )
        print(
            f"  mean_grouped_gain="
            f"{sum(gains) / len(gains) if gains else 0.0:.6f} "
            f"mean_residual_gain="
            f"{sum(residual_gains) / len(residual_gains) if residual_gains else 0.0:.6f}"
        )
        print(f"  stable_probes_75pct={stable_probes}")
        print(f"  stable_residual_probes_75pct={stable_residual_probes}")
        print(
            f"  distinct_groups_exposed={len(tested_group_occurrences)}/"
            f"{dataset.group_count}"
        )

        if len(tested_group_occurrences) != dataset.group_count:
            raise AssertionError(
                f"{dataset.name}: not every natural group reached a sealed future"
            )

        # Dataset-level transfer is deliberately strict: a transferable law is
        # declared only when it survives every independent natural-group split.
        transferable = accepted == repetitions
        residual_transferable = residual_accepted == repetitions
        print(f"  transferable={transferable}")
        print(f"  residual_transferable={residual_transferable}")
        print()

    print("VERDICT")
    print("NATURAL_GROUP_STABILITY_COMPLETE")


if __name__ == "__main__":
    main()
