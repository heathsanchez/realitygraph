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
from realitygraph.grammar import FiniteConstructor
from realitygraph.fixtures.boolean_observer_growth import (
    AUTHORITY,
    PAIR_INPUTS,
    PARITY_SIGNATURE,
    VERIFIER,
    enumerate_nand_candidates,
    old_x_only_grammar,
)
from realitygraph.fixtures.stateful_observer_growth import (
    FUTURE_HISTORIES,
    TARGET_SIGNATURE,
    TRAIN_HISTORIES,
    _history_target,
    _machine_observe,
    _stateless_history_constructors,
    enumerate_stateful_candidates,
)


def _active_capability(state: DevelopmentalState, capability_id: str) -> FiniteCapability:
    if capability_id not in state.capability_graph.active_ids():
        raise ValueError(f"required capability is not active: {capability_id}")
    return state.capability_graph.capability_map[capability_id]


def initial_v2_state() -> DevelopmentalState:
    protected = canonical_digest(
        {"protected": ["preserve-x-only-observers"]},
        prefix="v2-protected:",
    )
    return DevelopmentalState(
        generation_index=0,
        grammar=old_x_only_grammar(),
        capability_graph=CapabilityGraph(()),
        admitted_deltas=(),
        terminal_records=(),
        authority_snapshot=AUTHORITY,
        protected_consequence_digest=protected,
        provenance_ids=("v2-initial-x-only-language",),
    )


@dataclass(frozen=True)
class _BooleanCurrent:
    adapter_id: str = "all-four-boolean-functions-of-x-v2"

    def enumerate_current(self, state, spec):
        constructors = state.grammar.constructors
        return LanguageEnumeration(
            constructors=constructors,
            carrier_digest=canonical_digest(
                {"carrier": list(PAIR_INPUTS)}, prefix="boolean-carrier-v2:"
            ),
            enumeration_digest=canonical_digest(
                [constructor.payload() for constructor in constructors],
                prefix="boolean-current-v2:",
            ),
            replay_evidence=("exhausted-all-four-x-only-boolean-denotations",),
            complete=True,
            search_exhausted=True,
            raw_count=4,
        )


@dataclass(frozen=True)
class _NandLower:
    adapter_id: str = "atoms-0-1-x-y-plus-nand-depth3-v2"

    def enumerate_candidates(self, state, residual, spec):
        candidates, _ = enumerate_nand_candidates(3)
        return CandidateEnumeration(
            constructors=candidates,
            enumeration_digest=canonical_digest(
                [candidate.payload() for candidate in candidates],
                prefix="nand-candidates-v2:",
            ),
            replay_evidence=("canonical-nand-depth-enumeration",),
            complete=True,
            raw_count=len(candidates),
        )


@dataclass(frozen=True)
class _BooleanVerifier:
    adapter_id: str = VERIFIER

    def current_resolves(self, state, spec, constructor):
        return (
            constructor.input_type == "pair"
            and constructor.output_type == "bit"
            and constructor.semantic_signature == PARITY_SIGNATURE
        )

    def candidate_adequate(self, state, spec, candidate):
        return (
            candidate.input_type == "pair"
            and candidate.output_type == "bit"
            and candidate.semantic_signature == PARITY_SIGNATURE
        )

    def verify_candidate(self, state, spec, candidate):
        _, expressions = enumerate_nand_candidates(3)
        expression = expressions.get(candidate.constructor_id)
        return (
            expression is not None
            and expression.signature == candidate.semantic_signature
            and candidate.semantic_signature == PARITY_SIGNATURE
        )

    def verify_protected(self, state, spec, candidate):
        return all(
            constructor.constructor_id in state.grammar.constructor_map
            for constructor in state.grammar.constructors
        )

    def compile_capability(self, state, spec, candidate, delta):
        return FiniteCapability(
            capability_id=candidate.constructor_id,
            input_type=candidate.input_type,
            output_type=candidate.output_type,
            semantics=candidate.semantics,
            guard_inputs=(),
            certificate_id=delta.delta_id,
            dependencies=(),
            authority_snapshot=spec.authority_snapshot,
            verifier_id=self.adapter_id,
            provenance_ids=(delta.delta_id, spec.digest),
            cost=candidate.complexity,
        )

    def verify_future(self, state, spec, capability):
        oracle = dict(zip(PAIR_INPUTS, PARITY_SIGNATURE))
        observations = tuple(
            (value, capability.execute(value)) for value in spec.future_manifest
        )
        passed = all(actual == oracle[value] for value, actual in observations)
        return FutureEvaluation(
            passed=passed,
            evidence_digest=canonical_digest(
                {"observations": [list(item) for item in observations], "passed": passed},
                prefix="g1-future-v2:",
            ),
            grammar_search_calls=0,
            observations=observations,
        )


@dataclass(frozen=True)
class _BooleanAttack:
    adapter_id: str = "parity-full-carrier-attack-v2"

    def challenges(self, state, spec, capability):
        return PAIR_INPUTS

    def oracle(self, state, spec, challenge):
        return dict(zip(PAIR_INPUTS, PARITY_SIGNATURE))[challenge]


def make_g1_spec() -> GenerationSpec:
    return GenerationSpec(
        generation_id="boolean-observer-growth",
        obligation_id="parity-observer",
        input_type="pair",
        output_type="bit",
        current_language_adapter=_BooleanCurrent(),
        lower_substrate_adapter=_NandLower(),
        verifier_adapter=_BooleanVerifier(),
        attack_adapter=_BooleanAttack(),
        acquisition_manifest=("x-only-language",),
        growth_manifest=("parity-observer",),
        future_manifest=("11", "01"),
        resource_envelope=(("candidate_budget", 128), ("attack_budget", len(PAIR_INPUTS))),
        authority_snapshot=AUTHORITY,
        protected_consequences=("preserve-x-only-observers",),
        required_dependency_ids=(),
    )


@dataclass(frozen=True)
class _StatelessHistoryCurrent:
    adapter_id: str = "all-16-stateless-current-pair-denotations-v2"

    def enumerate_current(self, state, spec):
        stateless = _stateless_history_constructors()
        constructors = (*state.grammar.constructors, *stateless)
        return LanguageEnumeration(
            constructors=constructors,
            carrier_digest=canonical_digest(
                {"histories": list(TRAIN_HISTORIES)}, prefix="history-carrier-v2:"
            ),
            enumeration_digest=canonical_digest(
                [constructor.payload() for constructor in constructors],
                prefix="stateless-history-current-v2:",
            ),
            replay_evidence=("exhausted-all-16-current-pair-boolean-denotations",),
            complete=True,
            search_exhausted=True,
            raw_count=16,
        )


@dataclass(frozen=True)
class _TwoStateLower:
    dependency_id: str
    adapter_id: str = "generic-two-state-moore-over-earned-signal-v2"

    def enumerate_candidates(self, state, residual, spec):
        capability = _active_capability(state, self.dependency_id)
        constructor = state.grammar.constructor_map[self.dependency_id]
        candidates, _ = enumerate_stateful_candidates(constructor, capability)
        return CandidateEnumeration(
            constructors=candidates,
            enumeration_digest=canonical_digest(
                [candidate.payload() for candidate in candidates],
                prefix="two-state-candidates-v2:",
            ),
            replay_evidence=("exhausted-64-two-state-binary-moore-machines",),
            complete=True,
            raw_count=64,
        )


@dataclass(frozen=True)
class _HistoryVerifier:
    dependency_id: str
    adapter_id: str = VERIFIER

    def _inputs(self, state):
        capability = _active_capability(state, self.dependency_id)
        constructor = state.grammar.constructor_map[self.dependency_id]
        return constructor, capability

    def current_resolves(self, state, spec, constructor):
        return (
            constructor.input_type == "history"
            and constructor.output_type == "bit"
            and constructor.semantic_signature == TARGET_SIGNATURE
        )

    def candidate_adequate(self, state, spec, candidate):
        return (
            candidate.input_type == "history"
            and candidate.output_type == "bit"
            and candidate.semantic_signature == TARGET_SIGNATURE
            and self.dependency_id in candidate.dependencies
        )

    def verify_candidate(self, state, spec, candidate):
        constructor, capability = self._inputs(state)
        _, machines = enumerate_stateful_candidates(constructor, capability)
        machine = machines.get(candidate.constructor_id)
        return (
            machine is not None
            and "".join(
                _machine_observe(machine, capability, history)
                for history in TRAIN_HISTORIES
            )
            == candidate.semantic_signature
            == TARGET_SIGNATURE
        )

    def verify_protected(self, state, spec, candidate):
        return self.dependency_id in state.capability_graph.active_ids()

    def compile_capability(self, state, spec, candidate, delta):
        constructor, dependency = self._inputs(state)
        _, machines = enumerate_stateful_candidates(constructor, dependency)
        machine = machines[candidate.constructor_id]
        all_histories = (*TRAIN_HISTORIES, *FUTURE_HISTORIES)
        semantics = tuple(
            (history, _machine_observe(machine, dependency, history))
            for history in all_histories
        )
        return FiniteCapability(
            capability_id=candidate.constructor_id,
            input_type="history",
            output_type="bit",
            semantics=semantics,
            guard_inputs=(),
            certificate_id=f"{delta.delta_id}:complete-history-scope",
            dependencies=(self.dependency_id,),
            authority_snapshot=spec.authority_snapshot,
            verifier_id=self.adapter_id,
            provenance_ids=(delta.delta_id, spec.digest),
            cost=candidate.complexity,
        )

    def verify_future(self, state, spec, capability):
        dependency = _active_capability(state, self.dependency_id)
        observations = tuple(
            (history, capability.execute(history)) for history in spec.future_manifest
        )
        passed = all(
            actual == _history_target(dependency, history)
            for history, actual in observations
        )
        return FutureEvaluation(
            passed=passed,
            evidence_digest=canonical_digest(
                {"observations": [list(item) for item in observations], "passed": passed},
                prefix="g2-future-v2:",
            ),
            grammar_search_calls=0,
            observations=observations,
        )


@dataclass(frozen=True)
class _HistoryAttack:
    dependency_id: str
    adapter_id: str = "history-complete-attack-v2"

    def challenges(self, state, spec, capability):
        return (*TRAIN_HISTORIES, *FUTURE_HISTORIES)

    def oracle(self, state, spec, challenge):
        dependency = _active_capability(state, self.dependency_id)
        return _history_target(dependency, challenge)


def make_g2_spec(state: DevelopmentalState) -> GenerationSpec:
    if not state.terminal_records or state.terminal_records[-1].retained_capability_id is None:
        raise ValueError("state has no retained predecessor capability")
    dependency_id = state.terminal_records[-1].retained_capability_id
    _active_capability(state, dependency_id)
    return GenerationSpec(
        generation_id="stateful-history-observer-growth",
        obligation_id="remember-previous-earned-signal",
        input_type="history",
        output_type="bit",
        current_language_adapter=_StatelessHistoryCurrent(),
        lower_substrate_adapter=_TwoStateLower(dependency_id),
        verifier_adapter=_HistoryVerifier(dependency_id),
        attack_adapter=_HistoryAttack(dependency_id),
        acquisition_manifest=("earned-predecessor",),
        growth_manifest=("stateful-history-separation",),
        future_manifest=FUTURE_HISTORIES,
        resource_envelope=(
            ("candidate_budget", 128),
            ("attack_budget", len(TRAIN_HISTORIES) + len(FUTURE_HISTORIES)),
        ),
        authority_snapshot=AUTHORITY,
        protected_consequences=("preserve-earned-predecessor",),
        required_dependency_ids=(dependency_id,),
    )
