from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass, replace
from typing import Sequence

from .empirical import EmpiricalDataset
from .selective import (
    SelectiveModel,
    compile_selective_model,
    sealed_split,
)


@dataclass(frozen=True)
class FeatureMetric:
    numeric: tuple[bool, ...]
    scales: tuple[float, ...]

    def encode(self, row: tuple[str, ...]) -> tuple[float | str | None, ...]:
        out: list[float | str | None] = []
        for value, is_numeric in zip(row, self.numeric):
            if value in {"?", "", "NA", "NaN"}:
                out.append(None)
            elif is_numeric:
                out.append(float(value))
            else:
                out.append(value)
        return tuple(out)

    def distance(
        self,
        left: tuple[float | str | None, ...],
        right: tuple[float | str | None, ...],
    ) -> float:
        terms = []
        for a, b, is_numeric, scale in zip(
            left, right, self.numeric, self.scales
        ):
            if a is None and b is None:
                terms.append(0.0)
            elif a is None or b is None:
                terms.append(1.0)
            elif is_numeric:
                terms.append(((float(a) - float(b)) / scale) ** 2)
            else:
                terms.append(0.0 if a == b else 1.0)
        return math.sqrt(sum(terms) / len(terms)) if terms else 0.0


@dataclass(frozen=True)
class BandBall:
    center: tuple[float | str | None, ...]
    target: str
    radius: float


@dataclass(frozen=True)
class BandModel:
    metric: FeatureMetric
    balls: tuple[BandBall, ...]
    min_votes: int = 3

    def predict(self, row: tuple[str, ...]) -> tuple[str, str | None]:
        point = self.metric.encode(row)
        votes = [
            ball.target
            for ball in self.balls
            if self.metric.distance(point, ball.center) <= ball.radius
        ]
        if len(votes) < self.min_votes:
            return "UNKNOWN", None
        labels = set(votes)
        if len(labels) != 1:
            return "UNKNOWN", None
        return "ACCEPT", votes[0]


@dataclass(frozen=True)
class Consequence:
    kind: str
    labels: tuple[str, ...] = ()
    low: float | None = None
    high: float | None = None

    def contains(self, target: str) -> bool:
        if self.kind in {"EXACT", "SET"}:
            return target in self.labels
        if self.kind == "INTERVAL":
            value = float(target)
            lower_ok = self.low is None or value >= self.low
            upper_ok = self.high is None or value <= self.high
            return lower_ok and upper_ok
        return False


@dataclass(frozen=True)
class ConsequenceEvaluation:
    exact: int
    partial: int
    interval: int
    unknown: int
    wrong: int
    total_label_slots: int = 0
    interval_width_sum: float = 0.0

    @property
    def informative(self) -> int:
        return self.exact + self.partial + self.interval

    @property
    def total(self) -> int:
        return self.informative + self.unknown + self.wrong

    @property
    def coverage(self) -> float:
        return self.informative / self.total if self.total else 0.0


@dataclass(frozen=True)
class ConsequenceModel:
    target_kind: str
    metric: FeatureMetric
    train_rows: tuple[tuple[float | str | None, ...], ...]
    train_targets: tuple[str, ...]
    exact_model: SelectiveModel
    class_labels: tuple[str, ...] = ()
    class_ratio: float = 1.0
    class_fallback_enabled: bool = True
    regression_k: int = 7
    regression_radius: float = 0.0
    regression_enabled: bool = False
    numeric_target_span: float = 0.0
    numeric_band_model: BandModel | None = None
    numeric_band_edges: tuple[float, ...] = ()

    def predict(self, row: tuple[str, ...]) -> Consequence:
        if self.target_kind == "categorical":
            status, target = self.exact_model.predict(row)
            if status == "ACCEPT" and target is not None:
                return Consequence("EXACT", (target,))

            if not self.class_fallback_enabled:
                return Consequence("UNKNOWN")

            point = self.metric.encode(row)
            distances: dict[str, float] = {}
            for train_row, train_target in zip(self.train_rows, self.train_targets):
                distance = self.metric.distance(point, train_row)
                old = distances.get(train_target)
                if old is None or distance < old:
                    distances[train_target] = distance

            if not distances:
                return Consequence("UNKNOWN")
            nearest = min(distances.values())
            threshold = nearest * self.class_ratio + 1e-15
            labels = tuple(
                sorted(label for label, distance in distances.items() if distance <= threshold)
            )
            if not labels or len(labels) == len(self.class_labels):
                return Consequence("UNKNOWN")
            return Consequence("EXACT" if len(labels) == 1 else "SET", labels)

        exact_status, exact_target = self.exact_model.predict(row)
        if exact_status == "ACCEPT" and exact_target is not None:
            return Consequence("EXACT", (exact_target,))

        if self.regression_enabled:
            point = self.metric.encode(row)
            neighbors = sorted(
                (
                    self.metric.distance(point, train_row),
                    float(target),
                )
                for train_row, target in zip(self.train_rows, self.train_targets)
            )
            if neighbors:
                k = min(self.regression_k, len(neighbors))
                local_values = [value for _, value in neighbors[:k]]
                margin = self.regression_radius
                low = min(local_values) - margin
                high = max(local_values) + margin
                if (
                    high > low
                    and (
                        self.numeric_target_span <= 0
                        or (high - low) < self.numeric_target_span
                    )
                ):
                    return Consequence("INTERVAL", low=low, high=high)

        if self.numeric_band_model is not None:
            status, band = self.numeric_band_model.predict(row)
            if status == "ACCEPT" and band is not None:
                index = int(band.split(":", 1)[1])
                low_edge = self.numeric_band_edges[index - 1] if index > 0 else None
                high_edge = (
                    self.numeric_band_edges[index]
                    if index < len(self.numeric_band_edges)
                    else None
                )
                return Consequence("INTERVAL", low=low_edge, high=high_edge)
        return Consequence("UNKNOWN")


def _compile_metric(dataset: EmpiricalDataset) -> FeatureMetric:
    width = len(dataset.features[0])
    numeric: list[bool] = []
    scales: list[float] = []

    for j in range(width):
        values = [
            row[j]
            for row in dataset.features
            if row[j] not in {"?", "", "NA", "NaN"}
        ]
        parsed = []
        is_numeric = True
        for value in values:
            try:
                parsed.append(float(value))
            except ValueError:
                is_numeric = False
                break
        numeric.append(is_numeric)
        if is_numeric and parsed:
            span = max(parsed) - min(parsed)
            scales.append(span if span > 0 else 1.0)
        else:
            scales.append(1.0)
    return FeatureMetric(tuple(numeric), tuple(scales))


def _nearest_class_ratio(
    metric: FeatureMetric,
    train_rows: Sequence[tuple[float | str | None, ...]],
    train_targets: Sequence[str],
    row: tuple[str, ...],
    true_target: str,
) -> float:
    point = metric.encode(row)
    by_class: dict[str, float] = {}
    for train_row, target in zip(train_rows, train_targets):
        distance = metric.distance(point, train_row)
        old = by_class.get(target)
        if old is None or distance < old:
            by_class[target] = distance
    nearest = min(by_class.values())
    true_distance = by_class.get(true_target)
    if true_distance is None:
        return math.inf
    if nearest <= 1e-15:
        return 1.0 if true_distance <= 1e-15 else math.inf
    return true_distance / nearest


def _regression_envelope(
    metric: FeatureMetric,
    train_rows: Sequence[tuple[float | str | None, ...]],
    train_targets: Sequence[str],
    row: tuple[str, ...],
    k: int,
) -> tuple[float, float]:
    point = metric.encode(row)
    neighbors = sorted(
        (
            metric.distance(point, train_row),
            float(target),
        )
        for train_row, target in zip(train_rows, train_targets)
    )
    values = [value for _, value in neighbors[: min(k, len(neighbors))]]
    return min(values), max(values)


def _class_distance_map(
    metric: FeatureMetric,
    train_rows: Sequence[tuple[float | str | None, ...]],
    train_targets: Sequence[str],
    row: tuple[str, ...],
) -> dict[str, float]:
    point = metric.encode(row)
    by_class: dict[str, float] = {}
    for train_row, target in zip(train_rows, train_targets):
        distance = metric.distance(point, train_row)
        old = by_class.get(target)
        if old is None or distance < old:
            by_class[target] = distance
    return by_class


def _categorical_fallback_stable(
    metric: FeatureMetric,
    train_rows: Sequence[tuple[float | str | None, ...]],
    train_targets: Sequence[str],
    calibration: EmpiricalDataset,
    labels: Sequence[str],
    safety_factor: float,
) -> bool:
    n = len(calibration.features)
    if n < 4:
        return False

    ratios = [
        _nearest_class_ratio(
            metric, train_rows, train_targets, row, target
        )
        for row, target in zip(calibration.features, calibration.targets)
    ]
    folds = (
        (tuple(range(0, n, 2)), tuple(range(1, n, 2))),
        (tuple(range(1, n, 2)), tuple(range(0, n, 2))),
    )
    for fit_indices, audit_indices in folds:
        fit = [ratios[i] for i in fit_indices if math.isfinite(ratios[i])]
        if len(fit) != len(fit_indices):
            return False
        threshold_ratio = max(fit, default=1.0) * safety_factor

        for i in audit_indices:
            by_class = _class_distance_map(
                metric,
                train_rows,
                train_targets,
                calibration.features[i],
            )
            if not by_class:
                continue
            nearest = min(by_class.values())
            threshold = nearest * threshold_ratio + 1e-15
            predicted = {
                label for label, distance in by_class.items()
                if distance <= threshold
            }
            # Empty/all-class outcomes are UNKNOWN, therefore safe. Only a
            # proper informative set can falsify the fallback.
            if predicted and len(predicted) < len(labels):
                if calibration.targets[i] not in predicted:
                    return False
    return True


def _regression_miss(
    metric: FeatureMetric,
    train_rows: Sequence[tuple[float | str | None, ...]],
    train_targets: Sequence[str],
    row: tuple[str, ...],
    target: str,
    k: int,
) -> tuple[float, float, float]:
    low, high = _regression_envelope(metric, train_rows, train_targets, row, k)
    value = float(target)
    miss = max(low - value, value - high, 0.0)
    return low, high, miss


def _numeric_interval_stable(
    metric: FeatureMetric,
    train_rows: Sequence[tuple[float | str | None, ...]],
    train_targets: Sequence[str],
    calibration: EmpiricalDataset,
    target_span: float,
    k: int,
    safety_factor: float,
) -> bool:
    n = len(calibration.features)
    if n < 4:
        return False

    folds = (
        (tuple(range(0, n, 2)), tuple(range(1, n, 2))),
        (tuple(range(1, n, 2)), tuple(range(0, n, 2))),
    )
    for fit_indices, audit_indices in folds:
        fit_misses = [
            _regression_miss(
                metric,
                train_rows,
                train_targets,
                calibration.features[i],
                calibration.targets[i],
                k,
            )[2]
            for i in fit_indices
        ]
        margin = max(fit_misses, default=0.0) * safety_factor

        for i in audit_indices:
            low, high, _ = _regression_miss(
                metric,
                train_rows,
                train_targets,
                calibration.features[i],
                calibration.targets[i],
                k,
            )
            low -= margin
            high += margin
            # A vacuous interval would be UNKNOWN in production, so it cannot
            # count as a successful audit consequence.
            if target_span > 0 and (high - low) >= target_span:
                continue
            value = float(calibration.targets[i])
            if not (low <= value <= high):
                return False
    return True


def _categorical_shadow_promotion(
    training: EmpiricalDataset,
    safety_factor: float,
    replays: int,
) -> bool:
    """Require repeated zero-wrong fallback transfer inside outer training."""
    for replay in range(replays):
        shadow = sealed_split(training, f"shadow-class-{replay}")
        metric = _compile_metric(shadow.train)
        train_rows = tuple(metric.encode(row) for row in shadow.train.features)
        labels = tuple(sorted(set(shadow.train.targets)))
        ratios = [
            _nearest_class_ratio(
                metric, train_rows, shadow.train.targets, row, target
            )
            for row, target in zip(
                shadow.calibration.features, shadow.calibration.targets
            )
        ]
        finite = [ratio for ratio in ratios if math.isfinite(ratio)]
        stable = (
            len(finite) == len(ratios)
            and _categorical_fallback_stable(
                metric,
                train_rows,
                shadow.train.targets,
                shadow.calibration,
                labels,
                safety_factor,
            )
        )
        if not stable:
            return False
        ratio = max(finite, default=1.0) * safety_factor

        for row, target in zip(shadow.test.features, shadow.test.targets):
            by_class = _class_distance_map(
                metric, train_rows, shadow.train.targets, row
            )
            if not by_class:
                continue
            nearest = min(by_class.values())
            threshold = nearest * ratio + 1e-15
            predicted = {
                label
                for label, distance in by_class.items()
                if distance <= threshold
            }
            if predicted and len(predicted) < len(labels) and target not in predicted:
                return False
    return True


def _numeric_shadow_promotion(
    training: EmpiricalDataset,
    k: int,
    safety_factor: float,
    replays: int,
) -> bool:
    """Require repeated zero-wrong interval transfer inside outer training."""
    for replay in range(replays):
        shadow = sealed_split(training, f"shadow-numeric-{replay}")
        metric = _compile_metric(shadow.train)
        train_rows = tuple(metric.encode(row) for row in shadow.train.features)
        numeric_targets = [
            float(value)
            for value in shadow.train.targets + shadow.calibration.targets
        ]
        span = (
            max(numeric_targets) - min(numeric_targets)
            if numeric_targets
            else 0.0
        )
        stable = _numeric_interval_stable(
            metric,
            train_rows,
            shadow.train.targets,
            shadow.calibration,
            span,
            k,
            safety_factor,
        )
        if not stable:
            return False

        residuals = [
            _regression_miss(
                metric,
                train_rows,
                shadow.train.targets,
                row,
                target,
                k,
            )[2]
            for row, target in zip(
                shadow.calibration.features, shadow.calibration.targets
            )
        ]
        margin = max(residuals, default=0.0) * safety_factor

        for row, target in zip(shadow.test.features, shadow.test.targets):
            low, high = _regression_envelope(
                metric, train_rows, shadow.train.targets, row, k
            )
            low -= margin
            high += margin
            if high <= low:
                continue
            if span > 0 and (high - low) >= span:
                continue
            value = float(target)
            if not (low <= value <= high):
                return False
    return True


def _compile_band_model(
    train: EmpiricalDataset,
    calibration: EmpiricalDataset,
    margin_fraction: float = 0.80,
    min_calibration_support: int = 1,
    min_votes: int = 3,
) -> BandModel:
    metric = _compile_metric(train)
    train_rows = tuple(metric.encode(row) for row in train.features)
    cal_rows = tuple(metric.encode(row) for row in calibration.features)
    balls: list[BandBall] = []

    for center, target in zip(train_rows, train.targets):
        opposing = [
            metric.distance(center, other)
            for other, other_target in zip(train_rows, train.targets)
            if other_target != target
        ]
        if not opposing:
            continue
        safe_radius = min(opposing) * 0.5 * margin_fraction
        if safe_radius <= 0:
            continue

        support = []
        contradicted = False
        for point, cal_target in zip(cal_rows, calibration.targets):
            distance = metric.distance(center, point)
            if distance <= safe_radius:
                if cal_target != target:
                    contradicted = True
                    break
                support.append(distance)

        if contradicted or len(support) < min_calibration_support:
            continue
        radius = max(support)
        if radius <= 0:
            continue
        balls.append(BandBall(center, target, radius))

    unique: dict[tuple[tuple[float | str | None, ...], str, float], BandBall] = {}
    for ball in balls:
        unique[(ball.center, ball.target, ball.radius)] = ball
    return BandModel(metric, tuple(unique.values()), min_votes)


def _quantile_edges(values: Sequence[float], bins: int) -> tuple[float, ...]:
    ordered = sorted(values)
    if len(ordered) < bins:
        return ()
    edges: list[float] = []
    n = len(ordered)
    for j in range(1, bins):
        cut = min(n - 1, max(1, (j * n) // bins))
        left = ordered[cut - 1]
        right = ordered[cut]
        edge = (left + right) / 2 if left != right else left
        if not edges or edge > edges[-1]:
            edges.append(edge)
    return tuple(edges)


def _band_label(value: str, edges: Sequence[float]) -> str:
    return f"bin:{bisect_left(edges, float(value))}"


def _band_dataset(dataset: EmpiricalDataset, edges: Sequence[float]) -> EmpiricalDataset:
    source = replace(
        dataset.source,
        target_kind="categorical",
        target_name=f"{dataset.source.target_name}_band",
    )
    return EmpiricalDataset(
        source,
        dataset.features,
        tuple(_band_label(value, edges) for value in dataset.targets),
        dataset.source_sha256,
    )


def _promote_numeric_bands(
    training: EmpiricalDataset,
    calibration: EmpiricalDataset,
    replays: int,
    candidate_bins: Sequence[int] = (8, 6, 4, 3, 2),
    minimum_shadow_coverage: float = 0.03,
    min_calibration_support: int = 2,
    min_votes: int = 5,
) -> tuple[SelectiveModel | None, tuple[float, ...]]:
    training_values = [float(value) for value in training.targets]

    for bins in candidate_bins:
        edges = _quantile_edges(training_values, bins)
        if len(edges) < 1:
            continue
        transformed_training = _band_dataset(training, edges)
        shadow_correct = 0
        shadow_total = 0
        failed = False

        for replay in range(replays):
            shadow = sealed_split(
                transformed_training,
                f"shadow-band-{bins}-{replay}",
            )
            model = _compile_band_model(
                shadow.train,
                shadow.calibration,
                min_calibration_support=min_calibration_support,
                min_votes=min_votes,
            )
            correct = wrong = 0
            for row, target in zip(shadow.test.features, shadow.test.targets):
                status, predicted = model.predict(row)
                if status == "ACCEPT":
                    if predicted == target:
                        correct += 1
                    else:
                        wrong += 1
            if wrong:
                failed = True
                break
            shadow_correct += correct
            shadow_total += len(shadow.test.features)

        if failed:
            continue
        coverage = shadow_correct / shadow_total if shadow_total else 0.0
        if coverage < minimum_shadow_coverage:
            continue

        transformed_calibration = _band_dataset(calibration, edges)
        model = _compile_band_model(
            transformed_training,
            transformed_calibration,
            min_calibration_support=min_calibration_support,
            min_votes=min_votes,
        )
        return model, edges

    return None, ()


def compile_consequence_model(
    train: EmpiricalDataset,
    calibration: EmpiricalDataset,
    *,
    class_safety_factor: float = 1.10,
    regression_k: int = 7,
    regression_safety_factor: float = 1.25,
    promotion_replays: int = 4,
) -> ConsequenceModel:
    metric = _compile_metric(train)
    train_rows = tuple(metric.encode(row) for row in train.features)
    exact_model = compile_selective_model(train, calibration)

    if train.source.target_kind == "categorical":
        labels = tuple(sorted(set(train.targets)))
        ratios = [
            _nearest_class_ratio(
                metric, train_rows, train.targets, row, target
            )
            for row, target in zip(calibration.features, calibration.targets)
        ]
        finite = [ratio for ratio in ratios if math.isfinite(ratio)]
        shadow_promoted = _categorical_shadow_promotion(
            train,
            class_safety_factor,
            promotion_replays,
        )
        stable = (
            shadow_promoted
            and len(finite) == len(ratios)
            and _categorical_fallback_stable(
                metric,
                train_rows,
                train.targets,
                calibration,
                labels,
                class_safety_factor,
            )
        )
        class_ratio = (
            max(finite, default=1.0) * class_safety_factor
            if stable
            else 1.0
        )
        return ConsequenceModel(
            "categorical",
            metric,
            train_rows,
            train.targets,
            exact_model,
            class_labels=labels,
            class_ratio=class_ratio,
            class_fallback_enabled=stable,
        )

    numeric_targets = [float(value) for value in train.targets + calibration.targets]
    span = max(numeric_targets) - min(numeric_targets) if numeric_targets else 0.0

    shadow_promoted = _numeric_shadow_promotion(
        train,
        regression_k,
        regression_safety_factor,
        promotion_replays,
    )
    stable = shadow_promoted and _numeric_interval_stable(
        metric,
        train_rows,
        train.targets,
        calibration,
        span,
        regression_k,
        regression_safety_factor,
    )
    residuals = [
        _regression_miss(
            metric, train_rows, train.targets, row, target, regression_k
        )[2]
        for row, target in zip(calibration.features, calibration.targets)
    ]
    radius = (
        max(residuals, default=0.0) * regression_safety_factor
        if stable
        else 0.0
    )
    band_model, band_edges = _promote_numeric_bands(
        train,
        calibration,
        promotion_replays,
    )
    return ConsequenceModel(
        "numeric",
        metric,
        train_rows,
        train.targets,
        exact_model,
        regression_k=regression_k,
        regression_radius=radius,
        regression_enabled=stable,
        numeric_target_span=span,
        numeric_band_model=band_model,
        numeric_band_edges=band_edges,
    )


def evaluate_consequences(
    dataset: EmpiricalDataset,
    model: ConsequenceModel,
) -> ConsequenceEvaluation:
    exact = partial = interval = unknown = wrong = 0
    total_label_slots = 0
    interval_width_sum = 0.0

    for row, target in zip(dataset.features, dataset.targets):
        consequence = model.predict(row)
        if consequence.kind == "UNKNOWN":
            unknown += 1
            continue
        if not consequence.contains(target):
            wrong += 1
            continue
        if consequence.kind == "EXACT":
            exact += 1
            total_label_slots += 1
        elif consequence.kind == "SET":
            partial += 1
            total_label_slots += len(consequence.labels)
        elif consequence.kind == "INTERVAL":
            interval += 1
            if consequence.low is not None and consequence.high is not None:
                interval_width_sum += float(consequence.high - consequence.low)

    return ConsequenceEvaluation(
        exact,
        partial,
        interval,
        unknown,
        wrong,
        total_label_slots,
        interval_width_sum,
    )
