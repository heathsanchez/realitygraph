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
