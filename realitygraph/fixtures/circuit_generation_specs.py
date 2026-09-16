"""GenerationSpec adapters for exact circuit-support representation growth."""

from __future__ import annotations

from dataclasses import dataclass

from realitygraph.capability import FiniteCapability
from realitygraph.capability_graph import CapabilityGraph
from realitygraph.developmental_state import DevelopmentalState
from realitygraph.developmental_types import canonical_digest
from realitygraph.generation_spec import (
    CandidateEnumeration,
    FutureEvaluation,
    GenerationSpec,
    LanguageEnumeration,
)
from realitygraph.grammar import FiniteConstructor, Grammar

from .circuit_support_growth import (
    direct_nand_family_cost,
    enumerate_available_states,
    enumeration_call_count,
    factorization_census,
    input_masks,
    joint_cost_from_states,
    nand,
    provenance_antichains,
    singleton_relaxation_cost,
    state_antichains,
    support_union_cost,
)


AUTHORITY = "exact-finite-nand-dag-authority-v1"
VERIFIER = "circuit-support-verifier-v1"

XOR_QUERY = "nand:n3:xor01:size"
TRIPLE_QUERY = "nand:n2:joint:3,5,7"
DIRECT_N4_QUERY = "nand:n4:direct-pairs:01,02,03"
DIRECT_N6_FUTURE = "nand:n6:direct-pairs:01,02,03,04,05,12"

EXPECTED = {
    XOR_QUERY: "4",
    TRIPLE_QUERY: "3",
    "rule:support-union": "ENABLED",
    "rule:direct-nand-family": "ENABLED",
    DIRECT_N4_QUERY: "3",
}


def _constructor(
    constructor_id: str,
    rows: tuple[tuple[str, str], ...],
    *,
    dependencies: tuple[str, ...] = (),
    complexity: int,
) -> FiniteConstructor:
    return FiniteConstructor(
        constructor_id=constructor_id,
        input_type="joint-availability-query",
        output_type="exact-gate-cost",
        semantics=rows,
        complexity=complexity,
        dependencies=dependencies,
        primitive_expansion=("semantic-support-antichain",),
    )


def initial_circuit_state() -> DevelopmentalState:
    baseline = _constructor(
        "singleton-cost-relaxation",
        ((XOR_QUERY, "3"),),
        complexity=1,
    )
    return DevelopmentalState(
        generation_index=0,
        grammar=Grammar((baseline,)),
        capability_graph=CapabilityGraph(()),
        admitted_deltas=(),
        terminal_records=(),
        authority_snapshot=AUTHORITY,
        protected_consequence_digest=canonical_digest(
            {"protected": ["singleton-cost-baseline"]},
            prefix="circuit-support-protected-v1:",
        ),
        provenance_ids=("pvsnp-circuit-support-initial-v1",),
    )


@dataclass(frozen=True)
class _CurrentLanguage:
    adapter_id: str

    def enumerate_current(self, state, spec):
        constructors = state.grammar.constructors
        return LanguageEnumeration(
            constructors=constructors,
            carrier_digest=canonical_digest(
                {"queries": list(spec.acquisition_manifest)},
                prefix="circuit-query-carrier-v1:",
            ),
            enumeration_digest=canonical_digest(
                [constructor.payload() for constructor in constructors],
                prefix="circuit-current-language-v1:",
            ),
            replay_evidence=("complete-declared-finite-invariant-language",),
            complete=True,
            search_exhausted=True,
            raw_count=len(constructors),
        )


@dataclass(frozen=True)
class _OneCandidate:
    candidate: FiniteConstructor
    adapter_id: str

    def enumerate_candidates(self, state, residual, spec):
        return CandidateEnumeration(
            constructors=(self.candidate,),
            enumeration_digest=canonical_digest(
                self.candidate.payload(), prefix="circuit-candidate-v1:"
            ),
            replay_evidence=("single-frozen-representation-repair",),
            complete=True,
            raw_count=1,
        )


def _verify_j2() -> bool:
    enumeration = enumerate_available_states(3, 4)
    exact = enumeration.min_size[0x66]
    relaxed = singleton_relaxation_cost(0x66, 3, enumeration.min_size)
    parents = [
        (left, right)
        for left in enumeration.min_size
        for right in enumeration.min_size
        if left <= right and ((~(left & right)) & 0xFF) == 0x66
    ]
    parent_costs = [joint_cost_from_states(enumeration, pair) for pair in parents]
    return relaxed == 3 and exact == 4 and min(x for x in parent_costs if x is not None) == 3


def _verify_support_factorization() -> bool:
    enumeration = enumerate_available_states(3, 4)
    supports = provenance_antichains(3, 4)
    if supports != state_antichains(enumeration):
        return False
    functions = sorted(enumeration.min_size)
    for left_index, left in enumerate(functions):
        for right in functions[left_index:]:
            exact = joint_cost_from_states(enumeration, (left, right))
            factored = support_union_cost((left, right), supports)
            if (factored is not None and factored <= 4) != (exact is not None):
                return False
            if exact is not None and factored != exact:
                return False
    n2 = enumerate_available_states(2, 3)
    triples = factorization_census(3, 3, 3)
    n4 = enumerate_available_states(4, 4)
    n4_fixed_point_matches = provenance_antichains(4, 4) == state_antichains(n4)
    return (
        [
            joint_cost_from_states(n2, pair)
            for pair in ((0x3, 0x5), (0x3, 0x7), (0x5, 0x7))
        ]
        == [2, 2, 2]
        and joint_cost_from_states(n2, (0x3, 0x5, 0x7)) == 3
        and triples == {"checked": 17296, "unavailable": 16303, "errors": 0}
        and n4_fixed_point_matches
    )


def _verify_direct_family() -> bool:
    return direct_nand_family_cost(4, ((0, 1), (0, 2), (0, 3))) == 3


def derive_direct_family(
    state: DevelopmentalState,
    query: str,
    support_dependency_id: str,
    generalizer_id: str,
) -> str | None:
    active = set(state.capability_graph.active_ids())
    if support_dependency_id not in active or generalizer_id not in active:
        return None
    dependency = state.capability_graph.capability_map[support_dependency_id]
    generalizer = state.capability_graph.capability_map[generalizer_id]
    if not dependency.applicable("rule:support-union"):
        return None
    if dependency.execute("rule:support-union") != "ENABLED":
        return None
    if not generalizer.applicable("rule:direct-nand-family"):
        return None
    if generalizer.execute("rule:direct-nand-family") != "ENABLED":
        return None
    parts = query.split(":")
    if len(parts) != 4 or parts[0] != "nand" or parts[2] != "direct-pairs":
        return None
    try:
        n = int(parts[1].removeprefix("n"))
        pairs = tuple((int(pair[0]), int(pair[1])) for pair in parts[3].split(","))
        return str(direct_nand_family_cost(n, pairs))
    except (ValueError, IndexError):
        return None


def independent_direct_oracle(query: str) -> str | None:
    parts = query.split(":")
    if len(parts) != 4 or parts[0] != "nand" or parts[2] != "direct-pairs":
        return None
    try:
        n = int(parts[1].removeprefix("n"))
        pairs = tuple((int(pair[0]), int(pair[1])) for pair in parts[3].split(","))
        inputs = input_masks(n)
        outputs = {
            nand(inputs[left], inputs[right], n)
            for left, right in pairs
        }
        return str(len(outputs))
    except (ValueError, IndexError):
        return None


@dataclass(frozen=True)
class _Verifier:
    obligation: str
    candidate_id: str
    adapter_id: str = VERIFIER

    def current_resolves(self, state, spec, constructor):
        return constructor.semantic_table.get(self.obligation) == EXPECTED[self.obligation]

    def candidate_adequate(self, state, spec, candidate):
        return (
            candidate.constructor_id == self.candidate_id
            and candidate.semantic_table.get(self.obligation) == EXPECTED[self.obligation]
        )

    def verify_candidate(self, state, spec, candidate):
        checks = {
            "joint-coavailability-j2": _verify_j2,
            "provenance-support-union": _verify_support_factorization,
            "direct-nand-family-generalizer": _verify_direct_family,
        }
        dependencies_active = set(candidate.dependencies) <= set(
            state.capability_graph.active_ids()
        )
        return dependencies_active and checks[candidate.constructor_id]()

    def verify_protected(self, state, spec, candidate):
        active = set(state.capability_graph.active_ids())
        return set(candidate.dependencies) <= active

    def compile_capability(self, state, spec, candidate, delta):
        return FiniteCapability(
            capability_id=candidate.constructor_id,
            input_type=candidate.input_type,
            output_type=candidate.output_type,
            semantics=candidate.semantics,
            guard_inputs=(),
            certificate_id=delta.delta_id,
            dependencies=candidate.dependencies,
            authority_snapshot=spec.authority_snapshot,
            verifier_id=self.adapter_id,
            provenance_ids=(delta.delta_id, spec.digest),
            cost=candidate.complexity,
        )

    def verify_future(self, state, spec, capability):
        before = enumeration_call_count()
        if self.candidate_id == "direct-nand-family-generalizer":
            dependency_id = spec.required_dependency_ids[0]
            observations = tuple(
                (
                    query,
                    derive_direct_family(
                        state, query, dependency_id, capability.capability_id
                    ),
                )
                for query in spec.future_manifest
            )
            passed = all(
                actual is not None and actual == independent_direct_oracle(query)
                for query, actual in observations
            )
        else:
            observations = tuple(
                (query, capability.execute(query)) for query in spec.future_manifest
            )
            passed = all(actual == EXPECTED[query] for query, actual in observations)
        after = enumeration_call_count()
        observations = (*observations, ("enumeration_calls", str(after - before)))
        return FutureEvaluation(
            passed=passed and before == after,
            evidence_digest=canonical_digest(
                {"observations": [list(row) for row in observations]},
                prefix="circuit-future-v1:",
            ),
            grammar_search_calls=0,
            observations=observations,
        )


@dataclass(frozen=True)
class _Attack:
    challenges_: tuple[str, ...]
    adapter_id: str

    def challenges(self, state, spec, capability):
        return self.challenges_

    def oracle(self, state, spec, challenge):
        return EXPECTED[challenge]


def _spec(
    generation_id: str,
    obligation: str,
    candidate: FiniteConstructor,
    *,
    future: tuple[str, ...],
    required: tuple[str, ...],
) -> GenerationSpec:
    challenges = tuple(query for query, _ in candidate.semantics)
    return GenerationSpec(
        generation_id=generation_id,
        obligation_id=obligation,
        input_type="joint-availability-query",
        output_type="exact-gate-cost",
        current_language_adapter=_CurrentLanguage(f"{generation_id}-current-v1"),
        lower_substrate_adapter=_OneCandidate(candidate, f"{generation_id}-lower-v1"),
        verifier_adapter=_Verifier(obligation, candidate.constructor_id),
        attack_adapter=_Attack(challenges, f"{generation_id}-attack-v1"),
        acquisition_manifest=(obligation,),
        growth_manifest=(candidate.constructor_id,),
        future_manifest=future,
        resource_envelope=(("candidate_budget", 1), ("attack_budget", len(challenges))),
        authority_snapshot=AUTHORITY,
        protected_consequences=("preserve-prior-circuit-capabilities",),
        required_dependency_ids=required,
    )


def make_g1_spec() -> GenerationSpec:
    candidate = _constructor(
        "joint-coavailability-j2",
        ((XOR_QUERY, "4"),),
        complexity=2,
    )
    return _spec(
        "circuit-j2-growth", XOR_QUERY, candidate, future=(XOR_QUERY,), required=()
    )


def make_g2_spec(state: DevelopmentalState) -> GenerationSpec:
    dependency = state.terminal_records[-1].retained_capability_id
    if dependency is None:
        raise ValueError("G2 requires the retained J2 capability")
    candidate = _constructor(
        "provenance-support-union",
        ((TRIPLE_QUERY, "3"), ("rule:support-union", "ENABLED")),
        dependencies=(dependency,),
        complexity=3,
    )
    return _spec(
        "support-antichain-growth",
        TRIPLE_QUERY,
        candidate,
        future=(TRIPLE_QUERY,),
        required=(dependency,),
    )


def make_g3_spec(state: DevelopmentalState) -> GenerationSpec:
    dependency = state.terminal_records[-1].retained_capability_id
    if dependency is None:
        raise ValueError("G3 requires the retained support capability")
    candidate = _constructor(
        "direct-nand-family-generalizer",
        ((DIRECT_N4_QUERY, "3"), ("rule:direct-nand-family", "ENABLED")),
        dependencies=(dependency,),
        complexity=1,
    )
    return _spec(
        "symbolic-support-transfer",
        DIRECT_N4_QUERY,
        candidate,
        future=(DIRECT_N6_FUTURE,),
        required=(dependency,),
    )
