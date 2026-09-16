from acc_orbit_transfer import compare_orbit_on_split


def _trajectory(training_id, moves, states, *, n=1, w_vector=(-2,)):
    return {
        "training_id": training_id,
        "n": n,
        "w_vector": list(w_vector),
        "moves": list(moves),
        "states": [{"state": state} for state in states],
    }


def test_orbit_closure_adds_exact_symmetry_join_and_ablates():
    acquisition = [
        _trajectory(
            "known",
            [3],
            [
                [[1, 2], [2]],
                [[1], [2]],
            ],
        )
    ]
    heldout = [
        _trajectory(
            "future",
            [8, 3],
            [
                [[2, 1], [2]],
                [[1, 2], [2]],
                [[1], [2]],
            ],
            n=2,
        )
    ]

    summary = compare_orbit_on_split(acquisition, heldout, budget=1)
    assert summary["orbit_classes"] == 2
    assert summary["cold_solved"] == 0
    assert summary["warm_solved"] == 1
    assert summary["warm_only_solved"] == 1
    assert summary["orbit_joins"] == 1
    assert summary["ablation_mismatches"] == 0
