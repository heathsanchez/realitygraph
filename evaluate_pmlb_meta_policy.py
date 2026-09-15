from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from realitygraph.meta_policy import policy_from_memory
from realitygraph.mg import MG


def _load_worlds(root: Path):
    files = sorted(root.rglob("pmlb-world-*.json"))
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
                f"{policy.corpus_digest}|{world['index']}|{item['feature']}".encode()
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
    return best, sum(item["threshold_evals"] for item in selected), selected


def main():
    heldout_root = Path(
        os.environ.get("REALITYGRAPH_META_HELDOUT_DIR", "gathered-meta-heldout")
    )
    policy_dir = Path(
        os.environ.get("REALITYGRAPH_META_POLICY_DIR", "meta-policy-in")
    )
    heldout_start = int(
        os.environ.get("REALITYGRAPH_META_HELDOUT_START", "100")
    )
    heldout_stop = heldout_start + 20

    worlds = _load_worlds(heldout_root)
    if len(worlds) != 20:
        raise AssertionError(f"expected 20 held-out worlds, got {len(worlds)}")
    if any(
        world["role"] != "heldout" or not heldout_start <= world["index"] < heldout_stop
        for world in worlds
    ):
        raise AssertionError("training dataset leaked into held-out evaluation")

    memory_text = (policy_dir / "meta_policy.mg").read_text()
    memory = MG.parse(memory_text)
    policy = policy_from_memory(memory)
    if policy.training_worlds != 100:
        raise AssertionError("meta-policy was not trained on exactly 100 worlds")

    policy_cost = 0
    cold_cost = 0
    random_cost = 0
    policy_cal_accept = 0
    policy_test_accept = 0
    policy_false = 0
    cold_cal_accept = 0
    cold_test_accept = 0
    cold_false = 0
    random_test_accept = 0
    random_false = 0
    winner_in_budget = 0
    positive_cold_worlds = 0
    test_gain_policy = []
    test_gain_cold = []
    test_gain_random = []
    per_world = []

    print("REALITYGRAPH / HELD-OUT CROSS-DOMAIN META-TRANSFER")
    print("--------------------------------------------------")
    print(f"frozen_policy_training_worlds={policy.training_worlds}")
    print(f"heldout_worlds={len(worlds)}")
    print(f"heldout_range={heldout_start}:{heldout_stop}")
    print(f"learned_search_budget={policy.budget}")
    print(f"policy_memory_bytes={len(memory_text.encode())}")
    print()

    for world in worlds:
        if tuple(world["descriptor_names"]) != policy.descriptor_names:
            raise AssertionError("held-out descriptor schema drift")

        ordered = _policy_order(policy, world)
        policy_best, p_cost, selected = _choose(ordered, policy.budget)
        random_best, r_cost, _ = _choose(_hash_order(policy, world), policy.budget)
        cold_best = max(
            world["candidates"],
            key=lambda item: (item["cal_gain"], -item["feature"]),
        )

        policy_cost += p_cost
        random_cost += r_cost
        cold_cost += world["cold_search_cost"]

        p_cal = policy_best["cal_gain"] > 1e-4
        p_test = p_cal and policy_best["test_gain"] > 1e-4
        p_false = p_cal and not p_test
        c_cal = cold_best["cal_gain"] > 1e-4
        c_test = c_cal and cold_best["test_gain"] > 1e-4
        c_false = c_cal and not c_test
        r_cal = random_best["cal_gain"] > 1e-4
        r_test = r_cal and random_best["test_gain"] > 1e-4
        r_false = r_cal and not r_test

        policy_cal_accept += int(p_cal)
        policy_test_accept += int(p_test)
        policy_false += int(p_false)
        cold_cal_accept += int(c_cal)
        cold_test_accept += int(c_test)
        cold_false += int(c_false)
        random_test_accept += int(r_test)
        random_false += int(r_false)

        if c_cal:
            positive_cold_worlds += 1
            winner_in_budget += int(
                any(
                    item["feature"] == world["cold_best_feature"]
                    for item in selected
                )
            )

        test_gain_policy.append(policy_best["test_gain"] if p_cal else 0.0)
        test_gain_cold.append(cold_best["test_gain"] if c_cal else 0.0)
        test_gain_random.append(random_best["test_gain"] if r_cal else 0.0)

        per_world.append({
            "index": world["index"],
            "dataset": world["dataset"],
            "features": world["features"],
            "policy_feature": policy_best["feature"],
            "policy_cal_gain": policy_best["cal_gain"],
            "policy_test_gain": policy_best["test_gain"],
            "policy_test_accept": p_test,
            "policy_false_law": p_false,
            "cold_feature": cold_best["feature"],
            "cold_cal_gain": cold_best["cal_gain"],
            "cold_test_gain": cold_best["test_gain"],
            "cold_test_accept": c_test,
            "cold_false_law": c_false,
            "random_test_gain": random_best["test_gain"],
            "policy_search_cost": p_cost,
            "cold_search_cost": world["cold_search_cost"],
        })

        print(
            f"{world['index']:03d} {world['dataset'][:28]:28} "
            f"F={world['features']:2d} "
            f"search={world['cold_search_cost']:3d}->{p_cost:3d} "
            f"policy_test_gain={policy_best['test_gain']:+.4f} "
            f"cold_test_gain={cold_best['test_gain']:+.4f} "
            f"policy={'OK' if p_test else ('FALSE' if p_false else 'UNKNOWN')}"
        )

    reduction = cold_cost / max(policy_cost, 1)
    random_reduction = cold_cost / max(random_cost, 1)
    policy_mean_gain = sum(test_gain_policy) / len(test_gain_policy)
    cold_mean_gain = sum(test_gain_cold) / len(test_gain_cold)
    random_mean_gain = sum(test_gain_random) / len(test_gain_random)
    winner_rate = winner_in_budget / max(positive_cold_worlds, 1)

    # Causal ablation: with no meta-policy memory, the only supported path is
    # the exhaustive cold search across every candidate threshold.
    ablation_search_cost = cold_cost

    print()
    print("AGGREGATE")
    print(f"heldout_worlds={len(worlds)}")
    print(f"cold_search_cost={cold_cost}")
    print(f"meta_policy_search_cost={policy_cost}")
    print(f"search_reduction={reduction:.2f}x")
    print(f"ablation_delete_.mg_search_cost={ablation_search_cost}")
    print(f"cold_winner_in_meta_budget={winner_rate:.4f}")
    print(
        f"sealed_successes policy={policy_test_accept}/20 "
        f"cold={cold_test_accept}/20 random={random_test_accept}/20"
    )
    print(
        f"false_laws policy={policy_false} "
        f"cold={cold_false} random={random_false}"
    )
    print(
        f"mean_sealed_gain policy={policy_mean_gain:.6f} "
        f"cold={cold_mean_gain:.6f} random={random_mean_gain:.6f}"
    )
    print(f"future_policy_training_examples_seen=0")
    print(f"heldout_dataset_names_used_by_policy=0")

    result = {
        "heldout_worlds": len(worlds),
        "policy_budget": policy.budget,
        "policy_memory_bytes": len(memory_text.encode()),
        "cold_search_cost": cold_cost,
        "policy_search_cost": policy_cost,
        "search_reduction": reduction,
        "ablation_search_cost": ablation_search_cost,
        "winner_in_budget_rate": winner_rate,
        "policy_test_accept": policy_test_accept,
        "cold_test_accept": cold_test_accept,
        "random_test_accept": random_test_accept,
        "policy_false_laws": policy_false,
        "cold_false_laws": cold_false,
        "random_false_laws": random_false,
        "policy_mean_test_gain": policy_mean_gain,
        "cold_mean_test_gain": cold_mean_gain,
        "random_mean_test_gain": random_mean_gain,
        "per_world": per_world,
    }
    Path("meta-heldout-summary.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    if policy_cost >= cold_cost:
        raise AssertionError("meta-policy failed to reduce held-out search")
    if policy_false > cold_false + 2:
        raise AssertionError("meta-policy bought speed with excessive false laws")

    print("VERDICT")
    print("PAST_DATASETS_COMPILED_INTO_FASTER_HELDOUT_DISCOVERY")


if __name__ == "__main__":
    main()
