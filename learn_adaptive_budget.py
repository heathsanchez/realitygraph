from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path

from realitygraph.adaptive_policy import (
    FEATURE_NAMES,
    MetaBudgetPolicy,
    adaptive_memory,
    budget_features,
    fit_budget_regressor,
)
from realitygraph.meta_policy import policy_from_memory
from realitygraph.mg import MG


FOLD_SEED = "realitygraph-meta-budget-crossfit-v1"
MARGINS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0)


def _load_worlds(root: Path):
    files = sorted(root.rglob("pmlb-world-*.json"))
    rows = [json.loads(path.read_text()) for path in files]
    rows.sort(key=lambda row: row["index"])
    return rows


def _order(policy, world):
    return sorted(
        world["candidates"],
        key=lambda item: (
            -policy.score(tuple(item["descriptors"])),
            item["feature"],
        ),
    )


def _choose(order, budget):
    selected = order[: min(budget, len(order))]
    return max(
        selected,
        key=lambda item: (item["cal_gain"], -item["feature"]),
    )


def _target_budget(policy, world, max_budget):
    order = _order(policy, world)
    reference = _choose(order, max_budget)
    reference_gain = (
        reference["test_gain"]
        if reference["cal_gain"] > 1e-4
        else 0.0
    )

    if reference_gain <= 1e-4:
        return 1

    threshold = max(
        0.95 * reference_gain,
        reference_gain - 0.01,
        1e-4,
    )
    for budget in range(1, max_budget + 1):
        candidate = _choose(order, budget)
        gain = (
            candidate["test_gain"]
            if candidate["cal_gain"] > 1e-4
            else 0.0
        )
        if gain >= threshold:
            return budget
    return max_budget


def _fold(index):
    digest = hashlib.sha256(
        f"{FOLD_SEED}|{index}".encode()
    ).digest()
    return int.from_bytes(digest[:4], "big") % 5


def _fit(examples, targets, indices):
    rows = [examples[i] for i in indices]
    ys = [targets[i] for i in indices]
    return fit_budget_regressor(rows, ys, ridge=1.0)


def _predict(model, row):
    means, scales, weights, intercept = model
    z = [
        (value - mean) / scale
        for value, mean, scale in zip(row, means, scales)
    ]
    return intercept + sum(
        weight * value for weight, value in zip(weights, z)
    )


def _metrics(policy, worlds, budgets):
    successes = 0
    false_laws = 0
    gains = []
    cost = 0
    reference_cost = 0
    reference_success = 0
    reference_false = 0
    reference_gains = []

    for world, budget in zip(worlds, budgets):
        order = _order(policy, world)
        candidate = _choose(order, budget)
        reference = _choose(order, policy.budget)

        cost += sum(
            item["threshold_evals"]
            for item in order[:budget]
        )
        reference_cost += sum(
            item["threshold_evals"]
            for item in order[:policy.budget]
        )

        accepted = candidate["cal_gain"] > 1e-4
        ok = accepted and candidate["test_gain"] > 1e-4
        false = accepted and not ok
        successes += int(ok)
        false_laws += int(false)
        gains.append(
            candidate["test_gain"] if accepted else 0.0
        )

        r_accepted = reference["cal_gain"] > 1e-4
        r_ok = r_accepted and reference["test_gain"] > 1e-4
        r_false = r_accepted and not r_ok
        reference_success += int(r_ok)
        reference_false += int(r_false)
        reference_gains.append(
            reference["test_gain"] if r_accepted else 0.0
        )

    mean_gain = sum(gains) / len(gains)
    reference_mean = sum(reference_gains) / len(reference_gains)
    return {
        "cost": cost,
        "reference_cost": reference_cost,
        "additional_reduction": (
            reference_cost / max(cost, 1)
        ),
        "successes": successes,
        "false_laws": false_laws,
        "mean_gain": mean_gain,
        "reference_successes": reference_success,
        "reference_false_laws": reference_false,
        "reference_mean_gain": reference_mean,
        "success_retention": (
            successes / max(reference_success, 1)
        ),
        "gain_ratio": (
            mean_gain / max(reference_mean, 1e-12)
            if reference_mean > 0
            else 1.0
        ),
    }


def main():
    train_root = Path(
        os.environ.get(
            "REALITYGRAPH_META_TRAIN_DIR",
            "gathered-meta-train",
        )
    )
    policy_dir = Path(
        os.environ.get(
            "REALITYGRAPH_META_POLICY_DIR",
            "meta-policy-out",
        )
    )

    worlds = _load_worlds(train_root)
    if len(worlds) != 100:
        raise AssertionError(
            f"expected 100 training worlds, got {len(worlds)}"
        )
    if any(
        world["role"] != "train" or world["index"] >= 100
        for world in worlds
    ):
        raise AssertionError("held-out world leaked into budget training")

    base_text = (policy_dir / "meta_policy.mg").read_text()
    base_sha = hashlib.sha256(base_text.encode()).hexdigest()
    base_memory = MG.parse(base_text)
    policy = policy_from_memory(base_memory)
    if policy.training_worlds != 100:
        raise AssertionError("base policy training count drift")

    examples = [
        budget_features(policy, world)
        for world in worlds
    ]
    targets = [
        float(_target_budget(policy, world, policy.budget))
        for world in worlds
    ]

    folds = [_fold(world["index"]) for world in worlds]
    oof = [None] * len(worlds)
    for fold in range(5):
        train_indices = [
            i for i, value in enumerate(folds)
            if value != fold
        ]
        test_indices = [
            i for i, value in enumerate(folds)
            if value == fold
        ]
        model = _fit(examples, targets, train_indices)
        for i in test_indices:
            oof[i] = _predict(model, examples[i])

    if any(value is None for value in oof):
        raise AssertionError("incomplete budget cross-fit")

    margin_table = []
    chosen_margin = None
    chosen_metrics = None
    for margin in MARGINS:
        budgets = [
            max(
                1,
                min(
                    policy.budget,
                    int(__import__("math").ceil(value + margin)),
                ),
            )
            for value in oof
        ]
        metrics = _metrics(policy, worlds, budgets)
        row = {
            "margin": margin,
            "mean_budget": sum(budgets) / len(budgets),
            **metrics,
        }
        margin_table.append(row)
        if (
            chosen_margin is None
            and metrics["success_retention"] >= 0.95
            and metrics["gain_ratio"] >= 0.95
            and metrics["false_laws"]
            <= metrics["reference_false_laws"]
        ):
            chosen_margin = margin
            chosen_metrics = row

    if chosen_margin is None:
        chosen_margin = MARGINS[-1]
        chosen_metrics = margin_table[-1]

    means, scales, weights, intercept = fit_budget_regressor(
        examples,
        targets,
        ridge=1.0,
    )
    budget_policy = MetaBudgetPolicy(
        FEATURE_NAMES,
        means,
        scales,
        weights,
        intercept,
        chosen_margin,
        policy.budget,
        len(worlds),
        base_sha,
    )

    provenance = hashlib.sha256(
        (
            base_sha
            + "|"
            + ",".join(f"{value:.12g}" for value in weights)
            + f"|intercept={intercept:.12g}"
            + f"|margin={chosen_margin:.12g}"
        ).encode()
    ).hexdigest()[:12]
    memory = adaptive_memory(
        base_memory,
        budget_policy,
        provenance,
    )
    (policy_dir / "adaptive_policy.mg").write_text(
        memory.text()
    )
    (policy_dir / "budget_policy.json").write_text(
        json.dumps(
            {
                "feature_names": FEATURE_NAMES,
                "means": means,
                "scales": scales,
                "weights": weights,
                "intercept": intercept,
                "safety_margin": chosen_margin,
                "max_budget": policy.budget,
                "training_worlds": len(worlds),
                "base_policy_sha256": base_sha,
                "target_budget_counts": dict(
                    sorted(Counter(int(x) for x in targets).items())
                ),
                "margin_table": margin_table,
                "chosen_metrics": chosen_metrics,
                "provenance": provenance,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )

    print("REALITYGRAPH / ADAPTIVE SEARCH-BUDGET COMPILATION")
    print("------------------------------------------------")
    print(f"training_worlds={len(worlds)}")
    print(f"base_policy_sha256={base_sha}")
    print(f"budget_feature_names={list(FEATURE_NAMES)}")
    print(
        "target_budget_counts="
        f"{dict(sorted(Counter(int(x) for x in targets).items()))}"
    )
    print(
        f"budget_weights={[round(value, 6) for value in weights]}"
    )
    print(f"budget_intercept={intercept:.6f}")
    print(f"learned_safety_margin={chosen_margin:.2f}")
    print(
        f"crossfit_mean_budget={chosen_metrics['mean_budget']:.3f} "
        f"additional_reduction={chosen_metrics['additional_reduction']:.2f}x"
    )
    print(
        f"crossfit_successes={chosen_metrics['successes']}/100 "
        f"reference={chosen_metrics['reference_successes']}/100 "
        f"false_laws={chosen_metrics['false_laws']} "
        f"reference_false={chosen_metrics['reference_false_laws']}"
    )
    print(
        f"crossfit_gain_ratio={chosen_metrics['gain_ratio']:.4f} "
        f"success_retention={chosen_metrics['success_retention']:.4f}"
    )
    print(
        f"adaptive_mg_bytes={len(memory.text().encode())}"
    )
    print("ADAPTIVE_BUDGET_COMPILED_FROM_PAST_CONSEQUENCE_ONLY")


if __name__ == "__main__":
    main()
