from acc_exact_tail import build_tail_bank, search_with_tail


def _trajectory(training_id, states, moves):
    return {
        "training_id": training_id,
        "moves": list(moves),
        "states": [
            {"index": i, "state": [list(word) for word in state]}
            for i, state in enumerate(states)
        ],
    }


def test_tail_bank_retains_verified_suffix_for_each_exact_state():
    target = ((1,), (2,))
    middle = ((1, 2), (2,))
    start = ((1, 2), (2, 1, 2))
    bank = build_tail_bank([
        _trajectory("toy", (start, middle, target), (5, 3))
    ])
    assert bank[start] == (5, 3)
    assert bank[middle] == (3,)
    assert bank[target] == ()


def test_tail_bank_keeps_shortest_suffix_on_duplicate_state():
    target = ((1,), (2,))
    state = ((1, 2), (2,))
    inverted = ((-2, -1), (2,))
    bank = build_tail_bank([
        _trajectory("long", (state, inverted, state, target), (0, 0, 3)),
        _trajectory("short", (state, target), (3,)),
    ])
    assert bank[state] == (3,)


def test_search_with_tail_closes_from_exact_memory_before_budget_exhausts():
    target = ((1,), (2,))
    middle = ((1, 2), (2,))
    start = ((1, 2), (2, 1, 2))
    bank = build_tail_bank([
        _trajectory("toy", (middle, target), (3,))
    ])
    result = search_with_tail(start, tail_bank=bank, budget=2)
    assert result["solved"] is True
    assert result["tail_hit"] is True
    assert result["moves"][-1] == 3
