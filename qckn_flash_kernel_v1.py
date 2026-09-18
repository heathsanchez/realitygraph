from __future__ import annotations

import json

from realitygraph.capability import FiniteCapability
from realitygraph.flash import (
    FlashClosure,
    FlashCompositionRule,
    FlashContract,
    FlashObstruction,
    FutureQuotient,
    LiveObligation,
    PresentState,
    ProtectedContinuation,
)
from realitygraph.flash_kernel import FlashKernel


AUTHORITY = "flash-kernel-authority-v1"
VERIFIER = "flash-kernel-verifier-v1"
CONTRACT = FlashContract(AUTHORITY, VERIFIER)
DOMAINS = ("theorem", "arc", "kernel", "gpu")
OBLIGATIONS_PER_DOMAIN = 3
CANDIDATES_PER_OBLIGATION = 8
F_COST = 4
G_COST = 5
COMMON_BAD = "candidate:shared-refuted-route"


def capability(
    cid: str,
    input_type: str,
    output_type: str,
    rows: tuple[tuple[str, str], ...],
    cert: str,
    *,
    cost: int,
) -> FiniteCapability:
    return FiniteCapability(
        capability_id=cid,
        input_type=input_type,
        output_type=output_type,
        semantics=rows,
        guard_inputs=tuple(key for key, _ in rows),
        certificate_id=cert,
        dependencies=(),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        provenance_ids=(f"source:{cid}",),
        cost=cost,
    )


def cap_f() -> FiniteCapability:
    return capability(
        "f",
        "X",
        "Y",
        (("x0", "y0"), ("x1", "y1")),
        "cert-f",
        cost=F_COST,
    )


def cap_g() -> FiniteCapability:
    return capability(
        "g",
        "Y",
        "Z",
        (("y0", "z0"), ("y1", "z1")),
        "cert-g",
        cost=G_COST,
    )


def sham_capability() -> FiniteCapability:
    return capability(
        "q",
        "X",
        "Q",
        (("x0", "q0"), ("x1", "q1")),
        "cert-q",
        cost=1,
    )


def obligations(domains=DOMAINS) -> tuple[LiveObligation, ...]:
    rows: list[LiveObligation] = []
    for domain in domains:
        for index in range(OBLIGATIONS_PER_DOMAIN):
            oid = f"{domain}:{index}"
            candidates = (COMMON_BAD,) + tuple(
                f"candidate:{oid}:{j}"
                for j in range(1, CANDIDATES_PER_OBLIGATION)
            )
            rows.append(
                LiveObligation(
                    obligation_id=oid,
                    input_type=f"{domain}:Target{index}",
                    source_input_type="X",
                    output_type="Z",
                    oracle=(("t0", "z0"), ("t1", "z1")),
                    transport_to_source=(("t0", "x0"), ("t1", "x1")),
                    contract=CONTRACT,
                    candidate_fingerprints=candidates,
                    domain=domain,
                )
            )
    return tuple(rows)


def composition_rule() -> FlashCompositionRule:
    return FlashCompositionRule(
        rule_id="compose-f-g",
        first_capability_id="f",
        second_capability_id="g",
        result_capability_id="h",
        oracle=(("x0", "z0"), ("x1", "z1")),
        certificate_id="cert-h",
    )


def obstruction() -> FlashObstruction:
    return FlashObstruction(
        obstruction_id="obs:shared-refuted-route",
        input_type="X",
        output_type="Z",
        contract=CONTRACT,
        candidate_fingerprint=COMMON_BAD,
        separating_input="x0",
        expected_output="z0",
        actual_output="z1",
        provenance="verified failure in arc lens",
    )


def quotient() -> FutureQuotient:
    return FutureQuotient(
        states=(
            PresentState("a", provenance_ids=("history-a",)),
            PresentState("b", provenance_ids=("history-b",)),
            PresentState("c", provenance_ids=("history-c",)),
        ),
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
    )


def make_global_kernel() -> FlashKernel:
    return FlashKernel(
        FlashClosure(
            obligations(),
            composition_rules=(composition_rule(),),
            kernel="qckn-flash-kernel-v1",
        ),
        quotients={"arc": quotient()},
    )


def run_independent() -> dict[str, object]:
    kernels: dict[str, FlashKernel] = {}
    for domain in DOMAINS:
        kernels[domain] = FlashKernel(
            FlashClosure(
                obligations((domain,)),
                composition_rules=(composition_rule(),),
                kernel=f"independent:{domain}",
            )
        )

    # Evidence remains siloed: the theorem lens learns f, the gpu lens learns g,
    # and the arc lens learns the negative separator. No pipeline owns both f/g.
    kernels["theorem"].admit_capability(
        cap_f(),
        oracle=(("x0", "y0"), ("x1", "y1")),
        origin="theorem-local",
    )
    kernels["gpu"].admit_capability(
        cap_g(),
        oracle=(("y0", "z0"), ("y1", "z1")),
        origin="gpu-local",
    )
    kernels["arc"].admit_obstruction(obstruction())

    initial = sum(kernel.initial_candidate_occurrences for kernel in kernels.values())
    pending = sum(kernel.pending_candidate_search() for kernel in kernels.values())
    pruned = sum(kernel.pruned_candidate_search() for kernel in kernels.values())
    discharged = sum(
        len(kernel.closure.discharged_obligation_ids())
        for kernel in kernels.values()
    )
    represented_total_cost = F_COST + G_COST + pending

    return {
        "initial_candidate_search": initial,
        "pending_candidate_search_after_local_evidence": pending,
        "pruned_candidate_occurrences": pruned,
        "discharged_obligations": discharged,
        "acquisition_cost": F_COST + G_COST,
        "represented_total_cost_to_finish_remaining_portfolios": represented_total_cost,
    }


def run_sham() -> dict[str, object]:
    kernel = make_global_kernel()
    before = kernel.pending_candidate_search()
    event = kernel.admit_capability(
        sham_capability(),
        oracle=(("x0", "q0"), ("x1", "q1")),
        origin="sham-control",
    )
    after = kernel.pending_candidate_search()
    if before != after or event.discharged or event.generated_capabilities:
        raise AssertionError("irrelevant verified capability changed protected work")
    return {
        "before": before,
        "after": after,
        "discharged": list(event.discharged),
        "generated_capabilities": list(event.generated_capabilities),
    }


def run_flash() -> tuple[FlashKernel, dict[str, object]]:
    kernel = make_global_kernel()

    initial = kernel.snapshot()
    if initial["pending_candidate_search"] != 96:
        raise AssertionError("frozen initial candidate market changed")

    # Good failure becomes capital: one exact separator prunes the same invalid
    # route from every compatible live obligation before any worker pays for it.
    obs_event = kernel.admit_obstruction(obstruction())
    after_obstruction = kernel.snapshot()
    if obs_event.pruned_candidate_occurrences != 12:
        raise AssertionError("obstruction did not propagate globally")
    if after_obstruction["pending_candidate_search"] != 84:
        raise AssertionError("global obstruction pruning cost mismatch")

    # Future consequences define present identity independently of history.
    first_future = kernel.admit_continuation(
        "arc",
        ProtectedContinuation(
            continuation_id="future-1",
            outcomes=(("a", "0"), ("b", "0"), ("c", "1")),
            authority_snapshot=AUTHORITY,
            verifier_id=VERIFIER,
        ),
    )
    if kernel.quotients["arc"].classes() != (("a", "b"), ("c",)):
        raise AssertionError("first future failed to induce expected quotient")

    second_future = kernel.admit_continuation(
        "arc",
        ProtectedContinuation(
            continuation_id="future-2",
            outcomes=(("a", "0"), ("b", "1"), ("c", "1")),
            authority_snapshot=AUTHORITY,
            verifier_id=VERIFIER,
        ),
    )
    if kernel.quotients["arc"].classes() != (("a",), ("b",), ("c",)):
        raise AssertionError("future separator failed to refine present ontology")

    f_event = kernel.admit_capability(
        cap_f(),
        oracle=(("x0", "y0"), ("x1", "y1")),
        origin="theorem-lens",
    )
    if f_event.discharged:
        raise AssertionError("f alone should not settle any X->Z obligation")

    before_g_priority = kernel.developmental_value_order()
    g_event = kernel.admit_capability(
        cap_g(),
        oracle=(("y0", "z0"), ("y1", "z1")),
        origin="gpu-lens",
    )
    after_flash = kernel.snapshot()

    if g_event.generated_capabilities != ("h",):
        raise AssertionError("cross-lens composition h was not generated")
    if len(g_event.discharged) != 12 or g_event.flash_radius != 12:
        raise AssertionError("new capability did not flash through all live tasks")
    if g_event.closure_iterations < 2:
        raise AssertionError("closure did not require recursive fixed-point propagation")
    if after_flash["pending_candidate_search"] != 0:
        raise AssertionError("flash closure left avoidable candidate search")
    if after_flash["cancelled_candidate_search"] != 84:
        raise AssertionError("future search cancellation mismatch")
    if after_flash["current_search_eliminated"] != 96:
        raise AssertionError("total eliminated search should include failure pruning and discharge")
    if after_flash["open_worker_count"] != 0:
        raise AssertionError("redundant workers were not cancelled")

    flash_total_cost = F_COST + G_COST
    independent_remaining_equivalent = 93
    interaction_value = int(after_flash["current_search_eliminated"])

    pre_ablation = after_flash
    revoke_event = kernel.revoke_capability("f", reason="targeted causal ablation")
    after_ablation = kernel.snapshot()
    if len(revoke_event.reopened) != 12:
        raise AssertionError("ablation did not reopen all dependent obligations")
    if after_ablation["pending_candidate_search"] != 84:
        raise AssertionError("ablation did not restore unresolved search behind retained obstruction")
    if "h" in kernel.closure.active_capability_ids():
        raise AssertionError("dependent composition survived support revocation")

    future_revoke = kernel.revoke_continuation(
        "arc",
        "future-2",
        reason="protected future removed",
    )
    if kernel.quotients["arc"].classes() != (("a", "b"), ("c",)):
        raise AssertionError("future revocation failed to merge present states")

    return kernel, {
        "initial_candidate_search": 96,
        "after_global_obstruction_pending": 84,
        "pruned_by_informative_failure": 12,
        "f_alone_discharged": len(f_event.discharged),
        "g_event_generated": list(g_event.generated_capabilities),
        "flash_radius": g_event.flash_radius,
        "closure_iterations": g_event.closure_iterations,
        "cancelled_future_search": int(pre_ablation["cancelled_candidate_search"]),
        "total_search_eliminated": int(pre_ablation["current_search_eliminated"]),
        "open_workers_after_flash": int(pre_ablation["open_worker_count"]),
        "flash_acquisition_cost": flash_total_cost,
        "before_g_priority_head": [
            [oid, score] for oid, score in before_g_priority[:4]
        ],
        "ablation_reopened": len(revoke_event.reopened),
        "ablation_restored_pending_search": int(after_ablation["pending_candidate_search"]),
        "future_classes_after_first": [["a", "b"], ["c"]],
        "future_classes_after_separator": [["a"], ["b"], ["c"]],
        "future_separator_changed_states": list(second_future.changed_states),
        "future_classes_after_revocation": [["a", "b"], ["c"]],
        "future_revocation_changed_states": list(future_revoke.changed_states),
        "interaction_value": interaction_value,
        "represented_independent_remaining_search": independent_remaining_equivalent,
    }


def main() -> None:
    independent = run_independent()
    sham = run_sham()
    kernel, flash = run_flash()

    if independent["initial_candidate_search"] != 96:
        raise AssertionError("independent baseline market mismatch")
    if independent["pending_candidate_search_after_local_evidence"] != 93:
        raise AssertionError("independent baseline should receive only local pruning")
    if independent["discharged_obligations"] != 0:
        raise AssertionError("siloed f/g should not compose across independent pipelines")

    flash_total = int(flash["flash_acquisition_cost"])
    independent_total = int(
        independent["represented_total_cost_to_finish_remaining_portfolios"]
    )
    cost_reduction = 1.0 - flash_total / independent_total
    if not (flash_total == 9 and independent_total == 102 and cost_reduction > 0.9):
        raise AssertionError("frozen Flash-vs-independent economics changed")

    evidence = {
        "schema": "qckn-flash-kernel-v1",
        "independent": independent,
        "flash": flash,
        "sham": sham,
        "comparison": {
            "independent_represented_total_cost": independent_total,
            "flash_total_cost": flash_total,
            "represented_cost_reduction": cost_reduction,
            "global_search_eliminated": flash["total_search_eliminated"],
            "informative_failure_pruning": flash["pruned_by_informative_failure"],
            "recursive_composition_generated": flash["g_event_generated"],
            "causal_ablation_restored_pending_search": flash[
                "ablation_restored_pending_search"
            ],
        },
        "final_kernel_snapshot_after_ablation_and_future_revocation": kernel.snapshot(),
        "claim_boundary": (
            "exact finite four-lens qualification of a live global consequence runtime; "
            "the domain labels are fixture lenses sharing a declared typed contract, not "
            "evidence that theorem proving, ARC, kernel engineering, and GPU optimization "
            "share arbitrary semantic content. It establishes immediate verified propagation, "
            "informative-failure pruning, recursive composition, worker cancellation, "
            "continuation-relative present quotienting, restartable compiled capability, "
            "and causal reopening under ablation inside the frozen fixture."
        ),
    }
    print(json.dumps(evidence, indent=2, sort_keys=True))
    print("PASS_FLASH_GLOBAL_FAILURE_CAPITAL")
    print("PASS_FLASH_RECURSIVE_COMPOSITION")
    print("PASS_FLASH_FUTURE_DEFINES_PRESENT")
    print("PASS_FLASH_ABLATION_REOPENS")
    print("PASS_QCKN_FLASH_KERNEL_V1")


if __name__ == "__main__":
    main()
