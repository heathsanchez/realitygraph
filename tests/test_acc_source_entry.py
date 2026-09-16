from acc_source_entry import source_entry_macros


def _trajectory(training_id, n, w_vector, moves):
    return {
        "training_id": training_id,
        "n": n,
        "w_vector": list(w_vector),
        "moves": list(moves),
    }


def test_source_entry_uses_only_same_w_lower_n():
    trajectories = [
        _trajectory("same-low", 1, (-1, -2, 1, -2), (6, 2, 9, 3, 7, 4)),
        _trajectory("same-high", 4, (-1, -2, 1, -2), (1, 2, 3, 4)),
        _trajectory("other-low", 1, (2, 1, 2, -1), (8, 9, 10, 11)),
    ]
    macros = source_entry_macros(
        trajectories,
        target_n=3,
        target_w=(-1, -2, 1, -2),
        min_len=2,
        max_len=4,
        include_full=True,
    )
    assert (6, 2) in macros
    assert (6, 2, 9, 3) in macros
    assert (6, 2, 9, 3, 7, 4) in macros
    assert (1, 2) not in macros
    assert (8, 9) not in macros


def test_source_entry_prefers_nearest_lower_n_then_longer_prefix():
    trajectories = [
        _trajectory("n1", 1, (2, 1), (1, 2, 3, 4)),
        _trajectory("n2", 2, (2, 1), (6, 7, 8, 9)),
    ]
    macros = source_entry_macros(
        trajectories,
        target_n=3,
        target_w=(2, 1),
        min_len=2,
        max_len=3,
        include_full=False,
    )
    assert macros[:2] == [(6, 7, 8), (6, 7)]
