from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .developmental_executor import GenerationResult, GenerationRoute, execute_generation
from .developmental_state import DevelopmentalState
from .developmental_types import canonical_digest
from .generation_spec import GenerationSpec, LanguageEnumeration
from .meta_memory import MetaMemory, RepairEpisode, RepairPhase
from .obstruction_fingerprint import ObstructionFingerprint
from .repair_strategy import RepairPortfolio, RepairStrategy


class FingerprintBuilder(Protocol):
    builder_id: str

    def build(
        self,
        state: DevelopmentalState,
        spec: GenerationSpec,
        current: LanguageEnumeration,
    ) -> ObstructionFingerprint: ...


class MetaGrowthRoute(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    COMPILED = "COMPILED"
    UNKNOWN_SEARCH = "UNKNOWN_SEARCH"
    UNKNOWN_CHOICE = "UNKNOWN_CHOICE"
    NAMED_META_OBSTRUCTION = "NAMED_META_OBSTRUCTION"
    REFUTED = "REFUTED"


@dataclass(frozen=True)
class MetaGrowthSpec:
    episode_id: str
    phase: RepairPhase
    object_template: GenerationSpec
    fingerprint_builder: FingerprintBuilder
    portfolio: RepairPortfolio
    authority_snapshot: str
    verifier_id: str
    interface_digest: str
    portfolio_budget: int

    def __post_init__(self) -> None:
        if not self.episode_id:
            raise ValueError("meta growth spec requires episode_id")
        if not getattr(self.fingerprint_builder, "builder_id", ""):
            raise ValueError("meta growth spec requires stable fingerprint builder identity")
        if not self.authority_snapshot or not self.verifier_id or not self.interface_digest:
            raise ValueError("meta growth spec requires authority/verifier/interface identity")
        if self.portfolio_budget < 0:
            raise ValueError("meta growth portfolio budget must be non-negative")
        if self.object_template.authority_snapshot != self.authority_snapshot:
            raise ValueError("meta/object authority mismatch")
        if self.object_template.verifier_adapter.adapter_id != self.verifier_id:
            raise ValueError("meta/object verifier mismatch")

    def payload(self) -> dict[str, object]:
        return {
            "episode_id": self.episode_id,
            "phase": self.phase.value,
            "object_template": self.object_template.digest,
            "fingerprint_builder": self.fingerprint_builder.builder_id,
            "portfolio": self.portfolio.digest,
            "authority_snapshot": self.authority_snapshot,
            "verifier_id": self.verifier_id,
            "interface_digest": self.interface_digest,
            "portfolio_budget": self.portfolio_budget,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="meta-growth-spec-v3:")


@dataclass(frozen=True)
class StrategyAttempt:
    strategy_id: str
    strategy_version: str
    structural_cost: int
    parent_state_digest: str
    object_spec_digest: str
    result: GenerationResult

    @property
    def successful(self) -> bool:
        return self.result.trace.route == GenerationRoute.COMPILED.value

    @property
    def admitted_complexity(self) -> int | None:
        if not self.successful or self.result.growth is None or self.result.growth.candidate is None:
            return None
        return int(self.result.growth.candidate.complexity)

    @property
    def evidence_digest(self) -> str:
        return canonical_digest(
            {
                "strategy_id": self.strategy_id,
                "strategy_version": self.strategy_version,
                "structural_cost": self.structural_cost,
                "parent_state_digest": self.parent_state_digest,
                "object_spec_digest": self.object_spec_digest,
                "generation_trace": self.result.trace.digest,
            },
            prefix="strategy-attempt-v3:",
        )


@dataclass(frozen=True)
class MetaGrowthResult:
    object_state: DevelopmentalState
    meta_memory: MetaMemory
    route: MetaGrowthRoute
    fingerprint: ObstructionFingerprint | None
    selected_strategy_id: str | None
    selected_strategy_version: str | None
    selected_generation: GenerationResult | None
    attempts: tuple[StrategyAttempt, ...]
    rule_hit: bool
    matched_rule_id: str | None
    portfolio_search_calls: int
    competitor_strategy_calls: int
    selected_strategy_calls: int
    episode_digest: str | None

    @property
    def strategy_parent_digests(self) -> tuple[str, ...]:
        return tuple(attempt.parent_state_digest for attempt in self.attempts)


def _current_is_resolved(
    state: DevelopmentalState,
    spec: GenerationSpec,
    current: LanguageEnumeration,
) -> bool:
    return any(
        spec.verifier_adapter.current_resolves(state, spec, constructor)
        for constructor in sorted(current.constructors, key=lambda item: item.constructor_id)
    )


def _run_strategy(
    state: DevelopmentalState,
    meta_spec: MetaGrowthSpec,
    strategy: RepairStrategy,
) -> StrategyAttempt:
    object_spec = strategy.materialize_generation_spec(state, meta_spec)
    if object_spec.authority_snapshot != meta_spec.authority_snapshot:
        raise ValueError("repair strategy materialized stale authority")
    if object_spec.verifier_adapter.adapter_id != meta_spec.verifier_id:
        raise ValueError("repair strategy materialized wrong verifier")
    result = execute_generation(state, object_spec)
    return StrategyAttempt(
        strategy_id=str(strategy.strategy_id),
        strategy_version=str(strategy.strategy_version),
        structural_cost=int(strategy.structural_cost),
        parent_state_digest=state.digest,
        object_spec_digest=object_spec.digest,
        result=result,
    )


def _success_rank(attempt: StrategyAttempt) -> tuple[int, int]:
    complexity = attempt.admitted_complexity
    if complexity is None:
        raise ValueError("cannot rank unsuccessful repair attempt")
    return (attempt.structural_cost, complexity)


def _episode_from_selection(
    meta_spec: MetaGrowthSpec,
    fingerprint: ObstructionFingerprint,
    selected: StrategyAttempt,
) -> RepairEpisode:
    return RepairEpisode(
        episode_id=meta_spec.episode_id,
        phase=meta_spec.phase,
        obstruction_fingerprint=fingerprint.digest,
        strategy_id=selected.strategy_id,
        strategy_version=selected.strategy_version,
        portfolio_digest=meta_spec.portfolio.digest,
        authority_snapshot=meta_spec.authority_snapshot,
        verifier_id=meta_spec.verifier_id,
        interface_digest=meta_spec.interface_digest,
        selection_cost=selected.structural_cost,
        object_evidence_digest=selected.evidence_digest,
    )


def _result(
    *,
    state: DevelopmentalState,
    memory: MetaMemory,
    route: MetaGrowthRoute,
    fingerprint: ObstructionFingerprint | None,
    attempts: tuple[StrategyAttempt, ...] = (),
    selected: StrategyAttempt | None = None,
    rule_hit: bool = False,
    matched_rule_id: str | None = None,
    portfolio_search_calls: int = 0,
    competitor_strategy_calls: int = 0,
    selected_strategy_calls: int = 0,
    episode_digest: str | None = None,
) -> MetaGrowthResult:
    selected_generation = None if selected is None else selected.result
    return MetaGrowthResult(
        object_state=state,
        meta_memory=memory,
        route=route,
        fingerprint=fingerprint,
        selected_strategy_id=None if selected is None else selected.strategy_id,
        selected_strategy_version=None if selected is None else selected.strategy_version,
        selected_generation=selected_generation,
        attempts=attempts,
        rule_hit=rule_hit,
        matched_rule_id=matched_rule_id,
        portfolio_search_calls=portfolio_search_calls,
        competitor_strategy_calls=competitor_strategy_calls,
        selected_strategy_calls=selected_strategy_calls,
        episode_digest=episode_digest,
    )


def execute_meta_growth(
    object_state: DevelopmentalState,
    meta_memory: MetaMemory,
    meta_spec: MetaGrowthSpec,
) -> MetaGrowthResult:
    if object_state.authority_snapshot != meta_spec.authority_snapshot:
        raise ValueError("meta growth authority snapshot mismatch")

    template = meta_spec.object_template
    current = template.current_language_adapter.enumerate_current(object_state, template)
    if not current.complete:
        return _result(
            state=object_state,
            memory=meta_memory,
            route=MetaGrowthRoute.UNKNOWN_SEARCH,
            fingerprint=None,
        )
    if _current_is_resolved(object_state, template, current):
        return _result(
            state=object_state,
            memory=meta_memory,
            route=MetaGrowthRoute.AUTHORIZED,
            fingerprint=None,
        )

    fingerprint = meta_spec.fingerprint_builder.build(object_state, template, current)
    if fingerprint.authority_snapshot != meta_spec.authority_snapshot:
        raise ValueError("fingerprint authority mismatch")
    if fingerprint.verifier_id != meta_spec.verifier_id:
        raise ValueError("fingerprint verifier mismatch")

    promoted = meta_memory.promoted_match(
        obstruction_fingerprint=fingerprint.digest,
        portfolio_digest=meta_spec.portfolio.digest,
        authority_snapshot=meta_spec.authority_snapshot,
        verifier_id=meta_spec.verifier_id,
        interface_digest=meta_spec.interface_digest,
    )
    if promoted is not None:
        strategy = meta_spec.portfolio.get(promoted.strategy_id)
        if str(strategy.strategy_version) != promoted.strategy_version:
            raise ValueError("promoted repair rule strategy version is stale")
        if not strategy.applicable(fingerprint, object_state, meta_spec):
            raise ValueError("promoted repair rule no longer applies to exact obstruction")
        selected = _run_strategy(object_state, meta_spec, strategy)
        if not selected.successful:
            return _result(
                state=object_state,
                memory=meta_memory,
                route=MetaGrowthRoute.REFUTED,
                fingerprint=fingerprint,
                attempts=(selected,),
                rule_hit=True,
                matched_rule_id=promoted.rule_id,
                selected_strategy_calls=1,
            )
        return _result(
            state=selected.result.state,
            memory=meta_memory,
            route=MetaGrowthRoute.COMPILED,
            fingerprint=fingerprint,
            attempts=(selected,),
            selected=selected,
            rule_hit=True,
            matched_rule_id=promoted.rule_id,
            portfolio_search_calls=0,
            competitor_strategy_calls=0,
            selected_strategy_calls=1,
            episode_digest=selected.evidence_digest,
        )

    applicable = tuple(
        meta_spec.portfolio.get(ident)
        for ident in meta_spec.portfolio.strategy_ids
        if meta_spec.portfolio.get(ident).applicable(fingerprint, object_state, meta_spec)
    )
    if meta_spec.portfolio_budget < len(applicable):
        # A partial repair portfolio cannot establish that a checked success is minimal,
        # nor that checked failures exhaust the declared alternatives.
        attempts = tuple(
            _run_strategy(object_state, meta_spec, strategy)
            for strategy in applicable[: meta_spec.portfolio_budget]
        )
        return _result(
            state=object_state,
            memory=meta_memory,
            route=MetaGrowthRoute.UNKNOWN_SEARCH,
            fingerprint=fingerprint,
            attempts=attempts,
            portfolio_search_calls=len(attempts),
        )

    attempts = tuple(_run_strategy(object_state, meta_spec, strategy) for strategy in applicable)
    successes = tuple(attempt for attempt in attempts if attempt.successful)
    if not successes:
        return _result(
            state=object_state,
            memory=meta_memory,
            route=MetaGrowthRoute.NAMED_META_OBSTRUCTION,
            fingerprint=fingerprint,
            attempts=attempts,
            portfolio_search_calls=len(attempts),
        )

    minimal_rank = min(_success_rank(attempt) for attempt in successes)
    minimal = tuple(attempt for attempt in successes if _success_rank(attempt) == minimal_rank)
    if len(minimal) != 1:
        return _result(
            state=object_state,
            memory=meta_memory,
            route=MetaGrowthRoute.UNKNOWN_CHOICE,
            fingerprint=fingerprint,
            attempts=attempts,
            portfolio_search_calls=len(attempts),
        )

    selected = minimal[0]
    episode = _episode_from_selection(meta_spec, fingerprint, selected)
    updated_memory = meta_memory
    if meta_spec.phase in (RepairPhase.ACQUISITION, RepairPhase.CALIBRATION):
        updated_memory = meta_memory.record_success(episode)

    return _result(
        state=selected.result.state,
        memory=updated_memory,
        route=MetaGrowthRoute.COMPILED,
        fingerprint=fingerprint,
        attempts=attempts,
        selected=selected,
        rule_hit=False,
        matched_rule_id=None,
        portfolio_search_calls=len(attempts),
        competitor_strategy_calls=max(0, len(attempts) - 1),
        selected_strategy_calls=1,
        episode_digest=episode.digest,
    )
