from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from realitygraph.consequence import (
    compile_consequence_model,
    evaluate_consequences,
)
from realitygraph.empirical import fetch_dataset
from realitygraph.empirical_sources import uci_sources
from realitygraph.selective import sealed_split


def main():
    seed = os.environ.get("REALITYGRAPH_FREEZE_SEED", "local-consequence-frontier")
    cache = Path(".cache/real-datasets")
    totals = Counter()
    interval_width_ratio_sum = 0.0
    interval_datasets = 0

    print("REALITYGRAPH / ADAPTIVE CONSEQUENCE FRONTIER")
    print("-------------------------------------------")
    print("sealed split: commit SHA + pinned source bytes")
    print("order: exact label -> proper label set -> numeric interval -> UNKNOWN")
    print("wrong informative consequence => hard failure")
    print()

    for source in uci_sources():
        dataset = fetch_dataset(source, cache)
        split = sealed_split(dataset, seed)
        model = compile_consequence_model(split.train, split.calibration)
        result = evaluate_consequences(split.test, model)

        if result.wrong:
            raise AssertionError(
                f"{source.name}: {result.wrong} wrong informative consequences "
                f"on sealed test"
            )

        totals["datasets"] += 1
        totals["test"] += result.total
        totals["exact"] += result.exact
        totals["partial"] += result.partial
        totals["interval"] += result.interval
        totals["unknown"] += result.unknown
        totals["wrong"] += result.wrong
        totals["informative"] += result.informative

        if source.target_kind == "categorical":
            totals["categorical_test"] += result.total
            totals["categorical_exact"] += result.exact
            totals["categorical_partial"] += result.partial
            totals["categorical_unknown"] += result.unknown
            denom = result.exact + result.partial
            avg_slots = result.total_label_slots / denom if denom else 0.0
            print(source.name)
            print(
                f"  categorical test={result.total} exact={result.exact} "
                f"proper_set={result.partial} UNKNOWN={result.unknown} wrong={result.wrong}"
            )
            print(
                f"  class_ratio={model.class_ratio:.4f} "
                f"avg_labels_when_informative={avg_slots:.2f}"
            )
        else:
            totals["numeric_test"] += result.total
            totals["numeric_interval"] += result.interval
            totals["numeric_unknown"] += result.unknown
            avg_width = (
                result.interval_width_sum / result.interval
                if result.interval
                else 0.0
            )
            ratio = (
                avg_width / model.numeric_target_span
                if model.numeric_target_span > 0 and result.interval
                else 0.0
            )
            if result.interval:
                interval_width_ratio_sum += ratio
                interval_datasets += 1
            print(source.name)
            print(
                f"  numeric test={result.total} interval={result.interval} "
                f"UNKNOWN={result.unknown} wrong={result.wrong}"
            )
            print(
                f"  calibrated_radius={model.regression_radius:.6g} "
                f"mean_interval_width/range={ratio:.3f}"
            )
        print()

    if totals["wrong"] != 0:
        raise AssertionError("ZERO WRONG CONSEQUENCES violated")

    print("AGGREGATE")
    for key in (
        "datasets",
        "test",
        "informative",
        "exact",
        "partial",
        "interval",
        "unknown",
        "wrong",
        "categorical_test",
        "categorical_exact",
        "categorical_partial",
        "categorical_unknown",
        "numeric_test",
        "numeric_interval",
        "numeric_unknown",
    ):
        print(f"{key:24} {totals[key]}")

    coverage = totals["informative"] / totals["test"] if totals["test"] else 0.0
    categorical_info = (
        totals["categorical_exact"] + totals["categorical_partial"]
    )
    categorical_coverage = (
        categorical_info / totals["categorical_test"]
        if totals["categorical_test"]
        else 0.0
    )
    numeric_coverage = (
        totals["numeric_interval"] / totals["numeric_test"]
        if totals["numeric_test"]
        else 0.0
    )
    print(f"informative_coverage      {100 * coverage:.2f}%")
    print(f"categorical_coverage      {100 * categorical_coverage:.2f}%")
    print(f"numeric_interval_coverage {100 * numeric_coverage:.2f}%")
    if interval_datasets:
        print(
            f"mean_interval_width/range "
            f"{interval_width_ratio_sum / interval_datasets:.3f}"
        )
    print()
    print("VERDICT")
    print("SEALED_TEST_ZERO_WRONG_CONSEQUENCES")


if __name__ == "__main__":
    main()
