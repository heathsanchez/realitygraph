from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

from compiled_transfer_demo import compile_from_discovery, discover_minimal_transfer
from realitygraph.grouped_empirical import GroupedBinaryDataset, grouped_real_datasets
from realitygraph.mg import MG
from realitygraph.predictive import binary_log_loss
from realitygraph.retained_capability import (
    ablate_capability,
    applicable_transfer_capabilities,
    exact_restart,
    only_law,
)
from realitygraph.transfer_memory import law_to_model, model_memory, model_to_law


BOOT_FRACTION = 0.45
MIN_BOOT_GROUPS = 4
MIN_FUTURE_GROUPS = 7
MAX_MEMORY_BYTES = 8192
MIN_GAIN = 1e-4


def _hash(seed: str, value: str) -> bytes:
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()


def ordered_groups(dataset: GroupedBinaryDataset, seed: str) -> tuple[str, ...]:
    groups = sorted({str(group) for group in dataset.groups})
    return tuple(
        sorted(
            groups,
            key=lambda group: (
                _hash(f"{seed}|{dataset.name}|{dataset.source_hashes}", group),
                group,
            ),
        )
    )


def split_groups(
    dataset: GroupedBinaryDataset,
    seed: str,
) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    ordered = ordered_groups(dataset, seed)
    if len(ordered) < MIN_BOOT_GROUPS + MIN_FUTURE_GROUPS:
        raise ValueError("developmental tournament requires more natural groups")
    boot_count = max(MIN_BOOT_GROUPS, int(round(BOOT_FRACTION * len(ordered))))
    boot_count = min(boot_count, len(ordered) - MIN_FUTURE_GROUPS)
    boot = ordered[:boot_count]
    future = ordered[boot_count:]
    digest = hashlib.sha256(
        (
            f"{dataset.name}|{dataset.source_hashes}|"
            + "|".join(boot)
            + "||"
            + "|".join(future)
        ).encode()
    ).hexdigest()[:20]
    return boot, future, digest


def frontier_layers(groups: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    layers = []
    cursor = 0
    width = 1
    while cursor < len(groups):
        layer = groups[cursor:cursor + width]
        if not layer:
            break
        layers.append(layer)
        cursor += len(layer)
        width *= 2
    return tuple(layers)


def subset_groups(
    dataset: GroupedBinaryDataset,
    groups: tuple[str, ...],
) -> GroupedBinaryDataset:
    keep = set(groups)
    indices = [
        i for i, group in enumerate(dataset.groups)
        if str(group) in keep
    ]
    if not indices:
        raise ValueError("group subset is empty")
    return replace(
        dataset,
        values=tuple(dataset.values[i] for i in indices),
        labels=tuple(dataset.labels[i] for i in indices),
        groups=tuple(dataset.groups[i] for i in indices),
    )


def group_indices(dataset: GroupedBinaryDataset, group: str) -> tuple[int, ...]:
    return tuple(
        i for i, value in enumerate(dataset.groups)
        if str(value) == group
    )


def phase_prior(dataset: GroupedBinaryDataset) -> float:
    positives = sum(dataset.labels)
    return (positives + 1.0) / (len(dataset.labels) + 2.0)


def coverage_count(model, rows) -> int:
    table = {
        signature: support
        for signature, _, support in model.decoder
    }
    covered = 0
    for row in rows:
        signature = tuple(rule.observe(row) for rule in model.rules)
        if table.get(signature, 0) >= model.min_support:
            covered += 1
    return covered


def acquire_capability(
    dataset: GroupedBinaryDataset,
    history_groups: tuple[str, ...],
    seed: str,
):
    history = subset_groups(dataset, history_groups)
    candidate, mean_gain, search_calls = discover_minimal_transfer(history, seed)
    if candidate is None:
        return None, None, mean_gain, search_calls, 0

    model = compile_from_discovery(
        history,
        candidate,
        f"{seed}|compile",
    )
    provenance = hashlib.sha256(
        (
            f"{seed}|history={'|'.join(history_groups)}|"
            f"candidate={candidate}|gain={mean_gain:.12g}"
        ).encode()
    ).hexdigest()[:12]
    law = model_to_law(
        dataset.source_hashes,
        model,
        provenance=provenance,
    )
    memory = model_memory(law)
    memory_text = memory.text()
    restarted = exact_restart(memory_text)

    matches = applicable_transfer_capabilities(
        restarted,
        dataset.source_hashes,
        dataset.probe_names,
    )
    if len(matches) != 1:
        raise AssertionError("acquired capability did not survive exact restart")
    restarted_model = law_to_model(
        only_law(restarted, matches[0]),
        dataset.probe_names,
    )
    for row in history.values:
        narrowed = tuple(row[i] for i in candidate)
        if model.predict_values(narrowed) != restarted_model.predict_values(row):
            raise AssertionError("restart changed compiled capability behavior")

    return restarted, candidate, mean_gain, search_calls, len(memory_text.encode())


def target_free_manifest(
    dataset: GroupedBinaryDataset,
    layer: tuple[str, ...],
    memory: MG | None,
) -> list[dict]:
    """Freeze applicability before any target labels from this frontier are scored."""
    manifest = []
    if memory is None:
        for group in layer:
            manifest.append(
                {
                    "group": group,
                    "rows": len(group_indices(dataset, group)),
                    "covered_rows": 0,
                    "coverage": 0.0,
                    "applicable": False,
                }
            )
        return manifest

    matches = applicable_transfer_capabilities(
        memory,
        dataset.source_hashes,
        dataset.probe_names,
    )
    if len(matches) != 1:
        raise AssertionError("frontier expected zero or one retained capability")
    model = law_to_model(
        only_law(memory, matches[0]),
        dataset.probe_names,
    )

    for group in layer:
        indices = group_indices(dataset, group)
        rows = tuple(dataset.values[i] for i in indices)
        covered = coverage_count(model, rows)
        manifest.append(
            {
                "group": group,
                "rows": len(indices),
                "covered_rows": covered,
                "coverage": covered / len(indices),
                "applicable": covered > 0,
            }
        )
    return manifest


def evaluate_group(
    dataset: GroupedBinaryDataset,
    group: str,
    memory: MG | None,
    prior: float,
) -> dict:
    indices = group_indices(dataset, group)
    labels = [dataset.labels[i] for i in indices]
    cold = [prior] * len(indices)
    cold_loss = binary_log_loss(labels, cold)

    if memory is None:
        return {
            "group": group,
            "rows": len(indices),
            "cold_log_loss": cold_loss,
            "warm_log_loss": cold_loss,
            "gain": 0.0,
            "verified_help": False,
            "causal_ablation": False,
        }

    matches = applicable_transfer_capabilities(
        memory,
        dataset.source_hashes,
        dataset.probe_names,
    )
    if len(matches) != 1:
        raise AssertionError("evaluation expected exactly one retained capability")
    law = only_law(memory, matches[0])
    model = law_to_model(law, dataset.probe_names)
    warm = [model.predict_values(dataset.values[i], prior) for i in indices]
    warm_loss = binary_log_loss(labels, warm)
    gain = cold_loss - warm_loss

    ablated = ablate_capability(memory, law.id)
    if applicable_transfer_capabilities(
        ablated,
        dataset.source_hashes,
        dataset.probe_names,
    ):
        raise AssertionError("lineage deletion left applicable capability")

    ablated_loss = binary_log_loss(labels, cold)
    causal = gain > MIN_GAIN and warm_loss < ablated_loss - MIN_GAIN
    return {
        "group": group,
        "rows": len(indices),
        "cold_log_loss": cold_loss,
        "warm_log_loss": warm_loss,
        "gain": gain,
        "verified_help": gain > MIN_GAIN,
        "causal_ablation": causal,
    }


def developmental_dataset(
    dataset: GroupedBinaryDataset,
    seed: str,
) -> dict:
    boot, future, manifest_digest = split_groups(dataset, seed)
    layers = frontier_layers(future)
    history = tuple(boot)

    initial_memory, initial_candidate, initial_gain, bootstrap_calls, initial_bytes = (
        acquire_capability(
            dataset,
            history,
            f"{seed}|{dataset.name}|bootstrap|{manifest_digest}",
        )
    )

    record = {
        "dataset": dataset.name,
        "source_hashes": dataset.source_hashes,
        "manifest_digest": manifest_digest,
        "boot_groups": boot,
        "future_groups": future,
        "frontier_widths": [len(layer) for layer in layers],
        "bootstrap_candidate": None if initial_candidate is None else [
            dataset.probe_names[i] for i in initial_candidate
        ],
        "bootstrap_mean_gain": initial_gain,
        "bootstrap_search_calls": bootstrap_calls,
        "initial_memory_bytes": initial_bytes,
        "layers": [],
        "cold_future_search_calls": 0,
        "developmental_future_search_calls": 0,
        "static_verified_worlds": 0,
        "developmental_verified_worlds": 0,
        "causal_ablations": 0,
        "recompilations": 0,
        "revocations": 0,
        "peak_memory_bytes": initial_bytes,
        "peak_active_laws": 0 if initial_memory is None else len(initial_memory.laws),
        "saved_search_trace": [],
    }

    developmental = initial_memory
    static = initial_memory
    cumulative_cold = 0
    cumulative_dev = 0

    for layer_index, layer in enumerate(layers):
        history_dataset = subset_groups(dataset, history)
        prior = phase_prior(history_dataset)

        # Matched cold protocol: every independent future world reconstructs from
        # exactly the same pre-frontier history and frozen search order.
        _, _, _, cold_calls_one, _ = acquire_capability(
            dataset,
            history,
            f"{seed}|{dataset.name}|cold-layer={layer_index}|{manifest_digest}",
        )
        cold_layer_calls = cold_calls_one * len(layer)
        cumulative_cold += cold_layer_calls
        record["cold_future_search_calls"] += cold_layer_calls

        # Applicability is frozen without reading target labels for this layer.
        manifest = target_free_manifest(dataset, layer, developmental)

        dev_results = []
        static_results = []
        for event in manifest:
            result = evaluate_group(
                dataset,
                event["group"],
                developmental if event["applicable"] else None,
                prior,
            )
            result["target_free_applicable"] = event["applicable"]
            result["covered_rows"] = event["covered_rows"]
            dev_results.append(result)
            if result["verified_help"]:
                record["developmental_verified_worlds"] += 1
            if result["causal_ablation"]:
                record["causal_ablations"] += 1

            static_event = target_free_manifest(
                dataset,
                (event["group"],),
                static,
            )[0]
            static_result = evaluate_group(
                dataset,
                event["group"],
                static if static_event["applicable"] else None,
                prior,
            )
            static_results.append(static_result)
            if static_result["verified_help"]:
                record["static_verified_worlds"] += 1

        # The whole frontier is revealed together. Any failed world blocks blind
        # retention into the next frontier; repair is allowed only after these
        # outcomes become past evidence.
        frontier_pass = bool(dev_results) and all(
            result["verified_help"] for result in dev_results
        )
        route = "REUSE" if frontier_pass else "REVOKE_RECOMPILE"

        history = history + tuple(layer)
        reacquisition_calls = 0
        next_memory_bytes = 0

        if not frontier_pass:
            if developmental is not None:
                matches = applicable_transfer_capabilities(
                    developmental,
                    dataset.source_hashes,
                    dataset.probe_names,
                )
                for match in matches:
                    developmental = ablate_capability(developmental, match.law_id)
                record["revocations"] += 1

            if layer_index + 1 < len(layers):
                (
                    developmental,
                    candidate,
                    mean_gain,
                    reacquisition_calls,
                    next_memory_bytes,
                ) = acquire_capability(
                    dataset,
                    history,
                    (
                        f"{seed}|{dataset.name}|repair-after-layer={layer_index}|"
                        f"{manifest_digest}"
                    ),
                )
                record["recompilations"] += int(developmental is not None)
                record["developmental_future_search_calls"] += reacquisition_calls
                cumulative_dev += reacquisition_calls
            else:
                candidate = None
                mean_gain = 0.0
        else:
            next_memory_bytes = (
                len(developmental.text().encode())
                if developmental is not None
                else 0
            )
            candidate = None
            mean_gain = 0.0

        active_laws = 0 if developmental is None else len(developmental.laws)
        record["peak_active_laws"] = max(record["peak_active_laws"], active_laws)
        record["peak_memory_bytes"] = max(
            record["peak_memory_bytes"],
            next_memory_bytes,
        )

        saved = cumulative_cold - cumulative_dev
        bytes_now = max(1, next_memory_bytes or record["peak_memory_bytes"])
        efficiency = saved / bytes_now
        record["saved_search_trace"].append(
            {
                "layer": layer_index,
                "frontier_width": len(layer),
                "cumulative_cold_calls": cumulative_cold,
                "cumulative_developmental_calls": cumulative_dev,
                "cumulative_saved_calls": saved,
                "saved_calls_per_retained_byte": efficiency,
            }
        )

        record["layers"].append(
            {
                "layer": layer_index,
                "groups": layer,
                "frontier_width": len(layer),
                "target_free_manifest": manifest,
                "developmental_results": dev_results,
                "static_results": static_results,
                "route": route,
                "cold_search_calls": cold_layer_calls,
                "developmental_search_calls": reacquisition_calls,
                "next_candidate": None if candidate is None else [
                    dataset.probe_names[i] for i in candidate
                ],
                "next_mean_gain": mean_gain,
                "next_memory_bytes": next_memory_bytes,
            }
        )

    efficiencies = [
        point["saved_calls_per_retained_byte"]
        for point in record["saved_search_trace"]
        if point["cumulative_saved_calls"] > 0
    ]
    record["frontier_compounding"] = (
        len(efficiencies) >= 2
        and efficiencies[-1] > efficiencies[0]
    )
    record["future_search_saved"] = (
        record["cold_future_search_calls"]
        - record["developmental_future_search_calls"]
    )
    record["search_compression_ratio"] = (
        record["cold_future_search_calls"]
        / max(1, record["developmental_future_search_calls"])
    )
    record["memory_budget_ok"] = (
        record["peak_active_laws"] <= 1
        and record["peak_memory_bytes"] <= MAX_MEMORY_BYTES
    )
    return record


def main():
    seed = os.environ.get(
        "REALITYGRAPH_DEVELOPMENTAL_SEED",
        "verified-developmental-tournament-v1",
    )
    out_path = Path(
        os.environ.get(
            "REALITYGRAPH_DEVELOPMENTAL_RESULT",
            "verified-developmental-tournament-summary.json",
        )
    )

    datasets = grouped_real_datasets(".cache/grouped-real")
    print("REALITYGRAPH / VERIFIED DEVELOPMENTAL TOURNAMENT")
    print("------------------------------------------------")
    print("future topology: target-free expanding natural-group frontiers 1,2,4,...")
    print("cold comparator: independent frozen reconstruction per future world")
    print("developmental state: at most one executable law per source")
    print("retention: exact serialized restart")
    print("future reuse: zero search")
    print("failure response: revoke, then recompile only after failed frontier becomes past")
    print("score: future verifier search eliminated per retained byte")
    print()

    records = [developmental_dataset(dataset, seed) for dataset in datasets]

    aggregate = {
        "seed": seed,
        "datasets": records,
        "bootstrap_search_calls": sum(r["bootstrap_search_calls"] for r in records),
        "cold_future_search_calls": sum(r["cold_future_search_calls"] for r in records),
        "developmental_future_search_calls": sum(
            r["developmental_future_search_calls"] for r in records
        ),
        "future_search_saved": sum(r["future_search_saved"] for r in records),
        "developmental_verified_worlds": sum(
            r["developmental_verified_worlds"] for r in records
        ),
        "static_verified_worlds": sum(r["static_verified_worlds"] for r in records),
        "causal_ablations": sum(r["causal_ablations"] for r in records),
        "recompilations": sum(r["recompilations"] for r in records),
        "revocations": sum(r["revocations"] for r in records),
        "peak_memory_bytes": max(r["peak_memory_bytes"] for r in records),
    }

    aggregate["search_compression_ratio"] = (
        aggregate["cold_future_search_calls"]
        / max(1, aggregate["developmental_future_search_calls"])
    )

    gates = {
        "fresh_bootstrap_acquisition": all(
            r["bootstrap_candidate"] is not None for r in records
        ),
        "branching_future_frontier": all(
            len(r["frontier_widths"]) >= 2 and max(r["frontier_widths"]) >= 2
            for r in records
        ),
        "verified_future_reuse": aggregate["developmental_verified_worlds"] >= 2,
        "causal_lineage_ablation": aggregate["causal_ablations"] >= 2,
        "future_search_reduction": aggregate["future_search_saved"] > 0,
        "tiny_persistent_state": all(r["memory_budget_ok"] for r in records),
        "frontier_compounding": any(r["frontier_compounding"] for r in records),
    }
    aggregate["gates"] = gates
    aggregate["passed"] = all(gates.values())

    out_path.write_text(
        json.dumps(aggregate, sort_keys=True, indent=2, default=list) + "\n"
    )

    for record in records:
        print(record["dataset"])
        print(
            f"  boot={len(record['boot_groups'])} "
            f"future={len(record['future_groups'])} "
            f"frontiers={record['frontier_widths']}"
        )
        print(
            f"  bootstrap_candidate={record['bootstrap_candidate']} "
            f"bootstrap_search_calls={record['bootstrap_search_calls']} "
            f"memory_bytes={record['initial_memory_bytes']}"
        )
        for layer in record["layers"]:
            helped = sum(
                1 for x in layer["developmental_results"] if x["verified_help"]
            )
            print(
                f"    layer={layer['layer']} width={layer['frontier_width']} "
                f"helped={helped}/{layer['frontier_width']} "
                f"route={layer['route']} "
                f"cold_calls={layer['cold_search_calls']} "
                f"dev_calls={layer['developmental_search_calls']}"
            )
        print(
            f"  future_search_saved={record['future_search_saved']} "
            f"compression={record['search_compression_ratio']:.2f}x "
            f"peak_memory_bytes={record['peak_memory_bytes']} "
            f"frontier_compounding={record['frontier_compounding']}"
        )
        print()

    print("AGGREGATE")
    print(
        f"cold_future_search_calls={aggregate['cold_future_search_calls']} "
        f"developmental_future_search_calls={aggregate['developmental_future_search_calls']} "
        f"saved={aggregate['future_search_saved']}"
    )
    print(
        f"search_compression_ratio={aggregate['search_compression_ratio']:.2f}x "
        f"developmental_verified_worlds={aggregate['developmental_verified_worlds']} "
        f"static_verified_worlds={aggregate['static_verified_worlds']}"
    )
    print(
        f"causal_ablations={aggregate['causal_ablations']} "
        f"recompilations={aggregate['recompilations']} "
        f"revocations={aggregate['revocations']} "
        f"peak_memory_bytes={aggregate['peak_memory_bytes']}"
    )
    for name, ok in gates.items():
        print(f"gate_{name}={int(ok)}")

    print("VERDICT")
    if aggregate["passed"]:
        print("PASS_VERIFIED_DEVELOPMENTAL_TOURNAMENT_V1")
    else:
        print("PARTIAL_VERIFIED_DEVELOPMENTAL_TOURNAMENT_V1")
        raise AssertionError("one or more frozen developmental gates failed")


if __name__ == "__main__":
    main()
