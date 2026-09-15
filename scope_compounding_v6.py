from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from pmlb_meta_world import (
    DATA_URL,
    PMLB_COMMIT,
    SUMMARY_URL,
    _binary_labels,
    _descriptors,
    _download,
    _parse_dataset,
    _sample_and_cap,
    _stratified_split,
)
from probe_extended_pmlb_v6b import extended_manifest
from realitygraph.adaptive_policy import budget_features, budget_from_memory
from realitygraph.meta_policy import policy_from_memory
from realitygraph.mg import MG
from realitygraph.retained_capability import exact_restart
from scope_gate_v5 import (
    calibration_evaluation,
    compile_model,
    run_portfolio,
)
from developmental_runtime_v4 import future_groups
from realitygraph.transfer_memory import model_to_law


FROZEN_POLICY_PATH = Path("frozen-meta/adaptive_policy.mg")
FROZEN_POLICY_SHA256 = "3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
FROZEN_MANIFEST_DIGEST = "ee7def3be919efeafbad681a232fdbf44ce3fcb9f1aa6c68dfd1cab59b59fe06"
V4_EVIDENCE_DIGEST = "6f95c5d4ba84d90603a605be691cc48e0c23849ec4489e1fd7eb6e049f0d6efa"
V5_EVIDENCE_DIGEST = "36c5729c1235c021fe0086df6a8897231bf5157af7d19c6e4351f2710caca5f0"
V5_THRESHOLD = 0.04804871787364886
V6_THRESHOLD = 0.05718096689694352
START = 140
STOP = 146
MIN_GAIN = 1e-4


def manifest_digest(block):
    return hashlib.sha256(
        "\n".join(
            f"{START+i}|{row['dataset']}|{row['n_instances']}|"
            f"{row['n_features']}|{row['n_classes']}"
            for i, row in enumerate(block)
        ).encode()
    ).hexdigest()


def prepare_world(index, meta, policy, budget_policy):
    name = meta["dataset"]
    raw = _download(DATA_URL.format(name=name))
    source_sha = hashlib.sha256(raw).hexdigest()

    feature_names, rows, targets = _parse_dataset(raw)
    labels = _binary_labels(targets)
    anon_names, rows, labels = _sample_and_cap(
        name,
        feature_names,
        rows,
        labels,
    )
    train, calibration, test = _stratified_split(name, labels)
    groups = future_groups(name, test, labels)

    candidates = []
    for feature in range(len(anon_names)):
        train_values = [rows[i][feature] for i in train]
        train_labels = [labels[i] for i in train]
        descriptors = _descriptors(
            train_values,
            train_labels,
            name,
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
                f"v6|index={index}|dataset={name}|source={source_sha}|"
                f"feature={adaptive_best['feature']}|budget={budget}|"
                f"cal={adaptive_best['cal_gain']:.12g}|"
                f"v6threshold={V6_THRESHOLD:.12g}"
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
        "v5_promoted": adaptive_accept and adaptive_best["cal_gain"] >= V5_THRESHOLD,
        "v6_promoted": adaptive_accept and adaptive_best["cal_gain"] >= V6_THRESHOLD,
        "adaptive_search_cost": adaptive_cost,
        "cold_feature": cold_best["feature"],
        "cold_cal_gain": cold_best["cal_gain"],
        "cold_search_cost": cold_cost,
        "law": law,
    }


def main():
    out = Path(
        os.environ.get(
            "REALITYGRAPH_SCOPE_V6_RESULT",
            "scope-compounding-v6-summary.json",
        )
    )

    frozen_text = FROZEN_POLICY_PATH.read_text()
    frozen_sha = hashlib.sha256(frozen_text.encode()).hexdigest()
    if frozen_sha != FROZEN_POLICY_SHA256:
        raise AssertionError("frozen acquisition policy drift")
    memory = exact_restart(frozen_text)
    policy = policy_from_memory(memory)
    budget_policy = budget_from_memory(memory)

    summary_raw = _download(SUMMARY_URL)
    summary_sha = hashlib.sha256(summary_raw).hexdigest()
    manifest = extended_manifest(summary_raw)
    if len(manifest) != 146:
        raise AssertionError(f"PMLB classification universe drift: {len(manifest)}")
    block = manifest[START:STOP]
    digest = manifest_digest(block)
    if digest != FROZEN_MANIFEST_DIGEST:
        raise AssertionError(f"V6 manifest drift: {digest}")

    print("REALITYGRAPH / SCOPE COMPOUNDING V6")
    print("----------------------------------")
    print(f"v4_evidence_digest={V4_EVIDENCE_DIGEST}")
    print(f"v5_evidence_digest={V5_EVIDENCE_DIGEST}")
    print(f"v5_threshold={V5_THRESHOLD:.17g}")
    print(f"v6_threshold={V6_THRESHOLD:.17g}")
    print(f"manifest_digest={digest}")
    print(f"summary_sha256={summary_sha}")
    print("fresh_block=140:146")
    print("entire_remaining_pmlb_classification_universe=1")
    print("future_labels_used_for_promotion=0")
    print()

    worlds = [
        prepare_world(START + i, meta, policy, budget_policy)
        for i, meta in enumerate(block)
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
    event_retention_vs_base = v6["verified_events"] / max(1, base["verified_events"])
    event_retention_vs_v5 = v6["verified_events"] / max(1, v5["verified_events"])

    result = {
        "frozen_policy_sha256": frozen_sha,
        "manifest_digest": digest,
        "summary_sha256": summary_sha,
        "v4_evidence_digest": V4_EVIDENCE_DIGEST,
        "v5_evidence_digest": V5_EVIDENCE_DIGEST,
        "v5_threshold": V5_THRESHOLD,
        "v6_threshold": V6_THRESHOLD,
        "indices": list(range(START, STOP)),
        "pmlb_commit": PMLB_COMMIT,
        "worlds": [
            {
                "index": w["index"],
                "dataset": w["dataset"],
                "source_sha256": w["source_sha256"],
                "features": len(w["feature_names"]),
                "future_groups": len(w["future_groups"]),
                "budget": w["budget"],
                "adaptive_cal_gain": w["adaptive_cal_gain"],
                "adaptive_accept": w["adaptive_accept"],
                "v5_promoted": w["v5_promoted"],
                "v6_promoted": w["v6_promoted"],
                "adaptive_search_cost": w["adaptive_search_cost"],
                "cold_search_cost": w["cold_search_cost"],
                "base_verified": base["source_stats"][w["index"]]["verified"],
                "base_revoked": base["source_stats"][w["index"]]["revoked"],
                "v5_verified": v5["source_stats"][w["index"]]["verified"],
                "v5_revoked": v5["source_stats"][w["index"]]["revoked"],
                "v6_verified": v6["source_stats"][w["index"]]["verified"],
                "v6_revoked": v6["source_stats"][w["index"]]["revoked"],
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
        "event_retention_vs_base": event_retention_vs_base,
        "event_retention_vs_v5": event_retention_vs_v5,
    }

    gates = {
        "manifest_frozen_before_payloads": digest == FROZEN_MANIFEST_DIGEST,
        "entire_final_pmlb_remainder": list(range(START, STOP)) == list(range(140, 146)),
        "compounded_scope_threshold_frozen": abs(V6_THRESHOLD - 0.05718096689694352) < 1e-15,
        "nontrivial_v6_portfolio": v6["promoted_sources"] >= 2,
        "v6_revocations_no_worse_than_base": v6["failures"] <= base["failures"],
        "v6_survival_precision_no_worse_than_base": (
            v6["survival_precision"] >= base["survival_precision"]
        ),
        "v6_not_worse_than_v5_precision": (
            v6["survival_precision"] >= v5["survival_precision"]
        ),
        "v6_retains_at_least_75pct_base_verified_events": (
            event_retention_vs_base >= 0.75
        ),
        "every_v6_verified_event_causal": (
            v6["causal_ablations"] == v6["verified_events"]
        ),
        "adaptive_acquisition_reduction": acquisition_reduction >= 2.0,
        "lifecycle_reduction": lifecycle_reduction >= 8.0,
        "future_search_zero": True,
    }
    result["gates"] = gates
    result["passed"] = all(gates.values())
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    for w in result["worlds"]:
        print(
            f"{w['index']:03d} {w['dataset'][:18]:18} "
            f"gain={w['adaptive_cal_gain']:+.4f} "
            f"A={w['adaptive_accept']} V5={w['v5_promoted']} V6={w['v6_promoted']} "
            f"base={w['base_verified']}/{w['future_groups']} r={w['base_revoked']} "
            f"v5={w['v5_verified']}/{w['future_groups']} r={w['v5_revoked']} "
            f"v6={w['v6_verified']}/{w['future_groups']} r={w['v6_revoked']}"
        )

    print()
    for name, stats in (("BASE", base), ("V5", v5), ("V6", v6)):
        print(
            f"{name}: promoted={stats['promoted_sources']} "
            f"survived={stats['surviving_sources']} failures={stats['failures']} "
            f"verified={stats['verified_events']} "
            f"precision={stats['survival_precision']:.4f} "
            f"bytes={stats['initial_bytes']}"
        )
    print(
        f"event_retention_vs_base={event_retention_vs_base:.4f} "
        f"event_retention_vs_v5={event_retention_vs_v5:.4f}"
    )
    print(
        f"acquisition_reduction={acquisition_reduction:.2f}x "
        f"lifecycle_reduction={lifecycle_reduction:.2f}x"
    )
    for name, ok in gates.items():
        print(f"gate_{name}={int(ok)}")

    print("VERDICT")
    if result["passed"]:
        print("PASS_SCOPE_COMPOUNDING_V6")
    else:
        print("PARTIAL_SCOPE_COMPOUNDING_V6")
        raise AssertionError("one or more frozen V6 gates failed")


if __name__ == "__main__":
    main()
