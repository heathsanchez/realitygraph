from acc_consequence_closure import (
    build_suffix_closure,
    canonical_closure,
    closure_search,
    restart_closure,
)
from realitygraph.acc import replay


def _toy_trajectory():
    return {
        "training_id": "toy-proof",
        "moves": [3],
        "states": [
            {"state": [[1, 2], [2]]},
            {"state": [[1], [2]]},
        ],
    }


def test_suffix_closure_retains_verified_remaining_path():
    closure = build_suffix_closure([_toy_trajectory()])
    entry = closure["1,2|2"]
    assert entry["moves"] == [3]
    assert entry["training_id"] == "toy-proof"
    assert entry["index"] == 0
    assert replay(((1, 2), (2,)), entry["moves"])[-1] == ((1,), (2,))


def test_suffix_closure_restart_is_byte_exact():
    closure = build_suffix_closure([_toy_trajectory()])
    text = canonical_closure(closure)
    restarted = restart_closure(text)
    assert canonical_closure(restarted) == text


def test_closure_search_can_join_known_proof_before_standard_target():
    closure = build_suffix_closure([_toy_trajectory()])
    start = ((-2, -1), (2,))
    result = closure_search(
        start,
        closure=closure,
        bank=[],
        start_macros=[],
        budget=10,
    )
    assert result["solved"] is True
    assert result["join_training_id"] == "toy-proof"
    assert result["join_index"] == 0
    assert result["moves"] == [0, 3]
    assert replay(start, result["moves"])[-1] == ((1,), (2,))


def test_closure_search_ablation_is_plain_cold_search():
    start = ((1, 2), (2,))
    cold = closure_search(start, closure={}, bank=[], start_macros=[], budget=10)
    ablated = closure_search(start, closure={}, bank=[], start_macros=[], budget=10)
    assert cold == ablated
