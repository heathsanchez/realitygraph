from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from realitygraph.grouped_empirical import grouped_real_datasets
from realitygraph.har_grouped import HAR_SHA256, fetch_har_grouped
from realitygraph.retained_capability import (
    ablate_capability,
    applicable_transfer_capabilities,
)
from verified_developmental_tournament import (
    MAX_MEMORY_BYTES,
    acquire_capability,
    evaluate_group,
    frontier_layers,
    phase_prior,
    split_groups,
    subset_groups,
    target_free_manifest,
)


def history_search_seed(
    seed: str,
    dataset_name: str,
    manifest_digest: str,
    history: tuple[str, ...],
) -> str:
    digest = hashlib.sha256("|".join(history).encode()).hexdigest()[:16]
    return f"{seed}|{dataset_name}|manifest={manifest_digest}|history={digest}"


def retire_memory(dataset, memory):
    if memory is None:
        return None
    matches = applicable_transfer_capabilities(
        memory,
        dataset.source_hashes,
        dataset.probe_names,
    )
    for match in matches:
        memory = ablate_capability(memory, match.law_id)
    if applicable_transfer_capabilities(
        memory,
        dataset.source_hashes,
        dataset.probe_names,
    ):
        raise AssertionError("retirement left an applicable capability")
    return None


def run_source(dataset, seed: str) -> dict:
    boot, future, manifest_digest = split_groups(dataset, seed)
    layers = frontier_layers(future)
    history = tuple(boot)
    total_groups = len(boot) + len(future)

    bootstrap_seed = history_search_seed(
        seed,
        dataset.name,
        manifest_digest,
        history,
    )
    (
        memory,
        bootstrap_candidate,
        bootstrap_gain,
        bootstrap_calls,
        bootstrap_bytes,
    ) = acquire_capability(dataset, history, bootstrap_seed)

    next_search_size = len(history)
    failed_acquisitions = 0
    acquired_ever = memory is not None
    if memory is None:
        failed_acquisitions = 1
        next_search_size = min(
            total_groups,
            max(len(history) + 1, 2 * len(history)),
        )

    record = {
        "dataset": dataset.name,
        "source_hashes": dataset.source_hashes,
        "manifest_digest": manifest_digest,
        "boot_groups": boot,
        "future_groups": future,
        "frontier_widths": [len(layer) for layer in layers],
        "bootstrap_candidate": None if bootstrap_candidate is None else [
            dataset.probe_names[i] for i in bootstrap_candidate
        ],
        "bootstrap_mean_gain": bootstrap_gain,
        "bootstrap_search_calls": bootstrap_calls,
        "initial_memory_bytes": bootstrap_bytes,
        "layers": [],
        "cold_future_search_calls": 0,
        "developmental_future_search_calls": 0,
        "verified_worlds": 0,
        "causal_ablations": 0,
        "revocations": 0,
        "acquisitions": int(memory is not None),
        "failed_acquisitions": failed_acquisitions,
        "missed_qualified_backoff_opportunities": 0,
        "peak_memory_bytes": bootstrap_bytes,
        "peak_active_laws": 0 if memory is None else len(memory.laws),
        "max_full_reuse_frontier": 0,
        "efficiency_trace": [],
    }

    cumulative_cold = 0
    cumulative_dev_future = 0

    for layer_index, layer in enumerate(layers):
        history_dataset = subset_groups(dataset, history)
        prior = phase_prior(history_dataset)
        search_seed = history_search_seed(
            seed,
            dataset.name,
            manifest_digest,
            history,
        )

        # Frozen cold comparator: each future world independently pays the same
        # exhaustive acquisition protocol from the same pre-frontier history.
        (
            cold_memory,
            cold_candidate,
            _cold_gain,
            cold_calls_one,
            _cold_bytes,
        ) = acquire_capability(dataset, history, search_seed)
        cold_layer_calls = cold_calls_one * len(layer)
        cumulative_cold += cold_layer_calls
        record["cold_future_search_calls"] += cold_layer_calls

        acquisition_attempted = False
        acquisition_calls = 0
        acquisition_candidate = None
        acquisition_gain = 0.0
        acquisition_bytes = 0
        skipped_for_backoff = False

        if memory is None:
            if len(history) >= next_search_size:
                acquisition_attempted = True
                (
                    memory,
                    acquisition_candidate,
                    acquisition_gain,
                    acquisition_calls,
                    acquisition_bytes,
                ) = acquire_capability(dataset, history, search_seed)
                cumulative_dev_future += acquisition_calls
                record["developmental_future_search_calls"] += acquisition_calls

                if memory is None:
                    record["failed_acquisitions"] += 1
                    next_search_size = min(
                        total_groups,
                        max(len(history) + 1, 2 * len(history)),
                    )
                else:
                    acquired_ever = True
                    record["acquisitions"] += 1
                    next_search_size = len(history)
                    record["peak_memory_bytes"] = max(
                        record["peak_memory_bytes"],
                        acquisition_bytes,
                    )
                    record["peak_active_laws"] = max(
                        record["peak_active_laws"],
                        len(memory.laws),
                    )
            else:
                skipped_for_backoff = True
                if cold_candidate is not None:
                    record["missed_qualified_backoff_opportunities"] += 1

        # The applicability manifest is frozen before this frontier's labels
        # are scored. No target value participates in invocation.
        manifest = target_free_manifest(dataset, layer, memory)
        results = []
        for event in manifest:
            result = evaluate_group(
                dataset,
                event["group"],
                memory if event["applicable"] else None,
                prior,
            )
            result["target_free_applicable"] = event["applicable"]
            result["covered_rows"] = event["covered_rows"]
            results.append(result)
            if result["verified_help"]:
                record["verified_worlds"] += 1
            if result["causal_ablation"]:
                record["causal_ablations"] += 1

        full_reuse = (
            memory is not None
            and bool(results)
            and all(result["verified_help"] for result in results)
        )
        if full_reuse:
            record["max_full_reuse_frontier"] = max(
                record["max_full_reuse_frontier"],
                len(layer),
            )
            route = "REUSE"
        elif memory is not None:
            route = "REVOKE"
            memory = retire_memory(dataset, memory)
            record["revocations"] += 1
        else:
            route = "UNKNOWN_BACKOFF" if skipped_for_backoff else "UNKNOWN"

        # Only now does this entire frontier become past evidence.
        history = history + tuple(layer)
        if route == "REVOKE":
            # A capability was falsified. Permit immediate search from the
            # newly enlarged past at the next frontier.
            next_search_size = len(history)

        active_bytes = len(memory.text().encode()) if memory is not None else 0
        active_laws = len(memory.laws) if memory is not None else 0
        record["peak_memory_bytes"] = max(
            record["peak_memory_bytes"],
            active_bytes,
        )
        record["peak_active_laws"] = max(
            record["peak_active_laws"],
            active_laws,
        )

        dev_total = bootstrap_calls + cumulative_dev_future
        saved = cumulative_cold - dev_total
        retained_bytes = max(1, active_bytes or record["peak_memory_bytes"])
        efficiency = saved / retained_bytes

        record["efficiency_trace"].append(
            {
                "layer": layer_index,
                "frontier_width": len(layer),
                "cumulative_cold_future_calls": cumulative_cold,
                "cumulative_developmental_future_calls": cumulative_dev_future,
                "bootstrap_calls": bootstrap_calls,
                "amortized_developmental_calls": dev_total,
                "cumulative_saved_calls": saved,
                "saved_calls_per_retained_byte": efficiency,
            }
        )

        record["layers"].append(
            {
                "layer": layer_index,
                "groups": layer,
                "frontier_width": len(layer),
                "cold_candidate": None if cold_candidate is None else [
                    dataset.probe_names[i] for i in cold_candidate
                ],
                "cold_search_calls": cold_layer_calls,
                "developmental_acquisition_attempted": acquisition_attempted,
                "developmental_acquisition_calls": acquisition_calls,
                "developmental_candidate": (
                    None if acquisition_candidate is None else [
                        dataset.probe_names[i] for i in acquisition_candidate
                    ]
                ),
                "developmental_mean_gain": acquisition_gain,
                "developmental_memory_bytes": acquisition_bytes,
                "skipped_for_backoff": skipped_for_backoff,
                "next_search_history_size": next_search_size,
                "target_free_manifest": manifest,
                "results": results,
                "route": route,
            }
        )

    positive_efficiencies = [
        point["saved_calls_per_retained_byte"]
        for point in record["efficiency_trace"]
        if point["cumulative_saved_calls"] > 0
    ]
    record["frontier_compounding"] = (
        len(positive_efficiencies) >= 2
        and positive_efficiencies[-1] > positive_efficiencies[0]
    )
    record["acquired_ever"] = acquired_ever
    record["amortized_developmental_search_calls"] = (
        bootstrap_calls + record["developmental_future_search_calls"]
    )
    record["amortized_search_saved"] = (
        record["cold_future_search_calls"]
        - record["amortized_developmental_search_calls"]
    )
    record["amortized_search_compression_ratio"] = (
        record["cold_future_search_calls"]
        / max(1, record["amortized_developmental_search_calls"])
    )
    record["future_only_search_compression_ratio"] = (
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
        "REALITYGRAPH_DEVELOPMENTAL_V2_SEED",
        "verified-developmental-tournament-v2",
    )
    out_path = Path(
        os.environ.get(
            "REALITYGRAPH_DEVELOPMENTAL_V2_RESULT",
            "verified-developmental-tournament-v2-summary.json",
        )
    )

    datasets = grouped_real_datasets(".cache/grouped-real") + (
        fetch_har_grouped(".cache/grouped-real"),
    )
    records = [run_source(dataset, seed) for dataset in datasets]

    acquired_sources = [r for r in records if r["acquired_ever"]]
    reused_sources = [r for r in records if r["verified_worlds"] >= 2]
    ablated_sources = [r for r in records if r["causal_ablations"] >= 2]
    compounding_sources = [r for r in records if r["frontier_compounding"]]
    har_record = next(
        r for r in records if r["dataset"].startswith("UCI HAR smartphones")
    )

    aggregate = {
        "seed": seed,
        "datasets": records,
        "cold_future_search_calls": sum(
            r["cold_future_search_calls"] for r in records
        ),
        "bootstrap_search_calls": sum(
            r["bootstrap_search_calls"] for r in records
        ),
        "developmental_future_search_calls": sum(
            r["developmental_future_search_calls"] for r in records
        ),
        "verified_worlds": sum(r["verified_worlds"] for r in records),
        "causal_ablations": sum(r["causal_ablations"] for r in records),
        "revocations": sum(r["revocations"] for r in records),
        "failed_acquisitions": sum(r["failed_acquisitions"] for r in records),
        "missed_qualified_backoff_opportunities": sum(
            r["missed_qualified_backoff_opportunities"] for r in records
        ),
        "acquired_sources": len(acquired_sources),
        "reused_sources": len(reused_sources),
        "ablated_sources": len(ablated_sources),
        "compounding_sources": len(compounding_sources),
        "peak_memory_bytes": max(r["peak_memory_bytes"] for r in records),
    }
    aggregate["amortized_developmental_search_calls"] = (
        aggregate["bootstrap_search_calls"]
        + aggregate["developmental_future_search_calls"]
    )
    aggregate["amortized_search_saved"] = (
        aggregate["cold_future_search_calls"]
        - aggregate["amortized_developmental_search_calls"]
    )
    aggregate["amortized_search_compression_ratio"] = (
        aggregate["cold_future_search_calls"]
        / max(1, aggregate["amortized_developmental_search_calls"])
    )

    gates = {
        "har_source_pinned_before_evaluation": (
            bool(HAR_SHA256)
            and any(
                digest == HAR_SHA256
                for _, digest in har_record["source_hashes"]
            )
        ),
        "source_distinct_acquisition": len(acquired_sources) >= 2,
        "source_distinct_verified_reuse": len(reused_sources) >= 2,
        "source_distinct_causal_ablation": len(ablated_sources) >= 2,
        "fresh_har_contributes": (
            har_record["acquired_ever"]
            and har_record["verified_worlds"] >= 2
            and har_record["causal_ablations"] >= 2
        ),
        "backoff_misses_no_available_capability": (
            aggregate["missed_qualified_backoff_opportunities"] == 0
        ),
        "amortized_search_reduction": (
            aggregate["amortized_search_saved"] > 0
            and aggregate["amortized_search_compression_ratio"] >= 3.0
        ),
        "branching_frontier_compounding": len(compounding_sources) >= 2,
        "wide_zero_search_reuse": any(
            r["max_full_reuse_frontier"] >= 4 for r in records
        ),
        "tiny_persistent_state": all(
            r["memory_budget_ok"] for r in records
        ),
    }
    aggregate["gates"] = gates
    aggregate["passed"] = all(gates.values())

    out_path.write_text(
        json.dumps(aggregate, sort_keys=True, indent=2, default=list) + "\n"
    )

    print("REALITYGRAPH / VERIFIED DEVELOPMENTAL TOURNAMENT V2")
    print("---------------------------------------------------")
    print("new source: pinned UCI HAR / 30 subject groups")
    print("memory: <=1 executable capability per source")
    print("novelty policy: exhaustive refusal -> exponential search backoff")
    print("backoff safety: fail if a skipped search had a qualified cold capability")
    print("future topology: target-free expanding frontiers 1,2,4,...")
    print("score: amortized future verification search, including bootstrap")
    print()

    for r in records:
        print(r["dataset"])
        print(
            f"  boot={len(r['boot_groups'])} future={len(r['future_groups'])} "
            f"frontiers={r['frontier_widths']}"
        )
        print(
            f"  bootstrap={r['bootstrap_candidate']} "
            f"bootstrap_calls={r['bootstrap_search_calls']} "
            f"peak_memory_bytes={r['peak_memory_bytes']}"
        )
        for layer in r["layers"]:
            helped = sum(1 for x in layer["results"] if x["verified_help"])
            print(
                f"    layer={layer['layer']} width={layer['frontier_width']} "
                f"helped={helped}/{layer['frontier_width']} "
                f"route={layer['route']} "
                f"cold_calls={layer['cold_search_calls']} "
                f"dev_acquire_calls={layer['developmental_acquisition_calls']} "
                f"backoff={layer['skipped_for_backoff']}"
            )
        print(
            f"  verified_worlds={r['verified_worlds']} "
            f"causal_ablations={r['causal_ablations']} "
            f"missed_backoff={r['missed_qualified_backoff_opportunities']}"
        )
        print(
            f"  amortized_compression={r['amortized_search_compression_ratio']:.2f}x "
            f"future_only_compression={r['future_only_search_compression_ratio']:.2f}x "
            f"max_full_reuse_frontier={r['max_full_reuse_frontier']} "
            f"compounding={r['frontier_compounding']}"
        )
        print()

    print("AGGREGATE")
    print(
        f"cold_future_search_calls={aggregate['cold_future_search_calls']} "
        f"bootstrap_calls={aggregate['bootstrap_search_calls']} "
        f"developmental_future_calls={aggregate['developmental_future_search_calls']}"
    )
    print(
        f"amortized_developmental_calls="
        f"{aggregate['amortized_developmental_search_calls']} "
        f"saved={aggregate['amortized_search_saved']} "
        f"compression={aggregate['amortized_search_compression_ratio']:.2f}x"
    )
    print(
        f"acquired_sources={aggregate['acquired_sources']} "
        f"reused_sources={aggregate['reused_sources']} "
        f"ablated_sources={aggregate['ablated_sources']} "
        f"compounding_sources={aggregate['compounding_sources']}"
    )
    print(
        f"verified_worlds={aggregate['verified_worlds']} "
        f"causal_ablations={aggregate['causal_ablations']} "
        f"failed_acquisitions={aggregate['failed_acquisitions']} "
        f"missed_backoff={aggregate['missed_qualified_backoff_opportunities']}"
    )
    for name, ok in gates.items():
        print(f"gate_{name}={int(ok)}")

    print("VERDICT")
    if aggregate["passed"]:
        print("PASS_VERIFIED_DEVELOPMENTAL_COMPILER_V2")
    else:
        print("PARTIAL_VERIFIED_DEVELOPMENTAL_COMPILER_V2")
        raise AssertionError("one or more frozen V2 gates failed")


if __name__ == "__main__":
    main()
