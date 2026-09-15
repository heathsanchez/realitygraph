from __future__ import annotations

import hashlib
import itertools
import os
from dataclasses import replace
from pathlib import Path

from realitygraph.grouped_empirical import GroupedBinaryDataset, grouped_real_datasets
from realitygraph.ledger import Ledger
from realitygraph.mg import MG
from realitygraph.predictive import (
    PredictiveSplit,
    binary_auc,
    binary_log_loss,
    certify_predictive_batch,
    compile_predictive_model,
    design_predictive_batch,
    evaluate_predictive_model,
    field_from_matrix,
)
from realitygraph.transfer_memory import (
    model_from_memory,
    model_memory,
    model_to_law,
)


def _hash_key(seed: str, value: str) -> bytes:
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()


def reserve_future_group(dataset: GroupedBinaryDataset, seed: str) -> str:
    groups = sorted({str(group) for group in dataset.groups})
    digest = hashlib.sha256(
        f"{seed}|{dataset.name}|{dataset.source_hashes}".encode()
    ).digest()
    return groups[int.from_bytes(digest[:8], "big") % len(groups)]


def without_group(
    dataset: GroupedBinaryDataset,
    future_group: str,
) -> GroupedBinaryDataset:
    indices = [
        i for i, group in enumerate(dataset.groups)
        if str(group) != future_group
    ]
    return replace(
        dataset,
        values=tuple(dataset.values[i] for i in indices),
        labels=tuple(dataset.labels[i] for i in indices),
        groups=tuple(dataset.groups[i] for i in indices),
    )


def select_columns(
    dataset: GroupedBinaryDataset,
    probe_indices: tuple[int, ...],
) -> GroupedBinaryDataset:
    return replace(
        dataset,
        probe_names=tuple(dataset.probe_names[i] for i in probe_indices),
        values=tuple(
            tuple(row[i] for i in probe_indices)
            for row in dataset.values
        ),
    )


def leave_one_group_split(
    groups,
    heldout: str,
    seed: str,
) -> PredictiveSplit:
    unique = sorted({str(group) for group in groups})
    remaining = [group for group in unique if group != heldout]
    ordered = sorted(remaining, key=lambda group: _hash_key(seed, group))
    cal_count = max(1, round(0.20 * len(remaining)))
    calibration_groups = set(ordered[:cal_count])
    train_groups = set(ordered[cal_count:])

    train = tuple(
        i for i, group in enumerate(groups)
        if str(group) in train_groups
    )
    calibration = tuple(
        i for i, group in enumerate(groups)
        if str(group) in calibration_groups
    )
    test = tuple(
        i for i, group in enumerate(groups)
        if str(group) == heldout
    )
    if not train or not calibration or not test:
        raise ValueError("leave-one-group split produced an empty partition")
    return PredictiveSplit(
        train,
        calibration,
        test,
        hashlib.sha256(
            f"{seed}|heldout={heldout}".encode()
        ).hexdigest()[:16],
    )


def discovery_fit_split(groups, seed: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    unique = sorted({str(group) for group in groups})
    ordered = sorted(unique, key=lambda group: _hash_key(seed, group))
    cal_count = max(1, round(0.20 * len(unique)))
    calibration_groups = set(ordered[:cal_count])
    train_groups = set(ordered[cal_count:])
    train = tuple(
        i for i, group in enumerate(groups)
        if str(group) in train_groups
    )
    calibration = tuple(
        i for i, group in enumerate(groups)
        if str(group) in calibration_groups
    )
    return train, calibration


def qualify_candidate(
    dataset: GroupedBinaryDataset,
    candidate: tuple[int, ...],
    seed: str,
) -> tuple[bool, float, int]:
    narrowed = select_columns(dataset, candidate)
    field = field_from_matrix(
        narrowed.probe_names,
        narrowed.values,
        narrowed.labels,
        narrowed.groups,
    )
    gains = []
    calls = 0
    for heldout in sorted({str(group) for group in narrowed.groups}):
        calls += 1
        split = leave_one_group_split(
            narrowed.groups,
            heldout,
            f"{seed}|candidate={candidate}",
        )
        certificate = certify_predictive_batch(
            field,
            split,
            max_probes=len(candidate),
            max_thresholds=31,
            min_calibration_gain=1e-4,
            min_sealed_gain=1e-4,
            max_group_harm=0.0,
            min_support=4,
        )
        if not certificate.accepted:
            return False, 0.0, calls
        if certificate.sealed_metrics.max_group_harm > 1e-12:
            raise AssertionError("accepted discovery world harmed its held-out group")
        gains.append(
            certificate.sealed_baseline_metrics.log_loss
            - certificate.sealed_metrics.log_loss
        )
    return True, sum(gains) / len(gains), calls


def discover_minimal_transfer(
    dataset: GroupedBinaryDataset,
    seed: str,
) -> tuple[tuple[int, ...] | None, float, int]:
    width = len(dataset.probe_names)
    max_size = 2 if width <= 8 else 1
    calls = 0

    for size in range(1, max_size + 1):
        survivors = []
        for candidate in itertools.combinations(range(width), size):
            ok, mean_gain, used = qualify_candidate(dataset, candidate, seed)
            calls += used
            if ok:
                survivors.append((mean_gain, candidate))
        if survivors:
            survivors.sort(key=lambda item: (-item[0], item[1]))
            gain, candidate = survivors[0]
            return candidate, gain, calls
    return None, 0.0, calls


def compile_from_discovery(
    dataset: GroupedBinaryDataset,
    candidate: tuple[int, ...],
    seed: str,
):
    narrowed = select_columns(dataset, candidate)
    field = field_from_matrix(
        narrowed.probe_names,
        narrowed.values,
        narrowed.labels,
        narrowed.groups,
    )
    train, calibration = discovery_fit_split(
        narrowed.groups,
        f"{seed}|compile",
    )
    plan = design_predictive_batch(
        field,
        train,
        calibration,
        max_probes=len(candidate),
        max_thresholds=63,
        min_calibration_gain=1e-4,
        max_group_harm=0.0,
        min_support=4,
    )
    if not plan.rules:
        raise AssertionError("qualified transfer candidate compiled to no rule")
    fit = train + calibration
    model = compile_predictive_model(
        field,
        plan.rules,
        fit,
        min_support=4,
    )
    return model


def evaluate_untouched_future(
    dataset: GroupedBinaryDataset,
    future_group: str,
    memory_text: str,
):
    memory = MG.parse(memory_text)
    model = model_from_memory(
        memory,
        dataset.source_hashes,
        dataset.probe_names,
    )
    field = field_from_matrix(
        dataset.probe_names,
        dataset.values,
        dataset.labels,
        dataset.groups,
    )
    future = tuple(
        i for i, group in enumerate(dataset.groups)
        if str(group) == future_group
    )
    discovery = tuple(
        i for i, group in enumerate(dataset.groups)
        if str(group) != future_group
    )
    positives = sum(dataset.labels[i] for i in discovery)
    prior = (positives + 1.0) / (len(discovery) + 2.0)
    baseline = [prior] * len(dataset.values)

    metrics = evaluate_predictive_model(
        field,
        model,
        future,
        fallback_probabilities=baseline,
        baseline_probabilities=baseline,
    )
    future_labels = [dataset.labels[i] for i in future]
    baseline_probs = [prior] * len(future)
    baseline_loss = binary_log_loss(future_labels, baseline_probs)
    baseline_auc = binary_auc(future_labels, baseline_probs)
    accepted = (
        metrics.log_loss < baseline_loss - 1e-4
        and metrics.max_group_harm <= 1e-12
    )
    return accepted, baseline_loss, baseline_auc, metrics, len(future)


def main():
    seed = os.environ.get("REALITYGRAPH_TRANSFER_COMPILE_SEED", "local-transfer-compile")
    cache = Path(".cache/grouped-real")

    print("REALITYGRAPH / EXPERIENCE BECOMES EXECUTABLE")
    print("--------------------------------------------")
    print("future group: selected from commit-derived seed before discovery")
    print("future rows: physically absent from discovery/compile dataset")
    print("promotion: candidate must survive every other natural group")
    print("runtime: reparsed .mg only; probe search disabled")
    print()

    retained = 0
    for dataset in grouped_real_datasets(cache):
        future_group = reserve_future_group(dataset, seed)
        discovery = without_group(dataset, future_group)
        discovery_groups = sorted({str(group) for group in discovery.groups})

        candidate, mean_gain, cold_calls = discover_minimal_transfer(
            discovery,
            f"{seed}|{dataset.name}|discover",
        )

        print(dataset.name)
        print(
            f"  groups={dataset.group_count} discovery_groups={len(discovery_groups)} "
            f"untouched_future={future_group}"
        )
        print(
            f"  cold_candidate_certifications={cold_calls} "
            f"candidate={None if candidate is None else [dataset.probe_names[i] for i in candidate]}"
        )

        if candidate is None:
            print("  compile=REFUSED")
            print("  .mg_bytes=0")
            print("  future_search_calls=0")
            print("  future_verdict=UNKNOWN")
            print()
            continue

        model = compile_from_discovery(
            discovery,
            candidate,
            f"{seed}|{dataset.name}",
        )
        provenance = hashlib.sha256(
            (
                f"{seed}|{dataset.name}|future={future_group}|"
                f"candidate={candidate}|gain={mean_gain:.12g}"
            ).encode()
        ).hexdigest()[:12]
        law = model_to_law(
            dataset.source_hashes,
            model,
            provenance=provenance,
        )

        ledger = Ledger()
        ledger.append_add(law, "transfer-compiler")
        pre_future_memory = ledger.materialize("sealed-natural-group-transfer-v1")
        memory_text = pre_future_memory.text()

        # Restart boundary: only serialized .mg crosses into the untouched future.
        accepted, baseline_loss, baseline_auc, metrics, future_rows = (
            evaluate_untouched_future(
                dataset,
                future_group,
                memory_text,
            )
        )

        if not accepted:
            ledger.append_revoke(
                law.id,
                "untouched-future-verifier",
                reason="compiled transfer law failed untouched natural group",
            )
        active = ledger.materialize("sealed-natural-group-transfer-v1")

        print(
            f"  compiled_rules={[rule.probe_name for rule in model.rules]} "
            f"mean_discovery_gain={mean_gain:.6f}"
        )
        print(
            f"  .mg_bytes={len(memory_text.encode())} "
            f"future_rows={future_rows} future_search_calls=0"
        )
        print(
            f"  untouched_baseline_LL={baseline_loss:.6f} "
            f"compiled_LL={metrics.log_loss:.6f} "
            f"AUC={metrics.auc:.6f} "
            f"max_group_harm={metrics.max_group_harm:.6f}"
        )
        print(
            f"  untouched_future_accepted={accepted} "
            f"active_memory_laws={len(active.laws)}"
        )

        # True ablation: delete memory and perform the discovery again.
        ablated_candidate, _, ablation_calls = discover_minimal_transfer(
            discovery,
            f"{seed}|{dataset.name}|discover",
        )
        if ablated_candidate != candidate:
            raise AssertionError("ablation search did not reconstruct compiled candidate")
        if ablation_calls <= 0:
            raise AssertionError("memory ablation failed to restore search")
        print(
            f"  ABLATION delete_.mg -> search_calls={ablation_calls} "
            f"recovered={[dataset.probe_names[i] for i in ablated_candidate]}"
        )

        if accepted:
            retained += 1
        print()

    print(f"retained_transfer_laws={retained}")
    print("VERDICT")
    print("DISCOVERY_COMPILED_INTO_ZERO_SEARCH_FUTURE_CAPABILITY")


if __name__ == "__main__":
    main()
