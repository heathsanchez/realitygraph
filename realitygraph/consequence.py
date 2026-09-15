from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median
from typing import Sequence

from .empirical import EmpiricalDataset
from .selective import SelectiveModel, compile_selective_model


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
            return self.low is not None and self.high is not None and self.low <= value <= self.high
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
    regression_k: int = 7
    regression_radius: float = 0.0
    numeric_target_span: float = 0.0

    def predict(self, row: tuple[str, ...]) -> Consequence:
        if self.target_kind == "categorical":
            status, target = self.exact_model.predict(row)
            if status == "ACCEPT" and target is not None:
                return Consequence("EXACT", (target,))

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

        point = self.metric.encode(row)
        neighbors = sorted(
            (
                self.metric.distance(point, train_row),
                float(target),
            )
            for train_row, target in zip(self.train_rows, self.train_targets)
        )
        if not neighbors:
            return Consequence("UNKNOWN")
        k = min(self.regression_k, len(neighbors))
        center = median(value for _, value in neighbors[:k])
        radius = self.regression_radius
        if radius <= 0:
            return Consequence("UNKNOWN")
        if self.numeric_target_span > 0 and 2 * radius >= self.numeric_target_span:
            return Consequence("UNKNOWN")
        return Consequence("INTERVAL", low=center - radius, high=center + radius)


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


def _regression_point(
    metric: FeatureMetric,
    train_rows: Sequence[tuple[float | str | None, ...]],
    train_targets: Sequence[str],
    row: tuple[str, ...],
    k: int,
) -> float:
    point = metric.encode(row)
    neighbors = sorted(
        (
            metric.distance(point, train_row),
            float(target),
        )
        for train_row, target in zip(train_rows, train_targets)
    )
    return median(value for _, value in neighbors[: min(k, len(neighbors))])


def compile_consequence_model(
    train: EmpiricalDataset,
    calibration: EmpiricalDataset,
    *,
    class_safety_factor: float = 1.10,
    regression_k: int = 7,
    regression_safety_factor: float = 1.25,
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
        if len(finite) != len(ratios):
            class_ratio = math.inf
        else:
            class_ratio = max(finite, default=1.0) * class_safety_factor
        return ConsequenceModel(
            "categorical",
            metric,
            train_rows,
            train.targets,
            exact_model,
            class_labels=labels,
            class_ratio=class_ratio,
        )

    residuals = []
    for row, target in zip(calibration.features, calibration.targets):
        center = _regression_point(
            metric, train_rows, train.targets, row, regression_k
        )
        residuals.append(abs(float(target) - center))
    radius = max(residuals, default=0.0) * regression_safety_factor
    numeric_targets = [float(value) for value in train.targets + calibration.targets]
    span = max(numeric_targets) - min(numeric_targets) if numeric_targets else 0.0
    return ConsequenceModel(
        "numeric",
        metric,
        train_rows,
        train.targets,
        exact_model,
        regression_k=regression_k,
        regression_radius=radius,
        numeric_target_span=span,
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
