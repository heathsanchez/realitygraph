from __future__ import annotations

import json
import os
from pathlib import Path


def main():
    paths = [
        Path(value)
        for value in os.environ[
            "REALITYGRAPH_RECURSIVE_SUMMARIES"
        ].split(os.pathsep)
        if value
    ]
    if len(paths) != 3:
        raise AssertionError(
            "expected exactly three "
            "generation summaries"
        )

    rows = [
        json.loads(path.read_text())
        for path in paths
    ]
    rows.sort(
        key=lambda row: row["generation"]
    )
    if [
        row["generation"] for row in rows
    ] != [1, 2, 3]:
        raise AssertionError(
            "recursive generation "
            "sequence drift"
        )

    total_current_cost = sum(
        row["current_search_cost"]
        for row in rows
    )
    total_previous_cost = sum(
        row["previous_search_cost"]
        for row in rows
    )
    total_cold_cost = sum(
        row["cold_search_cost"]
        for row in rows
    )
    total_current_success = sum(
        row["current_successes"]
        for row in rows
    )
    total_previous_success = sum(
        row["previous_successes"]
        for row in rows
    )
    total_cold_success = sum(
        row["cold_successes"]
        for row in rows
    )
    total_current_false = sum(
        row["current_false_laws"]
        for row in rows
    )
    total_previous_false = sum(
        row["previous_false_laws"]
        for row in rows
    )
    total_cold_false = sum(
        row["cold_false_laws"]
        for row in rows
    )

    total_current_gain = sum(
        row["current_mean_gain"] * 20
        for row in rows
    )
    total_previous_gain = sum(
        row["previous_mean_gain"] * 20
        for row in rows
    )
    total_cold_gain = sum(
        row["cold_mean_gain"] * 20
        for row in rows
    )

    improved_cost_generations = sum(
        row["current_search_cost"]
        < row["previous_search_cost"]
        for row in rows
    )

    generation_table = []
    for row in rows:
        current_success_eff = (
            row["current_successes"]
            / max(
                row["current_search_cost"],
                1,
            )
        )
        previous_success_eff = (
            row["previous_successes"]
            / max(
                row["previous_search_cost"],
                1,
            )
        )
        current_gain_eff = (
            row["current_mean_gain"]
            * 20
            / max(
                row["current_search_cost"],
                1,
            )
        )
        previous_gain_eff = (
            row["previous_mean_gain"]
            * 20
            / max(
                row["previous_search_cost"],
                1,
            )
        )
        generation_table.append({
            "generation":
                row["generation"],
            "heldout_range":
                row["heldout_range"],
            "memory_bytes":
                row[
                    "current_memory_bytes"
                ],
            "cold_to_current_reduction":
                row[
                    "cold_to_current_reduction"
                ],
            "previous_to_current_reduction":
                row[
                    "previous_to_current_reduction"
                ],
            "current_successes":
                row["current_successes"],
            "previous_successes":
                row["previous_successes"],
            "current_false_laws":
                row["current_false_laws"],
            "previous_false_laws":
                row["previous_false_laws"],
            "success_efficiency_multiplier":
                current_success_eff
                / max(
                    previous_success_eff,
                    1e-12,
                ),
            "gain_efficiency_multiplier":
                (
                    current_gain_eff
                    / max(
                        previous_gain_eff,
                        1e-12,
                    )
                    if previous_gain_eff > 0
                    else 1.0
                ),
        })

    success_retention = (
        total_current_success
        / max(total_previous_success, 1)
    )
    gain_retention = (
        total_current_gain
        / max(
            total_previous_gain,
            1e-12,
        )
        if total_previous_gain > 0
        else 1.0
    )
    previous_to_current = (
        total_previous_cost
        / max(total_current_cost, 1)
    )
    cold_to_current = (
        total_cold_cost
        / max(total_current_cost, 1)
    )
    success_efficiency_multiplier = (
        (
            total_current_success
            / max(
                total_current_cost,
                1,
            )
        )
        / (
            total_previous_success
            / max(
                total_previous_cost,
                1,
            )
        )
    )
    gain_efficiency_multiplier = (
        (
            total_current_gain
            / max(
                total_current_cost,
                1,
            )
        )
        / (
            total_previous_gain
            / max(
                total_previous_cost,
                1,
            )
        )
        if total_previous_gain > 0
        else 1.0
    )

    verdict_checks = {
        "at_least_two_generations_reduce_parent_search":
            improved_cost_generations >= 2,
        "aggregate_search_reduction_at_least_10_percent":
            previous_to_current >= 1.10,
        "success_retention_at_least_90_percent":
            success_retention >= 0.90,
        "gain_retention_at_least_90_percent":
            gain_retention >= 0.90,
        "false_laws_no_worse_than_parent":
            total_current_false
            <= total_previous_false,
        "verified_success_per_search_improves":
            success_efficiency_multiplier
            > 1.0,
    }
    passed = all(
        verdict_checks.values()
    )

    result = {
        "generations":
            generation_table,
        "total_current_search_cost":
            total_current_cost,
        "total_previous_search_cost":
            total_previous_cost,
        "total_cold_search_cost":
            total_cold_cost,
        "cold_to_current_reduction":
            cold_to_current,
        "previous_to_current_reduction":
            previous_to_current,
        "total_current_successes":
            total_current_success,
        "total_previous_successes":
            total_previous_success,
        "total_cold_successes":
            total_cold_success,
        "success_retention":
            success_retention,
        "total_current_false_laws":
            total_current_false,
        "total_previous_false_laws":
            total_previous_false,
        "total_cold_false_laws":
            total_cold_false,
        "gain_retention":
            gain_retention,
        "success_efficiency_multiplier":
            success_efficiency_multiplier,
        "gain_efficiency_multiplier":
            gain_efficiency_multiplier,
        "improved_cost_generations":
            improved_cost_generations,
        "verdict_checks":
            verdict_checks,
        "passed":
            passed,
        "total_cold_gain":
            total_cold_gain,
    }
    Path(
        "recursive-curve-summary.json"
    ).write_text(
        json.dumps(
            result,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )

    print(
        "REALITYGRAPH / "
        "RECURSIVE SELF-COMPILATION CURVE"
    )
    print(
        "-----------------------------------------------"
    )
    for row in generation_table:
        print(
            f"G{row['generation']} "
            f"range="
            f"{row['heldout_range'][0]}"
            f":{row['heldout_range'][1]} "
            f"cold_reduction="
            f"{row['cold_to_current_reduction']:.2f}x "
            f"parent_reduction="
            f"{row['previous_to_current_reduction']:.2f}x "
            f"success="
            f"{row['current_successes']}/20 "
            f"parent_success="
            f"{row['previous_successes']}/20 "
            f"false="
            f"{row['current_false_laws']} "
            f"parent_false="
            f"{row['previous_false_laws']} "
            f"success_eff="
            f"{row['success_efficiency_multiplier']:.2f}x"
        )

    print()
    print(
        f"total_cold_search_cost="
        f"{total_cold_cost}"
    )
    print(
        f"total_parent_search_cost="
        f"{total_previous_cost}"
    )
    print(
        f"total_recursive_search_cost="
        f"{total_current_cost}"
    )
    print(
        f"cold_to_recursive_reduction="
        f"{cold_to_current:.2f}x"
    )
    print(
        f"parent_to_recursive_reduction="
        f"{previous_to_current:.2f}x"
    )
    print(
        "sealed_successes "
        f"recursive={total_current_success}/60 "
        f"parent={total_previous_success}/60 "
        f"cold={total_cold_success}/60"
    )
    print(
        "false_laws "
        f"recursive={total_current_false} "
        f"parent={total_previous_false} "
        f"cold={total_cold_false}"
    )
    print(
        f"success_retention="
        f"{success_retention:.4f}"
    )
    print(
        f"gain_retention="
        f"{gain_retention:.4f}"
    )
    print(
        "verified_success_per_search_multiplier="
        f"{success_efficiency_multiplier:.2f}x"
    )
    print(
        "verified_gain_per_search_multiplier="
        f"{gain_efficiency_multiplier:.2f}x"
    )
    print(
        f"improved_cost_generations="
        f"{improved_cost_generations}/3"
    )
    for name, value in (
        verdict_checks.items()
    ):
        print(
            f"check_{name}={int(value)}"
        )

    if not passed:
        raise AssertionError(
            "recursive self-compilation "
            "did not satisfy frozen verdict"
        )

    print("VERDICT")
    print(
        "VERIFIED_RECURSIVE_SELF_COMPILATION_"
        "IMPROVES_FUTURE_CONSEQUENCE_PER_SEARCH"
    )


if __name__ == "__main__":
    main()
