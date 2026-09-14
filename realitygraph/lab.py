from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Hashable, Iterable, Sequence

from .ledger import Ledger
from .mg import Law, MG

Hypothesis = Hashable
Action = Hashable
Observation = Hashable
Predict = Callable[[Hypothesis, Action], Observation]


@dataclass(frozen=True)
class BatchPlan:
    actions: tuple[Action, ...]
    design_predictions: int
    class_progress: tuple[int, ...]


@dataclass(frozen=True)
class CompiledIdentifier:
    scope: str
    actions: tuple[Action, ...]
    decoder: dict[tuple[Observation, ...], Hypothesis]
    compile_predictions: int

    def decode(self, observations: Sequence[Observation]) -> Hypothesis:
        signature = tuple(observations)
        if signature not in self.decoder:
            raise ValueError("observation signature is outside the verified model family")
        return self.decoder[signature]


class HiddenFiniteWorld:
    """Opaque finite world with batch observation and an independent verifier."""

    def __init__(self, hidden: Hypothesis, predict: Predict):
        self._hidden = hidden
        self._predict = predict
        self.rounds = 0
        self.actions_spent = 0

    def observe_batch(self, actions: Sequence[Action]) -> tuple[Observation, ...]:
        if not actions:
            raise ValueError("batch must contain at least one action")
        self.rounds += 1
        self.actions_spent += len(actions)
        return tuple(self._predict(self._hidden, action) for action in actions)

    def verify(self, hypothesis: Hypothesis, actions: Iterable[Action]) -> bool:
        return all(
            self._predict(hypothesis, action) == self._predict(self._hidden, action)
            for action in actions
        )


def design_separating_batch(
    hypotheses: Sequence[Hypothesis],
    actions: Sequence[Action],
    predict: Predict,
) -> BatchPlan:
    """Design a joint experiment before spending a real interaction.

    Every hypothesis/action consequence is computed at most once. Refinement
    then happens over the shared consequence field rather than repeatedly
    calling the predictor along a linear search path.
    """
    hypotheses = tuple(hypotheses)
    remaining = list(actions)
    if not hypotheses:
        raise ValueError("at least one hypothesis is required")
    if not remaining and len(hypotheses) > 1:
        raise ValueError("actions cannot distinguish the frontier")

    # One broad counterfactual pass. The rest of experiment design is quotient
    # algebra over cached consequences, not repeated model evaluation.
    columns: dict[Action, tuple[Observation, ...]] = {
        action: tuple(predict(hypothesis, action) for hypothesis in hypotheses)
        for action in remaining
    }
    predictions = len(hypotheses) * len(remaining)

    signatures: list[tuple[Observation, ...]] = [()] * len(hypotheses)
    chosen: list[Action] = []
    progress: list[int] = []

    while len(set(signatures)) < len(hypotheses):
        best_action = None
        best_signatures = None
        best_key = None

        for action in remaining:
            column = columns[action]
            candidate = [
                signatures[i] + (column[i],)
                for i in range(len(hypotheses))
            ]
            counts = Counter(candidate)
            key = (
                len(counts),
                -max(counts.values()),
                -sum(size * size for size in counts.values()),
            )
            if best_key is None or key > best_key:
                best_action = action
                best_signatures = candidate
                best_key = key

        if best_action is None or best_signatures is None:
            raise ValueError("no separating batch exists")
        if len(set(best_signatures)) == len(set(signatures)):
            raise ValueError("remaining actions cannot refine the frontier")

        chosen.append(best_action)
        remaining.remove(best_action)
        signatures = best_signatures
        progress.append(len(set(signatures)))

    return BatchPlan(tuple(chosen), predictions, tuple(progress))


def compile_identifier(
    scope: str,
    hypotheses: Sequence[Hypothesis],
    batch: Sequence[Action],
    predict: Predict,
) -> CompiledIdentifier:
    """Compile a verified separating batch into direct signature lookup."""
    decoder: dict[tuple[Observation, ...], Hypothesis] = {}
    predictions = 0

    for hypothesis in hypotheses:
        signature = tuple(predict(hypothesis, action) for action in batch)
        predictions += len(batch)
        if signature in decoder and decoder[signature] != hypothesis:
            raise ValueError("batch is not separating for this model family")
        decoder[signature] = hypothesis

    if len(decoder) != len(set(hypotheses)):
        raise ValueError("compiled decoder lost hypotheses")

    return CompiledIdentifier(scope, tuple(batch), decoder, predictions)


def identify(
    world: HiddenFiniteWorld,
    identifier: CompiledIdentifier,
) -> Hypothesis:
    """One batch collision followed by direct compiled decoding."""
    return identifier.decode(world.observe_batch(identifier.actions))


def retain_batch(
    identifier: CompiledIdentifier,
    ledger: Ledger,
    memory: MG,
    kernel_id: str = "lab",
) -> str:
    """Keep only the small source needed to rebuild the compiled identifier."""
    if not all(isinstance(action, int) for action in identifier.actions):
        raise TypeError("canonical demo codec currently supports integer actions")

    encoded = ",".join(str(action) for action in identifier.actions)
    evidence = f"{identifier.scope}|{encoded}|{len(identifier.decoder)}".encode()
    provenance = hashlib.sha256(evidence).hexdigest()[:12]
    law = Law(
        f"probe-{identifier.scope[:12]}",
        f"separating-batch:{encoded}",
        identifier.scope,
        provenance,
    )
    event = ledger.append_add(law, kernel_id)
    live = ledger.materialize(memory.verifier)
    memory.laws = live.laws
    return event.id


def batch_from_memory(memory: MG, scope: str) -> tuple[int, ...]:
    candidates = [
        law
        for law in memory.laws.values()
        if law.scope == scope and law.expr.startswith("separating-batch:")
    ]
    if len(candidates) != 1:
        raise ValueError("memory does not contain one separating batch for this scope")
    encoded = candidates[0].expr.split(":", 1)[1]
    return tuple(int(part) for part in encoded.split(",") if part)


def opaque_scope(specification: str) -> str:
    """Content address for a model family; not a human-facing family label."""
    return hashlib.sha256(specification.encode()).hexdigest()[:20]
