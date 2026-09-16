import acc_developmental_experiment as v1
from acc_developmental_experiment import _build_components
from acc_developmental_experiment_v3 import _composite_extra_callback
from acc_substitution_generator import compile_substitution, source_conditioned_candidates


def test_v3_composite_contains_v1_and_source_conditioned_substitutions():
    components = _build_components([])
    row = {
        "family": "ms",
        "n": 1,
        "w_vector": (2, -1, -2, 1, 2, 2),
    }
    start = ((-1, 2, 1, -2, -2), (1, -2, -2, -1, 2, 1, -2))
    actions = _composite_extra_callback("substitution", row, components)(start)
    generated = {action.moves for action in actions if action.generator_id == "substitution"}

    v1_moves = {
        action.moves for action in v1._substitution_generator().generate(start)[:48]
    }
    source_moves = {
        compile_substitution(candidate)
        for candidate in source_conditioned_candidates(row["w_vector"], max_words=12)
    }

    assert v1_moves <= generated
    assert generated & source_moves
    assert len(generated) <= 96
