from __future__ import annotations

from typing import Iterable

from realitygraph.acc import State, free_reduce, invert, replay

# Exact frozen AC move ids:
#   6: r0 <- x r0 x^-1
#   2: r0 <- r0 r1
#   9: r0 <- y^-1 r0 y
#   3: r0 <- r0 r1^-1
#   7: r0 <- x^-1 r0 x
N_REDUCTION_MACRO = (6, 2, 9, 3, 7)


def ms_state(n: int, w: Iterable[int]) -> State:
    """Canonical Miller-Schupp presentation P(n,w) used by the SAIR release."""
    if n < 1:
        raise ValueError("Miller-Schupp n must be positive")
    word = tuple(int(x) for x in w)
    r0 = free_reduce((-1,) + (2,) * n + (1,) + (-2,) * (n + 1))
    r1 = free_reduce((1,) + invert(word))
    return r0, r1


def commutes_with_y(w: Iterable[int]) -> bool:
    """Exact free-word check for w^-1 y w = y."""
    word = free_reduce(tuple(int(x) for x in w))
    return free_reduce(invert(word) + (2,) + word) == (2,)


def macro_reduces_n(n: int, w: Iterable[int]) -> bool:
    """Check the exact five-move witness P(n,w) -> P(n-1,w).

    For n >= 2 this equality holds whenever ``w`` commutes with ``y``.  The
    function deliberately checks the official move semantics rather than
    assuming that algebraic condition is sufficient.
    """
    if n < 2:
        return False
    word = tuple(int(x) for x in w)
    return replay(ms_state(n, word), N_REDUCTION_MACRO)[-1] == ms_state(n - 1, word)


def symbolic_residual_word(w: Iterable[int]) -> tuple[int, ...]:
    """Return the only w-dependent residual in the five-move reduction.

    Direct free-group expansion of the macro sends the variable part to
    ``w^-1 y w``.  Equality with ``y`` is therefore the precise boundary for
    this recurrence witness.
    """
    word = free_reduce(tuple(int(x) for x in w))
    return free_reduce(invert(word) + (2,) + word)
