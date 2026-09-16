from acc_quotient_structural_experiment import baseline_preserving_choice


def _result(solved, moves=(), expansions=0):
    return {"solved": solved, "moves": tuple(moves), "expansions": expansions}


def test_baseline_solution_can_never_be_replaced_by_failed_candidate():
    baseline = _result(True, (1, 2), 10)
    candidate = _result(False, (), 100)
    assert baseline_preserving_choice(baseline, candidate) is baseline


def test_candidate_is_used_only_as_rescue_when_baseline_failed():
    baseline = _result(False, (), 100)
    candidate = _result(True, (3, 4), 80)
    assert baseline_preserving_choice(baseline, candidate) is candidate


def test_two_failures_preserve_baseline_record():
    baseline = _result(False, (), 100)
    candidate = _result(False, (), 90)
    assert baseline_preserving_choice(baseline, candidate) is baseline
