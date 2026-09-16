from acc_consequence_closure import build_suffix_closure
from acc_orbit_closure import build_orbit_closure, orbit_closure_search
from realitygraph.acc import replay


def test_orbit_closure_compiles_inversion_to_official_move():
    trajectory = {
        "training_id": "known",
        "moves": [],
        "states": [{"state": [[1], [2]]}],
    }
    exact = build_suffix_closure([trajectory])
    orbit = build_orbit_closure(exact)
    start = ((1,), (-2,))
    result = orbit_closure_search(
        start,
        orbit_closure=orbit,
        bank=[],
        start_macros=[],
        budget=1,
    )
    assert result["solved"] is True
    assert result["orbit_join"] is True
    assert result["moves"] == [1]
    assert replay(start, result["moves"])[-1] == ((1,), (2,))


def test_orbit_closure_is_smaller_than_exact_closure_when_states_share_orbit():
    exact = {
        "1,2|2": {"training_id": "a", "index": 0, "moves": [3]},
        "2,1|2": {"training_id": "b", "index": 0, "moves": [8, 3]},
    }
    orbit = build_orbit_closure(exact)
    assert len(orbit) == 1
