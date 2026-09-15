from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path

from realitygraph.adaptive_policy import (
    budget_features,
    budget_from_memory,
)
from realitygraph.meta_policy import policy_from_memory
from realitygraph.mg import MG
from realitygraph.recursive_policy import (
    recursive_budget_features,
    recursive_from_memory,
    recursive_order,
    recursive_trust_features,
)


def _load_worlds(root: Path):
    files = sorted(
        root.rglob("pmlb-regression-world-*.json")
    )
    rows = [
        json.loads(path.read_text())
        for path in files
    ]
    rows.sort(key=lambda row: row["index"])
    return rows


def _choose(order, budget):
    selected = order[
        : min(budget, len(order))
    ]
    best = max(
        selected,
        key=lambda item: (
            item["cal_gain"],
            -item["feature"],
        ),
    )
    cost = sum(
        item["threshold_evals"]
        for item in selected
    )
    return best, selected, cost


def _apply(memory: MG, world: dict):
    base = policy_from_memory(memory)
    recursive = recursive_from_memory(memory)

    if recursive is None:
        budget_policy = budget_from_memory(
            memory
        )
        order = sorted(
            world["candidates"],
            key=lambda item: (
                -base.score(
                    tuple(
                        item["descriptors"]
                    )
                ),
                item["feature"],
            ),
        )
        budget = (
            budget_policy.choose_budget(
                budget_features(
                    base,
                    world,
                )
            )
        )
        best, selected, cost = _choose(
            order,
            budget,
        )
        accepted = (
            best["cal_gain"] > 1e-4
        )
        trust_score = None
        trust_pass = True
    else:
        order = recursive_order(
            recursive,
            base,
            world,
        )
        budget = recursive.choose_budget(
            recursive_budget_features(
                recursive,
                base,
                world,
            )
        )
        best, selected, cost = _choose(
            order,
            budget,
        )
        features = (
            recursive_trust_features(
                recursive,
                base,
                world,
                selected,
                best,
                budget,
            )
        )
        trust_score = (
            recursive.trust_score(
                features
            )
        )
        trust_pass = (
            trust_score
            >= recursive.trust_threshold
        )
        accepted = (
            best["cal_gain"] > 1e-4
            and trust_pass
        )

    success = (
        accepted
        and best["test_gain"] > 1e-4
    )
    false = accepted and not success
    gain = (
        best["test_gain"]
        if accepted
        else 0.0
    )
    return {
        "best": best,
        "selected": selected,
        "budget": budget,
        "cost": cost,
        "accepted": accepted,
        "success": success,
        "false": false,
        "gain": gain,
        "trust_score": trust_score,
        "trust_pass": trust_pass,
    }


def _cold(world):
    best = max(
        world["candidates"],
        key=lambda item: (
            item["cal_gain"],
            -item["feature"],
        ),
    )
    accepted = best["cal_gain"] > 1e-4
    success = (
        accepted
        and best["test_gain"] > 1e-4
    )
    false = accepted and not success
    return {
        "best": best,
        "cost": world[
            "cold_search_cost"
        ],
        "accepted": accepted,
        "success": success,
        "false": false,
        "gain": (
            best["test_gain"]
            if accepted
            else 0.0
        ),
    }


def _random(
    memory: MG,
    world: dict,
    budget: int,
):
    base = policy_from_memory(memory)
    order = sorted(
        world["candidates"],
        key=lambda item: (
            hashlib.sha256(
                (
                    f"{base.corpus_digest}"
                    f"|recursive-random|"
                    f"{world['index']}|"
                    f"{item['feature']}"
                ).encode()
            ).digest(),
            item["feature"],
        ),
    )
    best, selected, cost = _choose(
        order,
        budget,
    )
    accepted = best["cal_gain"] > 1e-4
    success = (
        accepted
        and best["test_gain"] > 1e-4
    )
    false = accepted and not success
    return {
        "best": best,
        "selected": selected,
        "cost": cost,
        "accepted": accepted,
        "success": success,
        "false": false,
        "gain": (
            best["test_gain"]
            if accepted
            else 0.0
        ),
    }


def _aggregate(rows, key):
    return sum(row[key] for row in rows)


def main():
    root = Path(
        os.environ[
            "REALITYGRAPH_RECURSIVE_WORLD_DIR"
        ]
    )
    current_path = Path(
        os.environ[
            "REALITYGRAPH_RECURSIVE_CURRENT_MEMORY"
        ]
    )
    parent_path = Path(
        os.environ[
            "REALITYGRAPH_RECURSIVE_PARENT_MEMORY"
        ]
    )
    summary_path = Path(
        os.environ[
            "REALITYGRAPH_RECURSIVE_SUMMARY"
        ]
    )
    generation = int(
        os.environ[
            "REALITYGRAPH_RECURSIVE_GENERATION"
        ]
    )
    start = int(
        os.environ[
            "REALITYGRAPH_RECURSIVE_START"
        ]
    )
    end = int(
        os.environ[
            "REALITYGRAPH_RECURSIVE_END"
        ]
    )

    worlds = _load_worlds(root)
    if (
        len(worlds) != end - start
        or end - start != 20
    ):
        raise AssertionError(
            "recursive generation must "
            "contain exactly 20 worlds"
        )
    if [
        world["index"] for world in worlds
    ] != list(range(start, end)):
        raise AssertionError(
            "recursive generation index drift"
        )
    if any(
        world["role"]
        != "heldout-regression"
        or world["source_task"]
        != "regression"
        for world in worlds
    ):
        raise AssertionError(
            "recursive generation corpus drift"
        )

    current_text = (
        current_path.read_text()
    )
    parent_text = (
        parent_path.read_text()
    )
    current_sha = hashlib.sha256(
        current_text.encode()
    ).hexdigest()
    parent_sha = hashlib.sha256(
        parent_text.encode()
    ).hexdigest()
    current_memory = MG.parse(
        current_text
    )
    parent_memory = MG.parse(
        parent_text
    )
    recursive = recursive_from_memory(
        current_memory
    )
    if recursive is None:
        raise AssertionError(
            "current memory lacks recursive law"
        )
    if recursive.generation != generation:
        raise AssertionError(
            "recursive generation label drift"
        )
    if (
        recursive.parent_sha256
        != parent_sha
    ):
        raise AssertionError(
            "recursive parent chain broken"
        )
    if (
        recursive.training_worlds
        != start - 20
    ):
        raise AssertionError(
            "fresh generation was visible "
            "to recursive compiler"
        )

    rows = []
    winner_hits = 0
    positive_cold = 0
    budgets = []

    print(
        "REALITYGRAPH / "
        "SEALED RECURSIVE GENERATION"
    )
    print(
        "------------------------------------------"
    )
    print(f"generation={generation}")
    print(
        f"heldout_range={start}:{end}"
    )
    print(
        f"parent_sha256={parent_sha}"
    )
    print(
        f"current_sha256={current_sha}"
    )
    print(
        "compiled_from_past_worlds="
        f"{recursive.training_worlds}"
    )
    print(
        "future_generation_training_examples_seen=0"
    )
    print(
        "heldout_dataset_names_used_by_policy=0"
    )
    print()

    for world in worlds:
        current = _apply(
            current_memory,
            world,
        )
        previous = _apply(
            parent_memory,
            world,
        )
        cold = _cold(world)
        random = _random(
            current_memory,
            world,
            current["budget"],
        )
        budgets.append(
            current["budget"]
        )

        if (
            cold["best"]["cal_gain"]
            > 1e-4
        ):
            positive_cold += 1
            winner_hits += int(
                any(
                    item["feature"]
                    == world[
                        "cold_best_feature"
                    ]
                    for item
                    in current["selected"]
                )
            )

        row = {
            "index": world["index"],
            "dataset": world["dataset"],
            "features": world["features"],
            "budget": current["budget"],
            "current_cost":
                current["cost"],
            "previous_cost":
                previous["cost"],
            "cold_cost":
                cold["cost"],
            "random_cost":
                random["cost"],
            "current_success":
                int(current["success"]),
            "previous_success":
                int(previous["success"]),
            "cold_success":
                int(cold["success"]),
            "random_success":
                int(random["success"]),
            "current_false":
                int(current["false"]),
            "previous_false":
                int(previous["false"]),
            "cold_false":
                int(cold["false"]),
            "random_false":
                int(random["false"]),
            "current_gain":
                current["gain"],
            "previous_gain":
                previous["gain"],
            "cold_gain":
                cold["gain"],
            "random_gain":
                random["gain"],
            "current_feature":
                current["best"]["feature"],
            "previous_feature":
                previous["best"]["feature"],
            "cold_feature":
                cold["best"]["feature"],
            "trust_score":
                current["trust_score"],
            "trust_pass":
                current["trust_pass"],
        }
        rows.append(row)

        status = (
            "OK"
            if current["success"]
            else (
                "FALSE"
                if current["false"]
                else "UNKNOWN"
            )
        )
        print(
            f"{world['index']:03d} "
            f"{world['dataset'][:22]:22} "
            f"F={world['features']:2d} "
            f"budget={current['budget']} "
            f"search={cold['cost']:3d}"
            f"->{previous['cost']:3d}"
            f"->{current['cost']:3d} "
            f"gain={current['gain']:+.4f} "
            f"status={status}"
        )

    n = len(rows)
    current_cost = _aggregate(
        rows,
        "current_cost",
    )
    previous_cost = _aggregate(
        rows,
        "previous_cost",
    )
    cold_cost = _aggregate(
        rows,
        "cold_cost",
    )
    random_cost = _aggregate(
        rows,
        "random_cost",
    )
    current_success = _aggregate(
        rows,
        "current_success",
    )
    previous_success = _aggregate(
        rows,
        "previous_success",
    )
    cold_success = _aggregate(
        rows,
        "cold_success",
    )
    random_success = _aggregate(
        rows,
        "random_success",
    )
    current_false = _aggregate(
        rows,
        "current_false",
    )
    previous_false = _aggregate(
        rows,
        "previous_false",
    )
    cold_false = _aggregate(
        rows,
        "cold_false",
    )
    random_false = _aggregate(
        rows,
        "random_false",
    )
    current_gain = (
        _aggregate(
            rows,
            "current_gain",
        )
        / n
    )
    previous_gain = (
        _aggregate(
            rows,
            "previous_gain",
        )
        / n
    )
    cold_gain = (
        _aggregate(
            rows,
            "cold_gain",
        )
        / n
    )
    random_gain = (
        _aggregate(
            rows,
            "random_gain",
        )
        / n
    )
    budget_counts = dict(
        sorted(Counter(budgets).items())
    )

    summary = {
        "generation": generation,
        "heldout_range": [
            start,
            end,
        ],
        "parent_sha256": parent_sha,
        "current_sha256": current_sha,
        "current_memory_bytes":
            len(current_text.encode()),
        "compiled_from_past_worlds":
            recursive.training_worlds,
        "current_search_cost":
            current_cost,
        "previous_search_cost":
            previous_cost,
        "cold_search_cost":
            cold_cost,
        "random_search_cost":
            random_cost,
        "cold_to_current_reduction":
            cold_cost
            / max(current_cost, 1),
        "previous_to_current_reduction":
            previous_cost
            / max(current_cost, 1),
        "current_successes":
            current_success,
        "previous_successes":
            previous_success,
        "cold_successes":
            cold_success,
        "random_successes":
            random_success,
        "current_false_laws":
            current_false,
        "previous_false_laws":
            previous_false,
        "cold_false_laws":
            cold_false,
        "random_false_laws":
            random_false,
        "current_mean_gain":
            current_gain,
        "previous_mean_gain":
            previous_gain,
        "cold_mean_gain":
            cold_gain,
        "random_mean_gain":
            random_gain,
        "mean_budget":
            sum(budgets) / n,
        "budget_counts":
            budget_counts,
        "cold_winner_in_current_budget":
            winner_hits
            / max(positive_cold, 1),
        "per_world": rows,
    }
    summary_path.write_text(
        json.dumps(
            summary,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )

    print()
    print("AGGREGATE")
    print(
        f"cold_search_cost={cold_cost}"
    )
    print(
        "previous_memory_search_cost="
        f"{previous_cost}"
    )
    print(
        "current_memory_search_cost="
        f"{current_cost}"
    )
    print(
        "cold_to_current_reduction="
        f"{summary['cold_to_current_reduction']:.2f}x"
    )
    print(
        "previous_to_current_reduction="
        f"{summary['previous_to_current_reduction']:.2f}x"
    )
    print(
        f"mean_budget="
        f"{summary['mean_budget']:.3f}"
    )
    print(
        f"budget_counts={budget_counts}"
    )
    print(
        "cold_winner_in_current_budget="
        f"{summary['cold_winner_in_current_budget']:.4f}"
    )
    print(
        "sealed_successes "
        f"current={current_success}/20 "
        f"previous={previous_success}/20 "
        f"cold={cold_success}/20 "
        f"random={random_success}/20"
    )
    print(
        "false_laws "
        f"current={current_false} "
        f"previous={previous_false} "
        f"cold={cold_false} "
        f"random={random_false}"
    )
    print(
        "mean_sealed_gain "
        f"current={current_gain:.6f} "
        f"previous={previous_gain:.6f} "
        f"cold={cold_gain:.6f} "
        f"random={random_gain:.6f}"
    )
    print(
        "GENERATION_EVIDENCE_PRESERVED"
    )


if __name__ == "__main__":
    main()
