from acc_consequence_closure import build_suffix_closure
from acc_generator_portfolio import (
    ACCGeneratorContext,
    ExactTailGenerator,
    GeneratorPortfolio,
    OrbitTailGenerator,
    RecurrenceGenerator,
)
from acc_ms_recurrence import N_REDUCTION_MACRO, ms_state
from acc_orbit_closure import build_orbit_closure
from realitygraph.acc import replay


def test_exact_tail_generator_emits_truthful_primitive_action():
    state = ((1, 2), (2,))
    target = ((1,), (2,))
    ctx = ACCGeneratorContext(exact_tail_bank={state: (3,)})
    actions = ExactTailGenerator().generate(state, ctx)
    assert len(actions) == 1
    action = actions[0]
    assert action.generator_id == "exact_tail"
    assert action.moves == (3,)
    assert action.successor == target
    assert replay(state, action.moves)[-1] == action.successor


def test_orbit_tail_generator_emits_explicit_inversion_bridge():
    target = ((1,), (2,))
    exact = build_suffix_closure([
        {"training_id": "known", "moves": [], "states": [{"state": [[1], [2]]}]}
    ])
    orbit = build_orbit_closure(exact)
    start = ((1,), (-2,))
    ctx = ACCGeneratorContext(orbit_closure=orbit)
    actions = OrbitTailGenerator().generate(start, ctx)
    assert len(actions) == 1
    action = actions[0]
    assert action.generator_id == "orbit_tail"
    assert action.moves == (1,)
    assert action.successor == target
    assert replay(start, action.moves)[-1] == target


def test_recurrence_generator_is_guarded_and_replay_exact():
    w = (2, 2)
    start = ms_state(3, w)
    ctx = ACCGeneratorContext(source_family="ms", n=3, w_vector=w)
    actions = RecurrenceGenerator().generate(start, ctx)
    assert len(actions) == 1
    assert actions[0].moves == N_REDUCTION_MACRO
    assert actions[0].successor == ms_state(2, w)
    assert replay(start, actions[0].moves)[-1] == actions[0].successor

    bad_w = (-1, -2, 1, -2)
    bad = ms_state(3, bad_w)
    bad_ctx = ACCGeneratorContext(source_family="ms", n=3, w_vector=bad_w)
    assert RecurrenceGenerator().generate(bad, bad_ctx) == ()


def test_portfolio_generator_order_is_frozen_and_deterministic():
    portfolio = GeneratorPortfolio.default()
    assert tuple(generator.generator_id for generator in portfolio.generators) == (
        "exact_tail",
        "orbit_tail",
        "ms_recurrence",
    )
