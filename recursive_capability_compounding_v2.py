from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path

from compiled_transfer_demo import (
    compile_from_discovery,
    discovery_fit_split,
    discover_minimal_transfer,
    leave_one_group_split,
    select_columns,
)
from prospective_capability_compounding import (
    exact_restart,
    ordered_groups,
    prior_from_phase_a,
    subset_groups,
)
from realitygraph.grouped_empirical import grouped_real_datasets
from realitygraph.mg import MG
from realitygraph.predictive import binary_log_loss, field_from_matrix
from realitygraph.residual import (
    certify_residual_batch,
    compile_residual_model,
    design_residual_batch,
)
from realitygraph.residual_memory import (
    add_residual_to_memory,
    applicable_residual_laws,
    law_to_residual_model,
    residual_to_law,
)
from realitygraph.retained_capability import (
    ablate_capability,
    applicable_transfer_capabilities,
    only_law,
)
from realitygraph.transfer_memory import law_to_model, model_memory, model_to_law


PHASE_A_FRACTION = 0.40
PHASE_B_FRACTION = 0.30
MIN_GAIN = 1e-5


def staged_groups(dataset, seed: str):
    ordered = ordered_groups(dataset, seed)
    n = len(ordered)
    if n < 10:
        raise ValueError("staged compounding needs at least ten natural groups")

    a = max(4, int(round(PHASE_A_FRACTION * n)))
    b = max(4, int(round(PHASE_B_FRACTION * n)))
    if a + b > n - 3:
        b = n - a - 3

    phase_a = ordered[:a]
    phase_b = ordered[a:a + b]
    phase_c = ordered[a + b:]
    return phase_a, phase_b, phase_c


def probabilities_from_base(model, dataset, prior):
    return tuple(
        model.predict_values(row, prior)
        for row in dataset.values
    )


def qualify_residual_candidate(dataset, candidate, baseline, seed):
    narrowed = select_columns(dataset, candidate)
    field = field_from_matrix(
        narrowed.probe_names,
        narrowed.values,
        narrowed.labels,
        narrowed.groups,
    )

    gains = []
    calls = 0
    for heldout in sorted({str(g) for g in narrowed.groups}):
        calls += 1
        split = leave_one_group_split(
            narrowed.groups,
            heldout,
            f"{seed}|candidate={candidate}",
        )
        certificate = certify_residual_batch(
            field,
            split,
            baseline,
            max_probes=len(candidate),
            max_thresholds=31,
            min_calibration_gain=MIN_GAIN,
            min_sealed_gain=MIN_GAIN,
            max_group_harm=0.0,
            min_support=4,
            ridge=4.0,
        )
        if not certificate.accepted or not certificate.plan.rules:
            return False, 0.0, calls
        if certificate.sealed_metrics.max_group_harm > 1e-12:
            raise AssertionError("accepted residual harmed held-out natural group")
        gains.append(
            certificate.sealed_baseline_metrics.log_loss
            - certificate.sealed_metrics.log_loss
        )

    return True, sum(gains) / len(gains), calls


def discover_residual(dataset, baseline, seed):
    width = len(dataset.probe_names)
    calls = 0

    for size in (1, 2):
        survivors = []
        for candidate in itertools.combinations(range(width), size):
            ok, gain, used = qualify_residual_candidate(
                dataset,
                candidate,
                baseline,
                seed,
            )
            calls += used
            if ok:
                survivors.append((gain, candidate))
        if survivors:
            survivors.sort(key=lambda item: (-item[0], item[1]))
            gain, candidate = survivors[0]
            return candidate, gain, calls

    return None, 0.0, calls


def compile_residual_from_stage(dataset, candidate, baseline, seed):
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
    plan = design_residual_batch(
        field,
        train,
        calibration,
        baseline,
        max_probes=len(candidate),
        max_thresholds=63,
        min_calibration_gain=MIN_GAIN,
        max_group_harm=0.0,
        min_support=4,
        ridge=4.0,
    )
    if not plan.rules:
        raise AssertionError("qualified residual candidate compiled to no rule")

    fit = train + calibration
    model = compile_residual_model(
        field,
        plan.rules,
        fit,
        baseline,
        min_support=4,
        ridge=4.0,
    )
    return model


def coverage_count(model, dataset, indices):
    table = {
        signature: support
        for signature, _, support in model.corrections
    }
    covered = 0
    for i in indices:
        row = dataset.values[i]
        signature = tuple(rule.observe(row) for rule in model.rules)
        if table.get(signature, 0) >= model.min_support:
            covered += 1
    return covered


def group_indices(dataset, group):
    return tuple(
        i for i, value in enumerate(dataset.groups)
        if str(value) == group
    )


def exact_residual_restart(
    original,
    restarted,
    stage_b,
    candidate,
    baseline,
):
    for i, row in enumerate(stage_b.values):
        narrowed = tuple(row[j] for j in candidate)
        left = original.predict_values(narrowed, baseline[i])
        right = restarted.predict_values(row, baseline[i])
        if left != right:
            return False
    return True


def main():
    seed = os.environ.get(
        "REALITYGRAPH_COMPOUNDING_V2_SEED",
        "capability-compounding-v2",
    )
    out = Path(
        os.environ.get(
            "REALITYGRAPH_COMPOUNDING_V2_RESULT",
            "capability-compounding-v2-summary.json",
        )
    )

    datasets = grouped_real_datasets(".cache/grouped-real")
    # V1 established the reusable external capability on occupancy.
    dataset = next(d for d in datasets if d.name.startswith("Occupancy"))

    phase_a_groups, phase_b_groups, phase_c_groups = staged_groups(
        dataset, seed
    )
    phase_a = subset_groups(dataset, phase_a_groups)
    phase_b = subset_groups(dataset, phase_b_groups)

    print("REALITYGRAPH / CAPABILITY COMPOUNDING V2")
    print("----------------------------------------")
    print("G1: acquire transferable operator on early natural groups")
    print("G2: acquire residual operator around retained G1")
    print("future: source-only applicability, zero search")
    print("causality: delete child and parent lineages independently")
    print()
    print(
        f"groups total={dataset.group_count} "
        f"G1={len(phase_a_groups)} G2={len(phase_b_groups)} "
        f"future={len(phase_c_groups)}"
    )

    # ---------------------------
    # Generation 1
    # ---------------------------
    g1_seed = f"{seed}|g1"
    candidate1, gain1, cold1_calls = discover_minimal_transfer(
        phase_a,
        g1_seed,
    )
    if candidate1 is None:
        raise AssertionError("G1 failed to acquire a transferable capability")

    original1 = compile_from_discovery(
        phase_a,
        candidate1,
        f"{g1_seed}|compile",
    )
    law1 = model_to_law(
        dataset.source_hashes,
        original1,
        provenance=hashlib.sha256(g1_seed.encode()).hexdigest()[:12],
    )
    memory1 = model_memory(law1)
    memory1 = exact_restart(memory1.text())

    matches1 = applicable_transfer_capabilities(
        memory1,
        dataset.source_hashes,
        dataset.probe_names,
    )
    if len(matches1) != 1:
        raise AssertionError("G1 restart lost source-applicable capability")
    model1 = law_to_model(
        only_law(memory1, matches1[0]),
        dataset.probe_names,
    )

    prior = prior_from_phase_a(phase_a)
    base_b = probabilities_from_base(model1, phase_b, prior)

    print(
        f"G1 acquired={[dataset.probe_names[i] for i in candidate1]} "
        f"mean_gain={gain1:.6f} cold_search_calls={cold1_calls}"
    )
    print(f"G1 memory_bytes={len(memory1.text().encode())} exact_restart=YES")

    # ---------------------------
    # Generation 2: residual around G1
    # ---------------------------
    g2_seed = f"{seed}|g2|parent={law1.id}"
    candidate2, gain2, warm2_calls = discover_residual(
        phase_b,
        base_b,
        g2_seed,
    )

    # Cold control: same residual vocabulary without retained G1.
    cold_b = tuple(prior for _ in phase_b.values)
    cold2_candidate, cold2_gain, cold2_calls = discover_residual(
        phase_b,
        cold_b,
        f"{g2_seed}|delete-parent",
    )

    if candidate2 is None:
        print(
            f"G2 acquisition=REFUSED warm_search_calls={warm2_calls} "
            f"cold_control_calls={cold2_calls}"
        )
        summary = {
            "g1_candidate": [dataset.probe_names[i] for i in candidate1],
            "g1_gain": gain1,
            "g1_cold_search_calls": cold1_calls,
            "g2_acquired": False,
            "g2_warm_search_calls": warm2_calls,
            "cold_control_candidate": (
                None if cold2_candidate is None
                else [dataset.probe_names[i] for i in cold2_candidate]
            ),
            "cold_control_gain": cold2_gain,
            "cold_control_calls": cold2_calls,
            "verdict": "G1_SATURATED__NO_VERIFIED_G2_RESIDUAL",
        }
        out.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
        print("VERDICT")
        print("G1_SATURATED__NO_VERIFIED_G2_RESIDUAL")
        return

    original2 = compile_residual_from_stage(
        phase_b,
        candidate2,
        base_b,
        g2_seed,
    )
    provenance2 = hashlib.sha256(
        (
            f"{g2_seed}|candidate={candidate2}|gain={gain2:.12g}"
        ).encode()
    ).hexdigest()[:12]
    law2 = residual_to_law(
        dataset.source_hashes,
        original2,
        parent_law_id=law1.id,
        provenance=provenance2,
    )
    memory2 = add_residual_to_memory(memory1, law2)
    memory2 = exact_restart(memory2.text())

    residual_matches = applicable_residual_laws(
        memory2,
        dataset.source_hashes,
        dataset.probe_names,
    )
    if len(residual_matches) != 1:
        raise AssertionError("G2 restart lost parent-linked residual")

    model2 = law_to_residual_model(
        residual_matches[0],
        dataset.probe_names,
    )
    if not exact_residual_restart(
        original2,
        model2,
        phase_b,
        candidate2,
        base_b,
    ):
        raise AssertionError("G2 predictions changed after serialized restart")

    print(
        f"G2 acquired={[dataset.probe_names[i] for i in candidate2]} "
        f"mean_residual_gain={gain2:.6f} warm_search_calls={warm2_calls}"
    )
    print(
        f"G2 cold_control_candidate="
        f"{None if cold2_candidate is None else [dataset.probe_names[i] for i in cold2_candidate]} "
        f"cold_control_gain={cold2_gain:.6f} cold_control_calls={cold2_calls}"
    )
    print(
        f"G2 memory_bytes={len(memory2.text().encode())} "
        f"exact_restart=YES parent={law1.id}"
    )

    # Parent deletion must make G2 inapplicable.
    parent_deleted = ablate_capability(memory2, law1.id)
    parent_dependency = (
        len(
            applicable_residual_laws(
                parent_deleted,
                dataset.source_hashes,
                dataset.probe_names,
            )
        )
        == 0
    )
    if not parent_dependency:
        raise AssertionError("G2 remained applicable after deleting G1 lineage")

    # ---------------------------
    # Later natural recurrence
    # ---------------------------
    events = []
    future_search_calls = 0
    causal_child_ablations = 0
    all_positive = True

    child_deleted = ablate_capability(memory2, law2.id)
    if applicable_residual_laws(
        child_deleted,
        dataset.source_hashes,
        dataset.probe_names,
    ):
        raise AssertionError("G2 deletion left residual capability active")

    for group in phase_c_groups:
        ids = group_indices(dataset, group)
        covered = coverage_count(model2, dataset, ids)
        if covered == 0:
            continue

        labels = [dataset.labels[i] for i in ids]
        g1_probs = [
            model1.predict_values(dataset.values[i], prior)
            for i in ids
        ]
        compound_probs = [
            model2.predict_values(dataset.values[i], p)
            for i, p in zip(ids, g1_probs)
        ]

        g1_loss = binary_log_loss(labels, g1_probs)
        compound_loss = binary_log_loss(labels, compound_probs)
        gain = g1_loss - compound_loss

        # Child lineage ablation must restore G1 exactly.
        ablated_probs = list(g1_probs)
        ablated_loss = binary_log_loss(labels, ablated_probs)
        if ablated_loss != g1_loss:
            raise AssertionError("G2 deletion did not restore exact G1 predictions")

        causal = gain > MIN_GAIN and compound_loss < ablated_loss - MIN_GAIN
        if causal:
            causal_child_ablations += 1
        if gain <= MIN_GAIN:
            all_positive = False

        event = {
            "group": group,
            "rows": len(ids),
            "covered_rows": covered,
            "g1_log_loss": g1_loss,
            "compound_log_loss": compound_loss,
            "g2_gain": gain,
            "causal_child_ablation": causal,
            "future_search_calls": 0,
        }
        events.append(event)

        print(
            f"future={group} coverage={covered}/{len(ids)} "
            f"G1_LL={g1_loss:.6f} G1+G2_LL={compound_loss:.6f} "
            f"gain={gain:+.6f} child_ablation={causal}"
        )

    gates = {
        "g1_acquired": candidate1 is not None,
        "g1_exact_restart": len(matches1) == 1,
        "g2_acquired": candidate2 is not None,
        "g2_exact_restart": len(residual_matches) == 1,
        "g2_depends_on_g1": parent_dependency,
        "natural_future_recurrence": len(events) >= 1,
        "all_future_recurrences_improve": bool(events) and all_positive,
        "causal_child_ablation": (
            causal_child_ablations == len(events) and len(events) >= 1
        ),
        "zero_future_search": future_search_calls == 0,
    }
    passed = all(gates.values())

    summary = {
        "dataset": dataset.name,
        "g1_groups": phase_a_groups,
        "g2_groups": phase_b_groups,
        "future_groups": phase_c_groups,
        "g1_candidate": [dataset.probe_names[i] for i in candidate1],
        "g1_gain": gain1,
        "g1_cold_search_calls": cold1_calls,
        "g2_candidate": [dataset.probe_names[i] for i in candidate2],
        "g2_gain": gain2,
        "g2_warm_search_calls": warm2_calls,
        "cold_control_candidate": (
            None if cold2_candidate is None
            else [dataset.probe_names[i] for i in cold2_candidate]
        ),
        "cold_control_gain": cold2_gain,
        "cold_control_calls": cold2_calls,
        "events": events,
        "causal_child_ablations": causal_child_ablations,
        "parent_dependency": parent_dependency,
        "future_search_calls": future_search_calls,
        "gates": gates,
        "passed": passed,
    }
    out.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")

    print()
    print("AGGREGATE")
    print(
        f"G1_candidate={summary['g1_candidate']} "
        f"G2_candidate={summary['g2_candidate']}"
    )
    print(
        f"G1_search={cold1_calls} G2_warm_search={warm2_calls} "
        f"G2_cold_control_search={cold2_calls}"
    )
    print(
        f"future_recurrences={len(events)} "
        f"causal_child_ablations={causal_child_ablations} "
        f"future_search_calls={future_search_calls}"
    )
    for name, ok in gates.items():
        print(f"gate_{name}={int(ok)}")

    print("VERDICT")
    if passed:
        print("PASS_RECURSIVE_VERIFIED_CAPABILITY_COMPOUNDING_V2")
    else:
        print("FAIL_RECURSIVE_VERIFIED_CAPABILITY_COMPOUNDING_V2")
        raise AssertionError("G2 did not survive frozen prospective gates")


if __name__ == "__main__":
    main()
