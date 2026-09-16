from acc_developmental_core import ACCResidual
from acc_generator_controller import (
    GeneratorObservation,
    GeneratorPolicy,
    apply_policy,
    learn_generator_policy,
)


def _residual(plateau, capability_expansions=0):
    return ACCResidual(
        source_family="ms",
        n=5,
        w_signature=(1, -2),
        relator_lengths=(12, 5),
        exponent_sum_matrix=((0, -1), (1, 1)),
        initial_heuristic=(17, 12, 5),
        best_heuristic=(12, 8, 4),
        min_total_length=12,
        best_depth=4,
        first_capability_depth=None,
        capability_expansions=capability_expansions,
        exact_tail_near_hits=0,
        orbit_tail_near_hits=0,
        plateau_length=plateau,
        max_total_reject_fraction=0.0,
        budget_consumed=100,
    )


def test_controller_selects_safe_residual_region_instead_of_unconditional_generator():
    observations = [
        GeneratorObservation(
            _residual(20), "structural_macro",
            baseline_solved=False, generated_solved=True, official_verified=True,
            baseline_expansions=100, generated_expansions=40, generator_cost=12,
        ),
        GeneratorObservation(
            _residual(24), "structural_macro",
            baseline_solved=False, generated_solved=True, official_verified=True,
            baseline_expansions=100, generated_expansions=50, generator_cost=12,
        ),
        GeneratorObservation(
            _residual(2), "structural_macro",
            baseline_solved=True, generated_solved=False, official_verified=False,
            baseline_expansions=20, generated_expansions=100, generator_cost=12,
        ),
        GeneratorObservation(
            _residual(4), "structural_macro",
            baseline_solved=True, generated_solved=True, official_verified=True,
            baseline_expansions=20, generated_expansions=22, generator_cost=12,
        ),
    ]
    policy = learn_generator_policy(observations)
    assert policy.promoted is True
    assert policy.rescues == 2
    assert policy.harms == 0
    assert apply_policy(policy, _residual(21)) == ("structural_macro",)
    assert apply_policy(policy, _residual(3)) == ()


def test_controller_restart_is_byte_exact_and_ablation_invokes_nothing():
    observations = [
        GeneratorObservation(
            _residual(30), "substitution",
            baseline_solved=False, generated_solved=True, official_verified=True,
            baseline_expansions=100, generated_expansions=30, generator_cost=20,
        ),
        GeneratorObservation(
            _residual(1), "substitution",
            baseline_solved=True, generated_solved=False, official_verified=False,
            baseline_expansions=10, generated_expansions=100, generator_cost=20,
        ),
    ]
    policy = learn_generator_policy(observations)
    text = policy.canonical_json()
    restarted = GeneratorPolicy.from_json(text)
    assert restarted.canonical_json() == text
    assert apply_policy(restarted, _residual(40)) == ("substitution",)
    assert apply_policy(restarted.ablate(), _residual(40)) == ()
