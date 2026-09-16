from acc_structural_generator import StructuralMacroGenerator, mine_structural_macros
from realitygraph.acc import replay


def _trajectory(training_id):
    start = ((1, 2), (2,))
    moves = (6, 7, 3)
    trace = replay(start, moves)
    return {
        "training_id": training_id,
        "moves": list(moves),
        "states": [
            {"index": i, "state": [list(word) for word in state]}
            for i, state in enumerate(trace)
        ],
    }


def test_miner_can_retain_repeated_fragment_without_final_length_reduction():
    trajectories = [_trajectory("a"), _trajectory("b")]
    bank = mine_structural_macros(
        trajectories,
        min_support=2,
        min_macro_len=2,
        max_macro_len=2,
    )
    cap = next(cap for cap in bank if tuple(cap["macro"]) == (6, 7))
    assert cap["support"] == 2
    assert cap["max_final_total_length_delta"] == 0
    assert cap["max_peak_total_length_delta"] > 0


def test_structural_generator_emits_only_replay_exact_actions_and_ablation_removes_it():
    trajectories = [_trajectory("a"), _trajectory("b")]
    bank = mine_structural_macros(
        trajectories,
        min_support=2,
        min_macro_len=2,
        max_macro_len=2,
    )
    start = ((1, 2), (2,))
    generator = StructuralMacroGenerator(bank)
    actions = generator.generate(start)
    macro = next(action for action in actions if action.moves == (6, 7))
    assert replay(start, macro.moves)[-1] == macro.successor

    removed = [cap for cap in bank if tuple(cap["macro"]) != (6, 7)]
    assert all(action.moves != (6, 7) for action in StructuralMacroGenerator(removed).generate(start))


def test_miner_rejects_inconsistent_trajectory_states():
    row = _trajectory("broken")
    row["states"][1]["state"] = [[1], [2]]
    try:
        mine_structural_macros([row], min_support=1, min_macro_len=2, max_macro_len=2)
    except ValueError as exc:
        assert "trajectory replay mismatch" in str(exc)
    else:
        raise AssertionError("inconsistent trajectory was accepted")
