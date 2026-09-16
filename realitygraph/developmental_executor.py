from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .attack import AttackEvidence, AttackStatus, exhaustive_attack
from .capability import FiniteCapability
from .capability_graph import CapabilityGraph
from .developmental_snapshot import DevelopmentalSnapshot
from .developmental_state import DevelopmentalState, TerminalRecord
from .developmental_types import (
    CompletenessCertificate,
    NoResolutionCertificate,
    canonical_digest,
)
from .generation_spec import (
    CandidateEnumeration,
    FutureEvaluation,
    GenerationSpec,
    LanguageEnumeration,
)
from .grammar import Grammar
from .grammar_growth import GrammarGrowthResult, apply_delta, grow_grammar
from .residual_certificate import ResidualCertificate, make_expressivity_residual


class GenerationRoute(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    COMPILED = "COMPILED"
    UNKNOWN_SEARCH = "UNKNOWN_SEARCH"
    UNKNOWN_CHOICE = "UNKNOWN_CHOICE"
    NAMED_OBSTRUCTION = "NAMED_OBSTRUCTION"
    REFUTED = "REFUTED"


@dataclass(frozen=True)
class GenerationTrace:
    generation_id: str
    state_before_digest: str
    spec_digest: str
    route: str
    completeness_digest: str | None
    no_resolution_digest: str | None
    residual_digest: str | None
    candidate_enumeration_digest: str | None
    admitted_delta_id: str | None
    retained_capability_id: str | None
    restart_digest: str | None
    attack_digest: str | None
    future_evidence_digest: str | None
    state_after_digest: str

    def payload(self) -> dict[str, object]:
        return {
            "generation_id": self.generation_id,
            "state_before_digest": self.state_before_digest,
            "spec_digest": self.spec_digest,
            "route": self.route,
            "completeness_digest": self.completeness_digest,
            "no_resolution_digest": self.no_resolution_digest,
            "residual_digest": self.residual_digest,
            "candidate_enumeration_digest": self.candidate_enumeration_digest,
            "admitted_delta_id": self.admitted_delta_id,
            "retained_capability_id": self.retained_capability_id,
            "restart_digest": self.restart_digest,
            "attack_digest": self.attack_digest,
            "future_evidence_digest": self.future_evidence_digest,
            "state_after_digest": self.state_after_digest,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="generation-trace-v2:")


@dataclass(frozen=True)
class GenerationResult:
    state: DevelopmentalState
    trace: GenerationTrace
    capability: FiniteCapability | None
    future: FutureEvaluation | None
    attack: AttackEvidence | None = None
    residual: ResidualCertificate | None = None
    growth: GrammarGrowthResult | None = None
    current_enumeration: LanguageEnumeration | None = None
    candidate_enumeration: CandidateEnumeration | None = None


def _trace(
    *,
    state: DevelopmentalState,
    spec: GenerationSpec,
    route: GenerationRoute,
    completeness_digest: str | None = None,
    no_resolution_digest: str | None = None,
    residual_digest: str | None = None,
    candidate_enumeration_digest: str | None = None,
    admitted_delta_id: str | None = None,
    retained_capability_id: str | None = None,
    restart_digest: str | None = None,
    attack_digest: str | None = None,
    future_evidence_digest: str | None = None,
    state_after: DevelopmentalState | None = None,
) -> GenerationTrace:
    after = state if state_after is None else state_after
    return GenerationTrace(
        generation_id=spec.generation_id,
        state_before_digest=state.digest,
        spec_digest=spec.digest,
        route=route.value,
        completeness_digest=completeness_digest,
        no_resolution_digest=no_resolution_digest,
        residual_digest=residual_digest,
        candidate_enumeration_digest=candidate_enumeration_digest,
        admitted_delta_id=admitted_delta_id,
        retained_capability_id=retained_capability_id,
        restart_digest=restart_digest,
        attack_digest=attack_digest,
        future_evidence_digest=future_evidence_digest,
        state_after_digest=after.digest,
    )


def _working_grammar(state: DevelopmentalState, enumeration: LanguageEnumeration) -> Grammar:
    grammar = Grammar(enumeration.constructors)
    current = grammar.constructor_map
    for ident, inherited in state.grammar.constructor_map.items():
        if ident not in current:
            raise ValueError(f"current language dropped inherited constructor: {ident}")
        if current[ident].payload() != inherited.payload():
            raise ValueError(f"current language changed inherited constructor: {ident}")
    return grammar


def _attack_digest(attack: AttackEvidence) -> str:
    return canonical_digest(
        {
            "capability_id": attack.capability_id,
            "status": attack.status.value,
            "checked": attack.checked,
            "total_challenges": attack.total_challenges,
            "counterexample": None if attack.counterexample is None else list(attack.counterexample),
        },
        prefix="generation-attack-v2:",
    )


def _candidate_state(
    state: DevelopmentalState,
    grammar: Grammar,
    graph: CapabilityGraph,
    delta,
    spec: GenerationSpec,
) -> DevelopmentalState:
    return DevelopmentalState(
        generation_index=state.generation_index + 1,
        grammar=grammar,
        capability_graph=graph,
        admitted_deltas=state.admitted_deltas + (delta,),
        terminal_records=state.terminal_records,
        authority_snapshot=state.authority_snapshot,
        protected_consequence_digest=state.protected_consequence_digest,
        provenance_ids=tuple(dict.fromkeys((*state.provenance_ids, spec.digest, delta.delta_id))),
    )


def execute_generation(
    state: DevelopmentalState,
    spec: GenerationSpec,
) -> GenerationResult:
    if state.authority_snapshot != spec.authority_snapshot:
        raise ValueError("generation authority snapshot mismatch")
    active = set(state.capability_graph.active_ids())
    missing_required = set(spec.required_dependency_ids) - active
    if missing_required:
        raise ValueError(f"generation has inactive required dependencies: {sorted(missing_required)}")

    current = spec.current_language_adapter.enumerate_current(state, spec)
    if not current.complete:
        trace = _trace(
            state=state,
            spec=spec,
            route=GenerationRoute.UNKNOWN_SEARCH,
        )
        return GenerationResult(
            state=state,
            trace=trace,
            capability=None,
            future=None,
            current_enumeration=current,
        )

    grammar = _working_grammar(state, current)
    signatures = current.semantic_signatures
    if not signatures:
        raise ValueError("complete current language must contain at least one denotation")

    for constructor in sorted(current.constructors, key=lambda item: item.constructor_id):
        if spec.verifier_adapter.current_resolves(state, spec, constructor):
            trace = _trace(
                state=state,
                spec=spec,
                route=GenerationRoute.AUTHORIZED,
            )
            return GenerationResult(
                state=state,
                trace=trace,
                capability=None,
                future=None,
                current_enumeration=current,
            )

    complete = CompletenessCertificate(
        language_id=grammar.digest,
        substrate_scope=spec.current_language_adapter.adapter_id,
        state_digest=state.digest,
        authority_snapshot=spec.authority_snapshot,
        enumerated_signatures=signatures,
        verifier_id=spec.verifier_adapter.adapter_id,
        replay_evidence=current.replay_evidence,
    )
    no_resolution = NoResolutionCertificate(
        language_id=grammar.digest,
        state_digest=state.digest,
        authority_snapshot=spec.authority_snapshot,
        unresolved=(spec.obligation_id,),
        checked_signatures=signatures,
        verifier_id=spec.verifier_adapter.adapter_id,
        replay_evidence=current.replay_evidence,
    )
    residual = make_expressivity_residual(
        obligation_id=spec.obligation_id,
        state_digest=state.digest,
        authority_snapshot=spec.authority_snapshot,
        language_id=grammar.digest,
        substrate_id=spec.lower_substrate_adapter.adapter_id,
        protected_consequences=spec.protected_consequences,
        observational_equivalence=("complete-current-language",),
        unresolved=(spec.obligation_id,),
        completeness=complete,
        no_resolution=no_resolution,
        necessary_constraints=(spec.obligation_id,),
        candidate_version_space_digest=canonical_digest(
            {
                "spec": spec.digest,
                "growth_manifest": list(spec.growth_manifest),
                "lower_substrate_adapter": spec.lower_substrate_adapter.adapter_id,
            },
            prefix="candidate-space-v2:",
        ),
        replay_evidence=tuple((*current.replay_evidence, spec.digest)),
    )

    candidates = spec.lower_substrate_adapter.enumerate_candidates(state, residual, spec)
    budget = spec.resource_limit("candidate_budget", len(candidates.constructors))
    bounded = candidates.constructors[:budget]
    growth = grow_grammar(
        residual,
        grammar,
        bounded,
        authority_snapshot=spec.authority_snapshot,
        adequate=lambda candidate, _: spec.verifier_adapter.candidate_adequate(
            state, spec, candidate
        ),
        preserves=lambda candidate: spec.verifier_adapter.verify_protected(
            state, spec, candidate
        ),
        verify=lambda candidate: spec.verifier_adapter.verify_candidate(
            state, spec, candidate
        ),
        verifier_id=spec.verifier_adapter.adapter_id,
        provenance_ids=(spec.digest, candidates.enumeration_digest),
    )

    if not growth.accepted or growth.candidate is None or growth.delta is None:
        fully_checked = candidates.complete and budget >= len(candidates.constructors)
        route = (
            GenerationRoute.NAMED_OBSTRUCTION
            if fully_checked
            else GenerationRoute.UNKNOWN_SEARCH
        )
        trace = _trace(
            state=state,
            spec=spec,
            route=route,
            completeness_digest=complete.digest,
            no_resolution_digest=no_resolution.digest,
            residual_digest=residual.digest,
            candidate_enumeration_digest=candidates.enumeration_digest,
        )
        return GenerationResult(
            state=state,
            trace=trace,
            capability=None,
            future=None,
            residual=residual,
            growth=growth,
            current_enumeration=current,
            candidate_enumeration=candidates,
        )

    child = apply_delta(grammar, growth.delta)
    capability = spec.verifier_adapter.compile_capability(
        state, spec, growth.candidate, growth.delta
    )
    graph = CapabilityGraph(
        (*state.capability_graph.capabilities, capability),
        state.capability_graph.revoked_ids,
    )
    tentative = _candidate_state(state, child, graph, growth.delta, spec)

    challenges = spec.attack_adapter.challenges(tentative, spec, capability)
    oracle = {
        challenge: spec.attack_adapter.oracle(tentative, spec, challenge)
        for challenge in challenges
    }
    attack = exhaustive_attack(
        capability,
        oracle,
        challenges,
        budget=spec.resource_limit("attack_budget", len(challenges)),
    )
    attack_digest = _attack_digest(attack)

    if attack.status is not AttackStatus.SURVIVE:
        trace = _trace(
            state=state,
            spec=spec,
            route=GenerationRoute.REFUTED,
            completeness_digest=complete.digest,
            no_resolution_digest=no_resolution.digest,
            residual_digest=residual.digest,
            candidate_enumeration_digest=candidates.enumeration_digest,
            admitted_delta_id=growth.delta.delta_id,
            retained_capability_id=capability.capability_id,
            attack_digest=attack_digest,
        )
        return GenerationResult(
            state=state,
            trace=trace,
            capability=None,
            future=None,
            attack=attack,
            residual=residual,
            growth=growth,
            current_enumeration=current,
            candidate_enumeration=candidates,
        )

    future = spec.verifier_adapter.verify_future(tentative, spec, capability)
    if not future.passed:
        trace = _trace(
            state=state,
            spec=spec,
            route=GenerationRoute.REFUTED,
            completeness_digest=complete.digest,
            no_resolution_digest=no_resolution.digest,
            residual_digest=residual.digest,
            candidate_enumeration_digest=candidates.enumeration_digest,
            admitted_delta_id=growth.delta.delta_id,
            retained_capability_id=capability.capability_id,
            attack_digest=attack_digest,
            future_evidence_digest=future.evidence_digest,
        )
        return GenerationResult(
            state=state,
            trace=trace,
            capability=None,
            future=future,
            attack=attack,
            residual=residual,
            growth=growth,
            current_enumeration=current,
            candidate_enumeration=candidates,
        )

    evidence_digest = canonical_digest(
        {
            "complete": complete.digest,
            "no_resolution": no_resolution.digest,
            "residual": residual.digest,
            "candidate_enumeration": candidates.enumeration_digest,
            "delta": growth.delta.delta_id,
            "capability": capability.capability_id,
            "attack": attack_digest,
            "future": future.evidence_digest,
        },
        prefix="generation-evidence-v2:",
    )
    record = TerminalRecord(
        generation_id=spec.generation_id,
        obligation_id=spec.obligation_id,
        route=GenerationRoute.COMPILED.value,
        evidence_digest=evidence_digest,
        retained_capability_id=capability.capability_id,
        admitted_delta_id=growth.delta.delta_id,
    )
    final_state = state.with_generation(
        grammar=child,
        capability_graph=graph,
        admitted_delta=growth.delta,
        terminal_record=record,
        provenance_ids=(spec.digest, candidates.enumeration_digest),
    )
    snapshot = DevelopmentalSnapshot.from_state(final_state)
    restarted = snapshot.restore()
    if restarted.digest != final_state.digest:
        raise ValueError("generation restart changed state digest")

    trace = _trace(
        state=state,
        spec=spec,
        route=GenerationRoute.COMPILED,
        completeness_digest=complete.digest,
        no_resolution_digest=no_resolution.digest,
        residual_digest=residual.digest,
        candidate_enumeration_digest=candidates.enumeration_digest,
        admitted_delta_id=growth.delta.delta_id,
        retained_capability_id=capability.capability_id,
        restart_digest=snapshot.digest,
        attack_digest=attack_digest,
        future_evidence_digest=future.evidence_digest,
        state_after=restarted,
    )
    return GenerationResult(
        state=restarted,
        trace=trace,
        capability=capability,
        future=future,
        attack=attack,
        residual=residual,
        growth=growth,
        current_enumeration=current,
        candidate_enumeration=candidates,
    )
