from acc_control_diagnostics import compare_progress


def test_compare_progress_detects_hidden_candidate_progress():
    baseline = {
        "best_heuristic": [5, 10],
        "min_total_length": 20,
        "plateau_length": 80,
        "max_total_reject_fraction": 0.10,
    }
    candidate = {
        "best_heuristic": [4, 12],
        "min_total_length": 18,
        "plateau_length": 60,
        "max_total_reject_fraction": 0.20,
    }
    result = compare_progress(baseline, candidate)
    assert result["heuristic_improved"] is True
    assert result["min_total_improved"] is True
    assert result["plateau_improved"] is True
    assert result["any_progress"] is True


def test_compare_progress_distinguishes_branching_without_progress():
    baseline = {
        "best_heuristic": [5, 10],
        "min_total_length": 20,
        "plateau_length": 80,
        "max_total_reject_fraction": 0.10,
    }
    candidate = {
        "best_heuristic": [5, 10],
        "min_total_length": 20,
        "plateau_length": 95,
        "max_total_reject_fraction": 0.30,
    }
    result = compare_progress(baseline, candidate)
    assert result["any_progress"] is False
    assert result["extra_reject_pressure"] is True
