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


def _exponent_sums(word: Word) -> tuple[int, int]:
    return (
        sum(1 if letter == 1 else -1 if letter == -1 else 0 for letter in word),
        sum(1 if letter == 2 else -1 if letter == -2 else 0 for letter in word),
    )


def _boundary(word: Word) -> tuple[int, int]:
    return (word[0], word[-1]) if word else (0, 0)


def _would_cancel(left: Word, right: Word) -> bool:
    return bool(left and right and left[-1] == -right[0])


def state_observables(state: State) -> dict[str, object]:
    r0, r1 = state
    inv0 = invert(r0)
    inv1 = invert(r1)
    return {
        "lengths": (len(r0), len(r1)),
        "total_length": len(r0) + len(r1),
        "exponent_sums": (_exponent_sums(r0), _exponent_sums(r1)),
        "boundaries": (_boundary(r0), _boundary(r1)),
        "mul_cancellation": (
            _would_cancel(r0, r1),
            _would_cancel(r0, inv1),
            _would_cancel(r1, r0),
            _would_cancel(r1, inv0),
        ),
    }


def _digest_json(value: object) -> str:
    import hashlib
    import json

    text = json.dumps(value, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def state_hash(state: State) -> str:
    return _digest_json([list(state[0]), list(state[1])])


def sequence_hash(moves: Iterable[int]) -> str:
    return _digest_json(list(moves))
