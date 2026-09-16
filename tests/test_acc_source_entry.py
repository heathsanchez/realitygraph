from acc_source_entry import source_entry_macros, source_family_split


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


def test_source_family_split_holds_out_largest_n_per_recurring_w():
    rows = [
        _trajectory("a1", 1, (2, 1), (1, 2)),
        _trajectory("a3", 3, (2, 1), (3, 4)),
        _trajectory("b2", 2, (-2, 1), (5, 6)),
        _trajectory("b4", 4, (-2, 1), (7, 8)),
        _trajectory("single", 2, (1, 1), (9, 10)),
    ]
    acquisition, heldout = source_family_split(rows)
    assert {row["training_id"] for row in heldout} == {"a3", "b4"}
    assert {row["training_id"] for row in acquisition} == {"a1", "b2", "single"}
    assert {tuple(row["w_vector"]) for row in heldout}.isdisjoint(
        {tuple(row["w_vector"]) for row in acquisition if row["training_id"] == "single"}
    )
