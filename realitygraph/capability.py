from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class FiniteCapability:
    capability_id: str
    input_type: str
    output_type: str
    semantics: tuple[tuple[str, str], ...]
    guard_inputs: tuple[str, ...]
    certificate_id: str
    dependencies: tuple[str, ...]
    authority_snapshot: str
    verifier_id: str
    provenance_ids: tuple[str, ...]
    cost: int

    def __post_init__(self) -> None:
        if not self.capability_id or not self.input_type or not self.output_type:
            raise ValueError("capability requires id and interface types")
        if not self.certificate_id or not self.authority_snapshot or not self.verifier_id:
            raise ValueError("capability requires certificate, authority, and verifier")
        if self.cost < 0:
            raise ValueError("capability cost must be non-negative")
        keys = [str(key) for key, _ in self.semantics]
        if not keys or len(keys) != len(set(keys)):
            raise ValueError("capability requires unique finite input semantics")
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("capability dependencies must be unique")
        if self.capability_id in self.dependencies:
            raise ValueError("capability cannot depend on itself")
        if self.guard_inputs:
            missing = set(self.guard_inputs) - set(keys)
            if missing:
                raise ValueError(f"guard inputs outside semantic table: {sorted(missing)}")

    @property
    def semantic_table(self) -> dict[str, str]:
        return {str(key): str(value) for key, value in self.semantics}

    @property
    def guarded_inputs(self) -> tuple[str, ...]:
        return tuple(self.guard_inputs) if self.guard_inputs else tuple(sorted(self.semantic_table))

    def applicable(self, value: str) -> bool:
        return str(value) in set(self.guarded_inputs)

    def execute(self, value: str) -> str:
        value = str(value)
        if not self.applicable(value):
            raise ValueError(f"capability guard does not admit input: {value}")
        try:
            return self.semantic_table[value]
        except KeyError as exc:
            raise ValueError(f"input outside verified capability carrier: {value}") from exc


def compose_capabilities(
    capability_id: str,
    first: FiniteCapability,
    second: FiniteCapability,
    *,
    bridge_verifier: Callable[[FiniteCapability, FiniteCapability], bool] | None = None,
) -> FiniteCapability:
    if first.output_type != second.input_type:
        raise ValueError("capability composition type mismatch")
    boundary_matches = (
        first.authority_snapshot == second.authority_snapshot
        and first.verifier_id == second.verifier_id
    )
    if not boundary_matches:
        if bridge_verifier is None or not bridge_verifier(first, second):
            raise ValueError("capability composition authority/verifier mismatch")

    rows: list[tuple[str, str]] = []
    for value in first.guarded_inputs:
        middle = first.execute(value)
        if not second.applicable(middle):
            raise ValueError("second capability guard does not cover first output")
        rows.append((value, second.execute(middle)))

    dependencies = tuple(sorted({
        first.capability_id,
        second.capability_id,
        *first.dependencies,
        *second.dependencies,
    }))
    provenance = tuple(dict.fromkeys((*first.provenance_ids, *second.provenance_ids)))
    certificate_id = f"compose:{first.certificate_id}+{second.certificate_id}"
    authority = (
        first.authority_snapshot
        if boundary_matches
        else f"bridge:{first.authority_snapshot}|{second.authority_snapshot}"
    )
    verifier = first.verifier_id if boundary_matches else "bridge-verified"
    return FiniteCapability(
        capability_id=capability_id,
        input_type=first.input_type,
        output_type=second.output_type,
        semantics=tuple(rows),
        guard_inputs=tuple(value for value, _ in rows),
        certificate_id=certificate_id,
        dependencies=dependencies,
        authority_snapshot=authority,
        verifier_id=verifier,
        provenance_ids=provenance,
        cost=first.cost + second.cost,
    )
