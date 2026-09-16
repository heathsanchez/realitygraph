from __future__ import annotations

from typing import Iterable, Sequence

Word = tuple[int, ...]
State = tuple[Word, Word]

GENS = (1, -1, 2, -2)
NUM_MOVES = 14


def free_reduce(word: Iterable[int]) -> Word:
    out: list[int] = []
    for letter in word:
        if out and out[-1] == -letter:
            out.pop()
        else:
            out.append(letter)
    return tuple(out)


def invert(word: Sequence[int]) -> Word:
    return tuple(-letter for letter in reversed(word))


def apply_move(state: State, move: int) -> State:
    r0, r1 = state
    if move == 0:
        return invert(r0), r1
    if move == 1:
        return r0, invert(r1)
    if move == 2:
        return free_reduce(r0 + r1), r1
    if move == 3:
        return free_reduce(r0 + invert(r1)), r1
    if move == 4:
        return r0, free_reduce(r1 + r0)
    if move == 5:
        return r0, free_reduce(r1 + invert(r0))
    if 6 <= move <= 9:
        g = GENS[move - 6]
        return free_reduce((g,) + r0 + (-g,)), r1
    if 10 <= move <= 13:
        g = GENS[move - 10]
        return r0, free_reduce((g,) + r1 + (-g,))
    raise ValueError(f"bad move id: {move!r}")


def replay(state: State, moves: Iterable[int]) -> tuple[State, ...]:
    current = (free_reduce(state[0]), free_reduce(state[1]))
    trace = [current]
    for move in moves:
        current = apply_move(current, move)
        trace.append(current)
    return tuple(trace)
