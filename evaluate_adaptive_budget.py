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


def _load_worlds(root: Path):
    files = sorted(root.rglob("pmlb-regression-world-*.json"))
    rows = [json.loads(path.read_text()) for path in files]
    rows.sort(key=lambda row: row["index"])
    return rows


def _policy_order(policy, world):
    return sorted(
        world["candidates"],
        key=lambda item: (
            -policy.score(tuple(item["descriptors"])),
            item["feature"],
        ),
    )


def _hash_order(policy, world):
    return sorted(
        world["candidates"],
        key=lambda item: (
            hashlib.sha256(
                (
                    f"{policy.corpus_digest}|adaptive-random|"
                    f"{world['index']}|{item['feature']}"
                ).encode()
            ).digest(),
            item["feature"],
        ),
    )


def _choose(order, budget):
    selected = order[: min(budget, len(order))]
    best = max(
        selected,
        key=lambda item: (item["cal_gain"], -item["feature"]),
    )
    cost = sum(item["threshold_evals"] for item in selected)
    return best, cost, selected


def _status(item):
    accepted = item["cal_gain"] > 1e-4
    success = accepted and item["test_gain"] > 1e-4
    false = accepted and not success
    gain = item["test_gain"] if accepted else 0.0
    return accepted, success, false, gain


def main():
    root = Path(
        os.environ.get(
            "REALITYGRAPH_REGRESSION_HELDOUT_DIR",
            "gathered-meta-regression-next",
        )
    )
    policy_dir = Path(
        os.environ.get(
            "REALITYGRAPH_META_POLICY_DIR",
            "meta-policy-out",
        )
    )

    worlds = _load_worlds(root)
    if len(worlds) != 20:
        raise AssertionError(
            f"expected 20 next regression worlds, got {len(worlds)}"
        )
    if any(
        world["role"] != "heldout-regression"
        or world["source_task"] != "regression"
        or not 20 <= world["index"] < 40
        for world in worlds
    ):
        raise AssertionError("next regression corpus drift")

    base_text = (policy_dir / "meta_policy.mg").read_text()
    base_sha = hashlib.sha256(base_text.encode()).hexdigest()
    memory = MG.parse(
        (policy_dir / "adaptive_policy.mg").read_text()
    )
    policy = policy_from_memory(memory)
    budget_policy = budget_from_memory(memory)

    if budget_policy.base_policy_sha256 != base_sha:
        raise AssertionError("adaptive budget is linked to wrong base policy")
    if policy.training_worlds != 100:
        raise AssertionError("base policy training count drift")
    if budget_policy.training_worlds != 100:
        raise AssertionError("budget policy training count drift")

    cold_cost = 0
    fixed_cost = 0
    adaptive_cost = 0
    random_cost = 0

    cold_success = fixed_success = adaptive_success = random_success = 0
    cold_false = fixed_false = adaptive_false = random_false = 0
    cold_gains = []
    fixed_gains = []
    adaptive_gains = []
    random_gains = []
    budgets = []
    winner_hits = 0
    cold_positive = 0
    per_world = []

    print("REALITYGRAPH / ADAPTIVE EXPERIMENT-BUDGET TRANSFER")
    print("--------------------------------------------------")
    print("training_task=classification")
    print("heldout_task=next_regression_to_binary")
    print("heldout_range=20:40")
    print(f"base_policy_budget={policy.budget}")
    print(
        f"adaptive_memory_bytes="
        f"{len((policy_dir / 'adaptive_policy.mg').read_bytes())}"
    )
    print(f"base_policy_sha256={base_sha}")
    print("budget_chosen_before_candidate_threshold_tests=1")
    print()

    for world in worlds:
        if tuple(world["descriptor_names"]) != policy.descriptor_names:
            raise AssertionError("descriptor schema drift")

        order = _policy_order(policy, world)
        budget = budget_policy.choose_budget(
            budget_features(policy, world)
        )
        budgets.append(budget)

        adaptive_best, a_cost, selected = _choose(
            order, budget
        )
        fixed_best, f_cost, _ = _choose(
            order, policy.budget
        )
        random_best, r_cost, _ = _choose(
            _hash_order(policy, world),
            budget,
        )
        cold_best = max(
            world["candidates"],
            key=lambda item: (item["cal_gain"], -item["feature"]),
        )

        cold_cost += world["cold_search_cost"]
        fixed_cost += f_cost
        adaptive_cost += a_cost
        random_cost += r_cost

        _, a_ok, a_false, a_gain = _status(adaptive_best)
        _, f_ok, f_false, f_gain = _status(fixed_best)
        _, r_ok, r_false, r_gain = _status(random_best)
        _, c_ok, c_false, c_gain = _status(cold_best)

        adaptive_success += int(a_ok)
        fixed_success += int(f_ok)
        random_success += int(r_ok)
        cold_success += int(c_ok)
        adaptive_false += int(a_false)
        fixed_false += int(f_false)
        random_false += int(r_false)
        cold_false += int(c_false)
        adaptive_gains.append(a_gain)
        fixed_gains.append(f_gain)
        random_gains.append(r_gain)
        cold_gains.append(c_gain)

        if cold_best["cal_gain"] > 1e-4:
            cold_positive += 1
            winner_hits += int(
                any(
                    item["feature"] == world["cold_best_feature"]
                    for item in selected
                )
            )

        per_world.append({
            "index": world["index"],
            "dataset": world["dataset"],
            "features": world["features"],
            "adaptive_budget": budget,
            "adaptive_feature": adaptive_best["feature"],
            "adaptive_test_gain": adaptive_best["test_gain"],
            "adaptive_success": a_ok,
            "adaptive_false_law": a_false,
            "fixed_feature": fixed_best["feature"],
            "fixed_test_gain": fixed_best["test_gain"],
            "cold_feature": cold_best["feature"],
            "cold_test_gain": cold_best["test_gain"],
            "adaptive_search_cost": a_cost,
            "fixed_search_cost": f_cost,
            "cold_search_cost": world["cold_search_cost"],
        })

        print(
            f"{world['index']:03d} "
            f"{world['dataset'][:25]:25} "
            f"F={world['features']:2d} "
            f"budget={budget} "
            f"search={world['cold_search_cost']:3d}"
            f"->{f_cost:3d}->{a_cost:3d} "
            f"adaptive_gain={adaptive_best['test_gain']:+.4f} "
            f"fixed_gain={fixed_best['test_gain']:+.4f} "
            f"status={'OK' if a_ok else ('FALSE' if a_false else 'UNKNOWN')}"
        )

    adaptive_mean = sum(adaptive_gains) / len(adaptive_gains)
    fixed_mean = sum(fixed_gains) / len(fixed_gains)
    cold_mean = sum(cold_gains) / len(cold_gains)
    random_mean = sum(random_gains) / len(random_gains)
    cold_reduction = cold_cost / max(adaptive_cost, 1)
    extra_reduction = fixed_cost / max(adaptive_cost, 1)
    winner_rate = winner_hits / max(cold_positive, 1)
    budget_counts = dict(sorted(Counter(budgets).items()))

    print()
    print("AGGREGATE")
    print(f"cold_search_cost={cold_cost}")
    print(f"fixed_policy_search_cost={fixed_cost}")
    print(f"adaptive_policy_search_cost={adaptive_cost}")
    print(f"cold_to_adaptive_reduction={cold_reduction:.2f}x")
    print(f"fixed_to_adaptive_reduction={extra_reduction:.2f}x")
    print(f"delete_budget_law_search_cost={fixed_cost}")
    print(f"delete_all_.mg_search_cost={cold_cost}")
    print(f"mean_adaptive_budget={sum(budgets)/len(budgets):.3f}")
    print(f"adaptive_budget_counts={budget_counts}")
    print(f"cold_winner_in_adaptive_budget={winner_rate:.4f}")
    print(
        f"sealed_successes adaptive={adaptive_success}/20 "
        f"fixed={fixed_success}/20 "
        f"cold={cold_success}/20 random={random_success}/20"
    )
    print(
        f"false_laws adaptive={adaptive_false} "
        f"fixed={fixed_false} cold={cold_false} random={random_false}"
    )
    print(
        f"mean_sealed_gain adaptive={adaptive_mean:.6f} "
        f"fixed={fixed_mean:.6f} "
        f"cold={cold_mean:.6f} random={random_mean:.6f}"
    )
    print("future_budget_training_examples_seen=0")
    print("heldout_dataset_names_used_by_budget_policy=0")

    result = {
        "heldout_worlds": len(worlds),
        "heldout_range": [20, 40],
        "adaptive_memory_bytes": len(
            (policy_dir / "adaptive_policy.mg").read_bytes()
        ),
        "cold_search_cost": cold_cost,
        "fixed_policy_search_cost": fixed_cost,
        "adaptive_policy_search_cost": adaptive_cost,
        "cold_to_adaptive_reduction": cold_reduction,
        "fixed_to_adaptive_reduction": extra_reduction,
        "delete_budget_law_search_cost": fixed_cost,
        "delete_all_memory_search_cost": cold_cost,
        "mean_adaptive_budget": sum(budgets) / len(budgets),
        "adaptive_budget_counts": budget_counts,
        "winner_in_adaptive_budget_rate": winner_rate,
        "adaptive_test_accept": adaptive_success,
        "fixed_test_accept": fixed_success,
        "cold_test_accept": cold_success,
        "random_test_accept": random_success,
        "adaptive_false_laws": adaptive_false,
        "fixed_false_laws": fixed_false,
        "cold_false_laws": cold_false,
        "random_false_laws": random_false,
        "adaptive_mean_test_gain": adaptive_mean,
        "fixed_mean_test_gain": fixed_mean,
        "cold_mean_test_gain": cold_mean,
        "random_mean_test_gain": random_mean,
        "per_world": per_world,
    }
    Path("meta-adaptive-summary.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    if adaptive_cost >= fixed_cost:
        raise AssertionError(
            "adaptive budget failed to reduce fixed-policy search"
        )
    if adaptive_success < fixed_success - 2:
        raise AssertionError(
            "adaptive budget lost excessive sealed successes"
        )
    if adaptive_false > fixed_false + 2:
        raise AssertionError(
            "adaptive budget increased false laws excessively"
        )
    if fixed_mean > 1e-9 and adaptive_mean < 0.90 * fixed_mean:
        raise AssertionError(
            "adaptive budget lost excessive mean sealed gain"
        )

    print("VERDICT")
    print("PAST_CONSEQUENCE_COMPILED_INTO_ADAPTIVE_EXPERIMENT_BUDGET")


if __name__ == "__main__":
    main()
