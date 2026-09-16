from realitygraph.acc import apply_move, free_reduce, replay


def test_free_reduce_cancels_adjacent_inverses():
    assert free_reduce((1, 2, -2, -1, 2)) == (2,)


def test_move_3_matches_official_example():
    assert apply_move(((1, 2), (2,)), 3) == ((1,), (2,))


def test_ms_train_0001_replays_to_ordered_standard_target():
    start = ((-1, 2, 1, -2, -2), (1, 2))
    moves = (0, 9, 1, 2, 9, 0, 4, 1)
    trace = replay(start, moves)
    assert trace[-1] == ((1,), (2,))
    assert len(trace) == len(moves) + 1


def test_state_observables_are_target_free_and_order_sensitive():
    from realitygraph.acc import state_observables

    obs = state_observables(((1, 2), (-2, 1)))
    assert obs["lengths"] == (2, 2)
    assert obs["total_length"] == 4
    assert obs["exponent_sums"] == ((1, 1), (1, -1))
    assert obs["boundaries"] == ((1, 2), (-2, 1))
    assert obs["mul_cancellation"] == (True, False, False, False)


def test_state_and_sequence_hashes_are_deterministic():
    from realitygraph.acc import sequence_hash, state_hash

    state = ((1, 2), (2,))
    assert state_hash(state) == state_hash(state)
    assert state_hash(state) != state_hash((state[1], state[0]))
    assert sequence_hash((3, 2, 9)) == sequence_hash((3, 2, 9))
    assert sequence_hash((3, 2, 9)) != sequence_hash((3, 9, 2))
