from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Hashable, Iterable, Sequence, TypeVar

H = TypeVar("H", bound=Hashable)
A = TypeVar("A", bound=Hashable)
O = TypeVar("O", bound=Hashable)


@dataclass(frozen=True)
class ProbeScore(Generic[A]):
    action: A
    outcome_classes: int
    largest_class: int
    expected_survivors: float
    predictions: int


@dataclass(frozen=True)
class Collision(Generic[A, O]):
    action: A
    observed: O
    before: int
    after: int


class Field(Generic[H]):
    """A sparse frontier of mutually lawful hypotheses.

    The field never votes. It predicts consequences, quotients hypotheses that
    currently agree, chooses a separating move, then lets observation remove
    incompatible hypotheses.
    """

    def __init__(self, hypotheses: Iterable[H]):
        self.hypotheses = tuple(dict.fromkeys(hypotheses))

    def partition(
        self,
        action: A,
        predict: Callable[[H, A], O],
    ) -> dict[O, tuple[H, ...]]:
        buckets: dict[O, list[H]] = {}
        for hypothesis in self.hypotheses:
            outcome = predict(hypothesis, action)
            buckets.setdefault(outcome, []).append(hypothesis)
        return {outcome: tuple(items) for outcome, items in buckets.items()}

    def score(
        self,
        action: A,
        predict: Callable[[H, A], O],
    ) -> ProbeScore[A]:
        buckets = self.partition(action, predict)
        n = len(self.hypotheses)
        sizes = [len(items) for items in buckets.values()]
        expected = sum(size * size for size in sizes) / n if n else 0.0
        return ProbeScore(
            action=action,
            outcome_classes=len(buckets),
            largest_class=max(sizes, default=0),
            expected_survivors=expected,
            predictions=n,
        )

    def choose(
        self,
        actions: Sequence[A],
        predict: Callable[[H, A], O],
    ) -> ProbeScore[A]:
        if not actions:
            raise ValueError("at least one action is required")

        # Prefer the action that creates the most distinct consequential
        # futures; then minimize the worst and expected surviving frontier.
        scores = [self.score(action, predict) for action in actions]
        return max(
            scores,
            key=lambda s: (
                s.outcome_classes,
                -s.largest_class,
                -s.expected_survivors,
            ),
        )

    def collide(
        self,
        action: A,
        observed: O,
        predict: Callable[[H, A], O],
    ) -> Collision[A, O]:
        before = len(self.hypotheses)
        survivors = tuple(
            hypothesis
            for hypothesis in self.hypotheses
            if predict(hypothesis, action) == observed
        )
        self.hypotheses = survivors
        return Collision(action, observed, before, len(survivors))

    def resolved(self) -> bool:
        return len(self.hypotheses) == 1
