from acc_developmental_core import GeneratedAction
from acc_developmental_search import developmental_search
from realitygraph.acc import replay


def test_instrumented_search_reports_target_free_residual_diagnostics():
    start = ((1, 2), (2,))
    result = developmental_search(
        start,
        orbit_closure={},
        bank=[],
        start_macros=[],
        budget=1,
        extra_actions=None,
    )
    diagnostics = result["diagnostics"]
    assert set(diagnostics) == {
        "initial_heuristic",
        "best_heuristic",
        "min_total_length",
        "best_depth",
        "first_capability_depth",
        "capability_expansions",
        "exact_tail_near_hits",
        "orbit_tail_near_hits",
        "plateau_length",
        "max_total_reject_fraction",
        "budget_consumed",
    }
    assert "target" not in str(diagnostics).lower()
    assert "solved" not in diagnostics


def test_verified_extra_action_can_rescue_with_same_expansion_budget():
    target = ((1,), (2,))
    start = replay(target, (6, 2))[-1]
    rescue_moves = (3, 7)
    assert replay(start, rescue_moves)[-1] == target

    cold = developmental_search(
        start,
        orbit_closure={},
        bank=[],
        start_macros=[],
        budget=1,
        extra_actions=None,
    )

    def extra(state):
        if state != start:
            return ()
        return (
            GeneratedAction(
                generator_id="unit_rescue",
                moves=rescue_moves,
                successor=target,
                provenance=("unit",),
            ),
        )

    warm = developmental_search(
        start,
        orbit_closure={},
        bank=[],
        start_macros=[],
        budget=1,
        extra_actions=extra,
    )
    assert cold["solved"] is False
    assert warm["solved"] is True
    assert warm["moves"] == list(rescue_moves)
    assert warm["generator_uses"] == {"unit_rescue": 1}


def test_invalid_extra_action_is_never_accepted():
    start = ((1, 2), (2,))

    def bad(_state):
        return (
            GeneratedAction(
                generator_id="bad",
                moves=(3,),
                successor=start,
                provenance=("lie",),
            ),
        )

    try:
        developmental_search(
            start,
            orbit_closure={},
            bank=[],
            start_macros=[],
            budget=2,
            extra_actions=bad,
        )
    except AssertionError as exc:
        assert "invalid generated action" in str(exc)
    else:
        raise AssertionError("invalid generated action was accepted")
