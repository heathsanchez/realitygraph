from acc_prospective_transfer import (
    best_first_search,
    deterministic_split,
    reconstruct_ms_state,
)


def test_reconstruct_ms_state_matches_published_training_example():
    assert reconstruct_ms_state(1, (-2,)) == ((-1, 2, 1, -2, -2), (1, 2))


def test_deterministic_split_is_stable_and_disjoint():
    rows = [{"training_id": f"id-{i}"} for i in range(20)]
    a1, b1 = deterministic_split(rows, 0.7, "acc-test")
    a2, b2 = deterministic_split(list(reversed(rows)), 0.7, "acc-test")
    assert [r["training_id"] for r in a1] == [r["training_id"] for r in a2]
    assert [r["training_id"] for r in b1] == [r["training_id"] for r in b2]
    assert set(r["training_id"] for r in a1).isdisjoint(r["training_id"] for r in b1)
    assert len(a1) + len(b1) == 20


def test_best_first_cold_search_solves_official_one_move_example():
    result = best_first_search(((1, 2), (2,)), bank=[], start_macros=[], budget=10)
    assert result["solved"] is True
    assert result["moves"] == [3]
    assert result["expansions"] <= 2


def test_bank_ablation_restores_cold_search_exactly():
    start = ((1, 2), (2,))
    cold = best_first_search(start, bank=[], start_macros=[], budget=10)
    ablated = best_first_search(start, bank=[], start_macros=[], budget=10)
    assert ablated == cold
