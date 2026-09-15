from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import openml
import pandas as pd

from pmlb_meta_world import _descriptors
from realitygraph.adaptive_policy import budget_features, budget_from_memory
from realitygraph.meta_policy import policy_from_memory
from realitygraph.mg import MG
from realitygraph.retained_capability import exact_restart
from realitygraph.transfer_memory import model_to_law
from scope_gate_v5 import (
    calibration_evaluation,
    compile_model,
    run_portfolio,
)


FROZEN_POLICY_PATH = Path("frozen-meta/adaptive_policy.mg")
FROZEN_POLICY_SHA256 = "3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
FROZEN_MANIFEST_DIGEST = "30c323cba712ccf537420f6167d380db68c97997972b67ed0f3c210d6f43293c"
V5_THRESHOLD = 0.04804871787364886
V6_THRESHOLD = 0.05718096689694352
MIN_GAIN = 1e-4
MAX_ROWS = 1000
MAX_NUMERIC_FEATURES = 32

WORLDS = (
    (146818, 40981, "Australian"),
    (359981, 41027, "jungle_chess_2pcs_raw_endgame_complete"),
    (359959, 23, "cmc"),
    (359955, 1464, "blood-transfusion-service-center"),
    (168784, 40982, "steel-plates-fault"),
    (190411, 41156, "ada"),
    (359958, 1049, "pc4"),
    (146820, 40983, "wilt"),
    (359992, 42733, "Click_prediction_small"),
    (190137, 1487, "ozone-level-8hr"),
    (359954, 188, "eucalyptus"),
    (359982, 1461, "bank-marketing"),
    (359956, 1494, "qsar-biodeg"),
    (168757, 31, "credit-g"),
    (359963, 40984, "segment"),
    (359970, 4538, "GesturePhaseSegmentationProcessed"),
    (359962, 1067, "kc1"),
    (359974, 40498, "wine-quality-white"),
    (359975, 40900, "Satellite"),
    (359969, 1475, "first-order-theorem-proving"),
)


def h(seed: str, value: str) -> bytes:
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()


def finite_float(value):
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def sampled_indices(task_id: int, n: int) -> tuple[int, ...]:
    indices = list(range(n))
    indices.sort(key=lambda i: (h(f"openml-v7|sample|{task_id}", str(i)), i))
    return tuple(sorted(indices[: min(MAX_ROWS, n)]))


def split_indices(task_id: int, indices: tuple[int, ...]):
    ordered = sorted(
        indices,
        key=lambda i: (h(f"openml-v7|split|{task_id}", str(i)), i),
    )
    n = len(ordered)
    train_n = max(20, int(0.60 * n))
    cal_n = max(10, int(0.20 * n))
    if train_n + cal_n >= n:
        train_n = max(2, n - 4)
        cal_n = max(1, (n - train_n) // 2)
    train = tuple(ordered[:train_n])
    calibration = tuple(ordered[train_n:train_n + cal_n])
    test = tuple(ordered[train_n + cal_n:])
    if not train or not calibration or len(test) < 4:
        raise ValueError("OpenML V7 split too small")
    return train, calibration, test


def hashed_future_groups(task_id: int, test: tuple[int, ...]):
    ordered = sorted(
        test,
        key=lambda i: (h(f"openml-v7|future|{task_id}", str(i)), i),
    )
    k = min(4, max(1, len(ordered) // 10))
    groups = [[] for _ in range(k)]
    for j, i in enumerate(ordered):
        groups[j % k].append(i)
    return tuple(tuple(sorted(group)) for group in groups if group)


def choose_positive_from_train(y_values, train):
    counts = {}
    for i in train:
        value = str(y_values[i])
        counts[value] = counts.get(value, 0) + 1
    if len(counts) < 2:
        raise ValueError("training target collapsed")
    total = sum(counts.values())
    ranked = sorted(
        counts,
        key=lambda value: (
            abs(counts[value] / total - 0.5),
            value,
        ),
    )
    return ranked[0]


def numeric_matrix(task_id: int, X, train):
    numeric = [
        str(column)
        for column in X.columns
        if pd.api.types.is_numeric_dtype(X[column])
    ]
    numeric.sort(
        key=lambda name: (h(f"openml-v7|feature|{task_id}", name), name)
    )
    numeric = numeric[:MAX_NUMERIC_FEATURES]
    if len(numeric) < 2:
        raise ValueError("fewer than two numeric features")

    medians = {}
    kept = []
    for name in numeric:
        vals = [
            finite_float(X.iloc[i][name])
            for i in train
        ]
        vals = sorted(x for x in vals if x is not None)
        if not vals:
            continue
        m = vals[len(vals) // 2]
        medians[name] = m
        kept.append(name)
    if len(kept) < 2:
        raise ValueError("numeric features collapsed after train-only imputation")

    rows = []
    for i in range(len(X)):
        row = []
        for name in kept:
            value = finite_float(X.iloc[i][name])
            row.append(medians[name] if value is None else value)
        rows.append(row)
    return kept, rows


def load_world(task_id: int, data_id: int, expected_name: str, policy, budget_policy):
    task = openml.tasks.get_task(task_id, download_splits=False)
    dataset = task.get_dataset()
    if int(dataset.dataset_id) != data_id:
        raise AssertionError("OpenML task/data id drift")
    if str(dataset.name) != expected_name:
        raise AssertionError(
            f"OpenML dataset name drift: {dataset.name} != {expected_name}"
        )

    X, y, _, _ = dataset.get_data(
        target=task.target_name,
        dataset_format="dataframe",
    )
    X = X.reset_index(drop=True)
    y = y.reset_index(drop=True)
    selected = sampled_indices(task_id, len(X))

    # Subset is chosen by row identity only, before any labels are consulted.
    Xs = X.iloc[list(selected)].reset_index(drop=True)
    ys = y.iloc[list(selected)].reset_index(drop=True)
    local = tuple(range(len(Xs)))
    train, calibration, test = split_indices(task_id, local)

    positive = choose_positive_from_train(ys, train)
    labels = [1 if str(value) == positive else 0 for value in ys]
    if len({labels[i] for i in train}) < 2:
        raise ValueError("binary training target collapsed")

    feature_names, rows = numeric_matrix(task_id, Xs, train)
    groups = hashed_future_groups(task_id, test)

    candidates = []
    for feature in range(len(feature_names)):
        train_values = [rows[i][feature] for i in train]
        train_labels = [labels[i] for i in train]
        descriptors = _descriptors(
            train_values,
            train_labels,
            f"openml-task-{task_id}",
            feature,
        )
        cal = calibration_evaluation(
            rows,
            labels,
            feature,
            train,
            calibration,
        )
        candidates.append({
            "feature": feature,
            "descriptors": list(descriptors),
            **cal,
        })

    descriptor_world = {
        "candidates": [
            {
                "feature": item["feature"],
                "descriptors": item["descriptors"],
            }
            for item in candidates
        ]
    }
    budget = budget_policy.choose_budget(
        budget_features(policy, descriptor_world)
    )
    ordered = sorted(
        candidates,
        key=lambda item: (
            -policy.score(tuple(item["descriptors"])),
            item["feature"],
        ),
    )
    selected_candidates = ordered[: min(budget, len(ordered))]
    adaptive_best = max(
        selected_candidates,
        key=lambda item: (item["cal_gain"], -item["feature"]),
    )
    cold_best = max(
        candidates,
        key=lambda item: (item["cal_gain"], -item["feature"]),
    )
    adaptive_cost = sum(
        item["threshold_evals"] for item in selected_candidates
    )
    cold_cost = sum(item["threshold_evals"] for item in candidates)
    adaptive_accept = adaptive_best["cal_gain"] > MIN_GAIN

    law = None
    prior = None
    checksum = str(
        getattr(dataset, "md5_checksum", "")
        or f"openml-data-{data_id}-version-{dataset.version}"
    )
    source_hashes = (
        (f"https://www.openml.org/d/{data_id}", checksum),
    )
    if adaptive_accept:
        model, prior = compile_model(
            feature_names,
            rows,
            labels,
            train,
            calibration,
            adaptive_best["feature"],
            adaptive_best["threshold"],
        )
        provenance = hashlib.sha256(
            (
                f"openml-v7|task={task_id}|data={data_id}|checksum={checksum}|"
                f"feature={adaptive_best['feature']}|cal={adaptive_best['cal_gain']:.12g}"
            ).encode()
        ).hexdigest()[:12]
        law = model_to_law(
            source_hashes,
            model,
            provenance=provenance,
        )
    else:
        fit = tuple(train) + tuple(calibration)
        fit_labels = [labels[i] for i in fit]
        prior = (sum(fit_labels) + 1.0) / (len(fit_labels) + 2.0)

    return {
        "index": task_id,
        "task_id": task_id,
        "data_id": data_id,
        "dataset": expected_name,
        "source_hashes": source_hashes,
        "feature_names": feature_names,
        "rows": rows,
        "labels": labels,
        "future_groups": groups,
        "prior": prior,
        "budget": budget,
        "adaptive_feature": adaptive_best["feature"],
        "adaptive_cal_gain": adaptive_best["cal_gain"],
        "adaptive_accept": adaptive_accept,
        "v5_promoted": (
            adaptive_accept
            and adaptive_best["cal_gain"] >= V5_THRESHOLD
        ),
        "v6_promoted": (
            adaptive_accept
            and adaptive_best["cal_gain"] >= V6_THRESHOLD
        ),
        "adaptive_search_cost": adaptive_cost,
        "cold_feature": cold_best["feature"],
        "cold_cal_gain": cold_best["cal_gain"],
        "cold_search_cost": cold_cost,
        "law": law,
        "rows_used": len(rows),
        "positive_class": positive,
    }


def main():
    out = Path(
        os.environ.get(
            "REALITYGRAPH_OPENML_V7_RESULT",
            "openml-v7-summary.json",
        )
    )

    frozen_text = FROZEN_POLICY_PATH.read_text()
    policy_sha = hashlib.sha256(frozen_text.encode()).hexdigest()
    if policy_sha != FROZEN_POLICY_SHA256:
        raise AssertionError("frozen acquisition policy drift")
    memory = exact_restart(frozen_text)
    policy = policy_from_memory(memory)
    budget_policy = budget_from_memory(memory)

    hardcoded_manifest = hashlib.sha256(
        "\n".join(
            f"{task}|{data}|{name}"
            for task, data, name in WORLDS
        ).encode()
    ).hexdigest()

    print("REALITYGRAPH / CROSS-CORPUS DEVELOPMENTAL SCOPE V7")
    print("---------------------------------------------------")
    print(f"source_manifest_digest={FROZEN_MANIFEST_DIGEST}")
    print(f"hardcoded_world_digest={hardcoded_manifest}")
    print(f"frozen_policy_sha256={policy_sha}")
    print(f"v5_threshold={V5_THRESHOLD:.17g}")
    print(f"v6_threshold={V6_THRESHOLD:.17g}")
    print("row_sampling_uses_targets=0")
    print("split_assignment_uses_targets=0")
    print("future_grouping_uses_targets=0")
    print()

    worlds = [
        load_world(task, data, name, policy, budget_policy)
        for task, data, name in WORLDS
    ]

    base = run_portfolio(worlds, lambda w: w["adaptive_accept"])
    v5 = run_portfolio(worlds, lambda w: w["v5_promoted"])
    v6 = run_portfolio(worlds, lambda w: w["v6_promoted"])

    adaptive_cost = sum(w["adaptive_search_cost"] for w in worlds)
    cold_cost = sum(w["cold_search_cost"] for w in worlds)
    stateless_future = sum(
        w["cold_search_cost"] * len(w["future_groups"])
        for w in worlds
    )
    acquisition_reduction = cold_cost / max(1, adaptive_cost)
    lifecycle_reduction = stateless_future / max(1, adaptive_cost)
    retention = v6["verified_events"] / max(1, base["verified_events"])

    result = {
        "frozen_source_manifest_digest": FROZEN_MANIFEST_DIGEST,
        "hardcoded_world_digest": hardcoded_manifest,
        "frozen_policy_sha256": policy_sha,
        "v5_threshold": V5_THRESHOLD,
        "v6_threshold": V6_THRESHOLD,
        "worlds": [
            {
                "task_id": w["task_id"],
                "data_id": w["data_id"],
                "dataset": w["dataset"],
                "rows_used": w["rows_used"],
                "numeric_features_used": len(w["feature_names"]),
                "future_groups": len(w["future_groups"]),
                "budget": w["budget"],
                "adaptive_cal_gain": w["adaptive_cal_gain"],
                "adaptive_accept": w["adaptive_accept"],
                "v5_promoted": w["v5_promoted"],
                "v6_promoted": w["v6_promoted"],
                "adaptive_search_cost": w["adaptive_search_cost"],
                "cold_search_cost": w["cold_search_cost"],
                "base_verified": base["source_stats"][w["task_id"]]["verified"],
                "base_revoked": base["source_stats"][w["task_id"]]["revoked"],
                "v5_verified": v5["source_stats"][w["task_id"]]["verified"],
                "v5_revoked": v5["source_stats"][w["task_id"]]["revoked"],
                "v6_verified": v6["source_stats"][w["task_id"]]["verified"],
                "v6_revoked": v6["source_stats"][w["task_id"]]["revoked"],
            }
            for w in worlds
        ],
        "base": base,
        "v5": v5,
        "v6": v6,
        "cold_acquisition_cost": cold_cost,
        "adaptive_acquisition_cost": adaptive_cost,
        "acquisition_reduction": acquisition_reduction,
        "stateless_future_cost": stateless_future,
        "future_search_cost": 0,
        "lifecycle_reduction": lifecycle_reduction,
        "v6_verified_event_retention_vs_base": retention,
    }

    gates = {
        "manifest_precommitted": FROZEN_MANIFEST_DIGEST == "30c323cba712ccf537420f6167d380db68c97997972b67ed0f3c210d6f43293c",
        "twenty_source_distinct_openml_worlds": len(worlds) == 20,
        "nontrivial_base_acquisition": base["promoted_sources"] >= 8,
        "nontrivial_v6_portfolio": v6["promoted_sources"] >= 6,
        "v6_revocations_no_worse_than_base": v6["failures"] <= base["failures"],
        "v6_survival_precision_no_worse_than_base": (
            v6["survival_precision"] >= base["survival_precision"]
        ),
        "v6_precision_no_worse_than_v5": (
            v6["survival_precision"] >= v5["survival_precision"]
        ),
        "cross_corpus_verified_retention_at_least_65pct": retention >= 0.65,
        "every_v6_verified_event_causal": (
            v6["causal_ablations"] == v6["verified_events"]
        ),
        "adaptive_acquisition_reduction_at_least_2x": acquisition_reduction >= 2.0,
        "lifecycle_reduction_at_least_6x": lifecycle_reduction >= 6.0,
        "future_search_zero": True,
    }
    result["gates"] = gates
    result["passed"] = all(gates.values())
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    for w in result["worlds"]:
        print(
            f"task={w['task_id']} {w['dataset'][:25]:25} "
            f"F={w['numeric_features_used']:2d} gain={w['adaptive_cal_gain']:+.4f} "
            f"A={w['adaptive_accept']} V5={w['v5_promoted']} V6={w['v6_promoted']} "
            f"base={w['base_verified']}/{w['future_groups']} r={w['base_revoked']} "
            f"v6={w['v6_verified']}/{w['future_groups']} r={w['v6_revoked']}"
        )

    print()
    for name, stats in (("BASE", base), ("V5", v5), ("V6", v6)):
        print(
            f"{name}: promoted={stats['promoted_sources']} "
            f"survived={stats['surviving_sources']} "
            f"failures={stats['failures']} verified={stats['verified_events']} "
            f"precision={stats['survival_precision']:.4f} "
            f"bytes={stats['initial_bytes']}"
        )
    print(
        f"v6_verified_event_retention={retention:.4f} "
        f"acquisition_reduction={acquisition_reduction:.2f}x "
        f"lifecycle_reduction={lifecycle_reduction:.2f}x"
    )
    for name, ok in gates.items():
        print(f"gate_{name}={int(ok)}")

    print("VERDICT")
    if result["passed"]:
        print("PASS_CROSS_CORPUS_DEVELOPMENTAL_SCOPE_V7")
    else:
        print("PARTIAL_CROSS_CORPUS_DEVELOPMENTAL_SCOPE_V7")
        raise AssertionError("one or more frozen V7 gates failed")


if __name__ == "__main__":
    main()
