from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from acc_developmental_core import GeneratedAction, primitive_expansion_ok
from realitygraph.acc import State, free_reduce, invert, replay


_CONJUGATE_MOVE = {
    0: {1: 6, -1: 7, 2: 8, -2: 9},
    1: {1: 10, -1: 11, 2: 12, -2: 13},
}
_MULTIPLY_MOVE = {
    (0, False): 2,
    (0, True): 3,
    (1, False): 4,
    (1, True): 5,
}


@dataclass(frozen=True)
class SubstitutionCandidate:
    target_relator: int
    conjugator: tuple[int, ...]
    inverse_other: bool = False


def _validate(candidate: SubstitutionCandidate) -> None:
    if candidate.target_relator not in (0, 1):
        raise ValueError("target_relator must be 0 or 1")
    if any(letter not in (1, -1, 2, -2) for letter in candidate.conjugator):
        raise ValueError("conjugator contains a non-generator letter")


def compile_substitution(candidate: SubstitutionCandidate) -> tuple[int, ...]:
    """Compile word-conjugation plus one relator multiplication to AC moves.

    To realize ``w r w^-1`` using primitive single-generator conjugations,
    letters of ``w`` are applied in reverse order.  The final move right-
    multiplies the transformed target relator by the other relator (or its
    inverse).  No high-level equality is trusted without replay.
    """
    _validate(candidate)
    cmap = _CONJUGATE_MOVE[candidate.target_relator]
    conjugations = tuple(cmap[letter] for letter in reversed(candidate.conjugator))
    multiply = _MULTIPLY_MOVE[(candidate.target_relator, bool(candidate.inverse_other))]
    return conjugations + (multiply,)


def substitution_successor(state: State, candidate: SubstitutionCandidate) -> State:
    _validate(candidate)
    target = candidate.target_relator
    other = 1 - target
    conjugator = tuple(candidate.conjugator)
    transformed = free_reduce(
        conjugator + state[target] + invert(conjugator)
    )
    factor = invert(state[other]) if candidate.inverse_other else state[other]
    transformed = free_reduce(transformed + factor)
    if target == 0:
        return transformed, state[1]
    return state[0], transformed


class SubstitutionGenerator:
    generator_id = "substitution"

    def __init__(
        self,
        candidates: Iterable[SubstitutionCandidate],
        *,
        max_total: int = 120,
        max_path_length: int = 64,
    ):
        self.candidates = tuple(candidates)
        self.max_total = int(max_total)
        self.max_path_length = int(max_path_length)

    def generate(self, state: State) -> tuple[GeneratedAction, ...]:
        actions: list[GeneratedAction] = []
        seen: set[tuple[int, ...]] = set()
        for candidate in self.candidates:
            try:
                moves = compile_substitution(candidate)
                direct = substitution_successor(state, candidate)
            except ValueError:
                continue
            if len(moves) > self.max_path_length or moves in seen:
                continue
            trace = replay(state, moves)
            if any(len(item[0]) + len(item[1]) > self.max_total for item in trace[1:]):
                continue
            successor = trace[-1]
            if successor != direct:
                raise AssertionError("substitution compiler disagrees with direct group semantics")
            action = GeneratedAction(
                self.generator_id,
                moves,
                successor,
                (
                    f"target={candidate.target_relator}",
                    "conjugator=" + ",".join(str(x) for x in candidate.conjugator),
                    f"inverse_other={int(candidate.inverse_other)}",
                ),
            )
            if not primitive_expansion_ok(state, action):
                raise AssertionError("substitution compiler emitted invalid primitive expansion")
            seen.add(moves)
            actions.append(action)
        return tuple(actions)
