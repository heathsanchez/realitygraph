from __future__ import annotations

import hashlib
from itertools import product

from .field import Field
from .ledger import Ledger
from .mg import Law, MG


def step(rule: int, row: tuple[int, ...]) -> tuple[int, ...]:
    """One elementary cellular-automaton step on a cyclic binary row."""
    if not 0 <= rule <= 255:
        raise ValueError("rule must be in [0,255]")
    n = len(row)
    if n < 3 or any(bit not in (0, 1) for bit in row):
        raise ValueError("row must be a binary tuple of length >= 3")

    out = []
    for i in range(n):
        neighborhood = (
            (row[(i - 1) % n] << 2)
            | (row[i] << 1)
            | row[(i + 1) % n]
        )
        out.append((rule >> neighborhood) & 1)
    return tuple(out)


def all_rules() -> tuple[int, ...]:
    return tuple(range(256))


def all_rows(width: int) -> tuple[tuple[int, ...], ...]:
    return tuple(product((0, 1), repeat=width))


class HiddenECA:
    """Ground-truth environment. The learner sees outputs, never the rule."""

    def __init__(self, rule: int):
        if not 0 <= rule <= 255:
            raise ValueError("rule must be in [0,255]")
        self._rule = rule
        self.interactions = 0

    def observe(self, row: tuple[int, ...]) -> tuple[int, ...]:
        self.interactions += 1
        return step(self._rule, row)

    def verify_heldout(
        self,
        row: tuple[int, ...],
        predicted: tuple[int, ...],
    ) -> bool:
        # Scientific verifier: does not alter the learner's interaction count.
        return step(self._rule, row) == predicted


def _refresh(memory: MG, ledger: Ledger) -> None:
    live = ledger.materialize(memory.verifier)
    memory.laws = live.laws


def compile_probe(
    action: tuple[int, ...],
    ledger: Ledger,
    memory: MG,
    kernel_id: str = "field",
) -> str:
    """Promote an experiment only after exhaustive family-level verification."""
    score = Field(all_rules()).score(action, step)
    if score.outcome_classes != 256 or score.largest_class != 1:
        raise ValueError("probe is not a perfect separator for the declared rule family")

    bits = "".join(str(bit) for bit in action)
    evidence = repr((action, score.outcome_classes, score.largest_class)).encode()
    provenance = hashlib.sha256(evidence).hexdigest()[:12]
    law = Law(
        "eca-probe",
        f"perfect-separator:{bits}",
        "eca-all-256-rules",
        provenance,
    )
    event = ledger.append_add(law, kernel_id)
    _refresh(memory, ledger)
    return event.id


def probe_from_memory(memory: MG) -> tuple[int, ...]:
    candidates = [
        law for law in memory.laws.values()
        if law.expr.startswith("perfect-separator:")
        and law.scope == "eca-all-256-rules"
    ]
    if len(candidates) != 1:
        raise ValueError("memory does not contain one resolved reusable ECA probe")
    bits = candidates[0].expr.split(":", 1)[1]
    return tuple(int(bit) for bit in bits)


def compile_rule(
    rule: int,
    action: tuple[int, ...],
    observed: tuple[int, ...],
    ledger: Ledger,
    memory: MG,
    world_scope: str,
    kernel_id: str = "field",
) -> str:
    """Retain an identified law only inside the world where it was earned."""
    if step(rule, action) != observed:
        raise ValueError("rule does not explain the observed consequence")

    evidence = repr((world_scope, action, observed)).encode()
    provenance = hashlib.sha256(evidence).hexdigest()[:12]
    scoped_id = hashlib.sha256(world_scope.encode()).hexdigest()[:8]
    law = Law(
        f"eca-rule-{scoped_id}",
        f"radius1-binary-rule:{rule}",
        world_scope,
        provenance,
    )
    event = ledger.append_add(law, kernel_id)
    _refresh(memory, ledger)
    return event.id


def rule_from_memory(memory: MG, world_scope: str) -> int:
    candidates = [
        law for law in memory.laws.values()
        if law.expr.startswith("radius1-binary-rule:")
        and law.scope == world_scope
    ]
    if len(candidates) != 1:
        raise ValueError("memory does not contain one resolved rule for this world")
    return int(candidates[0].expr.rsplit(":", 1)[1])
