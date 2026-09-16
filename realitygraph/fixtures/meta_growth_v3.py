from __future__ import annotations

from dataclasses import dataclass
from itertools import product

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
from realitygraph.meta_executor import MetaGrowthSpec
from realitygraph.meta_memory import RepairPhase
from realitygraph.obstruction_fingerprint import ObstructionFingerprint, canonicalize_obstruction
from realitygraph.repair_strategy import RepairPortfolio


FAMILY_C = "observation-collision"
FAMILY_T = "temporal-collision"
DEEPEN_STATELESS_COMPOSITION = "deepen_stateless_composition"
ADD_OBSERVABLE = "add_observable"
ADD_FINITE_MEMORY_2 = "add_finite_memory_2"
ADD_FINITE_MEMORY_3 = "add_finite_memory_3"

AUTHORITY = "verified-meta-growth-v3-authority"
VERIFIER = "verified-meta-growth-v3-exact-verifier"
STRATEGY_VERSION = "v1"


_SURFACES = {
    (FAMILY_C, "acquisition"): ("ca-elm", "ca-fir", "ca-ash", "ca-yew"),
    (FAMILY_C, "calibration"): ("cc-iris", "cc-lily", "cc-rose", "cc-pine"),
    (FAMILY_C, "future"): ("cf-moon", "cf-star", "cf-wave", "cf-dune"),
    (FAMILY_C, "partial"): ("cp-a", "cp-b", "cp-c", "cp-d"),
    (FAMILY_T, "acquisition"): ("ta-red", "ta-blue", "ta-gold", "ta-jade"),
    (FAMILY_T, "calibration"): ("tc-north", "tc-east", "tc-south", "tc-west"),
    (FAMILY_T, "future"): ("tf-one", "tf-two", "tf-three", "tf-four"),
    (FAMILY_T, "budget"): ("tb-a", "tb-b", "tb-c", "tb-d"),
}

_HIDDEN_BITS = ((0, 0), (0, 1), (1, 0), (1, 1))


@dataclass(frozen=True)
class MetaFixtureWorld:
    family: str
    variant: str
    carrier: tuple[str, ...]
    hidden_bits: tuple[tuple[int, int], ...]
    input_type: str
    current_complete: bool = True

    def __post_init__(self) -> None:
        if self.family not in (FAMILY_C, FAMILY_T):
            raise ValueError("unknown V3 fixture family")
        if len(self.carrier) != 4 or len(set(self.carrier)) != 4:
            raise ValueError("V3 fixture requires four unique surface states")
        if self.hidden_bits != _HIDDEN_BITS:
            raise ValueError("V3 fixture hidden finite carrier must remain frozen")

    @property
    def observed_map(self) -> dict[str, str]:
        # Family C observes only the first coordinate. Family T observes only
        # the present (second) bit of a two-symbol history.
        index = 0 if self.family == FAMILY_C else 1
        return {
            surface: str(bits[index])
            for surface, bits in zip(self.carrier, self.hidden_bits)
        }

    @property
    def target_map(self) -> dict[str, str]:
        if self.family == FAMILY_C:
            # The missing observable is the independent second coordinate.
            return {
                surface: str(bits[1])
                for surface, bits in zip(self.carrier, self.hidden_bits)
            }
        # Temporal target: whether a 1 has appeared anywhere in the two-symbol
        # history. Present-only state cannot distinguish 00 from 10, while a
        # two-state "seen one" automaton can.
        return {
            surface: str(int(bool(bits[0] or bits[1])))
            for surface, bits in zip(self.carrier, self.hidden_bits)
        }

    @property
    def interface_digest(self) -> str:
        return canonical_digest(
            {"input_type": self.input_type, "output_type": "bit"},
            prefix="meta-growth-v3-interface:",
        )


@dataclass(frozen=True)
class EpisodeBundle:
    world: MetaFixtureWorld
    state: DevelopmentalState
    spec: MetaGrowthSpec


class FixtureCurrentLanguage:
    def __init__(self, world: MetaFixtureWorld):
        self.world = world
        self.adapter_id = f"v3-current-{world.family}-{world.variant}"

    def enumerate_current(self, state, spec):
        return LanguageEnumeration(
            constructors=state.grammar.constructors,
            carrier_digest=canonical_digest(
                {"carrier": list(self.world.carrier)},
                prefix="v3-current-carrier:",
            ),
            enumeration_digest=canonical_digest(
                {
                    "world": self.world.variant,
                    "constructors": [c.payload() for c in state.grammar.constructors],
                    "complete": self.world.current_complete,
                },
                prefix="v3-current-enumeration:",
            ),
            replay_evidence=(
                "complete-four-boolean-functions-of-declared-observed-bit"
                if self.world.current_complete
                else "deliberately-partial-current-language-control",
            ),
            complete=self.world.current_complete,
            search_exhausted=self.world.current_complete,
            raw_count=len(state.grammar.constructors),
        )


class EmptyLowerSubstrate:
    adapter_id = "v3-meta-template-no-direct-lower-substrate"

    def enumerate_candidates(self, state, residual, spec):
        return CandidateEnumeration((), "v3-empty-template", ("meta-layer-selects-repair",), True, 0)


class CandidateAdapter:
    def __init__(self, adapter_id: str, constructors: tuple[FiniteConstructor, ...], raw_count: int):
        self.adapter_id = adapter_id
        self._constructors = constructors
        self._raw_count = raw_count

    def enumerate_candidates(self, state, residual, spec):
        return CandidateEnumeration(
            constructors=self._constructors,
            enumeration_digest=canonical_digest(
                {
                    "adapter": self.adapter_id,
                    "constructors": [c.payload() for c in self._constructors],
                    "raw_count": self._raw_count,
                },
                prefix="v3-repair-candidates:",
            ),
            replay_evidence=(f"exhausted-declared-repair-space:{self.adapter_id}",),
            complete=True,
            raw_count=self._raw_count,
        )


class FixtureVerifier:
    adapter_id = VERIFIER

    def __init__(self, world: MetaFixtureWorld):
        self.world = world

    def current_resolves(self, state, spec, constructor):
        return constructor.semantic_table == self.world.target_map

    def candidate_adequate(self, state, spec, candidate):
        return candidate.semantic_table == self.world.target_map

    def verify_candidate(self, state, spec, candidate):
        return candidate.semantic_table == self.world.target_map

    def verify_protected(self, state, spec, candidate):
        return all(
            ident in state.grammar.constructor_map
            for ident in state.grammar.constructor_map
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
            authority_snapshot=AUTHORITY,
            verifier_id=self.adapter_id,
            provenance_ids=(delta.delta_id, spec.digest),
            cost=candidate.complexity,
        )

    def verify_future(self, state, spec, capability):
        observations = tuple(
            (value, capability.execute(value)) for value in spec.future_manifest
        )
        passed = all(
            output == self.world.target_map[value]
            for value, output in observations
        )
        return FutureEvaluation(
            passed=passed,
            evidence_digest=canonical_digest(
                {"world": self.world.variant, "observations": [list(x) for x in observations]},
                prefix="v3-object-future:",
            ),
            grammar_search_calls=0,
            observations=observations,
        )


class FixtureAttack:
    adapter_id = "verified-meta-growth-v3-exhaustive-attack"

    def __init__(self, world: MetaFixtureWorld):
        self.world = world

    def challenges(self, state, spec, capability):
        return self.world.carrier

    def oracle(self, state, spec, challenge):
        return self.world.target_map[challenge]


class FixtureFingerprintBuilder:
    builder_id = "verified-meta-growth-v3-exact-partition-fingerprint"

    def __init__(self, world: MetaFixtureWorld):
        self.world = world

    @staticmethod
    def _partition(mapping: dict[str, str]) -> tuple[tuple[str, ...], ...]:
        classes: dict[str, list[str]] = {}
        for key, value in mapping.items():
            classes.setdefault(value, []).append(key)
        return tuple(tuple(sorted(classes[value])) for value in sorted(classes))

    def build(self, state, spec, current) -> ObstructionFingerprint:
        return canonicalize_obstruction(
            input_type=self.world.input_type,
            output_type="bit",
            current_partition=self._partition(self.world.observed_map),
            consequence_partition=self._partition(self.world.target_map),
            current_language_semantic_count=len(current.semantic_signatures),
            authority_snapshot=AUTHORITY,
            verifier_id=VERIFIER,
        )


def _current_constructors(world: MetaFixtureWorld) -> tuple[FiniteConstructor, ...]:
    observed = world.observed_map
    functions = {
        "zero": lambda bit: "0",
        "one": lambda bit: "1",
        "identity": lambda bit: bit,
        "not": lambda bit: "1" if bit == "0" else "0",
    }
    return tuple(
        FiniteConstructor(
            constructor_id=f"{world.family}-{world.variant}-current-{name}",
            input_type=world.input_type,
            output_type="bit",
            semantics=tuple((key, fn(observed[key])) for key in world.carrier),
            complexity=0,
            primitive_expansion=(f"declared-observed-bit:{name}",),
        )
        for name, fn in sorted(functions.items())
    )


def _seed_state(world: MetaFixtureWorld) -> DevelopmentalState:
    return DevelopmentalState(
        generation_index=0,
        grammar=Grammar(_current_constructors(world)),
        capability_graph=CapabilityGraph(()),
        admitted_deltas=(),
        terminal_records=(),
        authority_snapshot=AUTHORITY,
        protected_consequence_digest=canonical_digest(
            {"family": world.family, "protected": "complete-current-language"},
            prefix="v3-protected:",
        ),
        provenance_ids=(f"frozen-world:{world.family}:{world.variant}",),
    )


def _object_template(world: MetaFixtureWorld) -> GenerationSpec:
    return GenerationSpec(
        generation_id=f"meta-template-{world.family}-{world.variant}",
        obligation_id=f"resolve-certified-obstruction-{world.family}",
        input_type=world.input_type,
        output_type="bit",
        current_language_adapter=FixtureCurrentLanguage(world),
        lower_substrate_adapter=EmptyLowerSubstrate(),
        verifier_adapter=FixtureVerifier(world),
        attack_adapter=FixtureAttack(world),
        acquisition_manifest=world.carrier,
        growth_manifest=("certified-obstruction",),
        future_manifest=world.carrier,
        resource_envelope=(("candidate_budget", 6000), ("attack_budget", len(world.carrier))),
        authority_snapshot=AUTHORITY,
        protected_consequences=("preserve-complete-current-language",),
    )


def _repair_spec(
    world: MetaFixtureWorld,
    meta_spec: MetaGrowthSpec,
    strategy_id: str,
    candidates: tuple[FiniteConstructor, ...],
    raw_count: int,
) -> GenerationSpec:
    template = meta_spec.object_template
    return GenerationSpec(
        generation_id=f"{meta_spec.episode_id}-{strategy_id}",
        obligation_id=template.obligation_id,
        input_type=world.input_type,
        output_type="bit",
        current_language_adapter=template.current_language_adapter,
        lower_substrate_adapter=CandidateAdapter(
            f"v3-lower-{strategy_id}-{world.family}-{world.variant}",
            candidates,
            raw_count,
        ),
        verifier_adapter=template.verifier_adapter,
        attack_adapter=template.attack_adapter,
        acquisition_manifest=template.acquisition_manifest,
        growth_manifest=(strategy_id,),
        future_manifest=template.future_manifest,
        resource_envelope=(("candidate_budget", max(1, raw_count)), ("attack_budget", len(world.carrier))),
        authority_snapshot=AUTHORITY,
        protected_consequences=template.protected_consequences,
    )


def _stateless_candidates(world: MetaFixtureWorld, strategy_id: str) -> tuple[FiniteConstructor, ...]:
    observed = world.observed_map
    signatures = (
        ("zero", lambda bit: "0"),
        ("one", lambda bit: "1"),
        ("identity", lambda bit: bit),
        ("not", lambda bit: "1" if bit == "0" else "0"),
    )
    return tuple(
        FiniteConstructor(
            constructor_id=f"{world.variant}-{strategy_id}-{name}",
            input_type=world.input_type,
            output_type="bit",
            semantics=tuple((key, fn(observed[key])) for key in world.carrier),
            complexity=1,
            primitive_expansion=(f"stateless-function-of-declared-observation:{name}",),
        )
        for name, fn in signatures
    )


def _observable_candidates(world: MetaFixtureWorld, strategy_id: str) -> tuple[FiniteConstructor, ...]:
    if world.family == FAMILY_C:
        return (
            FiniteConstructor(
                constructor_id=f"{world.variant}-{strategy_id}-second-coordinate",
                input_type=world.input_type,
                output_type="bit",
                semantics=tuple((key, world.target_map[key]) for key in world.carrier),
                complexity=1,
                primitive_expansion=("new-stateless-second-coordinate-observer",),
            ),
        )
    # The declared temporal observation vocabulary remains present-only. Its
    # exhaustive Boolean denotations cannot recover an earlier symbol.
    return _stateless_candidates(world, strategy_id)


def _run_machine(
    state_count: int,
    transitions: tuple[int, ...],
    outputs: tuple[int, ...],
    sequence: tuple[int, ...],
) -> str:
    state = 0
    for symbol in sequence:
        state = transitions[state_count * symbol + state]
    return str(outputs[state])


def _machine_candidates(
    world: MetaFixtureWorld,
    strategy_id: str,
    state_count: int,
) -> tuple[FiniteConstructor, ...]:
    if world.family != FAMILY_T:
        return ()
    candidates: list[FiniteConstructor] = []
    # Transition table is indexed by symbol-major order: symbol * states + state.
    for transitions in product(range(state_count), repeat=state_count * 2):
        for outputs in product((0, 1), repeat=state_count):
            transition_text = "".join(str(x) for x in transitions)
            output_text = "".join(str(x) for x in outputs)
            semantics = tuple(
                (
                    surface,
                    _run_machine(state_count, tuple(transitions), tuple(outputs), bits),
                )
                for surface, bits in zip(world.carrier, world.hidden_bits)
            )
            candidates.append(
                FiniteConstructor(
                    constructor_id=(
                        f"{world.variant}-{strategy_id}-s{state_count}-"
                        f"t{transition_text}-o{output_text}"
                    ),
                    input_type=world.input_type,
                    output_type="bit",
                    semantics=semantics,
                    complexity=state_count,
                    primitive_expansion=(
                        f"complete-{state_count}-state-moore:"
                        f"transitions={tuple(transitions)}:outputs={tuple(outputs)}",
                    ),
                )
            )
    return tuple(candidates)


@dataclass(frozen=True)
class DeepenStatelessComposition:
    strategy_id: str = DEEPEN_STATELESS_COMPOSITION
    strategy_version: str = STRATEGY_VERSION
    structural_cost: int = 1

    def applicable(self, fingerprint, object_state, meta_spec):
        return True

    def materialize_generation_spec(self, object_state, meta_spec):
        world = meta_spec.object_template.verifier_adapter.world
        candidates = _stateless_candidates(world, self.strategy_id)
        return _repair_spec(world, meta_spec, self.strategy_id, candidates, len(candidates))


@dataclass(frozen=True)
class AddObservable:
    strategy_id: str = ADD_OBSERVABLE
    strategy_version: str = STRATEGY_VERSION
    structural_cost: int = 1

    def applicable(self, fingerprint, object_state, meta_spec):
        return True

    def materialize_generation_spec(self, object_state, meta_spec):
        world = meta_spec.object_template.verifier_adapter.world
        candidates = _observable_candidates(world, self.strategy_id)
        return _repair_spec(world, meta_spec, self.strategy_id, candidates, len(candidates))


@dataclass(frozen=True)
class AddFiniteMemory:
    state_count: int
    strategy_id: str
    structural_cost: int
    strategy_version: str = STRATEGY_VERSION

    def applicable(self, fingerprint, object_state, meta_spec):
        return meta_spec.object_template.input_type == "history"

    def materialize_generation_spec(self, object_state, meta_spec):
        world = meta_spec.object_template.verifier_adapter.world
        candidates = _machine_candidates(world, self.strategy_id, self.state_count)
        return _repair_spec(world, meta_spec, self.strategy_id, candidates, len(candidates))


def frozen_portfolio() -> RepairPortfolio:
    return RepairPortfolio((
        DeepenStatelessComposition(),
        AddObservable(),
        AddFiniteMemory(2, ADD_FINITE_MEMORY_2, 2),
        AddFiniteMemory(3, ADD_FINITE_MEMORY_3, 3),
    ))


def _world(family: str, variant: str, *, current_complete: bool = True) -> MetaFixtureWorld:
    try:
        surface = _SURFACES[(family, variant)]
    except KeyError as exc:
        raise ValueError(f"unknown frozen V3 episode: {family}/{variant}") from exc
    return MetaFixtureWorld(
        family=family,
        variant=variant,
        carrier=surface,
        hidden_bits=_HIDDEN_BITS,
        input_type="pair" if family == FAMILY_C else "history",
        current_complete=current_complete,
    )


def make_episode(
    family: str,
    variant: str,
    phase: RepairPhase,
    *,
    current_complete: bool = True,
    portfolio_budget: int | None = None,
) -> EpisodeBundle:
    world = _world(family, variant, current_complete=current_complete)
    state = _seed_state(world)
    portfolio = frozen_portfolio()
    template = _object_template(world)
    spec = MetaGrowthSpec(
        episode_id=f"{family}-{variant}",
        phase=phase,
        object_template=template,
        fingerprint_builder=FixtureFingerprintBuilder(world),
        portfolio=portfolio,
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        interface_digest=world.interface_digest,
        portfolio_budget=(
            len(portfolio.strategies) if portfolio_budget is None else portfolio_budget
        ),
    )
    return EpisodeBundle(world=world, state=state, spec=spec)


def episode_fingerprint(bundle: EpisodeBundle) -> ObstructionFingerprint:
    template = bundle.spec.object_template
    current = template.current_language_adapter.enumerate_current(bundle.state, template)
    if not current.complete:
        raise ValueError("cannot fingerprint incomplete current language")
    return bundle.spec.fingerprint_builder.build(bundle.state, template, current)


def make_tie_control() -> EpisodeBundle:
    world = _world(FAMILY_C, "partial", current_complete=True)
    state = _seed_state(world)
    portfolio = RepairPortfolio((
        AddObservable(strategy_id="tie-observe-a", structural_cost=1),
        AddObservable(strategy_id="tie-observe-b", structural_cost=1),
    ))
    template = _object_template(world)
    spec = MetaGrowthSpec(
        episode_id="tie-control",
        phase=RepairPhase.CONTROL,
        object_template=template,
        fingerprint_builder=FixtureFingerprintBuilder(world),
        portfolio=portfolio,
        authority_snapshot=AUTHORITY,
        verifier_id=VERIFIER,
        interface_digest=world.interface_digest,
        portfolio_budget=2,
    )
    return EpisodeBundle(world=world, state=state, spec=spec)
