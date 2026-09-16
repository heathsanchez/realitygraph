from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Iterable

from .developmental_types import canonical_digest


def _normalize_partition(
    partition: Iterable[Iterable[str]],
    *,
    name: str,
) -> tuple[tuple[str, ...], ...]:
    classes = tuple(tuple(str(value) for value in block) for block in partition)
    if not classes or any(not block for block in classes):
        raise ValueError(f"{name} partition requires non-empty classes")
    flattened = [value for block in classes for value in block]
    if len(flattened) != len(set(flattened)):
        raise ValueError(f"{name} partition classes must be disjoint")
    return classes


def _incidence_matrix(
    current: tuple[tuple[str, ...], ...],
    consequence: tuple[tuple[str, ...], ...],
) -> tuple[tuple[int, ...], ...]:
    consequence_sets = tuple(set(block) for block in consequence)
    return tuple(
        tuple(len(set(current_block) & consequence_block) for consequence_block in consequence_sets)
        for current_block in current
    )


def _canonical_matrix(
    matrix: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, ...], ...]:
    row_count = len(matrix)
    column_count = len(matrix[0])
    best_flat: tuple[int, ...] | None = None
    best_matrix: tuple[tuple[int, ...], ...] | None = None
    for row_order in permutations(range(row_count)):
        for column_order in permutations(range(column_count)):
            candidate = tuple(
                tuple(matrix[row][column] for column in column_order)
                for row in row_order
            )
            flat = tuple(value for row in candidate for value in row)
            if best_flat is None or flat < best_flat:
                best_flat = flat
                best_matrix = candidate
    if best_matrix is None:
        raise ValueError("cannot canonicalize empty incidence matrix")
    return best_matrix


@dataclass(frozen=True)
class ObstructionFingerprint:
    input_type: str
    output_type: str
    current_class_count: int
    consequence_class_count: int
    canonical_incidence_matrix: tuple[tuple[int, ...], ...]
    carrier_size: int
    current_language_semantic_count: int
    authority_snapshot: str
    verifier_id: str

    def __post_init__(self) -> None:
        if not self.input_type or not self.output_type:
            raise ValueError("obstruction fingerprint requires interface types")
        if self.current_class_count < 1 or self.consequence_class_count < 1:
            raise ValueError("obstruction fingerprint requires non-empty quotients")
        if self.carrier_size < 1:
            raise ValueError("obstruction fingerprint requires non-empty carrier")
        if self.current_language_semantic_count < 1:
            raise ValueError("obstruction fingerprint requires observed language semantics")
        if not self.authority_snapshot or not self.verifier_id:
            raise ValueError("obstruction fingerprint requires authority and verifier")
        if len(self.canonical_incidence_matrix) != self.current_class_count:
            raise ValueError("incidence row count mismatch")
        if any(len(row) != self.consequence_class_count for row in self.canonical_incidence_matrix):
            raise ValueError("incidence column count mismatch")
        if any(value < 0 for row in self.canonical_incidence_matrix for value in row):
            raise ValueError("incidence multiplicity must be non-negative")
        if sum(sum(row) for row in self.canonical_incidence_matrix) != self.carrier_size:
            raise ValueError("incidence multiplicity does not cover carrier")

    def payload(self) -> dict[str, object]:
        return {
            "input_type": self.input_type,
            "output_type": self.output_type,
            "current_class_count": self.current_class_count,
            "consequence_class_count": self.consequence_class_count,
            "canonical_incidence_matrix": [list(row) for row in self.canonical_incidence_matrix],
            "carrier_size": self.carrier_size,
            "current_language_semantic_count": self.current_language_semantic_count,
            "authority_snapshot": self.authority_snapshot,
            "verifier_id": self.verifier_id,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="obstruction-fingerprint-v3:")


def canonicalize_obstruction(
    *,
    input_type: str,
    output_type: str,
    current_partition: Iterable[Iterable[str]],
    consequence_partition: Iterable[Iterable[str]],
    current_language_semantic_count: int,
    authority_snapshot: str,
    verifier_id: str,
) -> ObstructionFingerprint:
    current = _normalize_partition(current_partition, name="current")
    consequence = _normalize_partition(consequence_partition, name="consequence")
    current_carrier = {value for block in current for value in block}
    consequence_carrier = {value for block in consequence for value in block}
    if current_carrier != consequence_carrier:
        raise ValueError("current and consequence partitions must cover the same carrier")
    if not current_carrier:
        raise ValueError("obstruction carrier must be non-empty")
    if current_language_semantic_count < 1:
        raise ValueError("current language semantic count must be positive")

    matrix = _incidence_matrix(current, consequence)
    canonical = _canonical_matrix(matrix)
    return ObstructionFingerprint(
        input_type=str(input_type),
        output_type=str(output_type),
        current_class_count=len(current),
        consequence_class_count=len(consequence),
        canonical_incidence_matrix=canonical,
        carrier_size=len(current_carrier),
        current_language_semantic_count=int(current_language_semantic_count),
        authority_snapshot=str(authority_snapshot),
        verifier_id=str(verifier_id),
    )
