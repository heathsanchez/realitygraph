from __future__ import annotations

from collections import defaultdict
import json
from math import comb, sqrt
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .manifest import load_analysis_plan
from .validity import validate_arm_input


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
    """Exact one-sided sign-randomization p-value for G's weighted statistic."""

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


def _validity_fields(arm: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    issues = validate_arm_input(arm, raw)
    return {
        "validity_pass": not issues,
        "validity_reason_codes": [issue.code for issue in issues],
        "validity_issues": [
            {"code": issue.code, "detail": issue.detail} for issue in issues
        ],
    }


def analyze_a(raw: Mapping[str, Any]) -> dict[str, Any]:
    pairs = [tuple(pair) for pair in raw.get("pairs", ())]
    if not pairs:
        raise ValueError("A requires paired outcomes")
    control = [pair[0] for pair in pairs]
    treatment = [pair[1] for pair in pairs]
    effect = _paired_effect(control, treatment)
    validity = _validity_fields("A", raw)
    return {
        "raw_pvalue": exact_mcnemar_one_sided(pairs),
        "effect": effect,
        "effect_interval": _paired_effect_interval(control, treatment),
        "effect_floor_pass": effect >= 0.05,
        "hard_gates_pass": validity["validity_pass"],
        "scientific_hard_gates_pass": True,
        "effect_direction_positive": effect > 0.0,
        **validity,
    }


def analyze_b(raw: Mapping[str, Any]) -> dict[str, Any]:
    treatment = list(raw.get("treatment", ()))
    wrong = list(raw.get("wrong_class", ()))
    shuffled = list(raw.get("shuffled_coupling", ()))
    if not treatment or not (len(treatment) == len(wrong) == len(shuffled)):
        raise ValueError("B requires equal non-empty treatment and control vectors")
    controls = {"wrong_class": wrong, "shuffled_coupling": shuffled}
    pvalues = {
        name: exact_mcnemar_one_sided(zip(control, treatment))
        for name, control in controls.items()
    }
    effects = {name: _paired_effect(control, treatment) for name, control in controls.items()}
    intervention = list(raw.get("intervention_agreement", ()))
    if not intervention:
        raise ValueError("B requires pooled intervention-agreement records")
    pooled = _mean_binary(intervention)
    validity = _validity_fields("B", raw)
    scientific_hard = pooled >= 0.90
    return {
        "raw_pvalue": max(pvalues.values()),
        "component_pvalues": pvalues,
        "control_effects": effects,
        "effect": min(effects.values()),
        "effect_floor_pass": min(effects.values()) >= 0.15,
        "pooled_intervention_agreement": pooled,
        "pooled_agreement_gate": scientific_hard,
        "hard_gates_pass": validity["validity_pass"] and scientific_hard,
        "scientific_hard_gates_pass": scientific_hard,
        "effect_direction_positive": min(effects.values()) > 0.0,
        **validity,
    }


def analyze_g(raw: Mapping[str, Any]) -> dict[str, Any]:
    pairs = list(raw.get("pairs", ()))
    if not pairs:
        raise ValueError("G requires matched relevance pairs")
    counts: dict[int, int] = defaultdict(int)
    observed = 0
    for record in pairs:
        weight = int(record["weight"])
        relevant = int(bool(record["relevant"]))
        irrelevant = int(bool(record["irrelevant"]))
        delta = relevant - irrelevant
        observed += weight * delta
        if delta:
            counts[weight] += 1
    relevant_max = list(raw.get("max_dose_relevant", ()))
    irrelevant_max = list(raw.get("max_dose_irrelevant", ()))
    if not relevant_max or len(relevant_max) != len(irrelevant_max):
        raise ValueError("G requires paired maximum-dose flip vectors")
    max_gap = _mean_binary(relevant_max) - _mean_binary(irrelevant_max)
    validity = _validity_fields("G", raw)
    return {
        "raw_pvalue": g_exact_randomization_pvalue(counts, observed),
        "observed_statistic": observed,
        "discordant_weight_counts": dict(sorted(counts.items())),
        "max_dose_flip_gap": max_gap,
        "effect": max_gap,
        "effect_floor_pass": max_gap >= 0.15,
        "hard_gates_pass": validity["validity_pass"],
        "scientific_hard_gates_pass": True,
        "effect_direction_positive": observed > 0 and max_gap > 0.0,
        **validity,
    }


def analyze_p(raw: Mapping[str, Any]) -> dict[str, Any]:
    retained = list(raw.get("retained", ()))
    baselines = raw.get("baselines")
    if not retained or not isinstance(baselines, Mapping) or not baselines:
        raise ValueError("P requires retained and baseline paired outcomes")
    expected = {
        "cold",
        "equal_compute_recheck",
        "verbal_rule_negative",
        "size_matched_sham",
        "wrong_class_object",
    }
    if set(baselines) != expected:
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
    deletion_gate = abs(deletion_accuracy - cold_accuracy) <= 0.02 and reacquisition > 0
    validity = _validity_fields("P", raw)
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
        "hard_gates_pass": validity["validity_pass"] and deletion_gate,
        "scientific_hard_gates_pass": deletion_gate,
        "effect_direction_positive": effect > 0.0,
        **validity,
    }


def _finalize_verdict(analysis: dict[str, Any], adjusted_pvalue: float, alpha: float) -> dict[str, Any]:
    result = dict(analysis)
    result["holm_adjusted_pvalue"] = adjusted_pvalue
    result["holm_significance_pass"] = adjusted_pvalue <= alpha
    if result.get("validity_reason_codes"):
        verdict = "INVALID"
    elif not result.get("scientific_hard_gates_pass", True) or not result["effect_direction_positive"]:
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
            analyses[arm],
            holm["adjusted_pvalues"][arm],
            plan.familywise_alpha,
        )
        for arm in _ARM_ORDER
    }
    if any(finalized[arm]["verdict"] == "INVALID" for arm in _ARM_ORDER):
        combined = "INVALID"
    elif all(finalized[arm]["verdict"] == "PASS" for arm in _ARM_ORDER):
        combined = "PASS"
    else:
        combined = "NOT_FULL_PASS"
    return _canonical_json_value(
        {
            "analysis_plan_digest": plan.digest,
            "raw_pvalues": raw_pvalues,
            "holm": holm,
            "arms": finalized,
            "combined_verdict": combined,
        }
    )
