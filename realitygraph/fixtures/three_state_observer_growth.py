from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from realitygraph.capability import FiniteCapability
from realitygraph.developmental_state import DevelopmentalState
from realitygraph.developmental_types import canonical_digest
from realitygraph.fixtures.boolean_observer_growth import AUTHORITY, VERIFIER
from realitygraph.generation_spec import (
    CandidateEnumeration,
    FutureEvaluation,
    GenerationSpec,
    LanguageEnumeration,
)
from realitygraph.grammar import FiniteConstructor


SEQUENCE_CARRIER = tuple(
    "".join(bits)
    for length in range(5)
    for bits in product("01", repeat=length)
)


def target_contains_11(sequence: str) -> str:
    if any(bit not in "01" for bit in sequence):
        raise ValueError("sequence carrier is binary")
    return "1" if "11" in sequence else "0"


TARGET_SIGNATURE = "".join(
    target_contains_11(sequence) for sequence in sorted(SEQUENCE_CARRIER)
)


class NegativeFixtureError(RuntimeError):
    pass


@dataclass(frozen=True)
class MooreMachine:
    state_count: int
    transitions: tuple[int, ...]
    outputs: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.state_count < 1:
            raise ValueError("Moore machine requires at least one state")
        if len(self.transitions) != self.state_count * 2:
            raise ValueError("binary-input Moore transition table has wrong size")
        if len(self.outputs) != self.state_count:
            raise ValueError("Moore output table has wrong size")
        if any(value < 0 or value >= self.state_count for value in self.transitions):
            raise ValueError("Moore transition leaves state carrier")
        if any(value not in (0, 1) for value in self.outputs):
            raise ValueError("fixture Moore outputs must be binary")

    @property
    def machine_id(self) -> str:
        transition_text = "".join(str(value) for value in self.transitions)
        output_text = "".join(str(value) for value in self.outputs)
        return f"s{self.state_count}-t{transition_text}-o{output_text}"

    @property
    def complexity(self) -> int:
        return self.state_count + sum(self.transitions) + sum(self.outputs)

    def run(self, signals: str) -> str:
        state = 0
        for signal in signals:
            if signal not in "01":
                raise ValueError("Moore machine input must be binary")
            state = self.transitions[2 * state + int(signal)]
        return str(self.outputs[state])


@dataclass(frozen=True)
class MachineEnumeration:
    constructors: tuple[FiniteConstructor, ...]
    machine_rows: tuple[tuple[str, MooreMachine], ...]
    raw_machine_count: int
    complete: bool
    carrier_digest: str
    enumeration_digest: str

    @property
    def machine_map(self) -> dict[str, MooreMachine]:
        return dict(self.machine_rows)

    @property
    def semantic_signatures(self) -> tuple[str, ...]:
        return tuple(sorted({constructor.semantic_signature for constructor in self.constructors}))


def _bit_history(bit: str) -> str:
    if bit == "0":
        return "00>00"
    if bit == "1":
        return "01>00"
    raise ValueError("signal bit must be binary")


def _signals_from_dependency(dependency: FiniteCapability, sequence: str) -> str:
    signals = "".join(dependency.execute(_bit_history(bit)) for bit in sequence)
    if signals != sequence:
        raise ValueError("earned dependency does not realize the frozen binary signal carrier")
    return signals


def _enumerate_machines(state_count: int, dependency: FiniteCapability) -> MachineEnumeration:
    best_by_signature: dict[str, tuple[tuple[int, str], FiniteConstructor, MooreMachine]] = {}
    raw_count = 0
    for transitions in product(range(state_count), repeat=state_count * 2):
        for outputs in product((0, 1), repeat=state_count):
            raw_count += 1
            machine = MooreMachine(state_count, tuple(transitions), tuple(outputs))
            signature = "".join(
                machine.run(_signals_from_dependency(dependency, sequence))
                for sequence in SEQUENCE_CARRIER
            )
            constructor_id = f"g3-{machine.machine_id}"
            constructor = FiniteConstructor(
                constructor_id=constructor_id,
                input_type="signal-sequence",
                output_type="bit",
                semantics=tuple(zip(SEQUENCE_CARRIER, signature)),
                complexity=machine.complexity,
                dependencies=(dependency.capability_id,),
                primitive_expansion=(
                    f"moore:{state_count}:transitions={machine.transitions}:outputs={machine.outputs}",
                ),
            )
            key = (machine.complexity, machine.machine_id)
            old = best_by_signature.get(signature)
            if old is None or key < old[0]:
                best_by_signature[signature] = (key, constructor, machine)

    ordered = sorted(
        ((row[1], row[2]) for row in best_by_signature.values()),
        key=lambda pair: (pair[0].complexity, pair[0].constructor_id),
    )
    constructors = tuple(pair[0] for pair in ordered)
    machine_rows = tuple((pair[0].constructor_id, pair[1]) for pair in ordered)
    carrier_digest = canonical_digest(
        {"sequences": list(SEQUENCE_CARRIER)}, prefix="g3-sequence-carrier-v2:"
    )
    enumeration_digest = canonical_digest(
        {
            "state_count": state_count,
            "raw_machine_count": raw_count,
            "carrier_digest": carrier_digest,
            "constructors": [constructor.payload() for constructor in constructors],
        },
        prefix="g3-machine-enumeration-v2:",
    )
    return MachineEnumeration(
        constructors=constructors,
        machine_rows=machine_rows,
        raw_machine_count=raw_count,
        complete=True,
        carrier_digest=carrier_digest,
        enumeration_digest=enumeration_digest,
    )


def enumerate_two_state_denotations(dependency: FiniteCapability) -> MachineEnumeration:
    return _enumerate_machines(2, dependency)


def enumerate_three_state_candidates(dependency: FiniteCapability) -> MachineEnumeration:
    return _enumerate_machines(3, dependency)


def _active_dependency(state: DevelopmentalState, capability_id: str) -> FiniteCapability:
    if capability_id not in state.capability_graph.active_ids():
        raise ValueError(f"required capability is not active: {capability_id}")
    return state.capability_graph.capability_map[capability_id]


@dataclass(frozen=True)
class _TwoStateCurrent:
    dependency_id: str
    adapter_id: str = "complete-two-state-moore-language-v2"

    def enumerate_current(self, state, spec):
        dependency = _active_dependency(state, self.dependency_id)
        enumeration = enumerate_two_state_denotations(dependency)
        constructors = (*state.grammar.constructors, *enumeration.constructors)
        return LanguageEnumeration(
            constructors=constructors,
            carrier_digest=enumeration.carrier_digest,
            enumeration_digest=enumeration.enumeration_digest,
            replay_evidence=(
                f"exhausted-{enumeration.raw_machine_count}-two-state-binary-input-moore-machines",
            ),
            complete=enumeration.complete,
            search_exhausted=True,
            raw_count=enumeration.raw_machine_count,
        )


@dataclass(frozen=True)
class _ThreeStateLower:
    dependency_id: str
    adapter_id: str = "complete-three-state-moore-substrate-v2"

    def enumerate_candidates(self, state, residual, spec):
        dependency = _active_dependency(state, self.dependency_id)
        enumeration = enumerate_three_state_candidates(dependency)
        return CandidateEnumeration(
            constructors=enumeration.constructors,
            enumeration_digest=enumeration.enumeration_digest,
            replay_evidence=(
                f"exhausted-{enumeration.raw_machine_count}-three-state-binary-input-moore-machines",
            ),
            complete=enumeration.complete,
            raw_count=enumeration.raw_machine_count,
        )


@dataclass(frozen=True)
class _ThreeStateVerifier:
    dependency_id: str
    adapter_id: str = VERIFIER

    def current_resolves(self, state, spec, constructor):
        return (
            constructor.input_type == "signal-sequence"
            and constructor.output_type == "bit"
            and constructor.semantic_signature == TARGET_SIGNATURE
        )

    def candidate_adequate(self, state, spec, candidate):
        return (
            candidate.input_type == "signal-sequence"
            and candidate.output_type == "bit"
            and candidate.semantic_signature == TARGET_SIGNATURE
            and self.dependency_id in candidate.dependencies
        )

    def verify_candidate(self, state, spec, candidate):
        dependency = _active_dependency(state, self.dependency_id)
        enumeration = enumerate_three_state_candidates(dependency)
        machine = enumeration.machine_map.get(candidate.constructor_id)
        if machine is None:
            return False
        signature = "".join(
            machine.run(_signals_from_dependency(dependency, sequence))
            for sequence in sorted(SEQUENCE_CARRIER)
        )
        return signature == candidate.semantic_signature == TARGET_SIGNATURE

    def verify_protected(self, state, spec, candidate):
        return self.dependency_id in state.capability_graph.active_ids()

    def compile_capability(self, state, spec, candidate, delta):
        return FiniteCapability(
            capability_id=candidate.constructor_id,
            input_type="signal-sequence",
            output_type="bit",
            semantics=candidate.semantics,
            guard_inputs=(),
            certificate_id=f"{delta.delta_id}:complete-sequence-scope",
            dependencies=(self.dependency_id,),
            authority_snapshot=spec.authority_snapshot,
            verifier_id=self.adapter_id,
            provenance_ids=(delta.delta_id, spec.digest),
            cost=candidate.complexity,
        )

    def verify_future(self, state, spec, capability):
        observations = tuple(
            (sequence, capability.execute(sequence)) for sequence in spec.future_manifest
        )
        passed = all(
            actual == target_contains_11(sequence)
            for sequence, actual in observations
        )
        return FutureEvaluation(
            passed=passed,
            evidence_digest=canonical_digest(
                {"observations": [list(item) for item in observations], "passed": passed},
                prefix="g3-future-v2:",
            ),
            grammar_search_calls=0,
            observations=observations,
        )


@dataclass(frozen=True)
class _ThreeStateAttack:
    dependency_id: str
    adapter_id: str = "complete-sequence-carrier-attack-v2"

    def challenges(self, state, spec, capability):
        return SEQUENCE_CARRIER

    def oracle(self, state, spec, challenge):
        _active_dependency(state, self.dependency_id)
        return target_contains_11(challenge)


def make_g3_spec(state: DevelopmentalState) -> GenerationSpec:
    if not state.terminal_records or state.terminal_records[-1].retained_capability_id is None:
        raise ValueError("state has no retained predecessor capability")
    dependency_id = state.terminal_records[-1].retained_capability_id
    dependency = _active_dependency(state, dependency_id)
    two_state = enumerate_two_state_denotations(dependency)
    if TARGET_SIGNATURE in two_state.semantic_signatures:
        raise NegativeFixtureError("G3 target realizable by two-state machine")
    future_manifest = ("0011", "1011", "1111", "0101")
    return GenerationSpec(
        generation_id="three-state-temporal-observer-growth",
        obligation_id="remember-whether-consecutive-ones-occurred",
        input_type="signal-sequence",
        output_type="bit",
        current_language_adapter=_TwoStateCurrent(dependency_id),
        lower_substrate_adapter=_ThreeStateLower(dependency_id),
        verifier_adapter=_ThreeStateVerifier(dependency_id),
        attack_adapter=_ThreeStateAttack(dependency_id),
        acquisition_manifest=("earned-stateful-predecessor",),
        growth_manifest=("contains-consecutive-ones",),
        future_manifest=future_manifest,
        resource_envelope=(
            ("candidate_budget", 10000),
            ("attack_budget", len(SEQUENCE_CARRIER)),
        ),
        authority_snapshot=AUTHORITY,
        protected_consequences=("preserve-earned-stateful-predecessor",),
        required_dependency_ids=(dependency_id,),
    )
