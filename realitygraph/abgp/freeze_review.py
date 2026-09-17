from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from typing import Any, Sequence

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


def _canonical_pair(pair: tuple[str, str]) -> tuple[str, str]:
    return tuple(sorted((str(pair[0]), str(pair[1]))))  # type: ignore[return-value]


def _label_blind_null_flip(record: GRecord) -> int:
    """A deterministic potential outcome used only to audit the sharp-null symmetry.

    It depends on every preregistered non-label input to the paired corruption
    operation (world, dose, count, magnitude, selected matched pairs) and not on
    whether a member of a pair is named relevant or irrelevant. The exact bit is
    immaterial; label blindness is the property the randomization test needs.
    """

    pairs = tuple(_canonical_pair(pair) for pair in record.matched_corruption_pairs)
    payload = (
        record.seed_digest,
        record.dose,
        record.relevant_corruption_count,
        record.relevant_corruption_magnitude,
        pairs,
    )
    return int(sha256(repr(payload).encode("utf-8")).hexdigest(), 16) & 1


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
        and len(record.matched_corruption_pairs) == record.relevant_corruption_count
        and tuple(pair[0] for pair in record.matched_corruption_pairs)
        == record.relevant_corrupted_cells
        and tuple(pair[1] for pair in record.matched_corruption_pairs)
        == record.irrelevant_corrupted_cells
        for record in records
    )
    preclassified = all(record.relevance_computed_before_corruption for record in records)

    # Pair ranking is based on an unordered pair identity in arm_g.py. Therefore
    # exchanging the two relevance labels inside every matched pair cannot alter
    # which pairs are selected at any dose.
    pair_selection_swap_invariant = matched_pairs and all(
        tuple(_canonical_pair(pair) for pair in record.matched_corruption_pairs)
        == tuple(_canonical_pair((pair[1], pair[0])) for pair in record.matched_corruption_pairs)
        for record in records
    )

    # Explicitly instantiate the declared sharp null. All potential flip outputs
    # depend on the world, dose and matched corruption operation, but not on the
    # relevance label. For each world, exchange the relevant/irrelevant entries
    # jointly across every nonzero dose and require the complete vector to be
    # byte-for-byte equal under the null model.
    null_swap_checks: list[bool] = []
    for world_records in by_world.values():
        nonzero = sorted((r for r in world_records if r.dose > 0), key=lambda r: r.dose)
        original = tuple((r.dose, _label_blind_null_flip(r), _label_blind_null_flip(r)) for r in nonzero)
        swapped = tuple((dose, irrelevant, relevant) for dose, relevant, irrelevant in original)
        null_swap_checks.append(original == swapped)
    sharp_null_swap_invariance = bool(null_swap_checks) and all(null_swap_checks)

    selection_fixed = complete_schedule and preclassified and matched_pairs and pair_selection_swap_invariant
    generation_label_symmetric_under_null = sharp_null_swap_invariance
    no_adaptive_stopping = complete_schedule and contiguous_worlds
    joint_exchangeable = (
        selection_fixed
        and generation_label_symmetric_under_null
        and no_adaptive_stopping
    )
    return {
        "null_model": "paired_label_blind_sharp_null",
        "null_hypothesis": (
            "conditional on the fixed matched-pair construction and all non-label inputs, "
            "the complete within-world outcome vector is unchanged by one joint exchange "
            "of relevant/irrelevant labels across every nonzero dose"
        ),
        "randomization_unit": "world",
        "joint_exchange_scope": "all_nonzero_doses_within_world",
        "selection_fixed_before_outcomes": selection_fixed,
        "matched_pair_selection_label_swap_invariant": pair_selection_swap_invariant,
        "sharp_null_vector_swap_invariance": sharp_null_swap_invariance,
        "generation_label_symmetric_under_null": generation_label_symmetric_under_null,
        "no_adaptive_stopping": no_adaptive_stopping,
        "matched_pair_construction": matched_pairs,
        "joint_world_vector_exchangeability_under_null": joint_exchangeable,
        "world_count": len(by_world),
        "complete_fixed_dose_schedule": complete_schedule,
        "scope_note": (
            "This is an explicit design/model contract for exact randomization under the stated sharp null; "
            "it is not a theorem that arbitrary natural-domain relevance classes are exchangeable."
        ),
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
            "complete_pass_power_status": "PENDING_EFFECT_FLOOR_COMPLETE_PASS_MODEL",
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
        "why_complete_power_is_not_identified": (
            "The frozen PASS rules include observed effect floors and, for B, a 90% agreement gate. "
            "The present nuisance specification fixes discordance/effect contrasts but not the full joint "
            "multi-control dependence or a true-alternative treatment-accuracy margin above those gates. "
            "Those quantities cannot be inferred from the existing component-power inputs without adding assumptions."
        ),
    }
