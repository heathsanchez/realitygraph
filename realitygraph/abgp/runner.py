from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .analysis import analyze_matrix
from .arm_a import generate_a_dev_records
from .arm_b import generate_b_dev_records, grammar_families
from .arm_g import generate_g_dev_records
from .arm_p import run_p_dev_records
from .manifest import (
    ConfirmatoryLockedError,
    load_analysis_plan,
    load_design_manifest,
    reject_confirmatory_namespace,
)


_ROOT = Path(__file__).resolve().parents[2]
_DESIGN_PATH = _ROOT / "preregistration" / "abgp-design-manifest-v1.json"
_ANALYSIS_PATH = _ROOT / "preregistration" / "abgp-analysis-plan-v1.json"
_DEV_NAMESPACE = "ABGP-DEV-v1"


def _a_inputs(records: list[Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    hard = {
        "message_nonidentifying": all(r.compatible_optimal_action_count > 1 for r in records),
        "single_message": all(r.verifier_message_count == 1 for r in records),
        "single_repair_round": all(r.repair_round_count == 1 for r in records),
        "budget_ok": all(r.equal_compute_units == r.verifier_compute_units for r in records),
    }
    return (
        {
            "pairs": [[r.equal_recheck_correct, r.verifier_correct] for r in records],
            "hard_gates": hard,
        },
        {
            "task_count": len(records),
            "all_messages_nonidentifying": hard["message_nonidentifying"],
            "max_verifier_messages_per_task": max(r.verifier_message_count for r in records),
            "max_repair_rounds_per_task": max(r.repair_round_count for r in records),
            "equal_compute_matched": hard["budget_ok"],
        },
    )


def _b_inputs(records: list[Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    families = grammar_families()
    alphabets = [set(g.surface_alphabet) for g in families]
    disjoint = all(
        alphabets[i].isdisjoint(alphabets[j])
        for i in range(len(alphabets))
        for j in range(i + 1, len(alphabets))
    )
    directions = [(r.acquisition_family, r.transfer_family) for r in records]
    hard = {
        "grammar_independence": disjoint
        and len({g.serialization_schema for g in families}) == 4
        and len({g.inference_route for g in families}) == 4,
        "no_translation": all(g.translation_table is None for g in families),
        "no_primitive_dictionary_by_construction": len({len(g.primitives) for g in families}) == 4,
        "no_shared_surface_serialization": disjoint,
        "all_12_ordered_directions": len(set(directions)) == 12,
    }
    intervention_bits = [bit for record in records for _, bit in record.intervention_results]
    return (
        {
            "treatment": [r.treatment_success for r in records],
            "wrong_class": [r.wrong_class_success for r in records],
            "shuffled_coupling": [r.shuffled_coupling_success for r in records],
            "direction_labels": [f"{a}->{b}" for a, b in directions],
            "intervention_agreement": intervention_bits,
            "hard_gates": hard,
        },
        {
            "record_count": len(records),
            "inferential_unit": "ordered_direction_world_pair",
            "ordered_directions": len(set(directions)),
            "interventions_per_unit": 4,
            "intervention_evaluations": len(intervention_bits),
            "surface_alphabets_pairwise_disjoint": disjoint,
            "serialization_schema_count": len({g.serialization_schema for g in families}),
            "inference_route_count": len({g.inference_route for g in families}),
        },
    )


def _g_inputs(records: list[Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    weights = {0.1: 2, 0.25: 5, 0.5: 10, 1.0: 20}
    nonzero = [r for r in records if r.dose > 0]
    maxdose = [r for r in records if r.dose == 1.0]
    hard = {
        "preclassified": all(r.relevance_computed_before_corruption for r in records),
        "matched_corruption": all(
            r.relevant_corruption_count == r.irrelevant_corruption_count
            and r.relevant_corruption_magnitude == r.irrelevant_corruption_magnitude
            for r in records
        ),
        "nonzero_dose_nonempty": all(r.relevant_corruption_count > 0 for r in nonzero),
    }
    return (
        {
            "pairs": [
                {
                    "world_id": r.world_index,
                    "weight": weights[r.dose],
                    "relevant": r.relevant_flip,
                    "irrelevant": r.irrelevant_flip,
                }
                for r in nonzero
            ],
            "max_dose_relevant": [r.relevant_flip for r in maxdose],
            "max_dose_irrelevant": [r.irrelevant_flip for r in maxdose],
            "hard_gates": hard,
        },
        {
            "world_count": len({r.world_index for r in records}),
            "record_count": len(records),
            "randomization_unit": "world",
            "relevance_computed_before_corruption": hard["preclassified"],
            "matched_count_and_magnitude": hard["matched_corruption"],
        },
    )


def _mean(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def _p_inputs(records: list[Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    cold = [r.cold_correct for r in records]
    post = [r.post_deletion_correct for r in records]
    reacquisition_total = sum(r.reacquisition_search_count_after_deletion for r in records)
    hard = {
        "zero_verifier": sum(r.future_verifier_calls for r in records) == 0,
        "zero_search": sum(r.future_reconstruction_search_count for r in records) == 0,
        "label_free": all(not r.applicability_used_target_labels for r in records),
        "source_distinct": all(r.source_distinct and not r.forbidden_shared_features for r in records),
        "targeted_deletion": post == cold and reacquisition_total > 0,
    }
    return (
        {
            "retained": [r.retained_correct for r in records],
            "baselines": {
                "cold": cold,
                "equal_compute_recheck": [r.equal_recheck_correct for r in records],
                "verbal_rule_negative": [r.verbal_rule_negative_correct for r in records],
                "size_matched_sham": [r.sham_correct for r in records],
                "wrong_class_object": [r.wrong_class_correct for r in records],
            },
            "hard_gates": hard,
            "post_deletion_accuracy": _mean(post),
            "cold_accuracy": _mean(cold),
            "reacquisition_search_count": reacquisition_total,
        },
        {
            "task_count": len(records),
            "future_verifier_calls": sum(r.future_verifier_calls for r in records),
            "future_reconstruction_search_count": sum(r.future_reconstruction_search_count for r in records),
            "all_source_distinct": hard["source_distinct"],
            "all_label_free": hard["label_free"],
            "reacquisition_search_count_after_deletion": reacquisition_total,
            "unique_retained_object_digests": len({r.retained_object_digest for r in records}),
        },
    )


def run_dev_matrix(
    *,
    a_count: int = 64,
    b_worlds_per_direction: int = 8,
    g_worlds: int = 32,
    p_count: int = 64,
) -> dict[str, Any]:
    design = load_design_manifest(_DESIGN_PATH)
    analysis_plan = load_analysis_plan(_ANALYSIS_PATH)
    if design.confirmatory_execution_enabled:
        raise ConfirmatoryLockedError("DEV runner refuses a manifest with confirmation enabled")

    a_records = generate_a_dev_records(a_count)
    b_records = generate_b_dev_records(b_worlds_per_direction)
    g_records = generate_g_dev_records(g_worlds)
    p_records = run_p_dev_records(p_count)

    a_input, a_audit = _a_inputs(a_records)
    b_input, b_audit = _b_inputs(b_records)
    g_input, g_audit = _g_inputs(g_records)
    p_input, p_audit = _p_inputs(p_records)
    analysis_inputs = {"A": a_input, "B": b_input, "G": g_input, "P": p_input}
    analysis = analyze_matrix(analysis_inputs)

    return {
        "schema": "realitygraph.abgp.dev-matrix-summary.v1",
        "mode": "DEV_ONLY",
        "confirmatory_namespace_used": False,
        "design": {
            "status": design.status,
            "confirmatory_execution_enabled": design.confirmatory_execution_enabled,
            "design_version": design.raw["design_version"],
            "manifest_digest": design.digest,
            "analysis_plan_digest": analysis_plan.digest,
            "registered_confirmatory_task_counts": {
                "A": design.raw["arms"]["A"]["task_count"],
                "B_worlds_per_direction": design.raw["arms"]["B"]["fresh_worlds_per_direction"],
                "G": design.raw["arms"]["G"]["task_count"],
                "P": design.raw["arms"]["P"]["task_count"],
            },
        },
        "dev_counts": {
            "A": a_count,
            "B_worlds_per_direction": b_worlds_per_direction,
            "G": g_worlds,
            "P": p_count,
        },
        "raw_records": {
            "A": [asdict(record) for record in a_records],
            "B": [asdict(record) for record in b_records],
            "G": [asdict(record) for record in g_records],
            "P": [asdict(record) for record in p_records],
        },
        "analysis_inputs": analysis_inputs,
        "audits": {"A": a_audit, "B": b_audit, "G": g_audit, "P": p_audit},
        "analysis": analysis,
        "scientific_status": "DEVELOPMENT_MECHANICS_ONLY_NOT_CONFIRMATORY_EVIDENCE",
    }


def run_matrix(*, namespace: str, **kwargs: Any) -> dict[str, Any]:
    if namespace != _DEV_NAMESPACE:
        reject_confirmatory_namespace(namespace)
    return run_dev_matrix(**kwargs)


def write_dev_summary(path: str | Path, summary: dict[str, Any]) -> None:
    target = Path(path)
    target.write_text(
        json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
