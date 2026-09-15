from __future__ import annotations

import hashlib
import os
from pathlib import Path

from realitygraph.grouped_empirical import grouped_real_datasets
from realitygraph.predictive import (
    PredictiveSplit,
    certify_predictive_batch,
    field_from_matrix,
    sealed_group_split,
)


def sealed_row_split(labels, seed: str) -> PredictiveSplit:
    by_label = {0: [], 1: []}
    for i, label in enumerate(labels):
        by_label[int(label)].append(i)

    train = []
    calibration = []
    test = []
    for label, members in by_label.items():
        ordered = sorted(
            members,
            key=lambda i: hashlib.sha256(
                f"{seed}|{label}|{i}".encode()
            ).digest(),
        )
        n = len(ordered)
        n_train = max(1, int(0.60 * n))
        n_cal = max(1, int(0.20 * n))
        if n_train + n_cal >= n:
            n_cal = max(1, n - n_train - 1)
        train.extend(ordered[:n_train])
        calibration.extend(ordered[n_train:n_train + n_cal])
        test.extend(ordered[n_train + n_cal:])

    return PredictiveSplit(
        tuple(sorted(train)),
        tuple(sorted(calibration)),
        tuple(sorted(test)),
        hashlib.sha256(seed.encode()).hexdigest()[:16],
    )


def main():
    seed = os.environ.get("REALITYGRAPH_GROUP_SEED", "local-grouped-real")
    cache = Path(".cache/grouped-real")

    print("REALITYGRAPH / REAL GROUPED PREDICTION")
    print("--------------------------------------")
    print("split authority: natural subject/day groups")
    print("policy: no group may appear in more than one partition")
    print("        accepted rule must improve sealed LL and harm no sealed group")
    print()

    accepted = 0
    for dataset in grouped_real_datasets(cache):
        field = field_from_matrix(
            dataset.probe_names,
            dataset.values,
            dataset.labels,
            dataset.groups,
        )
        split = sealed_group_split(dataset.groups, f"{seed}|{dataset.name}")

        train_groups = {dataset.groups[i] for i in split.train}
        cal_groups = {dataset.groups[i] for i in split.calibration}
        test_groups = {dataset.groups[i] for i in split.test}
        if train_groups & cal_groups or train_groups & test_groups or cal_groups & test_groups:
            raise AssertionError(f"{dataset.name}: group leakage")

        certificate = certify_predictive_batch(
            field,
            split,
            max_probes=8,
            min_calibration_gain=1e-4,
            min_sealed_gain=1e-4,
            max_group_harm=0.0,
            min_support=4,
        )
        row_certificate = certify_predictive_batch(
            field,
            sealed_row_split(dataset.labels, f"{seed}|{dataset.name}|row"),
            max_probes=8,
            min_calibration_gain=1e-4,
            min_sealed_gain=1e-4,
            min_support=4,
        )
        if certificate.accepted:
            accepted += 1
            if not (
                certificate.sealed_metrics.log_loss
                < certificate.sealed_baseline_metrics.log_loss
            ):
                raise AssertionError(f"{dataset.name}: accepted without sealed gain")
            if certificate.sealed_metrics.max_group_harm > 1e-12:
                raise AssertionError(f"{dataset.name}: accepted with sealed group harm")

        print(dataset.name)
        print(
            f"  rows={len(dataset.values)} groups={dataset.group_count} "
            f"train_groups={len(train_groups)} cal_groups={len(cal_groups)} "
            f"sealed_groups={len(test_groups)}"
        )
        print(f"  retained={[rule.probe_name for rule in certificate.plan.rules]}")
        print(
            f"  calibration_LL={certificate.plan.calibration_metrics.log_loss:.6f}"
        )
        print(
            f"  sealed_baseline_LL={certificate.sealed_baseline_metrics.log_loss:.6f}"
        )
        print(
            f"  sealed_candidate_LL={certificate.sealed_metrics.log_loss:.6f} "
            f"AUC={certificate.sealed_metrics.auc:.6f}"
        )
        print(
            f"  max_sealed_group_harm={certificate.sealed_metrics.max_group_harm:.6f} "
            f"accepted={certificate.accepted}"
        )
        print(
            f"  naive_row_split: baseline_LL="
            f"{row_certificate.sealed_baseline_metrics.log_loss:.6f} "
            f"candidate_LL={row_certificate.sealed_metrics.log_loss:.6f} "
            f"AUC={row_certificate.sealed_metrics.auc:.6f} "
            f"accepted={row_certificate.accepted}"
        )
        print(
            f"  grouping_penalty_LL="
            f"{certificate.sealed_metrics.log_loss - row_certificate.sealed_metrics.log_loss:.6f}"
        )
        for url, digest in dataset.source_hashes:
            print(f"  sha256={digest} url={url}")
        print()

    print(f"accepted_datasets={accepted}")
    print("VERDICT")
    print("REAL_GROUP_SPLIT_COMPLETE")


if __name__ == "__main__":
    main()
