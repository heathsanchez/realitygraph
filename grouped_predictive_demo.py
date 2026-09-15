from __future__ import annotations

import os
from pathlib import Path

from realitygraph.grouped_empirical import grouped_real_datasets
from realitygraph.predictive import (
    certify_predictive_batch,
    field_from_matrix,
    sealed_group_split,
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
        for url, digest in dataset.source_hashes:
            print(f"  sha256={digest} url={url}")
        print()

    print(f"accepted_datasets={accepted}")
    print("VERDICT")
    print("REAL_GROUP_SPLIT_COMPLETE")


if __name__ == "__main__":
    main()
