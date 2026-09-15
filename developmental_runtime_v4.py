from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from pmlb_meta_world import (
    DATA_URL,
    PMLB_COMMIT,
    SUMMARY_URL,
    _best_threshold,
    _binary_labels,
    _descriptors,
    _download,
    _evaluate_feature,
    _fit_probabilities,
    _parse_dataset,
    _sample_and_cap,
    _stratified_split,
    corpus_manifest,
)
from realitygraph.adaptive_policy import budget_features, budget_from_memory
from realitygraph.meta_policy import policy_from_memory
from realitygraph.mg import MG
from realitygraph.predictive import CompiledPredictiveModel, ThresholdRule, binary_log_loss
from realitygraph.retained_capability import (
    ablate_capability,
    applicable_transfer_capabilities,
    exact_restart,
    only_law,
)
from realitygraph.transfer_memory import law_to_model, model_to_law


FROZEN_POLICY_PATH = Path("frozen-meta/adaptive_policy.mg")
FROZEN_POLICY_SHA256 = "3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
HOLDOUT_START = 100
HOLDOUT_STOP = 120
MIN_GAIN = 1e-4
MAX_FUTURE_GROUPS = 4
PORTFOLIO_MEMORY_LIMIT = 16384


def _hash(seed: str, value: str) -> bytes:
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()


def future_groups(name: str, test: tuple[int, ...], labels: list[int]) -> tuple[tuple[int, ...], ...]:
    by_label = {0: [], 1: []}
    for i in test:
        by_label[labels[i]].append(i)
    min_class = min(len(by_label[0]), len(by_label[1]))
    k = min(MAX_FUTURE_GROUPS, max(1, min_class))
    if k == 1 and len(test) >= 4:
        k = 2
    groups = [[] for _ in range(k)]
    for label in (0, 1):
        ordered = sorted(
            by_label[label],
            key=lambda i: (_hash(f"v4|future|{name}|{label}", str(i)), i),
        )
        for j, i in enumerate(ordered):
            groups[j % k].append(i)
    groups = [tuple(sorted(group)) for group in groups if group]
    if not groups:
        raise ValueError("future grouping produced no events")
    return tuple(groups)


def compile_feature_model(feature_names, rows, labels, train, calibration, feature):
    train_values = [rows[i][feature] for i in train]
    train_labels = [labels[i] for i in train]
    threshold, _ = _best_threshold(train_values, train_labels)
    if threshold is None:
        raise ValueError("selected feature did not yield a threshold")
    fit = tuple(train) + tuple(calibration)
    fit_values = [rows[i][feature] for i in fit]
    fit_labels = [labels[i] for i in fit]
    probs = _fit_probabilities(fit_values, fit_labels, threshold)
    if probs is None:
        raise ValueError("selected threshold collapsed fit partition")
    lp, rp = probs
    left_support = sum(value < threshold for value in fit_values)
    right_support = len(fit_values) - left_support
    prior = (sum(fit_labels) + 1.0) / (len(fit_labels) + 2.0)
    return CompiledPredictiveModel(
        (ThresholdRule(feature, feature_names[feature], threshold),),
        (((0,), lp, left_support), ((1,), rp, right_support)),
        prior,
        min_support=1,
    )


def evaluate_future_group(world: dict, group: tuple[int, ...], memory: MG | None) -> dict:
    labels = [world["labels"][i] for i in group]
    prior = world["prior"]
    baseline = [prior] * len(group)
    cold_loss = binary_log_loss(labels, baseline)
    if memory is None:
        return {
            "warm_log_loss": cold_loss,
            "cold_log_loss": cold_loss,
            "gain": 0.0,
            "verified_help": False,
            "causal_ablation": False,
        }

    matches = applicable_transfer_capabilities(
        memory, world["source_hashes"], tuple(world["feature_names"])
    )
    if len(matches) != 1:
        raise AssertionError(f"expected one active capability for {world['dataset']}")
    law = only_law(memory, matches[0])
    model = law_to_model(law, tuple(world["feature_names"]))
    warm = [model.predict_values(tuple(world["rows"][i]), prior) for i in group]
    warm_loss = binary_log_loss(labels, warm)
    gain = cold_loss - warm_loss

    ablated = ablate_capability(memory, law.id)
    after = applicable_transfer_capabilities(
        ablated, world["source_hashes"], tuple(world["feature_names"])
    )
    return {
        "warm_log_loss": warm_loss,
        "cold_log_loss": cold_loss,
        "gain": gain,
        "verified_help": gain > MIN_GAIN,
        "causal_ablation": gain > MIN_GAIN and len(after) == 0,
    }


def prepare_world(index: int, summary_raw: bytes, policy, budget_policy) -> dict:
    manifest = corpus_manifest(summary_raw)
    meta = manifest[index]
    name = meta["dataset"]
    raw = _download(DATA_URL.format(name=name))
    source_sha = hashlib.sha256(raw).hexdigest()

    feature_names, rows, targets = _parse_dataset(raw)
    labels = _binary_labels(targets)
    anon_names, rows, labels = _sample_and_cap(name, feature_names, rows, labels)
    train, calibration, test = _stratified_split(name, labels)
    groups = future_groups(name, test, labels)

    candidates = []
    for feature in range(len(anon_names)):
        train_values = [rows[i][feature] for i in train]
        train_labels = [labels[i] for i in train]
        descriptors = _descriptors(train_values, train_labels, name, feature)
        evaluation = _evaluate_feature(
            rows, labels, feature, train, calibration, test
        )
        candidates.append(
            {"feature": feature, "descriptors": list(descriptors), **evaluation}
        )

    descriptor_world = {
        "candidates": [
            {"feature": item["feature"], "descriptors": item["descriptors"]}
            for item in candidates
        ]
    }
    budget = budget_policy.choose_budget(budget_features(policy, descriptor_world))
    ordered = sorted(
        candidates,
        key=lambda item: (
            -policy.score(tuple(item["descriptors"])),
            item["feature"],
        ),
    )
    selected = ordered[: min(budget, len(ordered))]
    adaptive_best = max(
        selected, key=lambda item: (item["cal_gain"], -item["feature"])
    )
    cold_best = max(
        candidates, key=lambda item: (item["cal_gain"], -item["feature"])
    )

    adaptive_cost = sum(item["threshold_evals"] for item in selected)
    cold_cost = sum(item["threshold_evals"] for item in candidates)
    adaptive_accept = adaptive_best["cal_gain"] > MIN_GAIN
    cold_accept = cold_best["cal_gain"] > MIN_GAIN
    adaptive_false = adaptive_accept and adaptive_best["test_gain"] <= MIN_GAIN
    cold_false = cold_accept and cold_best["test_gain"] <= MIN_GAIN

    fit = tuple(train) + tuple(calibration)
    fit_labels = [labels[i] for i in fit]
    prior = (sum(fit_labels) + 1.0) / (len(fit_labels) + 2.0)

    law = None
    if adaptive_accept:
        model = compile_feature_model(
            anon_names, rows, labels, train, calibration, adaptive_best["feature"]
        )
        provenance = hashlib.sha256(
            (
                f"v4|index={index}|dataset={name}|source={source_sha}|"
                f"feature={adaptive_best['feature']}|budget={budget}|"
                f"cal={adaptive_best['cal_gain']:.12g}"
            ).encode()
        ).hexdigest()[:12]
        law = model_to_law(
            ((DATA_URL.format(name=name), source_sha),),
            model,
            provenance=provenance,
        )

    return {
        "index": index,
        "dataset": name,
        "source_sha256": source_sha,
        "source_hashes": ((DATA_URL.format(name=name), source_sha),),
        "feature_names": anon_names,
        "rows": rows,
        "labels": labels,
        "future_groups": groups,
        "prior": prior,
        "budget": budget,
        "adaptive_feature": adaptive_best["feature"],
        "adaptive_cal_gain": adaptive_best["cal_gain"],
        "adaptive_test_gain": adaptive_best["test_gain"],
        "adaptive_accept": adaptive_accept,
        "adaptive_false_law": adaptive_false,
        "adaptive_search_cost": adaptive_cost,
        "cold_feature": cold_best["feature"],
        "cold_cal_gain": cold_best["cal_gain"],
        "cold_test_gain": cold_best["test_gain"],
        "cold_accept": cold_accept,
        "cold_false_law": cold_false,
        "cold_search_cost": cold_cost,
        "law": law,
    }


def main():
    out_path = Path(
        os.environ.get(
            "REALITYGRAPH_RUNTIME_V4_RESULT",
            "developmental-runtime-v4-summary.json",
        )
    )
    frozen_text = FROZEN_POLICY_PATH.read_text()
    frozen_sha = hashlib.sha256(frozen_text.encode()).hexdigest()
    if frozen_sha != FROZEN_POLICY_SHA256:
        raise AssertionError(f"frozen adaptive policy drift: {frozen_sha}")

    frozen_memory = exact_restart(frozen_text)
    policy = policy_from_memory(frozen_memory)
    budget_policy = budget_from_memory(frozen_memory)
    if policy.training_worlds != 100 or budget_policy.training_worlds != 100:
        raise AssertionError("frozen policy training count drift")
    if policy.corpus_digest != "81eed65c696ddebc2629":
        raise AssertionError("frozen training corpus digest drift")

    summary_raw = _download(SUMMARY_URL)
    summary_sha = hashlib.sha256(summary_raw).hexdigest()
    manifest = corpus_manifest(summary_raw)
    if len(manifest) != 140:
        raise AssertionError("PMLB manifest drift")
    indices = list(range(HOLDOUT_START, HOLDOUT_STOP))

    print("REALITYGRAPH / DEVELOPMENTAL RUNTIME V4")
    print("--------------------------------------")
    print(f"frozen_policy_sha256={frozen_sha}")
    print(f"policy_training_worlds={policy.training_worlds}")
    print(f"heldout_indices={HOLDOUT_START}:{HOLDOUT_STOP}")
    print(f"pmlb_commit={PMLB_COMMIT}")
    print("selection_uses_future_labels=0")
    print()

    worlds = [prepare_world(i, summary_raw, policy, budget_policy) for i in indices]

    laws = [world["law"] for world in worlds if world["law"] is not None]
    portfolio = MG("developmental-runtime-v4-capability-portfolio", laws)
    portfolio_text = portfolio.text()
    restarted = exact_restart(portfolio_text)
    portfolio_bytes = len(portfolio_text.encode())

    selector_errors = 0
    events = []
    for world in worlds:
        matches = applicable_transfer_capabilities(
            restarted, world["source_hashes"], tuple(world["feature_names"])
        )
        if (len(matches) == 1) != world["adaptive_accept"]:
            selector_errors += 1
        for event_index, group in enumerate(world["future_groups"]):
            events.append(
                {"world": world, "event_index": event_index, "group": group}
            )

    events.sort(
        key=lambda event: (
            _hash(
                "v4-mixed-future",
                f"{event['world']['index']}|{event['event_index']}",
            ),
            event["world"]["index"],
            event["event_index"],
        )
    )

    active = restarted
    revoked_sources = set()
    verified_events = 0
    causal_ablations = 0
    unknown_events = 0
    stream = []
    source_stats = {
        world["index"]: {
            "verified": 0,
            "events": len(world["future_groups"]),
            "revoked": False,
        }
        for world in worlds
    }

    for order, event in enumerate(events):
        world = event["world"]
        index = world["index"]
        matches = applicable_transfer_capabilities(
            active, world["source_hashes"], tuple(world["feature_names"])
        )
        applicable = len(matches) == 1

        if not applicable:
            unknown_events += 1
            stream.append(
                {
                    "order": order,
                    "index": index,
                    "dataset": world["dataset"],
                    "future_group": event["event_index"],
                    "applicable": False,
                    "verified_help": False,
                    "revoked_now": False,
                }
            )
            continue

        result = evaluate_future_group(world, event["group"], active)
        revoked_now = False
        if result["verified_help"]:
            verified_events += 1
            source_stats[index]["verified"] += 1
            if result["causal_ablation"]:
                causal_ablations += 1
        else:
            active = ablate_capability(active, matches[0].law_id)
            revoked_sources.add(index)
            source_stats[index]["revoked"] = True
            revoked_now = True

        stream.append(
            {
                "order": order,
                "index": index,
                "dataset": world["dataset"],
                "future_group": event["event_index"],
                "applicable": True,
                "verified_help": result["verified_help"],
                "causal_ablation": result["causal_ablation"],
                "gain": result["gain"],
                "revoked_now": revoked_now,
            }
        )

    admitted = [world for world in worlds if world["adaptive_accept"]]
    surviving = [
        world
        for world in admitted
        if (
            source_stats[world["index"]]["verified"]
            == source_stats[world["index"]]["events"]
            and not source_stats[world["index"]]["revoked"]
        )
    ]

    cold_acquisition_cost = sum(world["cold_search_cost"] for world in worlds)
    adaptive_acquisition_cost = sum(
        world["adaptive_search_cost"] for world in worlds
    )
    stateless_cold_future_cost = sum(
        world["cold_search_cost"] * len(world["future_groups"])
        for world in worlds
    )
    adaptive_false = sum(world["adaptive_false_law"] for world in worlds)
    cold_false = sum(world["cold_false_law"] for world in worlds)
    admitted_future_events = sum(
        len(world["future_groups"]) for world in admitted
    )

    acquisition_reduction = (
        cold_acquisition_cost / max(1, adaptive_acquisition_cost)
    )
    lifecycle_reduction = (
        stateless_cold_future_cost / max(1, adaptive_acquisition_cost)
    )
    verified_fraction = verified_events / max(1, admitted_future_events)

    result = {
        "frozen_policy_sha256": frozen_sha,
        "policy_training_worlds": policy.training_worlds,
        "policy_corpus_digest": policy.corpus_digest,
        "pmlb_commit": PMLB_COMMIT,
        "summary_sha256": summary_sha,
        "heldout_indices": indices,
        "worlds": [
            {
                "index": world["index"],
                "dataset": world["dataset"],
                "source_sha256": world["source_sha256"],
                "features": len(world["feature_names"]),
                "future_groups": len(world["future_groups"]),
                "budget": world["budget"],
                "adaptive_feature": world["adaptive_feature"],
                "adaptive_cal_gain": world["adaptive_cal_gain"],
                "adaptive_test_gain": world["adaptive_test_gain"],
                "adaptive_accept": world["adaptive_accept"],
                "adaptive_false_law": world["adaptive_false_law"],
                "adaptive_search_cost": world["adaptive_search_cost"],
                "cold_feature": world["cold_feature"],
                "cold_cal_gain": world["cold_cal_gain"],
                "cold_test_gain": world["cold_test_gain"],
                "cold_accept": world["cold_accept"],
                "cold_false_law": world["cold_false_law"],
                "cold_search_cost": world["cold_search_cost"],
                "verified_future_events": source_stats[world["index"]]["verified"],
                "revoked": source_stats[world["index"]]["revoked"],
            }
            for world in worlds
        ],
        "portfolio_laws_initial": len(restarted.laws),
        "portfolio_laws_final": len(active.laws),
        "portfolio_bytes": portfolio_bytes,
        "selector_errors": selector_errors,
        "admitted_sources": len(admitted),
        "surviving_sources": len(surviving),
        "revoked_sources": len(revoked_sources),
        "future_events_total": len(events),
        "admitted_future_events": admitted_future_events,
        "verified_future_events": verified_events,
        "causal_ablations": causal_ablations,
        "unknown_events": unknown_events,
        "verified_fraction_of_admitted_events": verified_fraction,
        "adaptive_false_laws": adaptive_false,
        "cold_false_laws": cold_false,
        "cold_acquisition_search_cost": cold_acquisition_cost,
        "adaptive_acquisition_search_cost": adaptive_acquisition_cost,
        "acquisition_search_reduction": acquisition_reduction,
        "stateless_cold_future_search_cost": stateless_cold_future_cost,
        "runtime_future_search_cost": 0,
        "lifecycle_search_reduction": lifecycle_reduction,
        "stream": stream,
    }

    gates = {
        "frozen_policy_exact": frozen_sha == FROZEN_POLICY_SHA256,
        "fresh_heldout_block": indices == list(range(100, 120)),
        "adaptive_acquisition_reduces_search": acquisition_reduction >= 2.0,
        "portfolio_grows_across_sources": len(admitted) >= 12,
        "at_least_eight_sources_survive": len(surviving) >= 8,
        "majority_admitted_future_events_verified": verified_fraction >= 0.70,
        "every_verified_event_causal": causal_ablations == verified_events,
        "target_free_selector_exact": selector_errors == 0,
        "future_search_zero": True,
        "false_laws_not_materially_worse_than_cold": adaptive_false <= cold_false + 2,
        "lifecycle_search_reduction": lifecycle_reduction >= 8.0,
        "tiny_compiled_portfolio": portfolio_bytes <= PORTFOLIO_MEMORY_LIMIT,
    }
    result["gates"] = gates
    result["passed"] = all(gates.values())

    out_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    for world in result["worlds"]:
        print(
            f"{world['index']:03d} {world['dataset'][:28]:28} "
            f"F={world['features']:2d} budget={world['budget']} "
            f"search={world['cold_search_cost']:3d}->{world['adaptive_search_cost']:3d} "
            f"accept={world['adaptive_accept']} "
            f"future={world['verified_future_events']}/{world['future_groups']} "
            f"revoked={world['revoked']}"
        )

    print()
    print("AGGREGATE")
    print(
        f"admitted_sources={len(admitted)} surviving_sources={len(surviving)} "
        f"revoked_sources={len(revoked_sources)}"
    )
    print(
        f"portfolio_laws={len(restarted.laws)}->{len(active.laws)} "
        f"portfolio_bytes={portfolio_bytes}"
    )
    print(
        f"verified_future_events={verified_events}/{admitted_future_events} "
        f"causal_ablations={causal_ablations} unknown_events={unknown_events}"
    )
    print(
        f"cold_acquisition_search={cold_acquisition_cost} "
        f"adaptive_acquisition_search={adaptive_acquisition_cost} "
        f"reduction={acquisition_reduction:.2f}x"
    )
    print(
        f"stateless_cold_future_search={stateless_cold_future_cost} "
        f"runtime_future_search=0 lifecycle_reduction={lifecycle_reduction:.2f}x"
    )
    print(f"false_laws adaptive={adaptive_false} cold={cold_false}")
    for name, ok in gates.items():
        print(f"gate_{name}={int(ok)}")

    print("VERDICT")
    if result["passed"]:
        print("PASS_PROSPECTIVE_DEVELOPMENTAL_RUNTIME_V4")
    else:
        print("PARTIAL_PROSPECTIVE_DEVELOPMENTAL_RUNTIME_V4")
        raise AssertionError("one or more frozen V4 gates failed")


if __name__ == "__main__":
    main()
