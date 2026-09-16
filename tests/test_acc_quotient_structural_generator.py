from acc_quotient_structural_generator import (
    QuotientStructuralGenerator,
    quotient_guard,
    mine_quotient_structural_macros,
)
from realitygraph.acc import replay


def _trajectory(training_id, start, moves):
    states = replay(start, moves)
    return {
        "training_id": training_id,
        "moves": list(moves),
        "states": [{"state": [list(s[0]), list(s[1])]} for s in states],
    }


def test_shape_guard_forgets_boundary_and_cancellation_details():
    a = ((1, 2, -1), (2, 1))
    b = ((-2, 1, 2), (1, 2))
    assert quotient_guard(a, "shape") == quotient_guard(b, "shape")


def test_miner_support_counts_distinct_verified_trajectories():
    start_a = ((1, 2, -1), (2, 1))
    start_b = ((-2, 1, 2), (1, 2))
    macro = (0, 9)
    rows = [
        _trajectory("a", start_a, macro),
        _trajectory("b", start_b, macro),
    ]
    bank = mine_quotient_structural_macros(
        rows,
        guard_kind="shape",
        min_support=2,
        min_macro_len=2,
        max_macro_len=2,
    )
    assert any(tuple(cap["macro"]) == macro for cap in bank)
    cap = next(cap for cap in bank if tuple(cap["macro"]) == macro)
    assert cap["support"] == 2


def test_generator_replays_macro_on_new_state_under_same_quotient_guard():
    start_a = ((1, 2, -1), (2, 1))
    start_b = ((-2, 1, 2), (1, 2))
    macro = (0, 9)
    bank = mine_quotient_structural_macros(
        [_trajectory("a", start_a, macro), _trajectory("b", start_b, macro)],
        guard_kind="shape",
        min_support=2,
        min_macro_len=2,
        max_macro_len=2,
    )
    generator = QuotientStructuralGenerator(bank, guard_kind="shape")
    actions = generator.generate(start_b)
    action = next(action for action in actions if tuple(action.moves) == macro)
    assert action.successor == replay(start_b, macro)[-1]


def test_corrupted_trajectory_is_rejected():
    start = ((1, 2, -1), (2, 1))
    row = _trajectory("bad", start, (0, 9))
    row["states"][1]["state"] = [[1], [2]]
    try:
        mine_quotient_structural_macros(
            [row], guard_kind="shape", min_support=1, min_macro_len=2, max_macro_len=2
        )
    except ValueError as exc:
        assert "trajectory replay mismatch" in str(exc)
    else:
        raise AssertionError("corrupted trajectory must be rejected")
