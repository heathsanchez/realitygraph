from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from acc_developmental_core import GeneratedAction, primitive_expansion_ok
from realitygraph.acc import State, free_reduce, invert, replay


_ALPHABET = (1, -1, 2, -2)
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
    if any(letter not in _ALPHABET for letter in candidate.conjugator):
        raise ValueError("conjugator contains a non-generator letter")


def source_conditioned_candidates(
    source_word: Iterable[int],
    *,
    max_words: int = 12,
) -> tuple[SubstitutionCandidate, ...]:
    """Build a fixed-width substitution portfolio conditioned on the source word.

    The old developmental experiment spent its 48-action budget on the first
    48 members of a global enumeration.  For Miller--Schupp rows the second
    relator already exposes a distinguished word ``w``.  Reuse that information
    without increasing width: reserve the same 12 conjugator slots for ``w``,
    ``w^-1``, the four primitive generators, then informative edge fragments of
    ``w``/``w^-1`` and finally generic reduced pairs as deterministic fill.

    Every retained conjugator is nonempty and freely reduced.  Four AC variants
    are emitted for each word (two target relators x other/inverse-other), so
    ``max_words=12`` gives exactly the historical 48-action budget.
    """
    limit = int(max_words)
    if limit <= 0:
        return ()

    raw = tuple(int(x) for x in source_word)
    if any(letter not in _ALPHABET for letter in raw):
        raise ValueError("source word contains a non-generator letter")
    word = free_reduce(raw)
    inverse_word = free_reduce(invert(word))

    selected: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()

    def add(candidate: Iterable[int]) -> None:
        reduced = free_reduce(tuple(int(x) for x in candidate))
        if not reduced or reduced in seen:
            return
        if any(letter not in _ALPHABET for letter in reduced):
            raise ValueError("candidate word contains a non-generator letter")
        seen.add(reduced)
        selected.append(reduced)

    # Preserve the source-specific long-range structure first, then the four
    # single-letter moves that were already useful in the V1 portfolio.
    add(word)
    add(inverse_word)
    for letter in _ALPHABET:
        add((letter,))

    # Edge fragments are the cheapest source-conditioned approximations to the
    # whole word and its inverse.  Longest first retains more structure while
    # the fixed width prevents search-cost growth.
    for basis in (word, inverse_word):
        max_fragment = min(4, len(basis) - 1)
        for width in range(max_fragment, 1, -1):
            add(basis[:width])
            add(basis[-width:])

    # Deterministic reduced-pair fill guarantees a full portfolio even for
    # very short or empty source words.
    for left in _ALPHABET:
        for right in _ALPHABET:
            if right == -left:
                continue
            add((left, right))

    words = selected[:limit]
    return tuple(
        SubstitutionCandidate(target, conjugator, inverse_other)
        for conjugator in words
        for target in (0, 1)
        for inverse_other in (False, True)
    )


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
