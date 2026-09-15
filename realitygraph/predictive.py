from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Hashable, Sequence


Label = int
Group = Hashable
Probe = Callable[[object], float]


@dataclass(frozen=True)
class ProbeField:
    probe_names: tuple[str, ...]
    values: tuple[tuple[float, ...], ...]
    labels: tuple[Label, ...]
    groups: tuple[Group, ...]
    design_predictions: int

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("probe field requires at least one row")
        width = len(self.probe_names)
        if width == 0:
            raise ValueError("probe field requires at least one probe")
        if len(self.labels) != len(self.values) or len(self.groups) != len(self.values):
            raise ValueError("values, labels, and groups must have equal length")
        if any(len(row) != width for row in self.values):
            raise ValueError("probe field rows must have constant width")
        if any(label not in {0, 1} for label in self.labels):
            raise ValueError("predictive field currently supports binary labels only")
        if any(not math.isfinite(value) for row in self.values for value in row):
            raise ValueError("probe field contains non-finite values")


@dataclass(frozen=True)
class ThresholdRule:
    probe_index: int
    probe_name: str
    threshold: float

    def observe(self, row: Sequence[float]) -> int:
        return 1 if row[self.probe_index] >= self.threshold else 0


@dataclass(frozen=True)
class PredictiveMetrics:
    log_loss: float
    auc: float
    worst_group_log_loss: float
    max_group_harm: float
    covered: int
    total: int


@dataclass(frozen=True)
class CandidateTrial:
    probe_name: str
    log_loss: float
    auc: float
    worst_group_log_loss: float
    max_group_harm: float


@dataclass(frozen=True)
class PredictivePlan:
    rules: tuple[ThresholdRule, ...]
    calibration_progress: tuple[float, ...]
    alternatives: tuple[tuple[CandidateTrial, ...], ...]
    calibration_metrics: PredictiveMetrics
    ablation_log_loss_delta: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class CompiledPredictiveModel:
    rules: tuple[ThresholdRule, ...]
    decoder: tuple[tuple[tuple[int, ...], float, int], ...]
    fallback_probability: float
    min_support: int = 1

    def predict_values(
        self,
        row: Sequence[float],
        fallback_probability: float | None = None,
    ) -> float:
        signature = tuple(rule.observe(row) for rule in self.rules)
        table = {key: (probability, support) for key, probability, support in self.decoder}
        item = table.get(signature)
        if item is None or item[1] < self.min_support:
            if fallback_probability is not None:
                return _clip_probability(fallback_probability)
            return self.fallback_probability
        return item[0]


@dataclass(frozen=True)
class PredictiveCertificate:
    plan: PredictivePlan
    model: CompiledPredictiveModel
    sealed_baseline_metrics: PredictiveMetrics
    sealed_metrics: PredictiveMetrics
    accepted: bool
    split_digest: str


@dataclass(frozen=True)
class PredictiveSplit:
    train: tuple[int, ...]
    calibration: tuple[int, ...]
    test: tuple[int, ...]
    seed_digest: str


def build_probe_field(
    states: Sequence[object],
    labels: Sequence[Label],
    groups: Sequence[Group],
    probes: Sequence[tuple[str, Probe]],
) -> ProbeField:
    if len(states) != len(labels) or len(states) != len(groups):
        raise ValueError("states, labels, and groups must have equal length")
    if not probes:
        raise ValueError("at least one probe is required")

    names = tuple(name for name, _ in probes)
    rows = []
    for state in states:
        row = tuple(float(probe(state)) for _, probe in probes)
        rows.append(row)
    return ProbeField(
        names,
        tuple(rows),
        tuple(int(label) for label in labels),
        tuple(groups),
        len(states) * len(probes),
    )


def field_from_matrix(
    probe_names: Sequence[str],
    values: Sequence[Sequence[float]],
    labels: Sequence[Label],
    groups: Sequence[Group],
) -> ProbeField:
    rows = tuple(tuple(float(value) for value in row) for row in values)
    return ProbeField(
        tuple(probe_names),
        rows,
        tuple(int(label) for label in labels),
        tuple(groups),
        len(rows) * len(probe_names),
    )


def sealed_group_split(
    groups: Sequence[Group],
    seed: str,
    train_fraction: float = 0.60,
    calibration_fraction: float = 0.20,
) -> PredictiveSplit:
    if not 0 < train_fraction < 1:
        raise ValueError("invalid train fraction")
    if not 0 < calibration_fraction < 1:
        raise ValueError("invalid calibration fraction")
    if train_fraction + calibration_fraction >= 1:
        raise ValueError("split leaves no test groups")

    unique = sorted(set(groups), key=lambda item: repr(item))
    if len(unique) < 3:
        raise ValueError("sealed group split requires at least three groups")

    def key(group: Group) -> bytes:
        return hashlib.sha256(f"{seed}|{group!r}".encode()).digest()

    ordered = sorted(unique, key=key)
    n = len(ordered)
    n_train = max(1, int(n * train_fraction))
    n_cal = max(1, int(n * calibration_fraction))
    if n_train + n_cal >= n:
        n_cal = max(1, n - n_train - 1)

    train_groups = set(ordered[:n_train])
    cal_groups = set(ordered[n_train : n_train + n_cal])
    test_groups = set(ordered[n_train + n_cal :])

    train = tuple(i for i, group in enumerate(groups) if group in train_groups)
    calibration = tuple(i for i, group in enumerate(groups) if group in cal_groups)
    test = tuple(i for i, group in enumerate(groups) if group in test_groups)
    if not train or not calibration or not test:
        raise ValueError("sealed split produced an empty partition")
    return PredictiveSplit(
        train,
        calibration,
        test,
        hashlib.sha256(seed.encode()).hexdigest()[:16],
    )


def leave_one_group_out_split(
    groups: Sequence[Group],
    held_out_group: Group,
    seed: str,
    calibration_fraction: float = 0.25,
) -> PredictiveSplit:
    """Seal exactly one natural group and partition every other group upstream.

    Unlike repeated random group splits, this makes group coverage exhaustive:
    every requested held-out person/site/day is the entire test partition.
    """
    if not 0 < calibration_fraction < 1:
        raise ValueError("invalid calibration fraction")

    unique = sorted(set(groups), key=lambda item: repr(item))
    if held_out_group not in unique:
        raise ValueError("held-out group is absent")
    remaining = [group for group in unique if group != held_out_group]
    if len(remaining) < 2:
        raise ValueError("leave-one-group-out requires at least three groups")

    def key(group: Group) -> bytes:
        return hashlib.sha256(
            f"{seed}|calibration|{group!r}".encode()
        ).digest()

    ordered = sorted(remaining, key=key)
    n_cal = max(1, int(round(len(ordered) * calibration_fraction)))
    if n_cal >= len(ordered):
        n_cal = len(ordered) - 1

    calibration_groups = set(ordered[:n_cal])
    train_groups = set(ordered[n_cal:])
    test_groups = {held_out_group}

    train = tuple(i for i, group in enumerate(groups) if group in train_groups)
    calibration = tuple(
        i for i, group in enumerate(groups) if group in calibration_groups
    )
    test = tuple(i for i, group in enumerate(groups) if group in test_groups)

    if not train or not calibration or not test:
        raise ValueError("leave-one-group-out produced an empty partition")
    return PredictiveSplit(
        train,
        calibration,
        test,
        hashlib.sha256(
            f"{seed}|held-out|{held_out_group!r}".encode()
        ).hexdigest()[:16],
    )


def _clip_probability(value: float) -> float:
    return min(max(float(value), 1e-6), 1.0 - 1e-6)


def binary_log_loss(labels: Sequence[Label], probabilities: Sequence[float]) -> float:
    if len(labels) != len(probabilities):
        raise ValueError("labels and probabilities must have equal length")
    if not labels:
        raise ValueError("cannot score an empty set")
    total = 0.0
    for label, probability in zip(labels, probabilities):
        p = _clip_probability(probability)
        total -= math.log(p if label else 1.0 - p)
    return total / len(labels)


def binary_auc(labels: Sequence[Label], scores: Sequence[float]) -> float:
    """Exact tie-aware ROC AUC in O(n log n).

    Counts positive/negative pair wins by score blocks instead of comparing
    every positive to every negative.
    """
    if len(labels) != len(scores):
        raise ValueError("labels and scores must have equal length")
    pairs = sorted(zip(scores, labels), key=lambda item: item[0])
    positives = sum(1 for _, label in pairs if label == 1)
    negatives = len(pairs) - positives
    if positives == 0 or negatives == 0:
        return 0.5

    wins = 0.0
    negatives_below = 0
    i = 0
    while i < len(pairs):
        score = pairs[i][0]
        block_pos = 0
        block_neg = 0
        j = i
        while j < len(pairs) and pairs[j][0] == score:
            if pairs[j][1] == 1:
                block_pos += 1
            else:
                block_neg += 1
            j += 1

        wins += block_pos * negatives_below
        wins += 0.5 * block_pos * block_neg
        negatives_below += block_neg
        i = j

    return wins / (positives * negatives)


def _candidate_thresholds(values: Sequence[float], max_thresholds: int) -> tuple[float, ...]:
    unique = sorted(set(values))
    if len(unique) <= 1:
        return ()
    mids = [(a + b) / 2.0 for a, b in zip(unique, unique[1:])]
    if len(mids) <= max_thresholds:
        return tuple(mids)
    chosen = []
    for i in range(max_thresholds):
        j = round(i * (len(mids) - 1) / (max_thresholds - 1))
        chosen.append(mids[j])
    return tuple(dict.fromkeys(chosen))


def _fit_rule(
    field: ProbeField,
    probe_index: int,
    train: Sequence[int],
    max_thresholds: int,
) -> ThresholdRule | None:
    values = [field.values[i][probe_index] for i in train]
    labels = [field.labels[i] for i in train]
    best_threshold = None
    best_loss = None

    for threshold in _candidate_thresholds(values, max_thresholds):
        left = [label for value, label in zip(values, labels) if value < threshold]
        right = [label for value, label in zip(values, labels) if value >= threshold]
        if not left or not right:
            continue
        lp = (sum(left) + 1.0) / (len(left) + 2.0)
        rp = (sum(right) + 1.0) / (len(right) + 2.0)
        probs = [rp if value >= threshold else lp for value in values]
        loss = binary_log_loss(labels, probs)
        if best_loss is None or loss < best_loss:
            best_loss = loss
            best_threshold = threshold

    if best_threshold is None:
        return None
    return ThresholdRule(probe_index, field.probe_names[probe_index], best_threshold)


def _signature(row: Sequence[float], rules: Sequence[ThresholdRule]) -> tuple[int, ...]:
    return tuple(rule.observe(row) for rule in rules)


def compile_predictive_model(
    field: ProbeField,
    rules: Sequence[ThresholdRule],
    fit_indices: Sequence[int],
    min_support: int = 1,
) -> CompiledPredictiveModel:
    counts: dict[tuple[int, ...], list[int]] = defaultdict(lambda: [0, 0])
    positives = 0
    for i in fit_indices:
        label = field.labels[i]
        positives += label
        key = _signature(field.values[i], rules)
        counts[key][label] += 1

    decoder = []
    for key, (negative, positive) in sorted(counts.items()):
        support = negative + positive
        probability = (positive + 1.0) / (support + 2.0)
        decoder.append((key, probability, support))
    fallback = (positives + 1.0) / (len(fit_indices) + 2.0)
    return CompiledPredictiveModel(
        tuple(rules),
        tuple(decoder),
        fallback,
        min_support=min_support,
    )


def _predict_indices(
    field: ProbeField,
    model: CompiledPredictiveModel,
    indices: Sequence[int],
    fallback_probabilities: Sequence[float] | None = None,
) -> list[float]:
    out = []
    for i in indices:
        fallback = None if fallback_probabilities is None else fallback_probabilities[i]
        out.append(model.predict_values(field.values[i], fallback))
    return out


def evaluate_predictive_model(
    field: ProbeField,
    model: CompiledPredictiveModel,
    indices: Sequence[int],
    fallback_probabilities: Sequence[float] | None = None,
    baseline_probabilities: Sequence[float] | None = None,
) -> PredictiveMetrics:
    labels = [field.labels[i] for i in indices]
    probs = _predict_indices(field, model, indices, fallback_probabilities)
    group_rows: dict[Group, list[int]] = defaultdict(list)
    for i in indices:
        group_rows[field.groups[i]].append(i)

    worst = 0.0
    max_harm = 0.0
    for members in group_rows.values():
        local_labels = [field.labels[i] for i in members]
        local_probs = _predict_indices(field, model, members, fallback_probabilities)
        local_loss = binary_log_loss(local_labels, local_probs)
        worst = max(worst, local_loss)
        if baseline_probabilities is not None:
            base = [baseline_probabilities[i] for i in members]
            max_harm = max(max_harm, local_loss - binary_log_loss(local_labels, base))

    return PredictiveMetrics(
        binary_log_loss(labels, probs),
        binary_auc(labels, probs),
        worst,
        max_harm,
        len(indices),
        len(indices),
    )


def _baseline_metrics(
    field: ProbeField,
    train: Sequence[int],
    indices: Sequence[int],
    baseline_probabilities: Sequence[float] | None,
) -> PredictiveMetrics:
    if baseline_probabilities is not None:
        labels = [field.labels[i] for i in indices]
        probs = [baseline_probabilities[i] for i in indices]
        worst = 0.0
        groups: dict[Group, list[int]] = defaultdict(list)
        for i in indices:
            groups[field.groups[i]].append(i)
        for members in groups.values():
            worst = max(
                worst,
                binary_log_loss(
                    [field.labels[i] for i in members],
                    [baseline_probabilities[i] for i in members],
                ),
            )
        return PredictiveMetrics(
            binary_log_loss(labels, probs),
            binary_auc(labels, probs),
            worst,
            0.0,
            len(indices),
            len(indices),
        )
    model = compile_predictive_model(field, (), train)
    return evaluate_predictive_model(field, model, indices)


def design_predictive_batch(
    field: ProbeField,
    train: Sequence[int],
    calibration: Sequence[int],
    *,
    baseline_probabilities: Sequence[float] | None = None,
    max_probes: int = 8,
    max_thresholds: int = 63,
    min_calibration_gain: float = 1e-4,
    max_group_harm: float | None = None,
    alternatives_per_round: int = 5,
    deletion_tolerance: float = 1e-6,
    min_support: int = 1,
) -> PredictivePlan:
    if not train or not calibration:
        raise ValueError("train and calibration partitions must be non-empty")
    if max_probes <= 0:
        raise ValueError("max_probes must be positive")

    fitted = {
        j: _fit_rule(field, j, train, max_thresholds)
        for j in range(len(field.probe_names))
    }
    fitted = {j: rule for j, rule in fitted.items() if rule is not None}

    selected: list[ThresholdRule] = []
    remaining = set(fitted)
    progress = []
    alternatives = []
    baseline = _baseline_metrics(field, train, calibration, baseline_probabilities)
    current_loss = baseline.log_loss

    while remaining and len(selected) < max_probes:
        trials = []
        for j in sorted(remaining):
            rules = selected + [fitted[j]]
            model = compile_predictive_model(field, rules, train, min_support=min_support)
            metrics = evaluate_predictive_model(
                field,
                model,
                calibration,
                fallback_probabilities=baseline_probabilities,
                baseline_probabilities=baseline_probabilities,
            )
            trials.append((metrics.log_loss, metrics.max_group_harm, -metrics.auc, j, metrics))

        trials.sort()
        round_alternatives = tuple(
            CandidateTrial(
                fitted[j].probe_name,
                metrics.log_loss,
                metrics.auc,
                metrics.worst_group_log_loss,
                metrics.max_group_harm,
            )
            for _, _, _, j, metrics in trials[:alternatives_per_round]
        )
        alternatives.append(round_alternatives)

        best_loss, _, _, best_j, best_metrics = trials[0]
        if current_loss - best_loss < min_calibration_gain:
            break
        if max_group_harm is not None and best_metrics.max_group_harm > max_group_harm:
            break

        selected.append(fitted[best_j])
        remaining.remove(best_j)
        current_loss = best_loss
        progress.append(best_loss)

    # Backward-delete anything that no longer earns its place on calibration.
    changed = True
    while changed and selected:
        changed = False
        full_model = compile_predictive_model(field, selected, train, min_support=min_support)
        full_metrics = evaluate_predictive_model(
            field,
            full_model,
            calibration,
            fallback_probabilities=baseline_probabilities,
            baseline_probabilities=baseline_probabilities,
        )
        for rule in tuple(reversed(selected)):
            trial = [candidate for candidate in selected if candidate != rule]
            trial_model = compile_predictive_model(field, trial, train, min_support=min_support)
            trial_metrics = evaluate_predictive_model(
                field,
                trial_model,
                calibration,
                fallback_probabilities=baseline_probabilities,
                baseline_probabilities=baseline_probabilities,
            )
            no_worse = trial_metrics.log_loss <= full_metrics.log_loss + deletion_tolerance
            harm_ok = max_group_harm is None or trial_metrics.max_group_harm <= max_group_harm
            if no_worse and harm_ok:
                selected = trial
                changed = True
                break

    final_model = compile_predictive_model(field, selected, train, min_support=min_support)
    final_metrics = evaluate_predictive_model(
        field,
        final_model,
        calibration,
        fallback_probabilities=baseline_probabilities,
        baseline_probabilities=baseline_probabilities,
    )

    ablation = []
    for rule in selected:
        trial = [candidate for candidate in selected if candidate != rule]
        trial_model = compile_predictive_model(field, trial, train, min_support=min_support)
        trial_metrics = evaluate_predictive_model(
            field,
            trial_model,
            calibration,
            fallback_probabilities=baseline_probabilities,
            baseline_probabilities=baseline_probabilities,
        )
        ablation.append((rule.probe_name, trial_metrics.log_loss - final_metrics.log_loss))

    return PredictivePlan(
        tuple(selected),
        tuple(progress),
        tuple(alternatives),
        final_metrics,
        tuple(ablation),
    )


def certify_predictive_batch(
    field: ProbeField,
    split: PredictiveSplit,
    *,
    baseline_probabilities: Sequence[float] | None = None,
    max_probes: int = 8,
    max_thresholds: int = 63,
    min_calibration_gain: float = 1e-4,
    min_sealed_gain: float = 0.0,
    max_group_harm: float | None = None,
    min_support: int = 1,
) -> PredictiveCertificate:
    plan = design_predictive_batch(
        field,
        split.train,
        split.calibration,
        baseline_probabilities=baseline_probabilities,
        max_probes=max_probes,
        max_thresholds=max_thresholds,
        min_calibration_gain=min_calibration_gain,
        max_group_harm=max_group_harm,
        min_support=min_support,
    )
    fit = tuple(split.train) + tuple(split.calibration)
    model = compile_predictive_model(field, plan.rules, fit, min_support=min_support)

    if baseline_probabilities is None:
        positives = sum(field.labels[i] for i in fit)
        base = (positives + 1.0) / (len(fit) + 2.0)
        sealed_baseline_probabilities = [base] * len(field.values)
    else:
        sealed_baseline_probabilities = list(baseline_probabilities)

    sealed_baseline = _baseline_metrics(
        field,
        fit,
        split.test,
        sealed_baseline_probabilities,
    )
    sealed = evaluate_predictive_model(
        field,
        model,
        split.test,
        fallback_probabilities=sealed_baseline_probabilities,
        baseline_probabilities=sealed_baseline_probabilities,
    )
    accepted = sealed.log_loss <= sealed_baseline.log_loss - min_sealed_gain
    if max_group_harm is not None:
        accepted = accepted and sealed.max_group_harm <= max_group_harm
    return PredictiveCertificate(
        plan,
        model,
        sealed_baseline,
        sealed,
        accepted,
        split.seed_digest,
    )
