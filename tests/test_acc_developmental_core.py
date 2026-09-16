import json

import pytest

from acc_developmental_core import (
    ACCResidual,
    GeneratedAction,
    primitive_expansion_ok,
    residual_from_search,
)


def test_generated_action_accepts_only_truthful_primitive_successor():
    start = ((1, 2), (2,))
    target = ((1,), (2,))
    good = GeneratedAction(
        generator_id="toy",
        moves=(3,),
        successor=target,
        provenance=("unit",),
    )
    bad = GeneratedAction(
        generator_id="toy",
        moves=(3,),
        successor=start,
        provenance=("unit",),
    )
    assert primitive_expansion_ok(start, good) is True
    assert primitive_expansion_ok(start, bad) is False


def test_residual_serialization_is_target_free_and_canonical():
    residual = ACCResidual(
        source_family="ms",
        n=7,
        w_signature=(-1, 2, 1),
        relator_lengths=(9, 4),
        exponent_sum_matrix=((0, -1), (1, 1)),
        initial_heuristic=(13, 9, 4),
        best_heuristic=(10, 7, 3),
        min_total_length=10,
        best_depth=5,
        first_capability_depth=3,
        capability_expansions=7,
        exact_tail_near_hits=2,
        orbit_tail_near_hits=4,
        plateau_length=11,
        max_total_reject_fraction=0.125,
        budget_consumed=100,
    )
    text = residual.canonical_json()
    assert text == residual.canonical_json()
    payload = json.loads(text)
    assert "target" not in text.lower()
    assert "moves" not in payload
    assert "solved" not in payload
    assert payload["n"] == 7


def test_residual_builder_rejects_target_or_outcome_diagnostics():
    start = ((1, 2), (2,))
    diagnostics = {
        "initial_heuristic": (3, 2, 1),
        "best_heuristic": (2, 1, 1),
        "min_total_length": 2,
        "best_depth": 1,
        "first_capability_depth": None,
        "capability_expansions": 0,
        "exact_tail_near_hits": 0,
        "orbit_tail_near_hits": 0,
        "plateau_length": 1,
        "max_total_reject_fraction": 0.0,
        "budget_consumed": 10,
        "target_moves": [3],
    }
    with pytest.raises(ValueError, match="target-free"):
        residual_from_search(
            start,
            source_family="ms",
            n=2,
            w_vector=(2,),
            diagnostics=diagnostics,
        )
