from __future__ import annotations

import json
import os
from pathlib import Path

from realitygraph.capability_graph import CapabilityGraph
from realitygraph.closure import (
    AdmissionEvidence,
    ClosureCertificate,
    FrozenBoundary,
    TerminalRecord,
    audit_closure,
)
from realitygraph.developmental_core import DevelopmentalRoute, route_residual
from realitygraph.developmental_types import (
    DevelopmentalResult,
    ResultKind,
    canonical_digest,
)
from realitygraph.fixtures.boolean_observer_growth import build_g1
from realitygraph.fixtures.stateful_observer_growth import build_g2
from realitygraph.grammar import FiniteConstructor
from realitygraph.grammar_growth import grow_grammar
from realitygraph.residual_certificate import make_expressivity_residual


RESULT_PATH = "verified-language-growth-closure-v1-summary.json"


def _controls(g1: dict) -> dict[str, bool]:
    search_result = DevelopmentalResult(
        ResultKind.UNKNOWN_SEARCH,
        "control-search-budget",
        "budget exhausted without a completeness certificate",
    )
    search_route = route_residual(search_result)
    missing_complete_rejected = False
    try:
        make_expressivity_residual(
            obligation_id="control-search-budget",
            state_digest=g1["residual"].state_digest,
            authority_snapshot=g1["residual"].authority_snapshot,
            language_id=g1["old_grammar"].digest,
            substrate_id="not-licensed",
            protected_consequences=(),
            observational_equivalence=("unresolved",),
            unresolved=("parity-observer",),
            completeness=None,
            no_resolution=g1["no_resolution"],
            necessary_constraints=("unknown",),
            candidate_version_space_digest="none",
            replay_evidence=(),
        )
    except ValueError:
        missing_complete_rejected = True

    choice_result = DevelopmentalResult(
        ResultKind.UNKNOWN_CHOICE,
        "control-noncanonical-choice",
        "two incomparable lawful repairs remain",
    )
    choice_route = route_residual(choice_result)
    lawful_alternatives = ("repair-a", "repair-b")

    stale_rejected = False
    try:
        grow_grammar(
            g1["residual"],
            g1["child_grammar"],
            g1["candidates"],
            authority_snapshot=g1["residual"].authority_snapshot,
            adequate=lambda candidate, residual: True,
            preserves=lambda candidate: True,
            verify=lambda candidate: True,
            verifier_id="control",
        )
    except ValueError:
        stale_rejected = True

    sham = FiniteConstructor(
        constructor_id="sham-nonseparator",
        input_type="pair",
        output_type="bit",
        semantics=(("00", "0"), ("01", "0"), ("10", "0"), ("11", "1")),
        complexity=1,
    )
    sham_result = grow_grammar(
        g1["residual"],
        g1["old_grammar"],
        (sham,),
        authority_snapshot=g1["residual"].authority_snapshot,
        adequate=lambda candidate, residual: candidate.semantic_signature == "0110",
        preserves=lambda candidate: True,
        verify=lambda candidate: True,
        verifier_id="control",
    )

    return {
        "unknown_search_blocks_growth": (
            search_route is DevelopmentalRoute.SEARCH and missing_complete_rejected
        ),
        "unknown_choice_preserved": (
            choice_route is DevelopmentalRoute.EVIDENCE
            and len(lawful_alternatives) == 2
        ),
        "stale_certificate_rejected": stale_rejected,
        "sham_extension_rejected": not sham_result.accepted,
    }


def _close(g1: dict, g2: dict) -> tuple[ClosureCertificate, bool]:
    graph = CapabilityGraph(
        (
            g1["capability"],
            g1["decoder"],
            g1["composite"],
            g2["capability"],
        )
    )
    obligations = (
        "baseline-reuse",
        "g1-language-growth",
        "g2-recursive-language-growth",
        "choice-control",
        "search-control",
    )
    records = (
        TerminalRecord(
            "baseline-reuse", ResultKind.AUTHORIZED,
            "baseline-exact-reuse-v1", True, "old capability retained",
        ),
        TerminalRecord(
            "g1-language-growth", ResultKind.COMPILED,
            g1["delta"].delta_id, True, "verified NAND-derived observer",
        ),
        TerminalRecord(
            "g2-recursive-language-growth", ResultKind.COMPILED,
            g2["delta"].delta_id, True, "verified stateful observer depending on G1",
        ),
        TerminalRecord(
            "choice-control", ResultKind.UNKNOWN_CHOICE,
            "two-lawful-repairs-v1", True, "selection evidence intentionally absent",
        ),
        TerminalRecord(
            "search-control", ResultKind.UNKNOWN_SEARCH,
            "no-completeness-no-expand-v1", True, "budget exhaustion is not expressivity",
        ),
    )
    boundary = FrozenBoundary(
        world_manifest_digest=canonical_digest(
            {"obligations": list(obligations)}, prefix="closure-worlds-v1:"
        ),
        obligation_ids=obligations,
        language_digest=g2["child_grammar"].digest,
        substrate_digest=canonical_digest(
            {
                "g1": g1["residual"].substrate_id,
                "g2": g2["residual"].substrate_id,
            },
            prefix="closure-substrates-v1:",
        ),
        verifier_digest=canonical_digest(
            {"verifier": "truth-table-exhaustive-v1"}, prefix="closure-verifier-v1:"
        ),
        protected_consequence_digest=canonical_digest(
            {"protected": ["g1-semantics", "g2-dependency"]},
            prefix="closure-protected-v1:",
        ),
        resource_envelope="g1:nand<=4;g2:all-64-two-state-machines;finite-attacks-exhaustive",
    )
    evidence = (
        AdmissionEvidence(
            g1["delta"].delta_id,
            "g1-grammar-and-delta-byte-exact-restart",
            "g1-delta-ablation-restores-parent",
        ),
        AdmissionEvidence(
            g2["delta"].delta_id,
            "g2-grammar-and-delta-byte-exact-restart",
            "g2-delta-ablation-restores-parent",
        ),
    )
    replay_digest = canonical_digest(
        {
            "g1_parent": g1["old_grammar"].text(),
            "g1_delta": g1["delta"].text(),
            "g1_child": g1["child_grammar"].text(),
            "g2_parent": g2["parent_grammar"].text(),
            "g2_delta": g2["delta"].text(),
            "g2_child": g2["child_grammar"].text(),
        },
        prefix="qualification-replay-v1:",
    )
    closure = audit_closure(
        boundary,
        records,
        grammar_deltas=(g1["delta"], g2["delta"]),
        capability_graph=graph,
        admission_evidence=evidence,
        replay_digest=replay_digest,
    )
    restarted = ClosureCertificate.from_text(closure.text())
    return closure, restarted.text() == closure.text()


def run_qualification(*, write_result: bool = True) -> dict:
    g1 = build_g1()
    g2 = build_g2(g1)
    controls = _controls(g1)
    closure, closure_restart_exact = _close(g1, g2)

    gates = {
        "g1_old_language_complete": bool(g1["old_language_complete"]),
        "g1_old_language_no_resolution": bool(g1["old_language_no_resolution"]),
        "g1_extensional_novelty": bool(g1["extensional_novelty"]),
        "g1_independently_verified": bool(g1["independently_verified"]),
        "g1_restart_exact": bool(g1["restart_exact"]),
        "g1_future_reuse_zero_search": bool(
            g1["future_reuse_zero_search"] and g1["future_search_calls"] == 0
        ),
        "g1_composition_verified": bool(g1["composition_verified"]),
        "g1_attack_survives": bool(g1["attack_survives"]),
        "g1_ablation_restores_old_limit": bool(g1["ablation_restores_old"]),
        "g2_stateless_language_complete": bool(g2["stateless_language_complete"]),
        "g2_stateless_no_resolution": bool(g2["stateless_no_resolution"]),
        "g2_stateful_novelty": bool(g2["stateful_novelty"]),
        "g2_depends_on_g1": bool(g2["depends_on_g1"]),
        "g2_restart_exact": bool(g2["restart_exact"]),
        "g2_future_reuse_zero_search": bool(
            g2["future_reuse_zero_search"] and g2["future_search_calls"] == 0
        ),
        "g2_attack_survives": bool(g2["attack_survives"]),
        "g1_ablation_invalidates_g2": bool(g2["g1_ablation_invalidates_g2"]),
        "g2_only_ablation_preserves_g1": bool(g2["g2_only_ablation_preserves_g1"]),
        **controls,
        "closed_bounded": closure.status == "CLOSED_BOUNDED" and closure_restart_exact,
    }
    passed = all(gates.values())
    verdict = (
        "PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V1"
        if passed
        else "PARTIAL_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V1"
    )

    summary = {
        "version": "verified-language-growth-closure-v1",
        "verdict": verdict,
        "passed": passed,
        "gates": gates,
        "g1": {
            "constructor_id": g1["constructor"].constructor_id,
            "constructor_signature": g1["constructor"].semantic_signature,
            "constructor_complexity": g1["constructor"].complexity,
            "capability_id": g1["capability"].capability_id,
            "grammar_search_calls": g1["grammar_search_calls"],
            "future_search_calls": g1["future_search_calls"],
            "delta_id": g1["delta"].delta_id,
            "attack_status": g1["attack"].status.value,
        },
        "g2": {
            "constructor_id": g2["constructor"].constructor_id,
            "constructor_signature": g2["constructor"].semantic_signature,
            "constructor_complexity": g2["constructor"].complexity,
            "constructor_dependencies": list(g2["constructor"].dependencies),
            "capability_id": g2["capability"].capability_id,
            "capability_dependencies": list(g2["capability"].dependencies),
            "grammar_search_calls": g2["grammar_search_calls"],
            "future_search_calls": g2["future_search_calls"],
            "delta_id": g2["delta"].delta_id,
            "attack_status": g2["attack"].status.value,
        },
        "closure": {
            "status": closure.status,
            "certificate_digest": closure.digest,
            "boundary_digest": closure.boundary.digest,
            "restart_exact": closure_restart_exact,
            "terminal_kinds": [record.kind.value for record in closure.terminal_records],
        },
        "claims": {
            "bounded_recursive_language_growth": passed,
            "open_ended_closure": False,
            "unbounded_self_development": False,
            "lowest_level_substrate_invented": False,
        },
    }

    if write_result:
        path = Path(os.environ.get("REALITYGRAPH_LANGUAGE_GROWTH_RESULT", RESULT_PATH))
        path.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    return summary


def main() -> None:
    summary = run_qualification(write_result=True)
    print("REALITYGRAPH / VERIFIED LANGUAGE-GROWTH CLOSURE V1")
    print("----------------------------------------------------")
    print(
        "G1",
        summary["g1"]["constructor_id"],
        "signature", summary["g1"]["constructor_signature"],
        "search", summary["g1"]["grammar_search_calls"],
        "future_search", summary["g1"]["future_search_calls"],
    )
    print(
        "G2",
        summary["g2"]["constructor_id"],
        "depends", summary["g2"]["constructor_dependencies"],
        "search", summary["g2"]["grammar_search_calls"],
        "future_search", summary["g2"]["future_search_calls"],
    )
    for name, value in summary["gates"].items():
        print(f"gate_{name}={int(bool(value))}")
    print("CLOSURE", summary["closure"]["status"])
    print("VERDICT")
    print(summary["verdict"])
    if not summary["passed"]:
        raise AssertionError("one or more verified language-growth closure gates failed")


if __name__ == "__main__":
    main()
