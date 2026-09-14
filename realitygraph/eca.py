from __future__ import annotations

import hashlib
from itertools import product

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


def compile_rule(
    rule: int,
    action: tuple[int, ...],
    observed: tuple[int, ...],
    ledger: Ledger,
    memory: MG,
    kernel_id: str = "field",
) -> str:
    evidence = repr((action, observed)).encode()
    provenance = hashlib.sha256(evidence).hexdigest()[:12]
    law = Law(
        "eca",
        f"radius1-binary-rule:{rule}",
        "cyclic-binary-row",
        provenance,
    )
    event = ledger.append_add(law, kernel_id)
    live = ledger.materialize(memory.verifier)
    memory.laws = live.laws
    return event.id


def rule_from_memory(memory: MG) -> int:
    candidates = [
        law for law in memory.laws.values()
        if law.expr.startswith("radius1-binary-rule:")
    ]
    if len(candidates) != 1:
        raise ValueError("memory does not contain one resolved ECA rule")
    return int(candidates[0].expr.rsplit(":", 1)[1])
