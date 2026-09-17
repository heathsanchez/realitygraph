from __future__ import annotations

from collections import defaultdict
import json
from math import comb, sqrt
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .b_iut import analyze_direction_iut
from .manifest import load_analysis_plan


_ROOT = Path(__file__).resolve().parents[2]
_ANALYSIS_PATH = _ROOT / "preregistration" / "abgp-analysis-plan-v1.json"
_ARM_ORDER = ("A", "B", "G", "P")


def _mean_binary(values: Sequence[int | bool]) -> float:
    if not values:
        return 0.0
    return sum(bool(v) for v in values) / len(values)


def _all_gates(gates: Mapping[str, Any] | None) -> bool:
    return bool(gates) and all(value is True for value in gates.values())


def _binomial_upper_tail(successes: int, trials: int) -> float:
    if trials <= 0:
        return 1.0
    numerator = sum(comb(trials, k) for k in range(successes, trials + 1))
    return numerator / (2**trials)


def exact_mcnemar_one_sided(pairs: Iterable[Sequence[int | bool]]) -> float:
    """Exact one-sided McNemar p-value for treatment > control."""

    wins = 0
    losses = 0
    for pair in pairs:
        if len(pair) != 2:
            raise ValueError("McNemar pairs must contain control and treatment outcomes")
        control, treatment = bool(pair[0]), bool(pair[1])
        if treatment and not control:
            wins += 1
        elif control and not treatment:
            losses += 1
    return _binomial_upper_tail(wins, wins + losses)


def holm_bonferroni(raw_pvalues: Mapping[str, float], alpha: float) -> dict[str, Any]:
    if set(raw_pvalues) != set(_ARM_ORDER):
        raise ValueError("Holm family must contain exactly A, B, G, P")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be between zero and one")
    order_index = {arm: i for i, arm in enumerate(_ARM_ORDER)}
    ordered = sorted(_ARM_ORDER, key=lambda arm: (float(raw_pvalues[arm]), order_index[arm]))
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    rejected: dict[str, bool] = {arm: False for arm in _ARM_ORDER}
    still_rejecting = True
    for i, arm in enumerate(ordered):
        p = min(1.0, max(0.0, float(raw_pvalues[arm])))
        running = max(running, min(1.0, (m - i) * p))
        adjusted[arm] = running
        threshold = alpha / (m - i)
        if still_rejecting and p <= threshold:
            rejected[arm] = True
        else:
            still_rejecting = False
    return {
        "order": ordered,
        "adjusted_pvalues": {arm: adjusted[arm] for arm in _ARM_ORDER},
        "rejected": rejected,
        "alpha": alpha,
    }


def g_exact_randomization_pvalue(
    discordant_weight_counts: Mapping[int, int], observed_statistic: int
) -> float:
    """Legacy exact sign-randomization over independent world-by-dose pairs."""

    distribution: dict[int, int] = {0: 1}
    n = 0
    for weight in sorted(discordant_weight_counts):
        count = int(discordant_weight_counts[weight])
        if weight <= 0 or count < 0:
            raise ValueError("G randomization weights must be positive with non-negative counts")
        for _ in range(count):
            nxt: dict[int, int] = defaultdict(int)
            for statistic, ways in distribution.items():
                nxt[statistic + weight] += ways
                nxt[statistic - weight] += ways
            distribution = dict(nxt)
            n += 1
    if n == 0:
        return 1.0
    favorable = sum(ways for statistic, ways in distribution.items() if statistic >= observed_statistic)
    return favorable / (2**n)


def g_world_blocked_randomization_pvalue(
    world_scores: Sequence[int], observed_statistic: int
) -> float:
    """Exact one-sided randomization with one joint relevance-label swap per world.

    Each world's four nonzero dose measurements are repeated observations inside
    one inferential unit. Under the sharp null the relevance labels are swapped
    jointly for the whole world, flipping the sign of the world's aggregated
    dose-weighted score while preserving its magnitude.
    """

    magnitudes = [abs(int(score)) for score in world_scores if int(score) != 0]
    if not magnitudes:
        return 1.0
    distribution: dict[int, int] = {0: 1}
    for magnitude in magnitudes:
        nxt: dict[int, int] = defaultdict(int)
        for statistic, ways in distribution.items():
            nxt[statistic + magnitude] += ways
            nxt[statistic - magnitude] += ways
        distribution = dict(nxt)
    favorable = sum(ways for statistic, ways in distribution.items() if statistic >= observed_statistic)
    return favorable / (2 ** len(magnitudes))


def _paired_effect(control: Sequence[int | bool], treatment: Sequence[int | bool]) -> float:
    if len(control) != len(treatment) or not treatment:
        raise ValueError("paired binary outcomes must be non-empty and equal length")
    return _mean_binary(treatment) - _mean_binary(control)


def _wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 1.0)
    p = successes / n
    z2 = z * z
    denominator = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denominator
    radius = z * sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n) / denominator
    return (max(0.0, center - radius), min(1.0, center + radius))


def _paired_effect_interval(
    control: Sequence[int | bool], treatment: Sequence[int | bool]
) -> tuple[float, float]:
    n = len(control)
    if n != len(treatment) or n == 0:
        raise ValueError("paired interval requires equal non-empty vectors")
    pc = _mean_binary(control)
    pt = _mean_binary(treatment)
    lc, uc = _wilson_interval(sum(bool(v) for v in control), n)
    lt, ut = _wilson_interval(sum(bool(v) for v in treatment), n)
    delta = pt - pc
    lower = delta - sqrt((pt - lt) ** 2 + (uc - pc) ** 2)
    upper = delta + sqrt((ut - pt) ** 2 + (pc - lc) ** 2)
    return (max(-1.0, lower), min(1.0, upper))


def _paired_control_summary(
    treatment: Sequence[int | bool], controls: Mapping[str, Sequence[int | bool]]
) -> tuple[dict[str, float], dict[str, float], dict[str, tuple[float, float]]]:
    pvalues: dict[str, float] = {}
    effects: dict[str, float] = {}
    intervals: dict[str, tuple[float, float]] = {}
    for name in sorted(controls):
        control = list(controls[name])
        if len(control) != len(treatment):
            raise ValueError("control vectors must be paired with treatment outcomes")
        pvalues[name] = exact_mcnemar_one_sided(zip(control, treatment))
        effects[name] = _paired_effect(control, treatment)
        intervals[name] = _paired_effect_interval(control, treatment)
    return pvalues, effects, intervals


def analyze_a(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Analyze A with paired tasks as the inferential unit.

    Final-lock inputs contain two primary controls: equal-compute recheck and an
    exact information-budget-matched Bayes policy. Legacy DEV inputs remain
    replayable so the clarification does not invalidate historical mechanics.
    """

    if "baselines" in raw:
        treatment = list(raw.get("treatment", ()))
        baselines = raw.get("baselines")
        expected = {"equal_compute_recheck", "information_matched_bayes"}
        if not treatment or not isinstance(baselines, Mapping) or set(baselines) != expected:
            raise ValueError("A final-lock input requires treatment and both primary controls")
        pvalues, effects, intervals = _paired_control_summary(treatment, baselines)
        effect = min(effects.values())
        return {
            "raw_pvalue": max(pvalues.values()),
            "component_pvalues": pvalues,
            "control_effects": effects,
            "effect_intervals": intervals,
            "effect": effect,
            "effect_floor_pass": effect >= 0.05,
            "hard_gates_pass": _all_gates(raw.get("hard_gates")),
            "effect_direction_positive": effect > 0.0,
            "inferential_unit": "paired_task",
            "analysis_mode": "INFORMATION_AND_COMPUTE_MATCHED_CONTROLS",
        }

    pairs = [tuple(pair) for pair in raw.get("pairs", ())]
    if not pairs:
        raise ValueError("A requires paired outcomes")
    control = [pair[0] for pair in pairs]
    treatment = [pair[1] for pair in pairs]
    effect = _paired_effect(control, treatment)
    return {
        "raw_pvalue": exact_mcnemar_one_sided(pairs),
        "effect": effect,
        "effect_interval": _paired_effect_interval(control, treatment),
        "effect_floor_pass": effect >= 0.05,
        "hard_gates_pass": _all_gates(raw.get("hard_gates")),
        "effect_direction_positive": effect > 0.0,
        "inferential_unit": "paired_task",
        "analysis_mode": "LEGACY_DEV_EQUAL_COMPUTE_ONLY",
    }


def analyze_b(raw: Mapping[str, Any]) -> dict[str, Any]:
    treatment = list(raw.get("treatment", ()))
    wrong = list(raw.get("wrong_class", ()))
    shuffled = list(raw.get("shuffled_coupling", ()))
    if not treatment or not (len(treatment) == len(wrong) == len(shuffled)):
        raise ValueError("B requires equal non-empty treatment and control vectors")
    controls = {"wrong_class": wrong, "shuffled_coupling": shuffled}
    intervention = list(raw.get("intervention_agreement", ()))
    if not intervention:
        raise ValueError("B requires intervention-agreement records")
    pooled = _mean_binary(intervention)
    separator = list(raw.get("bisimulation_separator_agreement", ()))
    separator_gate = True if not separator else _mean_binary(separator) >= 0.90
    scientific_hard = pooled >= 0.90 and separator_gate

    if "direction_labels" in raw:
        iut = analyze_direction_iut(
            treatment,
            controls,
            list(raw["direction_labels"]),
            intervention,
            pvalue_fn=exact_mcnemar_one_sided,
            effect_fn=_paired_effect,
            interval_fn=_paired_effect_interval,
        )
        effect = float(iut["minimum_component_effect"])
        return {
            "raw_pvalue": iut["raw_pvalue"],
            "component_pvalues": iut["component_pvalues"],
            "control_effects": iut["component_effects"],
            "effect_intervals": iut["component_effect_intervals"],
            "effect": effect,
            "effect_floor_pass": effect >= 0.15,
            "pooled_intervention_agreement": pooled,
            "pooled_agreement_gate": pooled >= 0.90,
            "bisimulation_separator_agreement": _mean_binary(separator) if separator else None,
            "bisimulation_separator_gate": separator_gate,
            "hard_gates_pass": _all_gates(raw.get("hard_gates")) and scientific_hard,
            "effect_direction_positive": effect > 0.0,
            "analysis_mode": "DIRECTION_STRATIFIED_IUT",
            "inferential_unit": iut["inferential_unit"],
            "direction_count": iut["direction_count"],
            "unit_count": iut["unit_count"],
            "unit_counts_by_direction": iut["unit_counts_by_direction"],
            "interventions_per_unit": iut["interventions_per_unit"],
            "intervention_evaluations": iut["intervention_evaluations"],
            "iut_rule": iut["iut_rule"],
        }

    pvalues, effects, intervals = _paired_control_summary(treatment, controls)
    return {
        "raw_pvalue": max(pvalues.values()),
        "component_pvalues": pvalues,
        "control_effects": effects,
        "effect_intervals": intervals,
        "effect": min(effects.values()),
        "effect_floor_pass": min(effects.values()) >= 0.15,
        "pooled_intervention_agreement": pooled,
        "pooled_agreement_gate": pooled >= 0.90,
        "bisimulation_separator_agreement": _mean_binary(separator) if separator else None,
        "bisimulation_separator_gate": separator_gate,
        "hard_gates_pass": _all_gates(raw.get("hard_gates")) and scientific_hard,
        "effect_direction_positive": min(effects.values()) > 0.0,
        "analysis_mode": "LEGACY_POOLED_DEV",
        "inferential_unit": "ordered_direction_world_pair",
    }


def analyze_g(raw: Mapping[str, Any]) -> dict[str, Any]:
    pairs = list(raw.get("pairs", ()))
    if not pairs:
        raise ValueError("G requires matched relevance pairs")

    has_world = ["world_id" in record for record in pairs]
    if any(has_world) and not all(has_world):
        raise ValueError("G world-blocked analysis requires world_id on every pair")

    counts: dict[int, int] = defaultdict(int)
    world_scores: dict[int, int] = {}
    observed = 0
    if all(has_world):
        grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
        for record in pairs:
            grouped[int(record["world_id"])].append(record)
        for world_id in sorted(grouped):
            records = grouped[world_id]
            if sorted(int(record["weight"]) for record in records) != [2, 5, 10, 20]:
                raise ValueError("each G world must contribute exactly four frozen nonzero doses")
            score = 0
            for record in records:
                relevant = int(bool(record["relevant"]))
                irrelevant = int(bool(record["irrelevant"]))
                score += int(record["weight"]) * (relevant - irrelevant)
            world_scores[world_id] = score
        observed = sum(world_scores.values())
        pvalue = g_world_blocked_randomization_pvalue(list(world_scores.values()), observed)
        mode = "WORLD_BLOCKED_REPEATED_MEASURES"
        randomization_unit = "world"
        inferential_unit = "world"
    else:
        for record in pairs:
            weight = int(record["weight"])
            relevant = int(bool(record["relevant"]))
            irrelevant = int(bool(record["irrelevant"]))
            delta = relevant - irrelevant
            observed += weight * delta
            if delta:
                counts[weight] += 1
        pvalue = g_exact_randomization_pvalue(counts, observed)
        mode = "LEGACY_WORLD_BY_DOSE"
        randomization_unit = "world_by_dose_pair"
        inferential_unit = "world_by_dose_pair"

    relevant_max = list(raw.get("max_dose_relevant", ()))
    irrelevant_max = list(raw.get("max_dose_irrelevant", ()))
    if not relevant_max or len(relevant_max) != len(irrelevant_max):
        raise ValueError("G requires paired maximum-dose flip vectors")
    if world_scores and len(relevant_max) != len(world_scores):
        raise ValueError("G maximum-dose vectors must have one entry per world")
    max_gap = _mean_binary(relevant_max) - _mean_binary(irrelevant_max)
    result = {
        "raw_pvalue": pvalue,
        "observed_statistic": observed,
        "max_dose_flip_gap": max_gap,
        "effect": max_gap,
        "effect_floor_pass": max_gap >= 0.15,
        "hard_gates_pass": _all_gates(raw.get("hard_gates")),
        "effect_direction_positive": observed > 0 and max_gap > 0.0,
        "analysis_mode": mode,
        "inferential_unit": inferential_unit,
        "randomization_unit": randomization_unit,
    }
    if world_scores:
        result["world_scores"] = {str(k): world_scores[k] for k in sorted(world_scores)}
        result["world_count"] = len(world_scores)
    else:
        result["discordant_weight_counts"] = dict(sorted(counts.items()))
    return result


def analyze_p(raw: Mapping[str, Any]) -> dict[str, Any]:
    retained = list(raw.get("retained", ()))
    baselines = raw.get("baselines")
    if not retained or not isinstance(baselines, Mapping) or not baselines:
        raise ValueError("P requires retained and baseline paired outcomes")
    legacy = {
        "cold",
        "equal_compute_recheck",
        "verbal_rule_negative",
        "size_matched_sham",
        "wrong_class_object",
    }
    strengthened = legacy | {"target_only_bisimulation"}
    if set(baselines) not in (legacy, strengthened):
        raise ValueError("P baseline set does not match preregistration")

    component_pvalues: dict[str, float] = {}
    effects: dict[str, float] = {}
    intervals: dict[str, tuple[float, float]] = {}
    for name in sorted(baselines):
        control = list(baselines[name])
        if len(control) != len(retained):
            raise ValueError("P baseline vectors must be paired with retained outcomes")
        component_pvalues[name] = exact_mcnemar_one_sided(zip(control, retained))
        effects[name] = _paired_effect(control, retained)
        intervals[name] = _paired_effect_interval(control, retained)

    strongest_name = max(baselines, key=lambda name: _mean_binary(list(baselines[name])))
    cold_accuracy = float(raw.get("cold_accuracy", _mean_binary(list(baselines["cold"]))))
    deletion_accuracy = float(raw.get("post_deletion_accuracy", 0.0))
    reacquisition = int(raw.get("reacquisition_search_count", 0))
    procedure_entries = int(raw.get("reacquisition_procedure_entries", reacquisition > 0))
    untracked = int(raw.get("untracked_regeneration_count", 0))
    deletion_gate = abs(deletion_accuracy - cold_accuracy) <= 0.02 and reacquisition > 0
    reacquisition_gate = reacquisition > 0 and procedure_entries > 0 and untracked == 0

    supplied_gates = dict(raw.get("hard_gates", {}))
    supplied_gates["computed_targeted_deletion"] = deletion_gate
    supplied_gates["computed_reacquisition_tracking"] = reacquisition_gate
    effect = min(effects.values())
    return {
        "raw_pvalue": max(component_pvalues.values()),
        "component_pvalues": component_pvalues,
        "control_effects": effects,
        "effect_intervals": intervals,
        "strongest_baseline": strongest_name,
        "effect": effect,
        "effect_floor_pass": effect >= 0.05,
        "targeted_deletion_gate": deletion_gate,
        "reacquisition_gate": reacquisition_gate,
        "hard_gates_pass": _all_gates(supplied_gates),
        "effect_direction_positive": effect > 0.0,
        "inferential_unit": "source_distinct_future_task",
        "analysis_mode": (
            "BISIMULATION_CONTROLLED_HARD_RESTART"
            if set(baselines) == strengthened
            else "LEGACY_HARD_RESTART"
        ),
    }


def _finalize_verdict(analysis: dict[str, Any], adjusted_pvalue: float, alpha: float) -> dict[str, Any]:
    result = dict(analysis)
    result["holm_adjusted_pvalue"] = adjusted_pvalue
    result["holm_significance_pass"] = adjusted_pvalue <= alpha
    if not result["hard_gates_pass"] or not result["effect_direction_positive"]:
        verdict = "FAIL"
    elif result["effect_floor_pass"] and result["holm_significance_pass"]:
        verdict = "PASS"
    else:
        verdict = "PARTIAL"
    result["verdict"] = verdict
    return result


def _canonical_json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True))


def analyze_matrix(raw_matrix: Mapping[str, Any]) -> dict[str, Any]:
    if set(raw_matrix) != set(_ARM_ORDER):
        raise ValueError("raw ABGP matrix must contain exactly A, B, G, P")
    plan = load_analysis_plan(_ANALYSIS_PATH)
    analyses = {
        "A": analyze_a(raw_matrix["A"]),
        "B": analyze_b(raw_matrix["B"]),
        "G": analyze_g(raw_matrix["G"]),
        "P": analyze_p(raw_matrix["P"]),
    }
    raw_pvalues = {arm: float(analyses[arm]["raw_pvalue"]) for arm in _ARM_ORDER}
    holm = holm_bonferroni(raw_pvalues, plan.familywise_alpha)
    finalized = {
        arm: _finalize_verdict(
            analyses[arm], holm["adjusted_pvalues"][arm], plan.familywise_alpha
        )
        for arm in _ARM_ORDER
    }
    combined = (
        "PASS"
        if all(finalized[arm]["verdict"] == "PASS" for arm in _ARM_ORDER)
        else "NOT_FULL_PASS"
    )
    return _canonical_json_value(
        {
            "analysis_plan_digest": plan.digest,
            "raw_pvalues": raw_pvalues,
            "holm": holm,
            "arms": finalized,
            "combined_verdict": combined,
        }
    )
