from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from realitygraph.grouped_empirical import (
    fetch_occupancy_grouped,
    fetch_parkinsons_grouped,
)
from realitygraph.predictive import (
    certify_predictive_batch,
    field_from_matrix,
    leave_one_group_out_split,
)
from realitygraph.residual import certify_residual_batch


def load_dataset(selector: str, cache: Path):
    if selector == "parkinsons":
        return fetch_parkinsons_grouped(cache)
    if selector == "occupancy":
        return fetch_occupancy_grouped(cache)
    raise ValueError(f"unknown grouped dataset selector: {selector}")


def main():
    selector = os.environ["REALITYGRAPH_LOGO_DATASET"]
    seed = os.environ.get("REALITYGRAPH_LOGO_SEED", "logo-natural-groups")
    cache = Path(".cache/grouped-real")
    out_path = Path(os.environ.get(
        "REALITYGRAPH_LOGO_RESULT",
        f"results/logo-{selector}.json",
    ))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset(selector, cache)
    field = field_from_matrix(
        dataset.probe_names,
        dataset.values,
        dataset.labels,
        dataset.groups,
    )
    unique_groups = sorted(set(dataset.groups), key=repr)

    accepted = 0
    residual_accepted = 0
    probes = Counter()
    residual_probes = Counter()
    rows = []

    print("REALITYGRAPH / EXHAUSTIVE LEAVE-ONE-GROUP-OUT")
    print("--------------------------------------------")
    print(f"dataset={dataset.name}")
    print(f"groups={len(unique_groups)} rows={len(dataset.values)}")

    for held_out in unique_groups:
        split = leave_one_group_out_split(
            dataset.groups,
            held_out,
            f"{seed}|{dataset.name}|{held_out!r}",
        )
        test_groups = {dataset.groups[i] for i in split.test}
        if test_groups != {held_out}:
            raise AssertionError(
                f"{dataset.name}: test partition is not exactly {held_out!r}"
            )

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
            if certificate.sealed_metrics.max_group_harm > 1e-12:
                raise AssertionError(
                    f"{dataset.name}/{held_out}: accepted with test-group harm"
                )
            probes.update(rule.probe_name for rule in certificate.plan.rules)

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
            if residual.sealed_metrics.max_group_harm > 1e-12:
                raise AssertionError(
                    f"{dataset.name}/{held_out}: residual harmed test group"
                )
            residual_probes.update(
                rule.probe_name for rule in residual.plan.rules
            )

        row = {
            "group": str(held_out),
            "test_rows": len(split.test),
            "accepted": certificate.accepted,
            "gain": gain,
            "group_harm": certificate.sealed_metrics.max_group_harm,
            "probes": [rule.probe_name for rule in certificate.plan.rules],
            "residual_accepted": residual.accepted,
            "residual_gain": residual_gain,
            "residual_group_harm": residual.sealed_metrics.max_group_harm,
            "residual_probes": [
                rule.probe_name for rule in residual.plan.rules
            ],
        }
        rows.append(row)
        print(
            f"group={held_out!r} rows={len(split.test)} "
            f"accepted={certificate.accepted} gain={gain:.6f} "
            f"residual={residual.accepted} residual_gain={residual_gain:.6f}"
        )

    stable = [
        [name, count]
        for name, count in probes.most_common()
        if accepted and count / accepted >= 0.75
    ]
    stable_residual = [
        [name, count]
        for name, count in residual_probes.most_common()
        if residual_accepted and count / residual_accepted >= 0.75
    ]
    summary = {
        "dataset": dataset.name,
        "groups": len(unique_groups),
        "rows": len(dataset.values),
        "accepted": accepted,
        "residual_accepted": residual_accepted,
        "universally_transferable": accepted == len(unique_groups),
        "universally_residual_transferable": (
            residual_accepted == len(unique_groups)
        ),
        "stable_probes_75pct": stable,
        "stable_residual_probes_75pct": stable_residual,
        "results": rows,
        "source_hashes": list(dataset.source_hashes),
    }
    out_path.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")

    print()
    print(f"accepted={accepted}/{len(unique_groups)}")
    print(f"residual_accepted={residual_accepted}/{len(unique_groups)}")
    print(f"stable_probes_75pct={stable}")
    print(f"stable_residual_probes_75pct={stable_residual}")
    print(f"universally_transferable={summary['universally_transferable']}")
    print(
        "universally_residual_transferable="
        f"{summary['universally_residual_transferable']}"
    )
    print("VERDICT")
    print("EXHAUSTIVE_NATURAL_GROUP_COVERAGE_COMPLETE")


if __name__ == "__main__":
    main()
