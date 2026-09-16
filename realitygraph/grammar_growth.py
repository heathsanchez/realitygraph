from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from .developmental_types import canonical_digest
from .grammar import FiniteConstructor, Grammar, GrammarDelta
from .residual_certificate import ResidualCertificate


@dataclass(frozen=True)
class CandidateVerdict:
    constructor_id: str
    accepted: bool
    reason: str


@dataclass(frozen=True)
class GrammarGrowthResult:
    accepted: bool
    candidate: FiniteConstructor | None
    delta: GrammarDelta | None
    verdicts: tuple[CandidateVerdict, ...]


def _validate_growth_boundary(
    residual: ResidualCertificate,
    grammar: Grammar,
    authority_snapshot: str,
) -> None:
    if residual.language_id != grammar.digest:
        raise ValueError("residual is stale for the current grammar")
    if residual.authority_snapshot != authority_snapshot:
        raise ValueError("residual authority snapshot mismatch")


def apply_delta(grammar: Grammar, delta: GrammarDelta) -> Grammar:
    if grammar.digest != delta.parent_language_id:
        raise ValueError("grammar delta parent mismatch")
    current = grammar.constructor_map
    for constructor in delta.added_constructors:
        if constructor.constructor_id in current:
            raise ValueError("grammar delta reuses an existing constructor ID")
        missing = set(constructor.dependencies) - set(current)
        if missing:
            raise ValueError(f"grammar delta has missing dependencies: {sorted(missing)}")
        current[constructor.constructor_id] = constructor
    child = Grammar(tuple(current.values()))
    if child.digest != delta.child_language_id:
        raise ValueError("grammar delta child digest mismatch")
    return child


def ablate_delta(grammar: Grammar, delta: GrammarDelta) -> Grammar:
    if grammar.digest != delta.child_language_id:
        raise ValueError("ablation expects the exact delta child grammar")
    removed = {constructor.constructor_id for constructor in delta.added_constructors}
    survivors = tuple(
        constructor for constructor in grammar.constructors
        if constructor.constructor_id not in removed
    )
    parent = Grammar(survivors)
    if parent.digest != delta.parent_language_id:
        raise ValueError("grammar delta ablation did not restore parent")
    return parent


def grow_grammar(
    residual: ResidualCertificate,
    grammar: Grammar,
    candidates: Iterable[FiniteConstructor],
    *,
    authority_snapshot: str,
    adequate: Callable[[FiniteConstructor, ResidualCertificate], bool],
    preserves: Callable[[FiniteConstructor], bool],
    verify: Callable[[FiniteConstructor], bool],
    verifier_id: str,
    provenance_ids: tuple[str, ...] = (),
) -> GrammarGrowthResult:
    _validate_growth_boundary(residual, grammar, authority_snapshot)
    if not verifier_id:
        raise ValueError("grammar growth requires verifier_id")

    verdicts: list[CandidateVerdict] = []
    known_ids = set(grammar.constructor_map)
    known_extensional = set(grammar.extensional_classes())

    for candidate in sorted(candidates, key=lambda item: (item.complexity, item.constructor_id)):
        if candidate.constructor_id in known_ids:
            verdicts.append(CandidateVerdict(candidate.constructor_id, False, "duplicate-id"))
            continue
        if candidate.extensional_key in known_extensional:
            verdicts.append(CandidateVerdict(candidate.constructor_id, False, "extensional-duplicate"))
            continue
        missing = set(candidate.dependencies) - known_ids
        if missing:
            verdicts.append(CandidateVerdict(candidate.constructor_id, False, "missing-dependency"))
            continue
        if not adequate(candidate, residual):
            verdicts.append(CandidateVerdict(candidate.constructor_id, False, "inadequate"))
            continue
        if not preserves(candidate):
            verdicts.append(CandidateVerdict(candidate.constructor_id, False, "preservation-failed"))
            continue
        if not verify(candidate):
            verdicts.append(CandidateVerdict(candidate.constructor_id, False, "verification-failed"))
            continue

        child = Grammar((*grammar.constructors, candidate))
        dependency_ids = tuple(sorted(set(candidate.dependencies)))
        ablation_handle = canonical_digest(
            {
                "parent": grammar.digest,
                "child": child.digest,
                "constructor": candidate.constructor_id,
                "residual": residual.digest,
            },
            prefix="grammar-ablation-v1:",
        )[:20]
        delta = GrammarDelta(
            parent_language_id=grammar.digest,
            child_language_id=child.digest,
            added_constructors=(candidate,),
            residual_digest=residual.digest,
            authority_snapshot=authority_snapshot,
            dependency_ids=dependency_ids,
            verifier_id=verifier_id,
            provenance_ids=tuple(provenance_ids),
            ablation_handle=ablation_handle,
        )
        verdicts.append(CandidateVerdict(candidate.constructor_id, True, "admitted"))
        return GrammarGrowthResult(True, candidate, delta, tuple(verdicts))

    return GrammarGrowthResult(False, None, None, tuple(verdicts))
