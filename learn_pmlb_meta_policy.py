from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from realitygraph.meta_policy import (
    MetaSearchPolicy,
    fit_ridge_ranker,
    policy_memory,
)


def _load_worlds(root: Path):
    files = sorted(root.rglob("pmlb-world-*.json"))
    rows = [json.loads(path.read_text()) for path in files]
    rows.sort(key=lambda row: row["index"])
    return rows


def _rank_targets(candidates):
    ordered = sorted(
        candidates,
        key=lambda item: (item["test_gain"], -item["feature"]),
    )
    n = len(ordered)
    target = {}
    for rank, item in enumerate(ordered):
        target[item["feature"]] = rank / max(n - 1, 1)
    return target


def _score_order(policy, world):
    return sorted(
        world["candidates"],
        key=lambda item: (
            -policy.score(tuple(item["descriptors"])),
            item["feature"],
        ),
    )


def _budget_stats(policy, worlds, budget):
    ratios = []
    positive_hits = 0
    eligible = 0
    winner_hits = 0
    costs = []
    cold_costs = []

    for world in worlds:
        ordered = _score_order(policy, world)
        k = min(budget, len(ordered))
        selected = ordered[:k]
        best = max(
            selected,
            key=lambda item: (item["cal_gain"], -item["feature"]),
        )
        cold_gain = world["cold_best_cal_gain"]
        if cold_gain > 1e-4:
            eligible += 1
            ratio = max(best["cal_gain"], 0.0) / max(cold_gain, 1e-12)
            ratios.append(ratio)
            positive_hits += int(best["cal_gain"] > 1e-4)
            winner_hits += int(
                any(
                    item["feature"] == world["cold_best_feature"]
                    for item in selected
                )
            )
        costs.append(sum(item["threshold_evals"] for item in selected))
        cold_costs.append(world["cold_search_cost"])

    mean_ratio = sum(ratios) / len(ratios) if ratios else 1.0
    positive_rate = positive_hits / eligible if eligible else 1.0
    winner_rate = winner_hits / eligible if eligible else 1.0
    mean_cost = sum(costs) / len(costs)
    mean_cold = sum(cold_costs) / len(cold_costs)
    reduction = mean_cold / max(mean_cost, 1e-12)
    return {
        "budget": budget,
        "eligible": eligible,
        "mean_gain_ratio": mean_ratio,
        "positive_hit_rate": positive_rate,
        "cold_winner_in_budget_rate": winner_rate,
        "mean_policy_search_cost": mean_cost,
        "mean_cold_search_cost": mean_cold,
        "search_reduction": reduction,
    }


def main():
    root = Path(os.environ.get("REALITYGRAPH_META_TRAIN_DIR", "gathered-meta-train"))
    out_dir = Path(os.environ.get("REALITYGRAPH_META_POLICY_DIR", "meta-policy-out"))
    out_dir.mkdir(parents=True, exist_ok=True)

    worlds = _load_worlds(root)
    if len(worlds) != 100:
        raise AssertionError(f"expected 100 training worlds, got {len(worlds)}")
    if any(world["role"] != "train" or world["index"] >= 100 for world in worlds):
        raise AssertionError("held-out PMLB world leaked into policy training")

    descriptor_names = tuple(worlds[0]["descriptor_names"])
    examples = []
    targets = []
    source_rows = []

    for world in worlds:
        if tuple(world["descriptor_names"]) != descriptor_names:
            raise AssertionError("descriptor schema drift")
        ranks = _rank_targets(world["candidates"])
        for item in world["candidates"]:
            examples.append(tuple(float(x) for x in item["descriptors"]))
            targets.append(ranks[item["feature"]])
        source_rows.append(
            f"{world['index']}|{world['dataset']}|{world['source_sha256']}"
        )

    means, scales, weights = fit_ridge_ranker(examples, targets, ridge=0.1)
    corpus_digest = hashlib.sha256(
        "\n".join(source_rows).encode()
    ).hexdigest()[:20]

    provisional = MetaSearchPolicy(
        descriptor_names,
        means,
        scales,
        weights,
        1,
        len(worlds),
        corpus_digest,
    )

    budget_table = []
    chosen_budget = None
    for budget in range(1, 13):
        stats = _budget_stats(provisional, worlds, budget)
        budget_table.append(stats)
        if (
            chosen_budget is None
            and stats["positive_hit_rate"] >= 0.90
            and stats["mean_gain_ratio"] >= 0.90
        ):
            chosen_budget = budget
    if chosen_budget is None:
        chosen_budget = 12

    policy = MetaSearchPolicy(
        descriptor_names,
        means,
        scales,
        weights,
        chosen_budget,
        len(worlds),
        corpus_digest,
    )
    chosen_stats = _budget_stats(policy, worlds, chosen_budget)

    provenance = hashlib.sha256(
        (
            corpus_digest
            + "|"
            + ",".join(f"{weight:.12g}" for weight in weights)
            + f"|budget={chosen_budget}"
        ).encode()
    ).hexdigest()[:12]
    memory = policy_memory(policy, provenance)

    (out_dir / "meta_policy.mg").write_text(memory.text())
    (out_dir / "policy.json").write_text(
        json.dumps(
            {
                "descriptor_names": descriptor_names,
                "means": means,
                "scales": scales,
                "weights": weights,
                "budget": chosen_budget,
                "training_worlds": len(worlds),
                "corpus_digest": corpus_digest,
                "provenance": provenance,
                "budget_table": budget_table,
                "chosen_stats": chosen_stats,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )

    print("REALITYGRAPH / 100-WORLD META-POLICY COMPILATION")
    print("------------------------------------------------")
    print(f"training_worlds={len(worlds)}")
    print(f"training_feature_examples={len(examples)}")
    print(f"descriptor_names={list(descriptor_names)}")
    print(f"learned_weights={[round(weight, 6) for weight in weights]}")
    print(f"learned_budget={chosen_budget}")
    print(
        f"training_positive_hit_rate={chosen_stats['positive_hit_rate']:.4f} "
        f"mean_gain_ratio={chosen_stats['mean_gain_ratio']:.4f}"
    )
    print(
        f"training_search_reduction={chosen_stats['search_reduction']:.2f}x "
        f"winner_in_budget={chosen_stats['cold_winner_in_budget_rate']:.4f}"
    )
    print(f"corpus_digest={corpus_digest}")
    print(f".mg_bytes={len(memory.text().encode())}")
    print("POLICY_COMPILED_BEFORE_HELDOUT_DATASETS")


if __name__ == "__main__":
    main()
