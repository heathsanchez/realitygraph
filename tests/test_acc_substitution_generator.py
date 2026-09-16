from itertools import product

import acc_substitution_generator as substitution_module
from acc_substitution_generator import (
    SubstitutionCandidate,
    SubstitutionGenerator,
    compile_substitution,
    substitution_successor,
)
from realitygraph.acc import free_reduce, invert, replay


def _words(max_len=3):
    alphabet = (1, -1, 2, -2)
    yield ()
    for length in range(1, max_len + 1):
        yield from product(alphabet, repeat=length)


def test_compiled_substitution_matches_direct_group_semantics_exhaustively_small():
    states = (
        ((1, 2), (2, -1)),
        ((2, 1, -2), (1, -2, -1)),
    )
    for state in states:
        for conjugator in _words(3):
            for target in (0, 1):
                for inverse_other in (False, True):
                    candidate = SubstitutionCandidate(
                        target_relator=target,
                        conjugator=tuple(conjugator),
                        inverse_other=inverse_other,
                    )
                    moves = compile_substitution(candidate)
                    assert replay(state, moves)[-1] == substitution_successor(
                        state, candidate
                    )


def test_substitution_generator_emits_replay_exact_action_and_skips_invalid_candidates():
    start = ((1, 2), (2, -1))
    valid = SubstitutionCandidate(0, (1, -2), False)
    invalid_target = SubstitutionCandidate(2, (1,), False)
    invalid_letter = SubstitutionCandidate(0, (3,), False)
    generator = SubstitutionGenerator(
        (valid, invalid_target, invalid_letter),
        max_total=120,
        max_path_length=16,
    )
    actions = generator.generate(start)
    assert len(actions) == 1
    assert actions[0].generator_id == "substitution"
    assert actions[0].moves == compile_substitution(valid)
    assert replay(start, actions[0].moves)[-1] == actions[0].successor


def test_substitution_generator_respects_path_and_intermediate_size_bounds():
    start = ((1, 2), (2, -1))
    long = SubstitutionCandidate(0, (1, 2, 1, 2), False)
    assert SubstitutionGenerator((long,), max_path_length=2).generate(start) == ()
    assert SubstitutionGenerator((long,), max_total=3, max_path_length=32).generate(start) == ()


def test_source_conditioned_candidates_keep_fixed_action_budget_and_include_source_word():
    build = getattr(substitution_module, "source_conditioned_candidates", None)
    assert callable(build), "source-conditioned substitution portfolio is missing"

    source_word = (2, -1, -2, 1, 2, 2)
    candidates = build(source_word, max_words=12)
    assert len(candidates) == 48

    conjugators = {candidate.conjugator for candidate in candidates}
    reduced = free_reduce(source_word)
    assert reduced in conjugators
    assert free_reduce(invert(reduced)) in conjugators
    assert all(word and free_reduce(word) == word for word in conjugators)
