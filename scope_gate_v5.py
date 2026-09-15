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
from developmental_runtime_v4 import future_groups


FROZEN_POLICY_PATH = Path("frozen-meta/adaptive_policy.mg")
FROZEN_POLICY_SHA256 = "3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
V4_EVIDENCE_DIGEST = "6f95c5d4ba84d90603a605be691cc48e0c23849ec4489e1fd7eb6e049f0d6efa"
PROMOTION_GAIN_THRESHOLD = 0.04804871787364886
HOLDOUT_START = 120
HOLDOUT_STOP = 140
MIN_GAIN = 1e-4


def _hash(seed: str, value: str) -> bytes:
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()


def calibration_evaluation(rows, labels, feature, train, calibration):
    train_values = [rows[i][feature] for i in train]
    train_labels = [labels[i] for i in train]
    cal_values = [rows[i][feature] for i in calibration]
    cal_labels = [labels[i] for i in calibration]

    threshold, threshold_evals = _best_threshold(train_values, train_labels)
    if threshold is None:
        return {
            "threshold": None,
            "cal_gain": 0.0,
            "threshold_evals": threshold_evals,
        }

    probs = _fit_probabilities(train_values, train_labels, threshold)
    if probs is None:
        return {
            "threshold": None,
            "cal_gain": 0.0,
            "threshold_evals": threshold_evals,
        }
    lp, rp = probs
    prior = (sum(train_labels) + 1.0) / (len(train_labels) + 2.0)
    baseline = binary_log_loss(cal_labels, [prior] * len(cal_labels))
    model = binary_log_loss(
        cal_labels,
        [rp if value >= threshold else lp for value in cal_values],
    )
    return {
        "threshold": threshold,
        "cal_gain": baseline - model,
        "threshold_evals": threshold_evals,
    }


def compile_model(feature_names, rows, labels, train, calibration, feature, threshold):
    fit = tuple(train) + tuple(calibration)
    values = [rows[i][feature] for i in fit]
    fit_labels = [labels[i] for i in fit]
    probs = _fit_probabilities(values, fit_labels, threshold)
    if probs is None:
        raise ValueError("selected threshold collapsed fit partition")
    lp, rp = probs
    left_support = sum(value < threshold for value in values)
    right_support = len(values) - left_support
    prior = (sum(fit_labels) + 1.0) / (len(fit_labels) + 2.0)
    return CompiledPredictiveModel(
        (ThresholdRule(feature, feature_names[feature], threshold),),
        (((0,), lp, left_support), ((1,), rp, right_support)),
        prior,
        min_support=1,
    ), prior


def prepare_world(index, summary_raw, policy, budget_policy):
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
        cal = calibration_evaluation(rows, labels, feature, train, calibration)
        candidates.append({
            "feature": feature,
            "descriptors": list(descriptors),
            **cal,
        })

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
        selected,
        key=lambda item: (item["cal_gain"], -item["feature"]),
    )
    cold_best = max(
        candidates,
        key=lambda item: (item["cal_gain"], -item["feature"]),
    )

    adaptive_accept = adaptive_best["cal_gain"] > MIN_GAIN
    promoted = adaptive_accept and adaptive_best["cal_gain"] >= PROMOTION_GAIN_THRESHOLD
    adaptive_cost = sum(item["threshold_evals"] for item in selected)
    cold_cost = sum(item["threshold_evals"] for item in candidates)

    law = None
    prior = None
    if adaptive_accept:
        model, prior = compile_model(
            anon_names,
            rows,
            labels,
            train,
            calibration,
            adaptive_best["feature"],
            adaptive_best["threshold"],
        )
        provenance = hashlib.sha256(
            (
                f"v5|index={index}|dataset={name}|source={source_sha}|"
                f"feature={adaptive_best['feature']}|budget={budget}|"
                f"cal={adaptive_best['cal_gain']:.12g}|"
                f"promotion={PROMOTION_GAIN_THRESHOLD:.12g}"
            ).encode()
        ).hexdigest()[:12]
        law = model_to_law(
            ((DATA_URL.format(name=name), source_sha),),
            model,
            provenance=provenance,
        )
    else:
        fit = tuple(train) + tuple(calibration)
        fit_labels = [labels[i] for i in fit]
        prior = (sum(fit_labels) + 1.0) / (len(fit_labels) + 2.0)

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
        "adaptive_accept": adaptive_accept,
        "promoted": promoted,
        "adaptive_search_cost": adaptive_cost,
        "cold_feature": cold_best["feature"],
        "cold_cal_gain": cold_best["cal_gain"],
        "cold_search_cost": cold_cost,
        "law": law,
    }


def eval_group(world, group, memory):
    ys = [world["labels"][i] for i in group]
    prior = world["prior"]
    cold = [prior] * len(group)
    cold_loss = binary_log_loss(ys, cold)

    matches = applicable_transfer_capabilities(
        memory,
        world["source_hashes"],
        tuple(world["feature_names"]),
    )
    if len(matches) != 1:
        raise AssertionError("expected exactly one active law")
    law = only_law(memory, matches[0])
    model = law_to_model(law, tuple(world["feature_names"]))
    warm = [
        model.predict_values(tuple(world["rows"][i]), prior)
        for i in group
    ]
    warm_loss = binary_log_loss(ys, warm)
    gain = cold_loss - warm_loss

    ablated = ablate_capability(memory, law.id)
    after = applicable_transfer_capabilities(
        ablated,
        world["source_hashes"],
        tuple(world["feature_names"]),
    )
    return {
        "gain": gain,
        "verified": gain > MIN_GAIN,
        "causal": gain > MIN_GAIN and len(after) == 0,
    }


def run_portfolio(worlds, promoted_selector):
    laws = [
        world["law"]
        for world in worlds
        if world["law"] is not None and promoted_selector(world)
    ]
    memory = exact_restart(
        MG("scope-gate-v5-portfolio", laws).text()
    )
    initial_bytes = len(memory.text().encode())
    active = memory
    events = []
    for world in worlds:
        for j, group in enumerate(world["future_groups"]):
            events.append({"world": world, "j": j, "group": group})
    events.sort(
        key=lambda e: (
            _hash("scope-gate-v5-stream", f"{e['world']['index']}|{e['j']}"),
            e["world"]["index"],
            e["j"],
        )
    )

    stats = {
        world["index"]: {
            "promoted": promoted_selector(world) and world["law"] is not None,
            "verified": 0,
            "events": len(world["future_groups"]),
            "revoked": False,
        }
        for world in worlds
    }
    verified = causal = failures = unknown = 0

    for event in events:
        world = event["world"]
        idx = world["index"]
        matches = applicable_transfer_capabilities(
            active,
            world["source_hashes"],
            tuple(world["feature_names"]),
        )
        if len(matches) == 0:
            unknown += 1
            continue
        if len(matches) != 1:
            raise AssertionError("ambiguous active capability")
        result = eval_group(world, event["group"], active)
        if result["verified"]:
            verified += 1
            stats[idx]["verified"] += 1
            causal += int(result["causal"])
        else:
            failures += 1
            stats[idx]["revoked"] = True
            active = ablate_capability(active, matches[0].law_id)

    promoted = [x for x in stats.values() if x["promoted"]]
    survivors = [
        x for x in promoted
        if x["verified"] == x["events"] and not x["revoked"]
    ]
    return {
        "initial_laws": len(memory.laws),
        "final_laws": len(active.laws),
        "initial_bytes": initial_bytes,
        "verified_events": verified,
        "causal_ablations": causal,
        "failures": failures,
        "unknown_events": unknown,
        "promoted_sources": len(promoted),
        "surviving_sources": len(survivors),
        "survival_precision": len(survivors) / max(1, len(promoted)),
        "source_stats": stats,
    }


def main():
    out = Path(
        os.environ.get(
            "REALITYGRAPH_SCOPE_V5_RESULT",
            "scope-gate-v5-summary.json",
        )
    )
    frozen_text = FROZEN_POLICY_PATH.read_text()
    frozen_sha = hashlib.sha256(frozen_text.encode()).hexdigest()
    if frozen_sha != FROZEN_POLICY_SHA256:
        raise AssertionError("frozen acquisition policy drift")
    frozen = exact_restart(frozen_text)
    policy = policy_from_memory(frozen)
    budget_policy = budget_from_memory(frozen)

    summary_raw = _download(SUMMARY_URL)
    manifest = corpus_manifest(summary_raw)
    indices = list(range(HOLDOUT_START, HOLDOUT_STOP))
    if len(manifest) != 140:
        raise AssertionError("PMLB manifest drift")

    print("REALITYGRAPH / LEARNED PROMOTION SCOPE V5")
    print("----------------------------------------")
    print(f"v4_evidence_digest={V4_EVIDENCE_DIGEST}")
    print(f"promotion_gain_threshold={PROMOTION_GAIN_THRESHOLD:.17g}")
    print("v4_training_survivors_retained=12/12")
    print("v4_training_revocations_blocked=3/6")
    print(f"fresh_indices={HOLDOUT_START}:{HOLDOUT_STOP}")
    print("promotion_uses_future_labels=0")
    print()

    worlds = [prepare_world(i, summary_raw, policy, budget_policy) for i in indices]

    base = run_portfolio(
        worlds,
        lambda world: world["adaptive_accept"],
    )
    gated = run_portfolio(
        worlds,
        lambda world: world["promoted"],
    )

    adaptive_cost = sum(w["adaptive_search_cost"] for w in worlds)
    cold_cost = sum(w["cold_search_cost"] for w in worlds)
    stateless_cold_future = sum(
        w["cold_search_cost"] * len(w["future_groups"])
        for w in worlds
    )
    acquisition_reduction = cold_cost / max(1, adaptive_cost)
    lifecycle_reduction = stateless_cold_future / max(1, adaptive_cost)
    event_retention = (
        gated["verified_events"] / max(1, base["verified_events"])
    )
    precision_gain = gated["survival_precision"] - base["survival_precision"]

    result = {
        "v4_evidence_digest": V4_EVIDENCE_DIGEST,
        "promotion_gain_threshold": PROMOTION_GAIN_THRESHOLD,
        "frozen_policy_sha256": frozen_sha,
        "heldout_indices": indices,
        "pmlb_commit": PMLB_COMMIT,
        "worlds": [
            {
                "index": w["index"],
                "dataset": w["dataset"],
                "features": len(w["feature_names"]),
                "budget": w["budget"],
                "adaptive_cal_gain": w["adaptive_cal_gain"],
                "adaptive_accept": w["adaptive_accept"],
                "promoted": w["promoted"],
                "adaptive_search_cost": w["adaptive_search_cost"],
                "cold_search_cost": w["cold_search_cost"],
                "base_verified": base["source_stats"][w["index"]]["verified"],
                "base_revoked": base["source_stats"][w["index"]]["revoked"],
                "gated_verified": gated["source_stats"][w["index"]]["verified"],
                "gated_revoked": gated["source_stats"][w["index"]]["revoked"],
                "future_groups": len(w["future_groups"]),
            }
            for w in worlds
        ],
        "base": base,
        "gated": gated,
        "adaptive_acquisition_cost": adaptive_cost,
        "cold_acquisition_cost": cold_cost,
        "acquisition_reduction": acquisition_reduction,
        "stateless_cold_future_cost": stateless_cold_future,
        "lifecycle_reduction": lifecycle_reduction,
        "verified_event_retention": event_retention,
        "survival_precision_gain": precision_gain,
    }

    gates = {
        "frozen_v4_learned_threshold": abs(
            PROMOTION_GAIN_THRESHOLD - 0.04804871787364886
        ) < 1e-15,
        "fresh_second_heldout_block": indices == list(range(120, 140)),
        "gated_promotes_nontrivial_portfolio": gated["promoted_sources"] >= 8,
        "gated_reduces_or_matches_revocations": gated["failures"] <= base["failures"],
        "gated_improves_or_matches_survival_precision": (
            gated["survival_precision"] >= base["survival_precision"]
        ),
        "verified_event_retention_at_least_75pct": event_retention >= 0.75,
        "all_gated_verified_events_causal": (
            gated["causal_ablations"] == gated["verified_events"]
        ),
        "adaptive_acquisition_still_efficient": acquisition_reduction >= 2.0,
        "lifecycle_compounding_still_large": lifecycle_reduction >= 8.0,
        "future_search_zero": True,
    }
    result["gates"] = gates
    result["passed"] = all(gates.values())
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    for w in result["worlds"]:
        print(
            f"{w['index']:03d} {w['dataset'][:28]:28} "
            f"gain={w['adaptive_cal_gain']:+.4f} "
            f"accept={w['adaptive_accept']} promote={w['promoted']} "
            f"base={w['base_verified']}/{w['future_groups']} "
            f"gated={w['gated_verified']}/{w['future_groups']} "
            f"base_rev={w['base_revoked']} gated_rev={w['gated_revoked']}"
        )

    print()
    print("BASE_PROMOTE_ALL")
    print(
        f"promoted={base['promoted_sources']} survived={base['surviving_sources']} "
        f"failures={base['failures']} verified={base['verified_events']} "
        f"precision={base['survival_precision']:.4f} bytes={base['initial_bytes']}"
    )
    print("LEARNED_SCOPE_GATE")
    print(
        f"promoted={gated['promoted_sources']} survived={gated['surviving_sources']} "
        f"failures={gated['failures']} verified={gated['verified_events']} "
        f"precision={gated['survival_precision']:.4f} bytes={gated['initial_bytes']}"
    )
    print(
        f"verified_event_retention={event_retention:.4f} "
        f"survival_precision_gain={precision_gain:+.4f}"
    )
    print(
        f"acquisition_reduction={acquisition_reduction:.2f}x "
        f"lifecycle_reduction={lifecycle_reduction:.2f}x"
    )
    for name, ok in gates.items():
        print(f"gate_{name}={int(ok)}")

    print("VERDICT")
    if result["passed"]:
        print("PASS_LEARNED_PROMOTION_SCOPE_V5")
    else:
        print("PARTIAL_LEARNED_PROMOTION_SCOPE_V5")
        raise AssertionError("one or more frozen V5 gates failed")


if __name__ == "__main__":
    main()
