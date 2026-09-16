from acc_developmental_experiment import _build_components
from acc_developmental_experiment_v2 import _source_conditioned_extra_callback
from acc_substitution_generator import compile_substitution, source_conditioned_candidates


def test_v2_callback_uses_row_source_word_without_widening_portfolio():
    components = _build_components([])
    row = {
        "family": "ms",
        "n": 1,
        "w_vector": (2, -1, -2, 1, 2, 2),
    }
    start = ((-1, 2, 1, -2, -2), (1, -2, -2, -1, 2, 1, -2))
    callback = _source_conditioned_extra_callback("substitution", row, components)
    actions = callback(start)

    expected = {
        compile_substitution(candidate)
        for candidate in source_conditioned_candidates(row["w_vector"], max_words=12)
    }
    generated = {action.moves for action in actions if action.generator_id == "substitution"}

    assert generated
    assert generated <= expected
    assert len(generated) <= 48
