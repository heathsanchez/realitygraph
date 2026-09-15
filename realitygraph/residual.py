from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from .predictive import (
    CandidateTrial,
    PredictiveMetrics,
    ProbeField,
    ThresholdRule,
    binary_auc,
    binary_log_loss,
)


@dataclass(frozen=True)
class CompiledResidualModel:
    rules: tuple[ThresholdRule, ...]
    corrections: tuple[tuple[tuple[int, ...], float, int], ...]
    min_support: int = 1

    def predict_values(self, row: Sequence[float], baseline_probability: float) -> float:
        baseline = _clip_probability(baseline_probability)
        if not self.rules:
            return baseline
        signature = tuple(rule.observe(row) for rule in self.rules)
        table = {key: (delta, support) for key, delta, support in self.corrections}
        item = table.get(signature)
        if item is None or item[1] < self.min_support:
            return baseline
        return _sigmoid(_logit(baseline) + item[0])


@dataclass(frozen=True)
class ResidualPlan:
    rules: tuple[ThresholdRule, ...]
    calibration_progress: tuple[float, ...]
    alternatives: tuple[tuple[CandidateTrial, ...], ...]
    calibration_metrics: PredictiveMetrics
    ablation_log_loss_delta: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class ResidualCertificate:
    plan: ResidualPlan
    model: CompiledResidualModel
    sealed_baseline_metrics: PredictiveMetrics
    sealed_metrics: PredictiveMetrics
    accepted: bool


def _clip_probability(value: float) -> float:
    return min(max(float(value), 1e-6), 1.0 - 1e-6)


def _logit(value: float) -> float:
    p = _clip_probability(value)
    return math.log(p / (1.0 - p))


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _candidate_thresholds(values: Sequence[float], max_thresholds: int) -> tuple[float, ...]:
    unique = sorted(set(values))
    if len(unique) <= 1:
        return ()
    mids = [(a + b) / 2.0 for a, b in zip(unique, unique[1:])]
    if len(mids) <= max_thresholds:
        return tuple(mids)
    if max_thresholds <= 1:
        return (mids[len(mids) // 2],)
    chosen = []
    for i in range(max_thresholds):
        j = round(i * (len(mids) - 1) / (max_thresholds - 1))
        chosen.append(mids[j])
    return tuple(dict.fromkeys(chosen))


def _fit_delta(
    labels: Sequence[int],
    baseline_probabilities: Sequence[float],
    ridge: float,
) -> float:
    if not labels:
        return 0.0
    delta = 0.0
    offsets = [_logit(p) for p in baseline_probabilities]
    for _ in range(32):
        gradient = ridge * delta
        hessian = ridge
        for label, offset in zip(labels, offsets):
            probability = _sigmoid(offset + delta)
            gradient += probability - label
            hessian += probability * (1.0 - probability)
        if hessian <= 1e-12:
            break
        step = gradient / hessian
        delta -= step
        if abs(step) < 1e-8:
            break
    return max(min(delta, 6.0), -6.0)


def compile_residual_model(
    field: ProbeField,
    rules: Sequence[ThresholdRule],
    fit_indices: Sequence[int],
    baseline_probabilities: Sequence[float],
    *,
    min_support: int = 1,
    ridge: float = 4.0,
) -> CompiledResidualModel:
    if len(baseline_probabilities) != len(field.values):
        raise ValueError("baseline probability count must equal field rows")
    if not rules:
        return CompiledResidualModel((), (), min_support=min_support)

    groups: dict[tuple[int, ...], list[int]] = defaultdict(list)
    for i in fit_indices:
        signature = tuple(rule.observe(field.values[i]) for rule in rules)
        groups[signature].append(i)

    corrections = []
    for signature, members in sorted(groups.items()):
        delta = _fit_delta(
            [field.labels[i] for i in members],
            [baseline_probabilities[i] for i in members],
            ridge,
        )
        corrections.append((signature, delta, len(members)))
    return CompiledResidualModel(tuple(rules), tuple(corrections), min_support=min_support)


def _predict_indices(
    field: ProbeField,
    model: CompiledResidualModel,
    indices: Sequence[int],
    baseline_probabilities: Sequence[float],
) -> list[float]:
    return [
        model.predict_values(field.values[i], baseline_probabilities[i])
        for i in indices
    ]


def _metrics_from_probabilities(
    field: ProbeField,
    indices: Sequence[int],
    probabilities: Sequence[float],
    baseline_probabilities: Sequence[float],
) -> PredictiveMetrics:
    labels = [field.labels[i] for i in indices]
    groups: dict[object, list[int]] = defaultdict(list)
    for local, i in enumerate(indices):
        groups[field.groups[i]].append(local)

    worst = 0.0
    max_harm = 0.0
    for local_members in groups.values():
        local_labels = [labels[j] for j in local_members]
        local_probs = [probabilities[j] for j in local_members]
        local_base = [baseline_probabilities[indices[j]] for j in local_members]
        loss = binary_log_loss(local_labels, local_probs)
        base_loss = binary_log_loss(local_labels, local_base)
        worst = max(worst, loss)
        max_harm = max(max_harm, loss - base_loss)

    return PredictiveMetrics(
        binary_log_loss(labels, probabilities),
        binary_auc(labels, probabilities),
        worst,
        max_harm,
        len(indices),
        len(indices),
    )


def baseline_metrics(
    field: ProbeField,
    indices: Sequence[int],
    baseline_probabilities: Sequence[float],
) -> PredictiveMetrics:
    probabilities = [baseline_probabilities[i] for i in indices]
    return _metrics_from_probabilities(
        field,
        indices,
        probabilities,
        baseline_probabilities,
    )


def evaluate_residual_model(
    field: ProbeField,
    model: CompiledResidualModel,
    indices: Sequence[int],
    baseline_probabilities: Sequence[float],
) -> PredictiveMetrics:
    probabilities = _predict_indices(
        field,
        model,
        indices,
        baseline_probabilities,
    )
    return _metrics_from_probabilities(
        field,
        indices,
        probabilities,
        baseline_probabilities,
    )


def _fit_residual_rule(
    field: ProbeField,
    probe_index: int,
    train: Sequence[int],
    baseline_probabilities: Sequence[float],
    *,
    max_thresholds: int,
    min_support: int,
    ridge: float,
) -> ThresholdRule | None:
    values = [field.values[i][probe_index] for i in train]
    best = None
    for threshold in _candidate_thresholds(values, max_thresholds):
        rule = ThresholdRule(
            probe_index,
            field.probe_names[probe_index],
            threshold,
        )
        model = compile_residual_model(
            field,
            (rule,),
            train,
            baseline_probabilities,
            min_support=min_support,
            ridge=ridge,
        )
        metrics = evaluate_residual_model(
            field,
            model,
            train,
            baseline_probabilities,
        )
        key = (metrics.log_loss, -metrics.auc)
        if best is None or key < best[0]:
            best = (key, rule)
    return None if best is None else best[1]


def design_residual_batch(
    field: ProbeField,
    train: Sequence[int],
    calibration: Sequence[int],
    baseline_probabilities: Sequence[float],
    *,
    max_probes: int = 6,
    max_thresholds: int = 31,
    min_calibration_gain: float = 1e-4,
    max_group_harm: float | None = None,
    alternatives_per_round: int = 5,
    deletion_tolerance: float = 1e-6,
    min_support: int = 4,
    ridge: float = 4.0,
) -> ResidualPlan:
    if not train or not calibration:
        raise ValueError("train and calibration partitions must be non-empty")
    if len(baseline_probabilities) != len(field.values):
        raise ValueError("baseline probability count must equal field rows")

    fitted = {}
    for j in range(len(field.probe_names)):
        rule = _fit_residual_rule(
            field,
            j,
            train,
            baseline_probabilities,
            max_thresholds=max_thresholds,
            min_support=min_support,
            ridge=ridge,
        )
        if rule is not None:
            fitted[j] = rule

    selected: list[ThresholdRule] = []
    remaining = set(fitted)
    progress = []
    alternatives = []
    base_metrics = baseline_metrics(field, calibration, baseline_probabilities)
    current_loss = base_metrics.log_loss

    while remaining and len(selected) < max_probes:
        trials = []
        for j in sorted(remaining):
            rules = selected + [fitted[j]]
            model = compile_residual_model(
                field,
                rules,
                train,
                baseline_probabilities,
                min_support=min_support,
                ridge=ridge,
            )
            metrics = evaluate_residual_model(
                field,
                model,
                calibration,
                baseline_probabilities,
            )
            trials.append((metrics.log_loss, metrics.max_group_harm, -metrics.auc, j, metrics))

        trials.sort()
        alternatives.append(tuple(
            CandidateTrial(
                fitted[j].probe_name,
                metrics.log_loss,
                metrics.auc,
                metrics.worst_group_log_loss,
                metrics.max_group_harm,
            )
            for _, _, _, j, metrics in trials[:alternatives_per_round]
        ))

        best_loss, _, _, best_j, best_metrics = trials[0]
        if current_loss - best_loss < min_calibration_gain:
            break
        if max_group_harm is not None and best_metrics.max_group_harm > max_group_harm:
            break

        selected.append(fitted[best_j])
        remaining.remove(best_j)
        current_loss = best_loss
        progress.append(best_loss)

    # Delete every distinction that does not still earn its place.
    changed = True
    while changed and selected:
        changed = False
        full = compile_residual_model(
            field,
            selected,
            train,
            baseline_probabilities,
            min_support=min_support,
            ridge=ridge,
        )
        full_metrics = evaluate_residual_model(
            field,
            full,
            calibration,
            baseline_probabilities,
        )
        for rule in tuple(reversed(selected)):
            trial_rules = [candidate for candidate in selected if candidate != rule]
            trial = compile_residual_model(
                field,
                trial_rules,
                train,
                baseline_probabilities,
                min_support=min_support,
                ridge=ridge,
            )
            trial_metrics = evaluate_residual_model(
                field,
                trial,
                calibration,
                baseline_probabilities,
            )
            no_worse = trial_metrics.log_loss <= full_metrics.log_loss + deletion_tolerance
            harm_ok = max_group_harm is None or trial_metrics.max_group_harm <= max_group_harm
            if no_worse and harm_ok:
                selected = trial_rules
                changed = True
                break

    final_model = compile_residual_model(
        field,
        selected,
        train,
        baseline_probabilities,
        min_support=min_support,
        ridge=ridge,
    )
    final_metrics = evaluate_residual_model(
        field,
        final_model,
        calibration,
        baseline_probabilities,
    )

    ablation = []
    for rule in selected:
        trial_rules = [candidate for candidate in selected if candidate != rule]
        trial = compile_residual_model(
            field,
            trial_rules,
            train,
            baseline_probabilities,
            min_support=min_support,
            ridge=ridge,
        )
        trial_metrics = evaluate_residual_model(
            field,
            trial,
            calibration,
            baseline_probabilities,
        )
        ablation.append((rule.probe_name, trial_metrics.log_loss - final_metrics.log_loss))

    return ResidualPlan(
        tuple(selected),
        tuple(progress),
        tuple(alternatives),
        final_metrics,
        tuple(ablation),
    )


def certify_residual_batch(
    field: ProbeField,
    split,
    baseline_probabilities: Sequence[float],
    *,
    max_probes: int = 6,
    max_thresholds: int = 31,
    min_calibration_gain: float = 1e-4,
    min_sealed_gain: float = 0.0,
    max_group_harm: float | None = None,
    min_support: int = 4,
    ridge: float = 4.0,
) -> ResidualCertificate:
    plan = design_residual_batch(
        field,
        split.train,
        split.calibration,
        baseline_probabilities,
        max_probes=max_probes,
        max_thresholds=max_thresholds,
        min_calibration_gain=min_calibration_gain,
        max_group_harm=max_group_harm,
        min_support=min_support,
        ridge=ridge,
    )
    fit = tuple(split.train) + tuple(split.calibration)
    model = compile_residual_model(
        field,
        plan.rules,
        fit,
        baseline_probabilities,
        min_support=min_support,
        ridge=ridge,
    )
    base = baseline_metrics(field, split.test, baseline_probabilities)
    sealed = evaluate_residual_model(
        field,
        model,
        split.test,
        baseline_probabilities,
    )
    accepted = sealed.log_loss <= base.log_loss - min_sealed_gain
    if max_group_harm is not None:
        accepted = accepted and sealed.max_group_harm <= max_group_harm
    return ResidualCertificate(plan, model, base, sealed, accepted)
