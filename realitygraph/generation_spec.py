from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .capability import FiniteCapability
from .developmental_state import DevelopmentalState
from .developmental_types import canonical_digest
from .grammar import FiniteConstructor, GrammarDelta
from .residual_certificate import ResidualCertificate


@dataclass(frozen=True)
class LanguageEnumeration:
    constructors: tuple[FiniteConstructor, ...]
    carrier_digest: str
    enumeration_digest: str
    replay_evidence: tuple[str, ...]
    complete: bool
    search_exhausted: bool
    raw_count: int = 0

    def __post_init__(self) -> None:
        if not self.carrier_digest or not self.enumeration_digest:
            raise ValueError("language enumeration requires carrier and enumeration digests")
        if self.raw_count < 0:
            raise ValueError("language enumeration raw_count must be non-negative")
        if self.complete and not self.search_exhausted:
            raise ValueError("complete language enumeration must be exhausted")

    @property
    def semantic_signatures(self) -> tuple[str, ...]:
        return tuple(sorted({item.semantic_signature for item in self.constructors}))


@dataclass(frozen=True)
class CandidateEnumeration:
    constructors: tuple[FiniteConstructor, ...]
    enumeration_digest: str
    replay_evidence: tuple[str, ...]
    complete: bool
    raw_count: int

    def __post_init__(self) -> None:
        if not self.enumeration_digest:
            raise ValueError("candidate enumeration requires digest")
        if self.raw_count < 0:
            raise ValueError("candidate enumeration raw_count must be non-negative")


@dataclass(frozen=True)
class FutureEvaluation:
    passed: bool
    evidence_digest: str
    grammar_search_calls: int
    observations: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.evidence_digest:
            raise ValueError("future evaluation requires evidence digest")
        if self.grammar_search_calls < 0:
            raise ValueError("grammar_search_calls must be non-negative")


class CurrentLanguageAdapter(Protocol):
    adapter_id: str

    def enumerate_current(
        self,
        state: DevelopmentalState,
        spec: "GenerationSpec",
    ) -> LanguageEnumeration: ...


class LowerSubstrateAdapter(Protocol):
    adapter_id: str

    def enumerate_candidates(
        self,
        state: DevelopmentalState,
        residual: ResidualCertificate,
        spec: "GenerationSpec",
    ) -> CandidateEnumeration: ...


class VerifierAdapter(Protocol):
    adapter_id: str

    def current_resolves(
        self,
        state: DevelopmentalState,
        spec: "GenerationSpec",
        constructor: FiniteConstructor,
    ) -> bool: ...

    def candidate_adequate(
        self,
        state: DevelopmentalState,
        spec: "GenerationSpec",
        candidate: FiniteConstructor,
    ) -> bool: ...

    def verify_candidate(
        self,
        state: DevelopmentalState,
        spec: "GenerationSpec",
        candidate: FiniteConstructor,
    ) -> bool: ...

    def verify_protected(
        self,
        state: DevelopmentalState,
        spec: "GenerationSpec",
        candidate: FiniteConstructor,
    ) -> bool: ...

    def compile_capability(
        self,
        state: DevelopmentalState,
        spec: "GenerationSpec",
        candidate: FiniteConstructor,
        delta: GrammarDelta,
    ) -> FiniteCapability: ...

    def verify_future(
        self,
        state: DevelopmentalState,
        spec: "GenerationSpec",
        capability: FiniteCapability,
    ) -> FutureEvaluation: ...


class AttackAdapter(Protocol):
    adapter_id: str

    def challenges(
        self,
        state: DevelopmentalState,
        spec: "GenerationSpec",
        capability: FiniteCapability,
    ) -> tuple[str, ...]: ...

    def oracle(
        self,
        state: DevelopmentalState,
        spec: "GenerationSpec",
        challenge: str,
    ) -> str: ...


@dataclass(frozen=True)
class GenerationSpec:
    generation_id: str
    obligation_id: str
    input_type: str
    output_type: str
    current_language_adapter: CurrentLanguageAdapter
    lower_substrate_adapter: LowerSubstrateAdapter
    verifier_adapter: VerifierAdapter
    attack_adapter: AttackAdapter
    acquisition_manifest: tuple[str, ...]
    growth_manifest: tuple[str, ...]
    future_manifest: tuple[str, ...]
    resource_envelope: tuple[tuple[str, int], ...]
    authority_snapshot: str
    protected_consequences: tuple[str, ...]
    required_dependency_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.generation_id or not self.obligation_id:
            raise ValueError("generation spec requires generation and obligation IDs")
        if not self.input_type or not self.output_type:
            raise ValueError("generation spec requires interface types")
        if not self.authority_snapshot:
            raise ValueError("generation spec requires authority snapshot")
        if len(self.required_dependency_ids) != len(set(self.required_dependency_ids)):
            raise ValueError("generation spec required dependencies must be unique")
        names = [name for name, _ in self.resource_envelope]
        if len(names) != len(set(names)):
            raise ValueError("resource envelope keys must be unique")
        if any(value < 0 for _, value in self.resource_envelope):
            raise ValueError("resource envelope values must be non-negative")
        for adapter in (
            self.current_language_adapter,
            self.lower_substrate_adapter,
            self.verifier_adapter,
            self.attack_adapter,
        ):
            if not getattr(adapter, "adapter_id", ""):
                raise ValueError("all generation adapters require stable adapter_id")

    def payload(self) -> dict[str, object]:
        return {
            "generation_id": self.generation_id,
            "obligation_id": self.obligation_id,
            "input_type": self.input_type,
            "output_type": self.output_type,
            "current_language_adapter": self.current_language_adapter.adapter_id,
            "lower_substrate_adapter": self.lower_substrate_adapter.adapter_id,
            "verifier_adapter": self.verifier_adapter.adapter_id,
            "attack_adapter": self.attack_adapter.adapter_id,
            "acquisition_manifest": list(self.acquisition_manifest),
            "growth_manifest": list(self.growth_manifest),
            "future_manifest": list(self.future_manifest),
            "resource_envelope": [[name, value] for name, value in self.resource_envelope],
            "authority_snapshot": self.authority_snapshot,
            "protected_consequences": list(self.protected_consequences),
            "required_dependency_ids": list(self.required_dependency_ids),
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="generation-spec-v2:")

    def resource_limit(self, name: str, default: int = 0) -> int:
        return dict(self.resource_envelope).get(name, default)
