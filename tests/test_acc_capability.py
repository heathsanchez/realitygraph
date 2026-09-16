from acc_capability_miner import (
    applicable_capabilities,
    canonical_bank,
    mine_capabilities,
    restart_bank,
)


def _trajectory(training_id, start, moves, states):
    return {
        "training_id": training_id,
        "moves": list(moves),
        "states": [
            {"index": i, "state": [list(state[0]), list(state[1])]}
            for i, state in enumerate(states)
        ],
    }


def test_mines_guarded_macro_that_transfers_across_word_lengths():
    t1 = _trajectory(
        "a",
        ((1, 2), (2,)),
        (3, 1),
        (((1, 2), (2,)), ((1,), (2,)), ((1,), (-2,))),
    )
    t2 = _trajectory(
        "b",
        ((1, 2, 2), (2, 2)),
        (3, 1),
        (((1, 2, 2), (2, 2)), ((1,), (2, 2)), ((1,), (-2, -2))),
    )

    bank = mine_capabilities([t1, t2], min_support=2, min_macro_len=2, max_macro_len=2)
    assert len(bank) >= 1
    matches = applicable_capabilities(((1, 2, 2, 2), (2, 2, 2)), bank)
    assert any(cap["macro"] == [3, 1] for cap in matches)
    assert applicable_capabilities(((-1,), (2,)), bank) == []


def test_capability_bank_restart_is_byte_exact():
    t = _trajectory(
        "a",
        ((1, 2), (2,)),
        (3, 1),
        (((1, 2), (2,)), ((1,), (2,)), ((1,), (-2,))),
    )
    bank = mine_capabilities([t, t], min_support=2, min_macro_len=2, max_macro_len=2)
    text = canonical_bank(bank)
    restarted = restart_bank(text)
    assert canonical_bank(restarted) == text
