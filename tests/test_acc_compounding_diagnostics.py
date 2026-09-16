import pytest

from acc_compounding_diagnostics import serialize_verified_solution
from acc_consequence_closure import STANDARD_TARGET


def test_serialize_verified_solution_keeps_exact_certificate_and_metadata():
    result = {
        "solved": True,
        "moves": [],
        "expansions": 1,
        "generator_uses": {"substitution": 3},
    }
    payload = serialize_verified_solution(STANDARD_TARGET, result)
    assert payload == {
        "local_solved": True,
        "moves": [],
        "path_length": 0,
        "expansions": 1,
        "generator_uses": {"substitution": 3},
    }


def test_serialize_verified_solution_rejects_invalid_certificate():
    result = {
        "solved": True,
        "moves": [0],
        "expansions": 1,
        "generator_uses": {},
    }
    with pytest.raises(AssertionError):
        serialize_verified_solution(STANDARD_TARGET, result)


def test_serialize_verified_solution_preserves_unsolved_result_without_moves():
    result = {
        "solved": False,
        "moves": [],
        "expansions": 100,
        "generator_uses": {},
    }
    assert serialize_verified_solution(STANDARD_TARGET, result) == {
        "local_solved": False,
        "moves": [],
        "path_length": 0,
        "expansions": 100,
        "generator_uses": {},
    }
