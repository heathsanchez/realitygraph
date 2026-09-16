from __future__ import annotations

import dataclasses
import json
import os
from pathlib import Path

from realitygraph.closure import (
    AdmissionEvidence,
    ClosureCertificate,
    FrozenBoundary,
    TerminalRecord as ClosureTerminalRecord,
    audit_closure,
)
from realitygraph.developmental_executor import GenerationTrace, execute_generation
from realitygraph.developmental_snapshot import DevelopmentalSnapshot
from realitygraph.developmental_types import ResultKind, canonical_digest
from realitygraph.fixtures.generation_specs_v2 import (
    initial_v2_state,
    make_g1_spec,
    make_g2_spec,
)
from realitygraph.fixtures.three_state_observer_growth import make_g3_spec
from verified_language_growth_closure_v1 import run_qualification as run_v1_qualification


RESULT_PATH = "verified-language-growth-closure-v2-summary.json"


def _novel(candidate, current_enumeration) -> bool:
    if candidate is None or current_enumeration is None:
        return False
    return all(
        constructor.extensional_key != candidate.extensional_key
        for constructor in current_enumeration.constructors
    )


def _exact_snapshot(state):
    snapshot = DevelopmentalSnapshot.from_state(state)
    restarted = snapshot.restore()
    exact = (
        snapshot.to_text() == DevelopmentalSnapshot.from_state(restarted).to_text()
        and restarted.to_text() == state.to_text()
        and restarted.digest == state.digest
        and restarted.capability_graph.active_ids() == state.capability_graph.active_ids()
        and tuple(c.constructor_id for c in restarted.grammar.constructors)
        == tuple(c.constructor_id for c in state.grammar.constructors)
    )
    return snapshot, restarted, exact


def _source_gates() -> tuple[bool, bool]:
    source = Path("realitygraph/developmental_executor.py").read_text()
    no_fixture_imports = "realitygraph.fixtures" not in source
    forbidden = ("G1", "G2", "G3", "generation_id ==", "constructor_id ==")
    no_generation_dispatch = all(token not in source for token in forbidden)
    return no_fixture_imports, no_generation_dispatch


def _ablation_gates(final_state, g1_id: str, g2_id: str, g3_id: str):
    graph = final_state.capability_graph
    g1_active = graph.ablate(g1_id).active_ids()
    g2_active = graph.ablate(g2_id).active_ids()
    g3_active = graph.ablate(g3_id).active_ids()
    return {
        "g1_ablation_invalidates_g2_g3": (
            g1_id not in g1_active and g2_id not in g1_active and g3_id not in g1_active
        ),
        "g2_ablation_invalidates_g3_preserves_g1": (
            g1_id in g2_active and g2_id not in g2_active and g3_id not in g2_active
        ),
        "g3_ablation_preserves_g1_g2": (
            g1_id in g3_active and g2_id in g3_active and g3_id not in g3_active
        ),
        "active_sets": {
            "ablate_g1": list(g1_active),
            "ablate_g2": list(g2_active),
            "ablate_g3": list(g3_active),
        },
    }


def _close(
    initial_state,
    final_state,
    specs,
    results,
    snapshots,
    controls,
    ablations,
):
    obligations = (
        "baseline-reuse",
        "g1-language-growth",
        "g2-recursive-language-growth",
        "g3-recursive-language-growth",
        "choice-control",
        "search-control",
    )
    records = (
        ClosureTerminalRecord(
            "baseline-reuse",
            ResultKind.AUTHORIZED,
            canonical_digest(
                {"initial_state": initial_state.digest}, prefix="v2-baseline-reuse:"
            ),
            True,
            "frozen initial state admitted before developmental growth",
        ),
        ClosureTerminalRecord(
            "g1-language-growth",
            ResultKind.COMPILED,
            results[0].trace.digest,
            True,
            "generic executor compiled first language extension",
        ),
        ClosureTerminalRecord(
            "g2-recursive-language-growth",
            ResultKind.COMPILED,
            results[1].trace.digest,
            True,
            "generic executor compiled second extension depending on G1",
        ),
        ClosureTerminalRecord(
            "g3-recursive-language-growth",
            ResultKind.COMPILED,
            results[2].trace.digest,
            True,
            "generic executor compiled third extension depending on G2",
        ),
        ClosureTerminalRecord(
            "choice-control",
            ResultKind.UNKNOWN_CHOICE,
            canonical_digest(
                {"preserved": controls["unknown_choice_preserved"]},
                prefix="v2-choice-control:",
            ),
            True,
            "multiple lawful repairs remain unselected without evidence",
        ),
        ClosureTerminalRecord(
            "search-control",
            ResultKind.UNKNOWN_SEARCH,
            canonical_digest(
                {"blocks_growth": controls["unknown_search_blocks_growth"]},
                prefix="v2-search-control:",
            ),
            True,
            "incomplete search does not authorize structural growth",
        ),
    )

    boundary = FrozenBoundary(
        world_manifest_digest=canonical_digest(
            {
                "initial_state": initial_state.digest,
                "specs": [spec.digest for spec in specs],
                "obligations": list(obligations),
                "qualification_depth": 3,
            },
            prefix="closure-worlds-v2:",
        ),
        obligation_ids=obligations,
        language_digest=final_state.grammar.digest,
        substrate_digest=canonical_digest(
            {
                "lower_substrates": [
                    spec.lower_substrate_adapter.adapter_id for spec in specs
                ],
                "candidate_enumerations": [
                    result.candidate_enumeration.enumeration_digest
                    for result in results
                ],
            },
            prefix="closure-substrates-v2:",
        ),
        verifier_digest=canonical_digest(
            {"verifiers": [spec.verifier_adapter.adapter_id for spec in specs]},
            prefix="closure-verifiers-v2:",
        ),
        protected_consequence_digest=final_state.protected_consequence_digest,
        resource_envelope=";".join(
            f"{spec.generation_id}:"
            + ",".join(f"{name}={value}" for name, value in spec.resource_envelope)
            for spec in specs
        ),
    )

    ablation_evidence = (
        canonical_digest(
            {"source": "g1", "active": ablations["active_sets"]["ablate_g1"]},
            prefix="v2-ablation:",
        ),
        canonical_digest(
            {"source": "g2", "active": ablations["active_sets"]["ablate_g2"]},
            prefix="v2-ablation:",
        ),
        canonical_digest(
            {"source": "g3", "active": ablations["active_sets"]["ablate_g3"]},
            prefix="v2-ablation:",
        ),
    )
    admission_evidence = tuple(
        AdmissionEvidence(
            result.growth.delta.delta_id,
            result.trace.restart_digest,
            ablation_evidence[index],
        )
        for index, result in enumerate(results)
    )
    replay_digest = canonical_digest(
        {
            "initial_state": initial_state.to_text(),
            "spec_digests": [spec.digest for spec in specs],
            "trace_payloads": [result.trace.payload() for result in results],
            "snapshots": [snapshot.to_text() for snapshot in snapshots],
            "final_state": final_state.to_text(),
            "ablation_active_sets": ablations["active_sets"],
        },
        prefix="qualification-replay-v2:",
    )
    closure = audit_closure(
        boundary,
        records,
        grammar_deltas=final_state.admitted_deltas,
        capability_graph=final_state.capability_graph,
        admission_evidence=admission_evidence,
        replay_digest=replay_digest,
    )
    restarted = ClosureCertificate.from_text(closure.text())
    restart_exact = restarted.text() == closure.text() and restarted.digest == closure.digest
    return closure, restart_exact


def run_qualification(*, write_result: bool = True) -> dict:
    initial_state = initial_v2_state()

    spec1 = make_g1_spec()
    result1 = execute_generation(initial_state, spec1)
    snapshot1, state1, snapshot1_exact = _exact_snapshot(result1.state)

    spec2 = make_g2_spec(state1)
    result2 = execute_generation(state1, spec2)
    snapshot2, state2, snapshot2_exact = _exact_snapshot(result2.state)

    spec3 = make_g3_spec(state2)
    result3 = execute_generation(state2, spec3)
    snapshot3, final_state, snapshot3_exact = _exact_snapshot(result3.state)

    results = (result1, result2, result3)
    specs = (spec1, spec2, spec3)
    snapshots = (snapshot1, snapshot2, snapshot3)

    executor_identity = f"{execute_generation.__module__}.{execute_generation.__name__}"
    executor_calls = (executor_identity, executor_identity, executor_identity)
    trace_fields = tuple(field.name for field in dataclasses.fields(GenerationTrace))
    same_trace_schema = all(
        tuple(field.name for field in dataclasses.fields(type(result.trace))) == trace_fields
        for result in results
    )
    no_fixture_imports, no_generation_dispatch = _source_gates()

    g1_id = result1.capability.capability_id
    g2_id = result2.capability.capability_id
    g3_id = result3.capability.capability_id
    ablations = _ablation_gates(final_state, g1_id, g2_id, g3_id)

    inherited_v1 = run_v1_qualification(write_result=False)
    controls = {
        key: bool(inherited_v1["gates"][key])
        for key in (
            "unknown_search_blocks_growth",
            "unknown_choice_preserved",
            "stale_certificate_rejected",
            "sham_extension_rejected",
        )
    }

    closure, closure_restart_exact = _close(
        initial_state,
        final_state,
        specs,
        results,
        snapshots,
        controls,
        ablations,
    )

    g1_candidate = result1.growth.candidate
    g2_candidate = result2.growth.candidate
    g3_candidate = result3.growth.candidate
    g3_signal_current = tuple(
        constructor
        for constructor in result3.current_enumeration.constructors
        if constructor.input_type == "signal-sequence"
    )

    gates = {
        "same_executor_g1_g2_g3": len(set(executor_calls)) == 1 and same_trace_schema,
        "executor_has_no_fixture_imports": no_fixture_imports,
        "executor_has_no_generation_dispatch": no_generation_dispatch,
        "g1_complete": bool(result1.current_enumeration.complete),
        "g1_no_resolution": bool(result1.trace.no_resolution_digest),
        "g1_novel": _novel(g1_candidate, result1.current_enumeration),
        "g1_restart_exact": bool(result1.trace.restart_digest) and snapshot1_exact,
        "g1_attack_survives": result1.attack.status.value == "SURVIVE",
        "g1_future_zero_search": result1.future.passed and result1.future.grammar_search_calls == 0,
        "g2_complete": bool(result2.current_enumeration.complete),
        "g2_no_resolution": bool(result2.trace.no_resolution_digest),
        "g2_novel": _novel(g2_candidate, result2.current_enumeration),
        "g2_depends_on_g1": result2.capability.dependencies == (g1_id,),
        "g2_restart_exact": bool(result2.trace.restart_digest) and snapshot2_exact,
        "g2_attack_survives": result2.attack.status.value == "SURVIVE",
        "g2_future_zero_search": result2.future.passed and result2.future.grammar_search_calls == 0,
        "g3_two_state_language_complete": (
            result3.current_enumeration.complete and result3.current_enumeration.raw_count == 64
        ),
        "g3_two_state_no_resolution": (
            bool(result3.trace.no_resolution_digest)
            and all(
                constructor.semantic_signature != g3_candidate.semantic_signature
                for constructor in g3_signal_current
            )
        ),
        "g3_three_state_novel": _novel(g3_candidate, result3.current_enumeration),
        "g3_depends_on_g2": result3.capability.dependencies == (g2_id,),
        "g3_restart_exact": bool(result3.trace.restart_digest) and snapshot3_exact,
        "g3_attack_survives": result3.attack.status.value == "SURVIVE",
        "g3_future_zero_search": result3.future.passed and result3.future.grammar_search_calls == 0,
        "full_snapshot_restart_exact": snapshot3_exact and final_state.digest == result3.state.digest,
        "g1_ablation_invalidates_g2_g3": ablations["g1_ablation_invalidates_g2_g3"],
        "g2_ablation_invalidates_g3_preserves_g1": ablations[
            "g2_ablation_invalidates_g3_preserves_g1"
        ],
        "g3_ablation_preserves_g1_g2": ablations["g3_ablation_preserves_g1_g2"],
        **controls,
        "inherited_v1_qualification_green": bool(inherited_v1["passed"]),
        "closed_bounded_depth3": (
            closure.status == "CLOSED_BOUNDED"
            and closure_restart_exact
            and final_state.generation_index == 3
        ),
    }
    passed = all(gates.values())
    verdict = (
        "PASS_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V2"
        if passed
        else "PARTIAL_VERIFIED_LANGUAGE_GROWTH_CLOSURE_V2"
    )

    summary = {
        "version": "verified-language-growth-closure-v2",
        "verdict": verdict,
        "passed": passed,
        "executor": {
            "identity": executor_identity,
            "trace_fields": list(trace_fields),
        },
        "gates": gates,
        "g1": {
            "spec_digest": spec1.digest,
            "trace_digest": result1.trace.digest,
            "constructor_id": g1_candidate.constructor_id,
            "constructor_signature": g1_candidate.semantic_signature,
            "constructor_complexity": g1_candidate.complexity,
            "constructor_dependencies": list(g1_candidate.dependencies),
            "capability_id": g1_id,
            "capability_dependencies": list(result1.capability.dependencies),
            "delta_id": result1.growth.delta.delta_id,
            "grammar_search_calls": len(result1.growth.verdicts),
            "future_search_calls": result1.future.grammar_search_calls,
            "attack_status": result1.attack.status.value,
            "snapshot_digest": snapshot1.digest,
        },
        "g2": {
            "spec_digest": spec2.digest,
            "trace_digest": result2.trace.digest,
            "constructor_id": g2_candidate.constructor_id,
            "constructor_signature": g2_candidate.semantic_signature,
            "constructor_complexity": g2_candidate.complexity,
            "constructor_dependencies": list(g2_candidate.dependencies),
            "capability_id": g2_id,
            "capability_dependencies": list(result2.capability.dependencies),
            "delta_id": result2.growth.delta.delta_id,
            "grammar_search_calls": len(result2.growth.verdicts),
            "future_search_calls": result2.future.grammar_search_calls,
            "attack_status": result2.attack.status.value,
            "snapshot_digest": snapshot2.digest,
        },
        "g3": {
            "spec_digest": spec3.digest,
            "trace_digest": result3.trace.digest,
            "constructor_id": g3_candidate.constructor_id,
            "constructor_signature": g3_candidate.semantic_signature,
            "constructor_complexity": g3_candidate.complexity,
            "constructor_dependencies": list(g3_candidate.dependencies),
            "capability_id": g3_id,
            "capability_dependencies": list(result3.capability.dependencies),
            "delta_id": result3.growth.delta.delta_id,
            "two_state_raw_count": result3.current_enumeration.raw_count,
            "three_state_raw_count": result3.candidate_enumeration.raw_count,
            "grammar_search_calls": len(result3.growth.verdicts),
            "future_search_calls": result3.future.grammar_search_calls,
            "attack_status": result3.attack.status.value,
            "snapshot_digest": snapshot3.digest,
        },
        "ablation": ablations["active_sets"],
        "states": {
            "initial_digest": initial_state.digest,
            "g1_digest": state1.digest,
            "g2_digest": state2.digest,
            "final_digest": final_state.digest,
            "active_capability_ids": list(final_state.capability_graph.active_ids()),
            "active_constructor_ids": [
                constructor.constructor_id for constructor in final_state.grammar.constructors
            ],
        },
        "closure": {
            "status": closure.status,
            "human_status": "CLOSED_BOUNDED_DEPTH3",
            "qualification_depth": 3,
            "certificate_digest": closure.digest,
            "boundary_digest": closure.boundary.digest,
            "restart_exact": closure_restart_exact,
            "terminal_kinds": [record.kind.value for record in closure.terminal_records],
        },
        "claims": {
            "bounded_generic_recursive_executor_depth3": passed,
            "open_ended_closure": False,
            "unbounded_self_development": False,
            "autonomous_verifier_authority": False,
            "universal_cross_domain_growth": False,
        },
    }

    if write_result:
        path = Path(os.environ.get("REALITYGRAPH_LANGUAGE_GROWTH_V2_RESULT", RESULT_PATH))
        path.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    return summary


def main() -> None:
    summary = run_qualification(write_result=True)
    print("REALITYGRAPH / VERIFIED LANGUAGE-GROWTH CLOSURE V2")
    print("----------------------------------------------------")
    for name in ("g1", "g2", "g3"):
        row = summary[name]
        print(
            name.upper(),
            row["constructor_id"],
            "depends", row["capability_dependencies"],
            "search", row["grammar_search_calls"],
            "future_search", row["future_search_calls"],
        )
    for name, value in summary["gates"].items():
        print(f"gate_{name}={int(bool(value))}")
    print(
        "CLOSURE",
        summary["closure"]["human_status"],
        "certificate",
        summary["closure"]["certificate_digest"],
    )
    print("VERDICT")
    print(summary["verdict"])
    if not summary["passed"]:
        raise AssertionError("one or more V2 verified language-growth gates failed")


if __name__ == "__main__":
    main()
