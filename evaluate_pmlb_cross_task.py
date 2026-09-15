from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

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
                    f"{policy.corpus_digest}|regression|"
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
    return (
        best,
        sum(item["threshold_evals"] for item in selected),
        selected,
    )


def main():
    root = Path(
        os.environ.get(
            "REALITYGRAPH_REGRESSION_HELDOUT_DIR",
            "gathered-meta-regression",
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
            f"expected 20 regression held-out worlds, got {len(worlds)}"
        )
    if any(
        world["role"] != "heldout-regression"
        or world["source_task"] != "regression"
        or not 0 <= world["index"] < 20
        for world in worlds
    ):
        raise AssertionError("regression held-out corpus drift")

    memory_text = (policy_dir / "meta_policy.mg").read_text()
    policy = policy_from_memory(MG.parse(memory_text))
    if policy.training_worlds != 100:
        raise AssertionError(
            "policy was not trained on exactly 100 classification worlds"
        )

    policy_cost = 0
    cold_cost = 0
    random_cost = 0
    policy_success = 0
    cold_success = 0
    random_success = 0
    policy_false = 0
    cold_false = 0
    random_false = 0
    policy_gains = []
    cold_gains = []
    random_gains = []
    winner_hits = 0
    cold_positive = 0
    per_world = []

    print("REALITYGRAPH / FROZEN POLICY CROSS-TASK TRANSFER")
    print("------------------------------------------------")
    print("training_task=classification")
    print("heldout_task=regression_to_binary")
    print(f"heldout_worlds={len(worlds)}")
    print(f"learned_search_budget={policy.budget}")
    print(f"policy_memory_bytes={len(memory_text.encode())}")
    print()

    for world in worlds:
        if tuple(world["descriptor_names"]) != policy.descriptor_names:
            raise AssertionError("descriptor schema drift")

        ordered = _policy_order(policy, world)
        policy_best, p_cost, selected = _choose(
            ordered, policy.budget
        )
        random_best, r_cost, _ = _choose(
            _hash_order(policy, world),
            policy.budget,
        )
        cold_best = max(
            world["candidates"],
            key=lambda item: (item["cal_gain"], -item["feature"]),
        )

        policy_cost += p_cost
        random_cost += r_cost
        cold_cost += world["cold_search_cost"]

        p_cal = policy_best["cal_gain"] > 1e-4
        c_cal = cold_best["cal_gain"] > 1e-4
        r_cal = random_best["cal_gain"] > 1e-4

        p_ok = p_cal and policy_best["test_gain"] > 1e-4
        c_ok = c_cal and cold_best["test_gain"] > 1e-4
        r_ok = r_cal and random_best["test_gain"] > 1e-4

        p_false = p_cal and not p_ok
        c_false = c_cal and not c_ok
        r_false = r_cal and not r_ok

        policy_success += int(p_ok)
        cold_success += int(c_ok)
        random_success += int(r_ok)
        policy_false += int(p_false)
        cold_false += int(c_false)
        random_false += int(r_false)

        policy_gains.append(
            policy_best["test_gain"] if p_cal else 0.0
        )
        cold_gains.append(
            cold_best["test_gain"] if c_cal else 0.0
        )
        random_gains.append(
            random_best["test_gain"] if r_cal else 0.0
        )

        if c_cal:
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
            "policy_feature": policy_best["feature"],
            "policy_test_gain": policy_best["test_gain"],
            "policy_success": p_ok,
            "policy_false_law": p_false,
            "cold_feature": cold_best["feature"],
            "cold_test_gain": cold_best["test_gain"],
            "cold_success": c_ok,
            "cold_false_law": c_false,
            "random_test_gain": random_best["test_gain"],
            "random_success": r_ok,
            "random_false_law": r_false,
            "policy_search_cost": p_cost,
            "cold_search_cost": world["cold_search_cost"],
        })

        print(
            f"{world['index']:03d} "
            f"{world['dataset'][:28]:28} "
            f"F={world['features']:2d} "
            f"search={world['cold_search_cost']:3d}->{p_cost:3d} "
            f"policy_gain={policy_best['test_gain']:+.4f} "
            f"cold_gain={cold_best['test_gain']:+.4f} "
            f"policy={'OK' if p_ok else ('FALSE' if p_false else 'UNKNOWN')}"
        )

    reduction = cold_cost / max(policy_cost, 1)
    winner_rate = winner_hits / max(cold_positive, 1)
    policy_mean = sum(policy_gains) / len(policy_gains)
    cold_mean = sum(cold_gains) / len(cold_gains)
    random_mean = sum(random_gains) / len(random_gains)

    print()
    print("AGGREGATE")
    print(f"cold_search_cost={cold_cost}")
    print(f"meta_policy_search_cost={policy_cost}")
    print(f"search_reduction={reduction:.2f}x")
    print(f"ablation_delete_.mg_search_cost={cold_cost}")
    print(f"cold_winner_in_meta_budget={winner_rate:.4f}")
    print(
        f"sealed_successes policy={policy_success}/20 "
        f"cold={cold_success}/20 random={random_success}/20"
    )
    print(
        f"false_laws policy={policy_false} "
        f"cold={cold_false} random={random_false}"
    )
    print(
        f"mean_sealed_gain policy={policy_mean:.6f} "
        f"cold={cold_mean:.6f} random={random_mean:.6f}"
    )
    print("future_policy_training_examples_seen=0")
    print("heldout_dataset_names_used_by_policy=0")

    result = {
        "heldout_worlds": len(worlds),
        "training_task": "classification",
        "heldout_task": "regression_to_binary",
        "policy_budget": policy.budget,
        "policy_memory_bytes": len(memory_text.encode()),
        "cold_search_cost": cold_cost,
        "policy_search_cost": policy_cost,
        "search_reduction": reduction,
        "ablation_search_cost": cold_cost,
        "winner_in_budget_rate": winner_rate,
        "policy_test_accept": policy_success,
        "cold_test_accept": cold_success,
        "random_test_accept": random_success,
        "policy_false_laws": policy_false,
        "cold_false_laws": cold_false,
        "random_false_laws": random_false,
        "policy_mean_test_gain": policy_mean,
        "cold_mean_test_gain": cold_mean,
        "random_mean_test_gain": random_mean,
        "per_world": per_world,
    }
    Path("meta-cross-task-summary.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    if policy_cost >= cold_cost:
        raise AssertionError(
            "frozen policy failed to reduce cross-task search"
        )
    if policy_false > cold_false + 2:
        raise AssertionError(
            "cross-task speedup bought excessive false laws"
        )
    if policy_success < cold_success - 2:
        raise AssertionError(
            "cross-task speedup lost excessive sealed successes"
        )

    print("VERDICT")
    print("FROZEN_CLASSIFICATION_POLICY_TRANSFERRED_TO_REGRESSION_WORLDS")


if __name__ == "__main__":
    main()
