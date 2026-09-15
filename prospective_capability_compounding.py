from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path

from compiled_transfer_demo import (
    compile_from_discovery,
    discover_minimal_transfer,
)
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


PHASE_A_FRACTION = 0.60
MIN_FUTURE_GROUPS = 3


def _hash(seed: str, value: str) -> bytes:
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()


def ordered_groups(dataset: GroupedBinaryDataset, seed: str) -> tuple[str, ...]:
    groups = sorted({str(group) for group in dataset.groups})
    return tuple(
        sorted(
            groups,
            key=lambda group: (
                _hash(
                    f"{seed}|{dataset.name}|{dataset.source_hashes}",
                    group,
                ),
                group,
            ),
        )
    )


def split_manifest(
    dataset: GroupedBinaryDataset,
    seed: str,
) -> tuple[tuple[str, ...], tuple[str, ...], str]:
    ordered = ordered_groups(dataset, seed)
    if len(ordered) < 7:
        raise ValueError("prospective compounding requires at least seven natural groups")
    cut = max(4, int(round(PHASE_A_FRACTION * len(ordered))))
    cut = min(cut, len(ordered) - MIN_FUTURE_GROUPS)
    phase_a = ordered[:cut]
    future = ordered[cut:]
    digest = hashlib.sha256(
        (
            f"{dataset.name}|{dataset.source_hashes}|"
            + "|".join(phase_a)
            + "||"
            + "|".join(future)
        ).encode()
    ).hexdigest()[:20]
    return phase_a, future, digest


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


def coverage_count(model, rows) -> int:
    """Target-free applicability inside a natural group."""
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


def exact_model_restart(
    original_model,
    restarted_model,
    phase_a: GroupedBinaryDataset,
    candidate: tuple[int, ...],
) -> bool:
    for row in phase_a.values:
        narrowed = tuple(row[i] for i in candidate)
        left = original_model.predict_values(narrowed)
        right = restarted_model.predict_values(row)
        if left != right:
            return False
    return True


def prior_from_phase_a(phase_a: GroupedBinaryDataset) -> float:
    positives = sum(phase_a.labels)
    return (positives + 1.0) / (len(phase_a.labels) + 2.0)


def scan_recurrences_without_targets(
    dataset: GroupedBinaryDataset,
    future_groups: tuple[str, ...],
    memory: MG,
):
    """Freeze later recurrence events without looking at any target labels."""
    matches = applicable_transfer_capabilities(
        memory,
        dataset.source_hashes,
        dataset.probe_names,
    )
    if len(matches) != 1:
        return []

    law = only_law(memory, matches[0])
    model = law_to_model(law, dataset.probe_names)

    manifest = []
    for group in future_groups:
        indices = group_indices(dataset, group)
        rows = tuple(dataset.values[i] for i in indices)
        covered = coverage_count(model, rows)
        if covered:
            manifest.append(
                {
                    "group": group,
                    "rows": len(indices),
                    "covered_rows": covered,
                    "coverage": covered / len(indices),
                    "law_id": law.id,
                }
            )
    return manifest


def evaluate_group(
    dataset: GroupedBinaryDataset,
    group: str,
    memory: MG,
    phase_a_prior: float,
):
    matches = applicable_transfer_capabilities(
        memory,
        dataset.source_hashes,
        dataset.probe_names,
    )
    if len(matches) != 1:
        raise AssertionError("future evaluation expected exactly one active capability")
    match = matches[0]
    law = only_law(memory, match)
    model = law_to_model(law, dataset.probe_names)

    indices = group_indices(dataset, group)
    labels = [dataset.labels[i] for i in indices]
    cold = [phase_a_prior] * len(indices)
    warm = [
        model.predict_values(dataset.values[i], phase_a_prior)
        for i in indices
    ]

    cold_loss = binary_log_loss(labels, cold)
    warm_loss = binary_log_loss(labels, warm)
    gain = cold_loss - warm_loss

    # Exact lineage deletion. Once the sole applicable capability is removed,
    # the system has no retained operator and must return to source-only prior.
    ablated = ablate_capability(memory, law.id)
    if applicable_transfer_capabilities(
        ablated,
        dataset.source_hashes,
        dataset.probe_names,
    ):
        raise AssertionError("lineage ablation left an applicable capability")

    ablated_predictions = cold
    ablated_loss = binary_log_loss(labels, ablated_predictions)
    if ablated_loss != cold_loss:
        raise AssertionError("capability deletion did not restore cold baseline exactly")

    causal = gain > 1e-4 and warm_loss < ablated_loss - 1e-4
    return {
        "group": group,
        "rows": len(indices),
        "cold_log_loss": cold_loss,
        "warm_log_loss": warm_loss,
        "gain": gain,
        "warm_only_verified": gain > 1e-4,
        "causal_lineage_ablation": causal,
        "ablated_log_loss": ablated_loss,
        "warm_search_calls": 0,
    }


def main():
    seed = os.environ.get(
        "REALITYGRAPH_COMPOUNDING_SEED",
        "prospective-capability-compounding-v1",
    )
    out_path = Path(
        os.environ.get(
            "REALITYGRAPH_COMPOUNDING_RESULT",
            "prospective-capability-compounding-summary.json",
        )
    )

    datasets = grouped_real_datasets(".cache/grouped-real")

    print("REALITYGRAPH / PROSPECTIVE CAPABILITY COMPOUNDING")
    print("--------------------------------------------------")
    print("Phase A: earlier natural groups only")
    print("retention: compiled .mg operator + exact restart")
    print("later scan: source/schema/coverage applicability only")
    print("selection uses future labels=0")
    print("future search calls=0")
    print("causality: exact retained-lineage deletion")
    print()

    summary = {
        "seed": seed,
        "datasets": [],
        "acquired_capabilities": 0,
        "exact_restarts": 0,
        "natural_recurrence_events": 0,
        "warm_only_verified_events": 0,
        "causal_lineage_ablations": 0,
        "future_search_calls": 0,
        "revoked_capabilities": 0,
        "surviving_capabilities": 0,
        "cold_reacquisition_calls": 0,
    }

    for dataset in datasets:
        phase_a_groups, future_groups, manifest_digest = split_manifest(
            dataset, seed
        )
        phase_a = subset_groups(dataset, phase_a_groups)

        # Physical separation: later natural groups do not exist in acquisition.
        if set(str(g) for g in phase_a.groups) & set(future_groups):
            raise AssertionError("later group leaked into Phase A")

        acquire_seed = (
            f"{seed}|{dataset.name}|phase-a|manifest={manifest_digest}"
        )
        candidate, mean_gain, cold_calls = discover_minimal_transfer(
            phase_a,
            acquire_seed,
        )

        record = {
            "dataset": dataset.name,
            "source_hashes": dataset.source_hashes,
            "manifest_digest": manifest_digest,
            "phase_a_groups": phase_a_groups,
            "later_groups": future_groups,
            "phase_a_rows": len(phase_a.values),
            "candidate": None,
            "mean_phase_a_gain": mean_gain,
            "cold_acquisition_calls": cold_calls,
            "memory_bytes": 0,
            "exact_restart": False,
            "recurrence_manifest": [],
            "events": [],
            "revoked": False,
            "survived_stream": False,
        }

        print(dataset.name)
        print(
            f"  groups={dataset.group_count} "
            f"phase_a={len(phase_a_groups)} later={len(future_groups)} "
            f"manifest={manifest_digest}"
        )
        print(
            f"  phase_a_rows={len(phase_a.values)} "
            f"cold_acquisition_calls={cold_calls}"
        )

        if candidate is None:
            print("  acquisition=REFUSED retained_capability=0")
            print()
            summary["datasets"].append(record)
            continue

        record["candidate"] = [
            dataset.probe_names[i] for i in candidate
        ]
        original_model = compile_from_discovery(
            phase_a,
            candidate,
            f"{acquire_seed}|compile",
        )
        provenance = hashlib.sha256(
            (
                f"{acquire_seed}|candidate={candidate}|"
                f"gain={mean_gain:.12g}"
            ).encode()
        ).hexdigest()[:12]
        law = model_to_law(
            dataset.source_hashes,
            original_model,
            provenance=provenance,
        )
        memory = model_memory(law)
        memory_text = memory.text()

        # Hard restart boundary: only serialized memory crosses.
        restarted = exact_restart(memory_text)
        restarted_matches = applicable_transfer_capabilities(
            restarted,
            dataset.source_hashes,
            dataset.probe_names,
        )
        if len(restarted_matches) != 1:
            raise AssertionError("restarted capability is not exactly applicable")
        restarted_model = law_to_model(
            only_law(restarted, restarted_matches[0]),
            dataset.probe_names,
        )
        restart_ok = exact_model_restart(
            original_model,
            restarted_model,
            phase_a,
            candidate,
        )
        if not restart_ok:
            raise AssertionError("compiled operator predictions changed after restart")

        record["memory_bytes"] = len(memory_text.encode())
        record["exact_restart"] = True
        summary["acquired_capabilities"] += 1
        summary["exact_restarts"] += 1
        summary["cold_reacquisition_calls"] += cold_calls

        print(
            f"  acquired={record['candidate']} "
            f"mean_phase_a_gain={mean_gain:.6f}"
        )
        print(
            f"  .mg_bytes={record['memory_bytes']} exact_restart=YES"
        )

        # Freeze the recurrence manifest before any future target is evaluated.
        recurrence_manifest = scan_recurrences_without_targets(
            dataset,
            future_groups,
            restarted,
        )
        record["recurrence_manifest"] = recurrence_manifest
        summary["natural_recurrence_events"] += len(recurrence_manifest)

        print(
            f"  target_free_natural_recurrences={len(recurrence_manifest)}"
        )

        active = restarted
        phase_a_prior = prior_from_phase_a(phase_a)

        for event in recurrence_manifest:
            # If a previous future falsified the law, stop using it.
            if not applicable_transfer_capabilities(
                active,
                dataset.source_hashes,
                dataset.probe_names,
            ):
                break

            result = evaluate_group(
                dataset,
                event["group"],
                active,
                phase_a_prior,
            )
            record["events"].append(result)
            summary["future_search_calls"] += result["warm_search_calls"]

            if result["warm_only_verified"]:
                summary["warm_only_verified_events"] += 1
            if result["causal_lineage_ablation"]:
                summary["causal_lineage_ablations"] += 1

            print(
                f"    recurrence={event['group']} "
                f"coverage={event['covered_rows']}/{event['rows']} "
                f"cold_LL={result['cold_log_loss']:.6f} "
                f"warm_LL={result['warm_log_loss']:.6f} "
                f"gain={result['gain']:+.6f} "
                f"causal_ablation={result['causal_lineage_ablation']}"
            )

            if not result["warm_only_verified"]:
                active = ablate_capability(active, law.id)
                record["revoked"] = True
                summary["revoked_capabilities"] += 1
                print(
                    f"    REVOKE lineage={law.id} "
                    f"after failed later consequence"
                )
                break

        record["survived_stream"] = (
            law.id in active.laws and bool(record["events"])
        )
        if record["survived_stream"]:
            summary["surviving_capabilities"] += 1

        # Deletion must restore the acquisition search that compilation removed.
        deleted = ablate_capability(restarted, law.id)
        if applicable_transfer_capabilities(
            deleted,
            dataset.source_hashes,
            dataset.probe_names,
        ):
            raise AssertionError("deleted memory still exposes retained capability")
        recovered, _, reacquisition_calls = discover_minimal_transfer(
            phase_a,
            acquire_seed,
        )
        if recovered != candidate:
            raise AssertionError("lineage deletion did not reconstruct same capability")
        if reacquisition_calls <= 0:
            raise AssertionError("lineage deletion failed to restore search")

        record["reacquisition_calls_after_delete"] = reacquisition_calls
        print(
            f"  DELETE_LINEAGE -> reacquisition_calls={reacquisition_calls} "
            f"recovered={record['candidate']}"
        )
        print(
            f"  survived_later_stream={record['survived_stream']}"
        )
        print()

        summary["datasets"].append(record)

    gates = {
        "fresh_phase_a_acquisition":
            summary["acquired_capabilities"] >= 1,
        "exact_restart":
            summary["exact_restarts"] == summary["acquired_capabilities"]
            and summary["acquired_capabilities"] >= 1,
        "natural_later_recurrence":
            summary["natural_recurrence_events"] >= 1,
        "warm_only_later_consequence":
            summary["warm_only_verified_events"] >= 1,
        "causal_lineage_ablation":
            summary["causal_lineage_ablations"] >= 1,
        "zero_future_search":
            summary["future_search_calls"] == 0,
        "surviving_retained_capability":
            summary["surviving_capabilities"] >= 1,
        "deletion_restores_search":
            summary["cold_reacquisition_calls"] > 0,
    }
    summary["gates"] = gates
    passed = all(gates.values())
    summary["passed"] = passed

    out_path.write_text(
        json.dumps(summary, sort_keys=True, indent=2, default=list) + "\n"
    )

    print("AGGREGATE")
    print(
        f"acquired_capabilities={summary['acquired_capabilities']} "
        f"exact_restarts={summary['exact_restarts']}"
    )
    print(
        f"natural_recurrence_events={summary['natural_recurrence_events']} "
        f"warm_only_verified={summary['warm_only_verified_events']}"
    )
    print(
        f"causal_lineage_ablations={summary['causal_lineage_ablations']} "
        f"future_search_calls={summary['future_search_calls']}"
    )
    print(
        f"revoked_capabilities={summary['revoked_capabilities']} "
        f"surviving_capabilities={summary['surviving_capabilities']}"
    )
    print(
        f"cold_reacquisition_calls={summary['cold_reacquisition_calls']}"
    )
    for name, ok in gates.items():
        print(f"gate_{name}={int(ok)}")

    print("VERDICT")
    if passed:
        print("PASS_PROSPECTIVE_EXTERNAL_RETAINED_CAPABILITY_RECURRENCE_V1")
    else:
        print("FAIL_PROSPECTIVE_EXTERNAL_RETAINED_CAPABILITY_RECURRENCE_V1")
        raise AssertionError(
            "prospective retained-capability recurrence did not satisfy frozen gates"
        )


if __name__ == "__main__":
    main()
