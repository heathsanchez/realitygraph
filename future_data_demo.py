from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from realitygraph.empirical import fetch_dataset
from realitygraph.empirical_sources import uci_sources
from realitygraph.selective import (
    compile_selective_model,
    evaluate_selective,
    sealed_split,
)


def main():
    seed = os.environ.get("REALITYGRAPH_FREEZE_SEED", "local-sealed-future")
    cache = Path(".cache/real-datasets")
    totals = Counter()

    print("REALITYGRAPH / SEALED FUTURE MEASUREMENTS")
    print("----------------------------------------")
    print("split authority: commit SHA + pinned source bytes")
    print("policy: accepted wrong verdict => hard failure")
    print("        unsupported future => UNKNOWN")
    print()

    for source in uci_sources():
        dataset = fetch_dataset(source, cache)
        split = sealed_split(dataset, seed)
        model = compile_selective_model(split.train, split.calibration)
        result = evaluate_selective(split.test, model)

        if result.wrong:
            raise AssertionError(
                f"{source.name}: {result.wrong} wrong accepted predictions "
                f"on sealed test"
            )

        retained = len(model.balls) if source.target_kind == "categorical" else len(model.exact_decoder)
        totals["datasets"] += 1
        totals["train"] += len(split.train.features)
        totals["calibration"] += len(split.calibration.features)
        totals["test"] += len(split.test.features)
        totals["correct"] += result.correct
        totals["unknown"] += result.unknown
        totals["wrong"] += result.wrong
        totals["retained_rules"] += retained
        if source.target_kind == "categorical":
            totals["categorical_test"] += result.total
            totals["categorical_correct"] += result.correct
            totals["categorical_unknown"] += result.unknown
        else:
            totals["numeric_test"] += result.total
            totals["numeric_correct"] += result.correct
            totals["numeric_unknown"] += result.unknown

        print(source.name)
        print(
            f"  kind={source.target_kind} "
            f"train={len(split.train.features)} "
            f"cal={len(split.calibration.features)} "
            f"sealed_test={result.total}"
        )
        print(
            f"  retained_rules={retained} "
            f"correct={result.correct} UNKNOWN={result.unknown} wrong={result.wrong} "
            f"coverage={100 * result.coverage:.1f}%"
        )
        print()

    if totals["wrong"] != 0:
        raise AssertionError("ZERO WRONG VERDICTS violated")

    print("AGGREGATE")
    for key in (
        "datasets",
        "train",
        "calibration",
        "test",
        "retained_rules",
        "correct",
        "unknown",
        "wrong",
        "categorical_test",
        "categorical_correct",
        "categorical_unknown",
        "numeric_test",
        "numeric_correct",
        "numeric_unknown",
    ):
        print(f"{key:24} {totals[key]}")

    coverage = totals["correct"] / totals["test"] if totals["test"] else 0.0
    categorical_coverage = (
        totals["categorical_correct"] / totals["categorical_test"]
        if totals["categorical_test"]
        else 0.0
    )
    print(f"overall_coverage         {100 * coverage:.2f}%")
    print(f"categorical_coverage     {100 * categorical_coverage:.2f}%")
    print()
    print("VERDICT")
    print("SEALED_TEST_ZERO_WRONG")


if __name__ == "__main__":
    main()
