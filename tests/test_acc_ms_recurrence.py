from acc_ms_recurrence import (
    N_REDUCTION_MACRO,
    commutes_with_y,
    macro_reduces_n,
    ms_state,
)
from realitygraph.acc import replay


def _y_power(k: int) -> tuple[int, ...]:
    if k >= 0:
        return (2,) * k
    return (-2,) * (-k)


def test_five_move_macro_reduces_n_for_y_powers():
    assert N_REDUCTION_MACRO == (6, 2, 9, 3, 7)
    for n in range(2, 8):
        for k in range(-5, 6):
            w = _y_power(k)
            assert commutes_with_y(w)
            assert macro_reduces_n(n, w)
            assert replay(ms_state(n, w), N_REDUCTION_MACRO)[-1] == ms_state(n - 1, w)


def test_noncommuting_w_exposes_exact_boundary():
    w = (-1, -2, 1, -2)
    assert not commutes_with_y(w)
    assert not macro_reduces_n(3, w)
