from acc_consequence_open import attack_open_rows
from acc_training_replay import replay_training_document


def test_open_attack_can_join_full_training_closure_at_source():
    training = {
        "move_spec_version": "ac-r2-v1",
        "instances": [
            {
                "training_id": "known",
                "family": "miller-schupp",
                "n": 1,
                "w_vector": [-2],
                "initial_relators": [[-1, 2, 1, -2, -2], [1, 2]],
                "target_relators": [[1], [2]],
                "moves": [0, 9, 1, 2, 9, 0, 4, 1],
            }
        ],
    }
    trajectories = replay_training_document(training)["trajectories"]
    open_rows = [{"seq": 9999, "n": 1, "w_vector": (-2,)}]
    manifest = {
        "limits": {
            "max_path_length": 100000,
            "max_total_relator_length": 10000,
            "max_work": 5000000,
        },
        "challenges": [
            {
                "challenge_id": "ac-test",
                "move_spec_version": "ac-r2-v1",
                "initial_relators": [[-1, 2, 1, -2, -2], [1, 2]],
                "target_relators": [[1], [2]],
            }
        ],
    }

    summary, solved, unmatched = attack_open_rows(
        trajectories,
        open_rows,
        manifest,
        official_tools=None,
        budget=2,
    )
    assert summary["open_rows"] == 1
    assert summary["closure_states"] > 0
    assert summary["open_solved"] == 1
    assert summary["closure_join_solved"] == 1
    assert unmatched == []
    assert solved[0]["challenge_id"] == "ac-test"
    assert solved[0]["search_expansions"] == 1
    assert solved[0]["moves"] == training["instances"][0]["moves"]
