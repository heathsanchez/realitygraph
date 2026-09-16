from acc_training_replay import replay_training_document


def test_replay_training_document_records_exact_trajectories():
    doc = {
        "move_spec_version": "ac-r2-v1",
        "instances": [
            {
                "training_id": "toy-1",
                "family": "toy",
                "n": 1,
                "w_vector": [-2],
                "initial_relators": [[1, 2], [2]],
                "target_relators": [[1], [2]],
                "moves": [3],
            },
            {
                "training_id": "toy-2",
                "family": "toy",
                "n": 0,
                "w_vector": [],
                "initial_relators": [[1], [2]],
                "target_relators": [[1], [2]],
                "moves": [],
            },
        ],
    }

    result = replay_training_document(doc)
    assert result["summary"]["instances"] == 2
    assert result["summary"]["accepted"] == 2
    assert result["summary"]["rejected"] == 0
    assert result["trajectories"][0]["states"][-1]["state"] == [[1], [2]]
    assert result["trajectories"][0]["move_count"] == 1
    assert result["trajectories"][0]["moves"] == [3]
