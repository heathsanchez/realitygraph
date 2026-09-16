from acc_consequence_transfer import compare_closure_on_split


def _trajectory(training_id, start, moves, states):
    return {
        "training_id": training_id,
        "moves": moves,
        "states": [{"state": state} for state in states],
    }


def test_consequence_closure_creates_warm_only_solution_and_ablates_exactly():
    acquisition = [
        _trajectory(
            "known",
            [[1, 2], [2]],
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
            [[-2, -1], [2]],
            [0, 3],
            [
                [[-2, -1], [2]],
                [[1, 2], [2]],
                [[1], [2]],
            ],
        )
    ]

    summary = compare_closure_on_split(acquisition, heldout, budget=2)
    assert summary["closure_states"] == 2
    assert summary["cold_solved"] == 0
    assert summary["warm_solved"] == 1
    assert summary["warm_only_solved"] == 1
    assert summary["ablation_mismatches"] == 0
    assert summary["exact_restart"] is True
    assert summary["closure_joins"] == 1
