from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path

from realitygraph.meta_policy import fit_ridge_ranker, policy_from_memory
from realitygraph.mg import MG
from realitygraph.recursive_policy import (
    BUDGET_FEATURE_NAMES,
    TRUST_FEATURE_NAMES,
    RecursiveSearchPolicy,
    fit_ridge_with_intercept,
    recursive_budget_features,
    recursive_memory,
    recursive_order,
    recursive_trust_features,
)


ALPHAS = (0.0, 0.25, 0.5, 0.75, 1.0)
MARGINS = (0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
FOLD_SEED = "realitygraph-recursive-self-compile-v1"


def _load_worlds(spec: str):
    roots = [Path(value) for value in spec.split(os.pathsep) if value]
    rows = []
    seen = set()
    for root in roots:
        for path in sorted(
            root.rglob("pmlb-regression-world-*.json")
        ):
            world = json.loads(path.read_text())
            if world["index"] in seen:
                continue
            seen.add(world["index"])
            rows.append(world)
    rows.sort(key=lambda row: row["index"])
    return rows


def _rank_targets(candidates):
    ordered = sorted(
        candidates,
        key=lambda item: (item["test_gain"], -item["feature"]),
    )
    n = len(ordered)
    return {
        item["feature"]: rank / max(n - 1, 1)
        for rank, item in enumerate(ordered)
    }


def _fit_rank(worlds):
    examples, targets = [], []
    for world in worlds:
        ranks = _rank_targets(world["candidates"])
        for item in world["candidates"]:
            examples.append(
                tuple(float(x) for x in item["descriptors"])
            )
            targets.append(ranks[item["feature"]])
    return fit_ridge_ranker(examples, targets, ridge=0.1)


def _task_score(model, descriptors):
    means, scales, weights = model
    z = [
        (float(value) - mean) / scale
        for value, mean, scale in zip(
            descriptors, means, scales
        )
    ]
    return sum(
        weight * value for weight, value in zip(weights, z)
    )


def _fold(index):
    digest = hashlib.sha256(
        f"{FOLD_SEED}|{index}".encode()
    ).digest()
    return int.from_bytes(digest[:4], "big") % 5


def _choose_rank_blend(base, worlds):
    fold_map = [_fold(world["index"]) for world in worlds]
    stats = {alpha: [] for alpha in ALPHAS}
    for fold in range(5):
        train = [
            world
            for world, value in zip(worlds, fold_map)
            if value != fold
        ]
        test = [
            world
            for world, value in zip(worlds, fold_map)
            if value == fold
        ]
        if not train or not test:
            continue
        model = _fit_rank(train)
        for world in test:
            verified_best = max(
                world["candidates"],
                key=lambda item: (
                    item["test_gain"],
                    -item["feature"],
                ),
            )
            n = max(len(world["candidates"]) - 1, 1)
            for alpha in ALPHAS:
                order = sorted(
                    world["candidates"],
                    key=lambda item: (
                        -(
                            (1.0 - alpha)
                            * base.score(
                                tuple(item["descriptors"])
                            )
                            + alpha
                            * _task_score(
                                model,
                                tuple(item["descriptors"]),
                            )
                        ),
                        item["feature"],
                    ),
                )
                rank = next(
                    i
                    for i, item in enumerate(order)
                    if item["feature"]
                    == verified_best["feature"]
                )
                stats[alpha].append(rank / n)

    means = {
        alpha: (
            sum(values) / len(values)
            if values
            else float("inf")
        )
        for alpha, values in stats.items()
    }
    chosen = min(
        ALPHAS,
        key=lambda alpha: (means[alpha], alpha),
    )
    return chosen, means


def _choose(order, budget):
    selected = order[: min(budget, len(order))]
    best = max(
        selected,
        key=lambda item: (
            item["cal_gain"],
            -item["feature"],
        ),
    )
    cost = sum(
        item["threshold_evals"] for item in selected
    )
    return best, selected, cost


def _target_budget(order, max_budget):
    reference, _, _ = _choose(order, max_budget)
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
        candidate, _, _ = _choose(order, budget)
        gain = (
            candidate["test_gain"]
            if candidate["cal_gain"] > 1e-4
            else 0.0
        )
        if gain >= threshold:
            return budget
    return max_budget


def _fit_budget_oof(features, targets, worlds):
    folds = [_fold(world["index"]) for world in worlds]
    oof = [None] * len(worlds)
    for fold in range(5):
        train = [
            i for i, value in enumerate(folds)
            if value != fold
        ]
        test = [
            i for i, value in enumerate(folds)
            if value == fold
        ]
        if not test:
            continue
        if not train:
            for i in test:
                oof[i] = sum(targets) / len(targets)
            continue
        model = fit_ridge_with_intercept(
            [features[i] for i in train],
            [targets[i] for i in train],
            ridge=1.0,
        )
        means, scales, weights, intercept = model
        for i in test:
            z = [
                (value - mean) / scale
                for value, mean, scale in zip(
                    features[i], means, scales
                )
            ]
            oof[i] = intercept + sum(
                weight * value
                for weight, value in zip(weights, z)
            )
    if any(value is None for value in oof):
        raise AssertionError(
            "incomplete recursive budget cross-fit"
        )
    return oof


def _budget_metrics(
    orders,
    worlds,
    budgets,
    max_budget,
):
    success = 0
    false = 0
    reference_success = 0
    reference_false = 0
    gains = []
    reference_gains = []
    cost = 0
    reference_cost = 0

    for order, world, budget in zip(
        orders, worlds, budgets
    ):
        best, _, item_cost = _choose(order, budget)
        reference, _, ref_cost = _choose(
            order, max_budget
        )
        cost += item_cost
        reference_cost += ref_cost

        accepted = best["cal_gain"] > 1e-4
        ok = accepted and best["test_gain"] > 1e-4
        success += int(ok)
        false += int(accepted and not ok)
        gains.append(
            best["test_gain"] if accepted else 0.0
        )

        r_accepted = reference["cal_gain"] > 1e-4
        r_ok = (
            r_accepted
            and reference["test_gain"] > 1e-4
        )
        reference_success += int(r_ok)
        reference_false += int(
            r_accepted and not r_ok
        )
        reference_gains.append(
            reference["test_gain"]
            if r_accepted
            else 0.0
        )

    mean_gain = sum(gains) / len(gains)
    reference_mean = (
        sum(reference_gains)
        / len(reference_gains)
    )
    return {
        "cost": cost,
        "reference_cost": reference_cost,
        "reduction": reference_cost / max(cost, 1),
        "success": success,
        "false": false,
        "mean_gain": mean_gain,
        "reference_success": reference_success,
        "reference_false": reference_false,
        "reference_mean_gain": reference_mean,
        "success_retention": (
            success / max(reference_success, 1)
        ),
        "gain_ratio": (
            mean_gain / max(reference_mean, 1e-12)
            if reference_mean > 0
            else 1.0
        ),
    }


def _fit_trust_oof(features, targets, worlds):
    if not features:
        return [], None
    folds = [_fold(world["index"]) for world in worlds]
    oof = [None] * len(worlds)
    for fold in range(5):
        train = [
            i for i, value in enumerate(folds)
            if value != fold
        ]
        test = [
            i for i, value in enumerate(folds)
            if value == fold
        ]
        if not test:
            continue
        if len(train) < 2:
            mean = sum(targets) / len(targets)
            for i in test:
                oof[i] = mean
            continue
        model = fit_ridge_with_intercept(
            [features[i] for i in train],
            [targets[i] for i in train],
            ridge=1.0,
        )
        means, scales, weights, intercept = model
        for i in test:
            z = [
                (value - mean) / scale
                for value, mean, scale in zip(
                    features[i], means, scales
                )
            ]
            oof[i] = intercept + sum(
                weight * value
                for weight, value in zip(weights, z)
            )
    if any(value is None for value in oof):
        raise AssertionError(
            "incomplete recursive trust cross-fit"
        )
    final_model = fit_ridge_with_intercept(
        features,
        targets,
        ridge=1.0,
    )
    return oof, final_model


def _choose_trust_threshold(oof, targets):
    if not oof:
        return -1e30, {
            "success_retention": 1.0,
            "false_laws": 0,
            "reference_false_laws": 0,
        }
    reference_success = sum(
        int(y > 0.5) for y in targets
    )
    reference_false = (
        len(targets) - reference_success
    )
    candidates = [-1e30] + sorted(
        set(float(x) for x in oof)
    )
    viable = []
    for threshold in candidates:
        success = sum(
            int(pred >= threshold and y > 0.5)
            for pred, y in zip(oof, targets)
        )
        false = sum(
            int(pred >= threshold and y <= 0.5)
            for pred, y in zip(oof, targets)
        )
        retention = (
            success / max(reference_success, 1)
        )
        if (
            retention >= 0.95
            and false <= reference_false
        ):
            viable.append(
                (
                    false,
                    -success,
                    threshold,
                    retention,
                )
            )
    if not viable:
        threshold = -1e30
        success = reference_success
        false = reference_false
        retention = 1.0
    else:
        (
            false,
            neg_success,
            threshold,
            retention,
        ) = min(viable)
        success = -neg_success

    return threshold, {
        "successes": success,
        "reference_successes": reference_success,
        "false_laws": false,
        "reference_false_laws": reference_false,
        "success_retention": retention,
    }


def main():
    past_spec = os.environ[
        "REALITYGRAPH_RECURSIVE_PAST_DIRS"
    ]
    parent_path = Path(
        os.environ[
            "REALITYGRAPH_RECURSIVE_PARENT_MEMORY"
        ]
    )
    out_path = Path(
        os.environ[
            "REALITYGRAPH_RECURSIVE_OUTPUT_MEMORY"
        ]
    )
    generation = int(
        os.environ[
            "REALITYGRAPH_RECURSIVE_GENERATION"
        ]
    )
    meta_path = out_path.with_suffix(".json")
    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    worlds = _load_worlds(past_spec)
    expected = 20 * generation
    if len(worlds) != expected:
        raise AssertionError(
            f"generation {generation} expected "
            f"{expected} past worlds, got {len(worlds)}"
        )
    if any(
        world["role"] != "heldout-regression"
        for world in worlds
    ):
        raise AssertionError(
            "non-regression world in recursive history"
        )

    parent_text = parent_path.read_text()
    parent_sha = hashlib.sha256(
        parent_text.encode()
    ).hexdigest()
    parent = MG.parse(parent_text)
    base = policy_from_memory(parent)
    if base.training_worlds != 100:
        raise AssertionError(
            "base rank policy drift"
        )

    rank_model = _fit_rank(worlds)
    rank_blend, alpha_table = (
        _choose_rank_blend(base, worlds)
    )

    provisional = RecursiveSearchPolicy(
        tuple(worlds[0]["descriptor_names"]),
        rank_model[0],
        rank_model[1],
        rank_model[2],
        rank_blend,
        BUDGET_FEATURE_NAMES,
        (0.0,) * len(BUDGET_FEATURE_NAMES),
        (1.0,) * len(BUDGET_FEATURE_NAMES),
        (0.0,) * len(BUDGET_FEATURE_NAMES),
        1.0,
        0.0,
        base.budget,
        TRUST_FEATURE_NAMES,
        (0.0,) * len(TRUST_FEATURE_NAMES),
        (1.0,) * len(TRUST_FEATURE_NAMES),
        (0.0,) * len(TRUST_FEATURE_NAMES),
        1.0,
        -1e30,
        len(worlds),
        generation,
        parent_sha,
    )

    orders = [
        recursive_order(
            provisional,
            base,
            world,
        )
        for world in worlds
    ]
    budget_features = [
        recursive_budget_features(
            provisional,
            base,
            world,
        )
        for world in worlds
    ]
    budget_targets = [
        float(
            _target_budget(
                order,
                base.budget,
            )
        )
        for order in orders
    ]
    budget_oof = _fit_budget_oof(
        budget_features,
        budget_targets,
        worlds,
    )

    margin_table = []
    chosen_margin = None
    chosen_budget_metrics = None
    for margin in MARGINS:
        budgets = [
            max(
                1,
                min(
                    base.budget,
                    int(
                        math.ceil(
                            value + margin
                        )
                    ),
                ),
            )
            for value in budget_oof
        ]
        metrics = _budget_metrics(
            orders,
            worlds,
            budgets,
            base.budget,
        )
        row = {
            "margin": margin,
            "mean_budget": (
                sum(budgets)
                / len(budgets)
            ),
            **metrics,
        }
        margin_table.append(row)
        if (
            chosen_margin is None
            and metrics[
                "success_retention"
            ] >= 0.95
            and metrics[
                "gain_ratio"
            ] >= 0.95
            and metrics["false"]
            <= metrics["reference_false"]
        ):
            chosen_margin = margin
            chosen_budget_metrics = row

    if chosen_margin is None:
        chosen_margin = MARGINS[-1]
        chosen_budget_metrics = (
            margin_table[-1]
        )

    (
        b_means,
        b_scales,
        b_weights,
        b_intercept,
    ) = fit_ridge_with_intercept(
        budget_features,
        budget_targets,
        ridge=1.0,
    )

    with_budget = RecursiveSearchPolicy(
        provisional.descriptor_names,
        provisional.rank_means,
        provisional.rank_scales,
        provisional.rank_weights,
        provisional.rank_blend,
        BUDGET_FEATURE_NAMES,
        b_means,
        b_scales,
        b_weights,
        b_intercept,
        chosen_margin,
        base.budget,
        TRUST_FEATURE_NAMES,
        provisional.trust_means,
        provisional.trust_scales,
        provisional.trust_weights,
        provisional.trust_intercept,
        provisional.trust_threshold,
        len(worlds),
        generation,
        parent_sha,
    )

    chosen_budgets = [
        with_budget.choose_budget(
            recursive_budget_features(
                with_budget,
                base,
                world,
            )
        )
        for world in worlds
    ]

    trust_features = []
    trust_targets = []
    trust_worlds = []
    for world, order, budget in zip(
        worlds,
        orders,
        chosen_budgets,
    ):
        best, selected, _ = _choose(
            order,
            budget,
        )
        if best["cal_gain"] <= 1e-4:
            continue
        trust_features.append(
            recursive_trust_features(
                with_budget,
                base,
                world,
                selected,
                best,
                budget,
            )
        )
        trust_targets.append(
            float(
                best["test_gain"] > 1e-4
            )
        )
        trust_worlds.append(world)

    if len(trust_features) >= 5:
        (
            trust_oof,
            trust_model,
        ) = _fit_trust_oof(
            trust_features,
            trust_targets,
            trust_worlds,
        )
        (
            trust_threshold,
            trust_metrics,
        ) = _choose_trust_threshold(
            trust_oof,
            trust_targets,
        )
        (
            t_means,
            t_scales,
            t_weights,
            t_intercept,
        ) = trust_model
    else:
        trust_threshold = -1e30
        trust_metrics = {
            "success_retention": 1.0,
            "false_laws": 0,
            "reference_false_laws": 0,
        }
        t_means = (
            0.0,
        ) * len(TRUST_FEATURE_NAMES)
        t_scales = (
            1.0,
        ) * len(TRUST_FEATURE_NAMES)
        t_weights = (
            0.0,
        ) * len(TRUST_FEATURE_NAMES)
        t_intercept = 1.0

    policy = RecursiveSearchPolicy(
        with_budget.descriptor_names,
        with_budget.rank_means,
        with_budget.rank_scales,
        with_budget.rank_weights,
        with_budget.rank_blend,
        BUDGET_FEATURE_NAMES,
        with_budget.budget_means,
        with_budget.budget_scales,
        with_budget.budget_weights,
        with_budget.budget_intercept,
        with_budget.budget_safety_margin,
        with_budget.max_budget,
        TRUST_FEATURE_NAMES,
        t_means,
        t_scales,
        t_weights,
        t_intercept,
        trust_threshold,
        len(worlds),
        generation,
        parent_sha,
    )

    provenance = hashlib.sha256(
        (
            parent_sha
            + f"|generation={generation}"
            + f"|worlds={len(worlds)}"
            + f"|blend={rank_blend:.12g}"
            + f"|margin={chosen_margin:.12g}"
            + f"|trust={trust_threshold:.12g}"
        ).encode()
    ).hexdigest()[:12]

    memory = recursive_memory(
        parent,
        policy,
        provenance,
    )
    out_path.write_text(memory.text())
    memory_sha = hashlib.sha256(
        memory.text().encode()
    ).hexdigest()

    meta = {
        "generation": generation,
        "training_worlds": len(worlds),
        "training_indices": [
            world["index"]
            for world in worlds
        ],
        "parent_sha256": parent_sha,
        "memory_sha256": memory_sha,
        "memory_bytes": len(
            memory.text().encode()
        ),
        "rank_blend": rank_blend,
        "rank_alpha_oof_mean_verified_best_rank":
            alpha_table,
        "budget_target_counts": dict(
            sorted(
                Counter(
                    int(x)
                    for x in budget_targets
                ).items()
            )
        ),
        "budget_safety_margin":
            chosen_margin,
        "budget_crossfit":
            chosen_budget_metrics,
        "trust_threshold":
            trust_threshold,
        "trust_crossfit":
            trust_metrics,
        "provenance":
            provenance,
    }
    meta_path.write_text(
        json.dumps(
            meta,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )

    print(
        "REALITYGRAPH / "
        "RECURSIVE SELF-COMPILATION"
    )
    print(
        "-----------------------------------------"
    )
    print(f"generation={generation}")
    print(
        f"past_verified_worlds={len(worlds)}"
    )
    print(f"parent_sha256={parent_sha}")
    print(f"rank_blend={rank_blend:.2f}")
    print(
        "rank_alpha_oof_mean_verified_best_rank="
        f"{alpha_table}"
    )
    print(
        "budget_target_counts="
        f"{dict(sorted(Counter(int(x) for x in budget_targets).items()))}"
    )
    print(
        f"budget_safety_margin="
        f"{chosen_margin:.2f} "
        f"crossfit_mean_budget="
        f"{chosen_budget_metrics['mean_budget']:.3f}"
    )
    print(
        f"budget_crossfit_success_retention="
        f"{chosen_budget_metrics['success_retention']:.4f} "
        f"gain_ratio="
        f"{chosen_budget_metrics['gain_ratio']:.4f}"
    )
    print(
        f"trust_threshold="
        f"{trust_threshold:.6g} "
        f"trust_success_retention="
        f"{trust_metrics['success_retention']:.4f} "
        f"trust_false_laws="
        f"{trust_metrics['false_laws']}"
    )
    print(
        f"recursive_mg_bytes="
        f"{len(memory.text().encode())}"
    )
    print(
        f"recursive_mg_sha256="
        f"{memory_sha}"
    )
    print(
        "WHERE_HOW_MUCH_AND_WHEN_TO_REFUSE_COMPILED"
    )


if __name__ == "__main__":
    main()
