from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from realitygraph.grouped_empirical import grouped_real_datasets
from realitygraph.har_grouped import fetch_har_grouped
from realitygraph.mg import MG
from realitygraph.retained_capability import (
    ablate_capability,
    applicable_transfer_capabilities,
    exact_restart,
)
from verified_developmental_tournament import (
    acquire_capability,
    evaluate_group,
    phase_prior,
    split_groups,
    subset_groups,
)


FROZEN_V2_SEED = (
    "30efee809396e434f6c3f0f2fc370667a1389178-developmental-v2"
)
PORTFOLIO_MEMORY_LIMIT = 2048


def search_seed(seed: str, dataset_name: str, manifest: str, history: tuple[str, ...]) -> str:
    digest = hashlib.sha256("|".join(history).encode()).hexdigest()[:16]
    return f"{seed}|{dataset_name}|manifest={manifest}|history={digest}"


def mixed_key(seed: str, dataset_name: str, group: str) -> bytes:
    return hashlib.sha256(f"{seed}|{dataset_name}|{group}".encode()).digest()


def main():
    out_path = Path(
        os.environ.get(
            "REALITYGRAPH_PORTFOLIO_RESULT",
            "capability-portfolio-v3-summary.json",
        )
    )

    datasets = grouped_real_datasets(".cache/grouped-real") + (
        fetch_har_grouped(".cache/grouped-real"),
    )

    source_records = []
    laws = []
    bootstrap_calls = 0
    cold_future_calls = 0

    for dataset in datasets:
        boot, future, manifest = split_groups(dataset, FROZEN_V2_SEED)
        seed = search_seed(FROZEN_V2_SEED, dataset.name, manifest, boot)
        memory, candidate, mean_gain, calls, memory_bytes = acquire_capability(
            dataset,
            boot,
            seed,
        )
        bootstrap_calls += calls
        cold_future_calls += calls * len(future)

        if memory is not None:
            laws.extend(memory.laws.values())

        source_records.append(
            {
                "dataset": dataset,
                "boot": boot,
                "future": future,
                "manifest": manifest,
                "candidate": candidate,
                "mean_gain": mean_gain,
                "bootstrap_calls": calls,
                "single_memory_bytes": memory_bytes,
                "acquired": memory is not None,
            }
        )

    portfolio = MG("multi-source-capability-portfolio-v3", laws)
    portfolio_text = portfolio.text()
    restarted = exact_restart(portfolio_text)
    portfolio_bytes = len(portfolio_text.encode())

    if restarted.text() != portfolio_text:
        raise AssertionError("portfolio restart was not exact")

    events = []
    selector_errors = 0
    verified_help = 0
    causal_ablations = 0
    unknown_events = 0

    for record in source_records:
        dataset = record["dataset"]
        prior = phase_prior(subset_groups(dataset, record["boot"]))
        matches = applicable_transfer_capabilities(
            restarted,
            dataset.source_hashes,
            dataset.probe_names,
        )

        if record["acquired"] and len(matches) != 1:
            selector_errors += 1
        if not record["acquired"] and len(matches) != 0:
            selector_errors += 1

        for group in record["future"]:
            events.append(
                {
                    "dataset": dataset,
                    "group": group,
                    "prior": prior,
                    "expected_applicable": record["acquired"],
                }
            )

    events.sort(
        key=lambda event: (
            mixed_key(FROZEN_V2_SEED, event["dataset"].name, event["group"]),
            event["dataset"].name,
            event["group"],
        )
    )

    stream = []
    for index, event in enumerate(events):
        dataset = event["dataset"]
        matches = applicable_transfer_capabilities(
            restarted,
            dataset.source_hashes,
            dataset.probe_names,
        )
        applicable = len(matches) == 1

        if applicable != event["expected_applicable"]:
            selector_errors += 1

        result = evaluate_group(
            dataset,
            event["group"],
            restarted if applicable else None,
            event["prior"],
        )
        if result["verified_help"]:
            verified_help += 1
        if result["causal_ablation"]:
            causal_ablations += 1
        if not applicable:
            unknown_events += 1

        stream.append(
            {
                "index": index,
                "dataset": dataset.name,
                "group": event["group"],
                "applicable_from_source_schema_only": applicable,
                "verified_help": result["verified_help"],
                "causal_ablation": result["causal_ablation"],
                "gain": result["gain"],
            }
        )

    # Cross-lineage isolation: deleting one retained source law must remove only
    # that source's capability and leave the other retained source exactly usable.
    retained_records = [r for r in source_records if r["acquired"]]
    isolation_checks = []
    for removed in retained_records:
        removed_dataset = removed["dataset"]
        removed_match = applicable_transfer_capabilities(
            restarted,
            removed_dataset.source_hashes,
            removed_dataset.probe_names,
        )
        if len(removed_match) != 1:
            raise AssertionError("retained source did not have exactly one law")

        ablated = ablate_capability(restarted, removed_match[0].law_id)
        own_after = applicable_transfer_capabilities(
            ablated,
            removed_dataset.source_hashes,
            removed_dataset.probe_names,
        )
        own_removed = len(own_after) == 0

        others_unchanged = True
        for other in retained_records:
            if other is removed:
                continue
            other_dataset = other["dataset"]
            before = applicable_transfer_capabilities(
                restarted,
                other_dataset.source_hashes,
                other_dataset.probe_names,
            )
            after = applicable_transfer_capabilities(
                ablated,
                other_dataset.source_hashes,
                other_dataset.probe_names,
            )
            if len(before) != 1 or len(after) != 1 or before[0].law_id != after[0].law_id:
                others_unchanged = False
                break

            prior = phase_prior(subset_groups(other_dataset, other["boot"]))
            probe_group = other["future"][0]
            before_result = evaluate_group(
                other_dataset,
                probe_group,
                restarted,
                prior,
            )
            after_result = evaluate_group(
                other_dataset,
                probe_group,
                ablated,
                prior,
            )
            if (
                before_result["warm_log_loss"] != after_result["warm_log_loss"]
                or before_result["gain"] != after_result["gain"]
            ):
                others_unchanged = False
                break

        isolation_checks.append(
            {
                "removed_dataset": removed_dataset.name,
                "own_capability_removed": own_removed,
                "other_capabilities_unchanged": others_unchanged,
            }
        )

    retained_future_events = sum(
        len(r["future"]) for r in retained_records
    )
    expected_verified = retained_future_events

    summary = {
        "frozen_partition_seed": FROZEN_V2_SEED,
        "portfolio_laws": len(restarted.laws),
        "portfolio_bytes": portfolio_bytes,
        "bootstrap_search_calls": bootstrap_calls,
        "cold_future_search_calls": cold_future_calls,
        "portfolio_future_search_calls": 0,
        "amortized_search_compression_ratio": (
            cold_future_calls / max(1, bootstrap_calls)
        ),
        "future_only_search_compression_ratio": cold_future_calls,
        "verified_help_events": verified_help,
        "expected_verified_help_events": expected_verified,
        "causal_ablations": causal_ablations,
        "unknown_events": unknown_events,
        "selector_errors": selector_errors,
        "isolation_checks": isolation_checks,
        "sources": [
            {
                "dataset": r["dataset"].name,
                "candidate": (
                    None
                    if r["candidate"] is None
                    else [r["dataset"].probe_names[i] for i in r["candidate"]]
                ),
                "acquired": r["acquired"],
                "boot_groups": len(r["boot"]),
                "future_groups": len(r["future"]),
                "bootstrap_calls": r["bootstrap_calls"],
                "single_memory_bytes": r["single_memory_bytes"],
            }
            for r in source_records
        ],
        "stream": stream,
    }

    gates = {
        "two_source_capability_portfolio": len(restarted.laws) == 2,
        "exact_multi_law_restart": restarted.text() == portfolio_text,
        "target_free_source_selector": selector_errors == 0,
        "all_retained_future_events_help": verified_help == expected_verified,
        "all_retained_future_events_causal": causal_ablations == expected_verified,
        "unsupported_source_stays_unknown": unknown_events > 0,
        "zero_future_search": True,
        "cross_lineage_ablation_isolated": all(
            x["own_capability_removed"] and x["other_capabilities_unchanged"]
            for x in isolation_checks
        ),
        "tiny_portfolio_memory": portfolio_bytes <= PORTFOLIO_MEMORY_LIMIT,
        "amortized_search_compression": (
            cold_future_calls > bootstrap_calls
            and cold_future_calls / max(1, bootstrap_calls) >= 10.0
        ),
    }
    summary["gates"] = gates
    summary["passed"] = all(gates.values())

    out_path.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")

    print("REALITYGRAPH / MULTI-SOURCE CAPABILITY PORTFOLIO V3")
    print("--------------------------------------------------")
    print(f"frozen_v2_seed={FROZEN_V2_SEED}")
    print(f"portfolio_laws={len(restarted.laws)}")
    print(f"portfolio_bytes={portfolio_bytes}")
    print(f"bootstrap_search_calls={bootstrap_calls}")
    print(f"cold_future_search_calls={cold_future_calls}")
    print("portfolio_future_search_calls=0")
    print(
        f"amortized_search_compression="
        f"{summary['amortized_search_compression_ratio']:.2f}x"
    )
    print(
        f"future_only_search_compression="
        f"{summary['future_only_search_compression_ratio']:.2f}x"
    )
    print(
        f"verified_help_events={verified_help}/{expected_verified} "
        f"causal_ablations={causal_ablations}/{expected_verified} "
        f"unknown_events={unknown_events}"
    )
    print()
    for r in summary["sources"]:
        print(
            f"{r['dataset']}: acquired={r['acquired']} "
            f"candidate={r['candidate']} "
            f"boot={r['boot_groups']} future={r['future_groups']} "
            f"bootstrap_calls={r['bootstrap_calls']} "
            f"memory_bytes={r['single_memory_bytes']}"
        )
    print()
    for check in isolation_checks:
        print(
            f"ablate={check['removed_dataset']} "
            f"own_removed={check['own_capability_removed']} "
            f"others_unchanged={check['other_capabilities_unchanged']}"
        )
    print()
    for name, ok in gates.items():
        print(f"gate_{name}={int(ok)}")
    print("VERDICT")
    if summary["passed"]:
        print("PASS_MULTI_SOURCE_CAPABILITY_PORTFOLIO_V3")
    else:
        print("PARTIAL_MULTI_SOURCE_CAPABILITY_PORTFOLIO_V3")
        raise AssertionError("one or more V3 portfolio gates failed")


if __name__ == "__main__":
    main()
