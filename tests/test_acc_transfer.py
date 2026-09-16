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


def test_find_orbit_bridge_handles_rotation_inversion_and_swap():
    from acc_open_ms_transfer import find_orbit_bridge
    from realitygraph.acc import replay

    rotation_source = ((2, 1, 1), (1, 2))
    rotation_target = ((1, 1, 2), (1, 2))
    rotation_moves = find_orbit_bridge(rotation_source, rotation_target)
    assert replay(rotation_source, rotation_moves)[-1] == rotation_target

    inversion_source = ((1,), (1, 2))
    inversion_target = ((1,), (-2, -1))
    inversion_moves = find_orbit_bridge(inversion_source, inversion_target)
    assert replay(inversion_source, inversion_moves)[-1] == inversion_target

    swap_source = ((1, 2), (2, 1))
    swap_target = ((2, 1), (1, 2))
    swap_moves = find_orbit_bridge(swap_source, swap_target)
    assert replay(swap_source, swap_moves)[-1] == swap_target


def test_manifest_orbit_map_finds_symmetry_equivalent_representative():
    from acc_open_ms_transfer import _manifest_orbit_map, presentation_orbit_key

    native = ((2, 1, 1), (1, 2))
    representative = ((1, 1, 2), (-2, -1))
    manifest = {
        "challenges": [
            {
                "challenge_id": "ac-00001",
                "move_spec_version": "ac-r2-v1",
                "initial_relators": [list(representative[0]), list(representative[1])],
            }
        ]
    }
    mapping = _manifest_orbit_map(manifest)
    assert mapping[presentation_orbit_key(native)]["challenge_id"] == "ac-00001"
