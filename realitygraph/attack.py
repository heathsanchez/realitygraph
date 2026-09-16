from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from .capability import FiniteCapability


class AttackStatus(str, Enum):
    SURVIVE = "SURVIVE"
    NARROW_SCOPE = "NARROW_SCOPE"
    REVOKE = "REVOKE"
    UNKNOWN_ATTACK = "UNKNOWN_ATTACK"


@dataclass(frozen=True)
class AttackEvidence:
    capability_id: str
    status: AttackStatus
    checked: int
    total_challenges: int
    counterexample: tuple[str, str, str] | None = None


def exhaustive_attack(
    capability: FiniteCapability,
    oracle: Mapping[str, str],
    challenges: Sequence[str],
    *,
    budget: int,
) -> AttackEvidence:
    if budget < 0:
        raise ValueError("attack budget must be non-negative")
    ordered = tuple(str(value) for value in challenges)
    if len(ordered) != len(set(ordered)):
        raise ValueError("attack challenges must be unique")

    checked = 0
    for value in ordered[:budget]:
        if value not in oracle:
            raise ValueError(f"oracle missing attack challenge: {value}")
        if not capability.applicable(value):
            return AttackEvidence(
                capability.capability_id,
                AttackStatus.REVOKE,
                checked,
                len(ordered),
                (value, "<guard-refused>", str(oracle[value])),
            )
        actual = capability.execute(value)
        expected = str(oracle[value])
        checked += 1
        if actual != expected:
            return AttackEvidence(
                capability.capability_id,
                AttackStatus.REVOKE,
                checked,
                len(ordered),
                (value, actual, expected),
            )

    if checked < len(ordered):
        return AttackEvidence(
            capability.capability_id,
            AttackStatus.UNKNOWN_ATTACK,
            checked,
            len(ordered),
            None,
        )
    return AttackEvidence(
        capability.capability_id,
        AttackStatus.SURVIVE,
        checked,
        len(ordered),
        None,
    )
