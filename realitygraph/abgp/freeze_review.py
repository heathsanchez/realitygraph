from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from .arm_a import AGrowthEpisode
from .arm_g import GRecord
from .arm_p import PIndependentEpisode
from .manifest import ABGPAnalysisPlan
from .power import qualification_power_audit


def _shared_ancestor_count(groups: Sequence[tuple[str, ...]]) -> int:
    owners: dict[str, set[int]] = defaultdict(set)
    for index, group in enumerate(groups):
        for ancestor in group:
            owners[str(ancestor)].add(index)
    return sum(1 for episode_ids in owners.values() if len(episode_ids) > 1)


def audit_a_stochastic_ancestry(episodes: Sequence[AGrowthEpisode]) -> dict[str, Any]:
    if not episodes:
        raise ValueError("A stochastic-ancestry audit requires episodes")
    groups = [
        (
            f"acquisition:{episode.acquisition_seed_digest}",
            f"sealed_future:{episode.future_seed_digest}",
        )
        for episode in episodes
    ]
    shared = _shared_ancestor_count(groups)
    return {
        "inferential_unit": "acquisition_to_sealed_future_episode",
        "earliest_stochastic_ancestor_rule": (
            "episode-specific acquisition seed and separately derived sealed-future seed; "
            "no randomly generated world, grammar, acquisition pool, or constructor is shared across episodes"
        ),
        "fixed_protocol_objects": [
            "old-language R0 definition",
            "constructor family and verifier-message alphabet",
            "deterministic generator code/version",
            "analysis rule",
        ],
        "sampled_objects_per_episode": ["acquisition seed material", "sealed-future seed material"],
        "shared_stochastic_ancestor_count": shared,
        "no_cross_episode_shared_stochastic_ancestor": shared == 0,
        "episode_ancestor_digests": [list(group) for group in groups],
    }


def audit_p_stochastic_ancestry(episodes: Sequence[PIndependentEpisode]) -> dict[str, Any]:
    if not episodes:
        raise ValueError("P stochastic-ancestry audit requires episodes")
    groups = [
        tuple(
            [f"acquisition:{episode.acquisition_seed_digest}"]
            + [f"future:{seed}" for seed in episode.future_seed_digests]
        )
        for episode in episodes
    ]
    shared = _shared_ancestor_count(groups)
    return {
        "inferential_unit": "acquisition_restart_future_episode",
        "earliest_stochastic_ancestor_rule": (
            "each acquisition seed and each nested future seed is episode-specific; "
            "the retained object is a within-episode descendant and the only state crossing restart"
        ),
        "fixed_protocol_objects": [
            "24-policy candidate space",
            "four abstract context classes",
            "acquisition algorithm/version",
            "restart environment template",
            "analysis rule",
        ],
        "sampled_objects_per_episode": [
            "acquisition seed material",
            "acquired policy/retained object",
            "four future seed materials",
        ],
        "shared_stochastic_ancestor_count": shared,
        "no_cross_episode_shared_stochastic_ancestor": shared == 0,
        "episode_ancestor_digests": [list(group) for group in groups],
    }


def audit_g_exchangeability_design(records: Sequence[GRecord]) -> dict[str, Any]:
    if not records:
        raise ValueError("G exchangeability audit requires records")
    by_world: dict[int, list[GRecord]] = defaultdict(list)
    for record in records:
        by_world[int(record.world_index)].append(record)

    expected_doses = (0.0, 0.1, 0.25, 0.5, 1.0)
    complete_schedule = all(
        tuple(sorted(record.dose for record in world_records)) == expected_doses
        for world_records in by_world.values()
    )
    contiguous_worlds = tuple(sorted(by_world)) == tuple(range(len(by_world)))
    matched_pairs = all(
        record.relevant_corruption_count == record.irrelevant_corruption_count
        and record.relevant_corruption_magnitude == record.irrelevant_corruption_magnitude
        and len(record.relevant_corrupted_cells) == record.relevant_corruption_count
        and len(record.irrelevant_corrupted_cells) == record.irrelevant_corruption_count
        for record in records
    )
    preclassified = all(record.relevance_computed_before_corruption for record in records)

    # The DEV generator fixes the entire dose schedule and the matched cell-set
    # selections before any flip outcomes are read. Both relevance classes use
    # the same count/magnitude rule and the same deterministic rank-by-seed
    # selection mechanism within class. Under the sharp null that relevance has
    # no effect on the complete within-world outcome vector, swapping the two
    # class labels therefore leaves the joint vector distribution unchanged.
    selection_fixed = complete_schedule and preclassified and matched_pairs
    label_symmetric_under_null = matched_pairs and preclassified
    no_adaptive_stopping = complete_schedule and contiguous_worlds
    joint_exchangeable = (
        selection_fixed and label_symmetric_under_null and no_adaptive_stopping
    )
    return {
        "null_hypothesis": (
            "the complete relevant/irrelevant outcome vector for a world is invariant in distribution "
            "to one joint exchange of the two preregistered class labels across all nonzero doses"
        ),
        "randomization_unit": "world",
        "joint_exchange_scope": "all_nonzero_doses_within_world",
        "selection_fixed_before_outcomes": selection_fixed,
        "generation_label_symmetric_under_null": label_symmetric_under_null,
        "no_adaptive_stopping": no_adaptive_stopping,
        "matched_pair_construction": matched_pairs,
        "joint_world_vector_exchangeability_under_null": joint_exchangeable,
        "world_count": len(by_world),
        "complete_fixed_dose_schedule": complete_schedule,
    }


def freeze_power_review(plan: ABGPAnalysisPlan) -> dict[str, Any]:
    """Review the scope of the existing power calculations without inventing new alternatives.

    The historical qualification power audit is retained as a component-level
    diagnostic. Complete-arm PASS power cannot be honestly claimed from the
    present specification because the joint multi-control dependence and the
    true-alternative margin above observed effect floors are not frozen.
    """

    component = qualification_power_audit(plan)
    arms = {name: dict(value) for name, value in component["arms"].items()}
    arms["A"].update(
        {
            "complete_pass_power_status": "PENDING_JOINT_3_CONTROL_EFFECT_FLOOR_MODEL",
            "current_power_scope": "single paired significance component over declared discordance envelope",
            "complete_pass_components": 3,
        }
    )
    arms["B"].update(
        {
            "complete_pass_power_status": "PENDING_90_PERCENT_AGREEMENT_GATE_ALTERNATIVE",
            "current_power_scope": "36 component significance rejections via dependence-agnostic union bound",
            "complete_pass_components": 36,
            "agreement_gate": 0.90,
        }
    )
    arms["P"].update(
        {
            "complete_pass_power_status": "PENDING_JOINT_7_CONTROL_EFFECT_FLOOR_AND_DELETION_MODEL",
            "current_power_scope": "single paired significance component over declared discordance envelope",
            "complete_pass_components": 7,
        }
    )
    arms["G"].update(
        {
            "complete_pass_power_status": "PENDING_DESIGN_LEVEL_EXCHANGEABILITY_ACCEPTANCE",
            "current_power_scope": "max-dose conservative significance calculation; lower-dose signal fixed to zero",
        }
    )
    return {
        "alpha_provenance": (
            "four_arm_familywise_holm_worst_case_component_alpha_not_b_iut_multiplicity"
        ),
        "familywise_alpha": float(plan.familywise_alpha),
        "component_alpha_used_by_historical_audit": float(component["component_alpha"]),
        "historical_component_power_qualified": bool(component["qualified"]),
        "complete_pass_power_qualified": False,
        "arms": arms,
        "review_status": "POWER_MODEL_INCOMPLETE_FOR_FULL_ARM_PASS",
    }
