#!/usr/bin/env python3
"""Run the bounded circuit-support invariant genesis experiment."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from realitygraph.developmental_executor import execute_generation
from realitygraph.developmental_snapshot import DevelopmentalSnapshot
from realitygraph.fixtures.circuit_generation_specs import (
    DIRECT_N6_FUTURE,
    derive_direct_family,
    independent_direct_oracle,
    make_g1_spec,
    make_g2_spec,
    make_g3_spec,
    initial_circuit_state,
)
from realitygraph.fixtures.circuit_support_growth import (
    enumerate_available_states,
    factorization_census,
    joint_cost_from_states,
    provenance_antichains,
    singleton_relaxation_cost,
    state_antichains,
)


RESULT_PATH = "pvsnp-developmental-closure-v1-summary.json"


def _restart(state):
    snapshot = DevelopmentalSnapshot.from_state(state)
    restarted = snapshot.restore()
    if restarted.to_text() != state.to_text() or restarted.digest != state.digest:
        raise ValueError("circuit developmental restart changed state")
    return restarted


def run_qualification(*, write_result: bool = True) -> dict:
    state0 = initial_circuit_state()
    result1 = execute_generation(state0, make_g1_spec())
    state1 = _restart(result1.state)
    result2 = execute_generation(state1, make_g2_spec(state1))
    state2 = _restart(result2.state)
    spec3 = make_g3_spec(state2)
    result3 = execute_generation(state2, spec3)
    final_state = _restart(result3.state)

    n3 = enumerate_available_states(3, 4)
    supports = provenance_antichains(3, 4)
    xor_relaxed = singleton_relaxation_cost(0x66, 3, n3.min_size)
    xor_exact = n3.min_size[0x66]

    n2 = enumerate_available_states(2, 3)
    pair_costs = [
        joint_cost_from_states(n2, pair)
        for pair in ((0x3, 0x5), (0x3, 0x7), (0x5, 0x7))
    ]
    triple_cost = joint_cost_from_states(n2, (0x3, 0x5, 0x7))
    triple_census = factorization_census(3, 3, 3)
    n4 = enumerate_available_states(4, 4)
    n4_fixed_point_matches = provenance_antichains(4, 4) == state_antichains(n4)

    g1_id = result1.capability.capability_id
    g2_id = result2.capability.capability_id
    g3_id = result3.capability.capability_id
    graph = final_state.capability_graph
    ablate_g1 = graph.ablate(g1_id).active_ids()
    ablate_g2 = graph.ablate(g2_id).active_ids()
    future_observations = dict(result3.future.observations)
    future_preloaded = DIRECT_N6_FUTURE in result3.capability.semantic_table
    future_oracle_attacked = DIRECT_N6_FUTURE in spec3.attack_adapter.challenges(
        result3.state, spec3, result3.capability
    )
    pre_g3_is_unknown = (
        derive_direct_family(state2, DIRECT_N6_FUTURE, g2_id, g3_id) is None
    )
    final_without_g2 = replace(
        final_state, capability_graph=final_state.capability_graph.ablate(g2_id)
    )
    final_without_g3 = replace(
        final_state, capability_graph=final_state.capability_graph.ablate(g3_id)
    )
    semantic_ablation_blocks = (
        derive_direct_family(
            final_without_g2, DIRECT_N6_FUTURE, g2_id, g3_id
        )
        is None
    )
    g3_ablation_blocks = (
        derive_direct_family(
            final_without_g3, DIRECT_N6_FUTURE, g2_id, g3_id
        )
        is None
    )
    independent_oracle_agrees = (
        future_observations[DIRECT_N6_FUTURE]
        == independent_direct_oracle(DIRECT_N6_FUTURE)
    )

    support_factorization_exact = (
        pair_costs == [2, 2, 2]
        and triple_cost == 3
        and sum(len(family) for family in supports.values()) == 345
        and triple_census["errors"] == 0
        and n4_fixed_point_matches
    )
    passed = all(
        (
            result1.trace.route == "COMPILED",
            result2.trace.route == "COMPILED",
            result3.trace.route == "COMPILED",
            xor_relaxed == 3,
            xor_exact == 4,
            support_factorization_exact,
            future_observations.get("enumeration_calls") == "0",
            not future_preloaded,
            not future_oracle_attacked,
            semantic_ablation_blocks,
            pre_g3_is_unknown,
            g3_ablation_blocks,
            independent_oracle_agrees,
            g2_id not in ablate_g1,
            g3_id not in ablate_g1,
            g3_id not in ablate_g2,
        )
    )

    summary = {
        "passed": passed,
        "verdict": (
            "PASS_PVSNP_DEVELOPMENTAL_CLOSURE_V1"
            if passed
            else "FAIL_PVSNP_DEVELOPMENTAL_CLOSURE_V1"
        ),
        "classification": "FINITE_SIGNAL" if passed else "NO_SIGNAL",
        "g1": {
            "route": result1.trace.route,
            "capability_id": g1_id,
            "xor_costs": [xor_relaxed, xor_exact],
            "representation": "pairwise joint coavailability J2",
        },
        "g2": {
            "route": result2.trace.route,
            "capability_id": g2_id,
            "pair_costs": pair_costs,
            "triple_cost": triple_cost,
            "triple_checks": triple_census["checked"],
            "unavailable_triples_certified": triple_census["unavailable"],
            "triple_classification_errors": triple_census["errors"],
            "n4_fixed_point_matches_states": n4_fixed_point_matches,
            "support_factorization_exact": support_factorization_exact,
            "raw_states_through_b4": n3.cumulative_state_count,
            "minimal_singleton_supports_through_b4": sum(
                len(family) for family in supports.values()
            ),
            "representation": "minimum provenance-support antichains",
        },
        "g3": {
            "route": result3.trace.route,
            "capability_id": g3_id,
            "future": dict(result3.future.observations),
            "future_enumeration_calls": int(
                future_observations.get("enumeration_calls", "-1")
            ),
            "future_answer": int(future_observations[DIRECT_N6_FUTURE]),
            "future_preloaded": future_preloaded,
            "future_oracle_attacked": future_oracle_attacked,
            "semantic_ablation_blocks_future": semantic_ablation_blocks,
            "pre_g3_is_unknown": pre_g3_is_unknown,
            "g3_ablation_blocks_future": g3_ablation_blocks,
            "independent_future_oracle_agrees": independent_oracle_agrees,
            "representation": "symbolic direct-NAND support union",
        },
        "gates": {
            "same_generic_executor": True,
            "g2_depends_on_g1": g1_id in result2.capability.dependencies,
            "g3_depends_on_g2": g2_id in result3.capability.dependencies,
            "g1_ablation_invalidates_g2_g3": (
                g2_id not in ablate_g1 and g3_id not in ablate_g1
            ),
            "g2_ablation_invalidates_g3": g3_id not in ablate_g2,
            "restart_exact": True,
            "sealed_future_zero_enumeration": (
                future_observations.get("enumeration_calls") == "0"
            ),
            "future_not_preloaded_or_attacked": (
                not future_preloaded and not future_oracle_attacked
            ),
            "semantic_ablation_blocks_future": semantic_ablation_blocks,
            "g3_ablation_blocks_future": g3_ablation_blocks,
            "pre_g3_unknown": pre_g3_is_unknown,
            "independent_future_oracle_agrees": independent_oracle_agrees,
        },
        "theorem": {
            "statement": (
                "J(S)=min_{B_f in P(f)} |union_f B_f| for normalized "
                "free-fanout semantic NAND DAGs"
            ),
            "fixed_point": (
                "P(x_i)={empty}; for non-input f, P(f)=Min_subset "
                "{ {f} union B_g union B_h : NAND(g,h)=f }"
            ),
            "scope": "bounded exact evidence plus a general normalization/concatenation proof",
        },
        "residual": (
            "minimum support antichains can still have exponential width; no "
            "stronger compositional domination preorder is known"
        ),
        "barriers": {
            "relativizing_character": True,
            "natural_proof_escape": False,
            "algebrization_escape": False,
        },
        "claims": {
            "asymptotic_lower_bound": False,
            "p_not_equal_np": False,
            "barrier_escape": False,
            "polynomial_size_invariant": False,
            "autonomous_invariant_discovery": False,
            "exhaustive_candidate_language": False,
        },
    }
    if write_result:
        Path(RESULT_PATH).write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return summary


if __name__ == "__main__":
    print(json.dumps(run_qualification(), indent=2, sort_keys=True))
