from __future__ import annotations

import hashlib
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable

from .empirical import EmpiricalDataset


@dataclass(frozen=True)
class SealedSplit:
    train: EmpiricalDataset
    calibration: EmpiricalDataset
    test: EmpiricalDataset
    seed_digest: str


@dataclass(frozen=True)
class CertifiedBall:
    center: tuple[float, ...]
    target: str
    radius: float
    calibration_support: int


@dataclass(frozen=True)
class SelectiveModel:
    target_kind: str
    feature_scales: tuple[float, ...]
    balls: tuple[CertifiedBall, ...] = ()
    exact_decoder: tuple[tuple[tuple[str, ...], str], ...] = ()
    min_votes: int = 3

    def predict(self, row: tuple[str, ...]) -> tuple[str, str | None]:
        if self.target_kind == "numeric":
            decoder = dict(self.exact_decoder)
            value = decoder.get(row)
            return ("ACCEPT", value) if value is not None else ("UNKNOWN", None)

        point = _numeric_row(row)
        votes = [
            ball.target
            for ball in self.balls
            if _distance(point, ball.center, self.feature_scales) <= ball.radius
        ]
        if len(votes) < self.min_votes:
            return "UNKNOWN", None
        labels = set(votes)
        if len(labels) != 1:
            return "UNKNOWN", None
        return "ACCEPT", votes[0]


@dataclass(frozen=True)
class SelectiveEvaluation:
    correct: int
    unknown: int
    wrong: int

    @property
    def covered(self) -> int:
        return self.correct + self.wrong

    @property
    def total(self) -> int:
        return self.correct + self.unknown + self.wrong

    @property
    def coverage(self) -> float:
        return self.covered / self.total if self.total else 0.0


def _subset(dataset: EmpiricalDataset, indices: Iterable[int]) -> EmpiricalDataset:
    idx = tuple(indices)
    return EmpiricalDataset(
        dataset.source,
        tuple(dataset.features[i] for i in idx),
        tuple(dataset.targets[i] for i in idx),
        dataset.source_sha256,
    )


def _stable_key(seed: str, dataset: EmpiricalDataset, index: int) -> bytes:
    return hashlib.sha256(
        f"{seed}|{dataset.source_sha256}|{dataset.source.name}|{index}".encode()
    ).digest()


def sealed_split(
    dataset: EmpiricalDataset,
    seed: str,
    train_fraction: float = 0.60,
    calibration_fraction: float = 0.20,
) -> SealedSplit:
    """Commit-seeded train/calibration/test split.

    Categorical datasets are stratified by target. Numeric targets use a global
    hash split. A rerun of the same commit gets the same test rows; any repair
    commit receives a different sealed partition.
    """
    if not 0 < train_fraction < 1:
        raise ValueError("invalid train fraction")
    if not 0 < calibration_fraction < 1:
        raise ValueError("invalid calibration fraction")
    if train_fraction + calibration_fraction >= 1:
        raise ValueError("split leaves no test set")

    groups: dict[str, list[int]] = defaultdict(list)
    if dataset.source.target_kind == "categorical":
        for i, target in enumerate(dataset.targets):
            groups[target].append(i)
    else:
        groups["*"] = list(range(len(dataset.features)))

    train: list[int] = []
    calibration: list[int] = []
    test: list[int] = []

    for _, members in sorted(groups.items()):
        ordered = sorted(members, key=lambda i: _stable_key(seed, dataset, i))
        n = len(ordered)
        if n < 3:
            raise ValueError("every split group needs at least three rows")
        n_train = max(1, int(n * train_fraction))
        n_cal = max(1, int(n * calibration_fraction))
        if n_train + n_cal >= n:
            n_cal = max(1, n - n_train - 1)
        train.extend(ordered[:n_train])
        calibration.extend(ordered[n_train : n_train + n_cal])
        test.extend(ordered[n_train + n_cal :])

    # Keep source-order irrelevant: each partition is deterministically shuffled
    # by the same hidden seed before use.
    train.sort(key=lambda i: _stable_key(seed + ":train", dataset, i))
    calibration.sort(key=lambda i: _stable_key(seed + ":cal", dataset, i))
    test.sort(key=lambda i: _stable_key(seed + ":test", dataset, i))

    return SealedSplit(
        _subset(dataset, train),
        _subset(dataset, calibration),
        _subset(dataset, test),
        hashlib.sha256(seed.encode()).hexdigest()[:16],
    )


def _numeric_row(row: tuple[str, ...]) -> tuple[float, ...]:
    try:
        values = tuple(float(value) for value in row)
    except ValueError as exc:
        raise ValueError("categorical selective predictor requires numeric features") from exc
    if not all(math.isfinite(value) for value in values):
        raise ValueError("non-finite feature")
    return values


def _scales(rows: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    width = len(rows[0])
    out = []
    for j in range(width):
        values = [row[j] for row in rows]
        span = max(values) - min(values)
        out.append(span if span > 0 else 1.0)
    return tuple(out)


def _distance(
    left: tuple[float, ...],
    right: tuple[float, ...],
    scales: tuple[float, ...],
) -> float:
    return math.sqrt(
        sum(((a - b) / scale) ** 2 for a, b, scale in zip(left, right, scales))
        / len(scales)
    )


def _compile_numeric_exact(
    train: EmpiricalDataset,
    calibration: EmpiricalDataset,
) -> SelectiveModel:
    train_counts: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    calibration_counts: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    for row, target in zip(train.features, train.targets):
        train_counts[row][target] += 1
    for row, target in zip(calibration.features, calibration.targets):
        calibration_counts[row][target] += 1

    decoder: list[tuple[tuple[str, ...], str]] = []
    for signature, train_targets in train_counts.items():
        cal_targets = calibration_counts.get(signature)
        if not cal_targets:
            continue
        union = set(train_targets) | set(cal_targets)
        if len(union) == 1:
            decoder.append((signature, next(iter(union))))

    return SelectiveModel(
        target_kind="numeric",
        feature_scales=(),
        exact_decoder=tuple(sorted(decoder)),
        min_votes=1,
    )


def _compile_categorical_balls(
    train: EmpiricalDataset,
    calibration: EmpiricalDataset,
    margin_fraction: float = 0.80,
    min_calibration_support: int = 1,
    min_votes: int = 3,
) -> SelectiveModel:
    train_rows = tuple(_numeric_row(row) for row in train.features)
    cal_rows = tuple(_numeric_row(row) for row in calibration.features)
    scales = _scales(train_rows)

    balls: list[CertifiedBall] = []
    for i, (center, target) in enumerate(zip(train_rows, train.targets)):
        opposing = [
            _distance(center, other, scales)
            for other, other_target in zip(train_rows, train.targets)
            if other_target != target
        ]
        if not opposing:
            continue
        safe_radius = min(opposing) * 0.5 * margin_fraction
        if safe_radius <= 0:
            continue

        supported_distances = []
        contradicted = False
        for point, cal_target in zip(cal_rows, calibration.targets):
            distance = _distance(center, point, scales)
            if distance <= safe_radius:
                if cal_target != target:
                    contradicted = True
                    break
                supported_distances.append(distance)

        if contradicted or len(supported_distances) < min_calibration_support:
            continue

        # Do not extrapolate all the way to the geometric safe radius. Retain
        # only the part of the neighborhood actually reached by calibration.
        radius = max(supported_distances)
        if radius <= 0:
            continue
        balls.append(
            CertifiedBall(center, target, radius, len(supported_distances))
        )

    # Exact duplicate balls buy nothing; collapse them deterministically.
    unique = {
        (ball.center, ball.target, ball.radius): ball
        for ball in balls
    }
    return SelectiveModel(
        target_kind="categorical",
        feature_scales=scales,
        balls=tuple(unique[key] for key in sorted(unique)),
        min_votes=min_votes,
    )


def compile_selective_model(
    train: EmpiricalDataset,
    calibration: EmpiricalDataset,
) -> SelectiveModel:
    if train.source.target_kind != calibration.source.target_kind:
        raise ValueError("target kind mismatch")
    if train.source.target_kind == "numeric":
        return _compile_numeric_exact(train, calibration)
    return _compile_categorical_balls(train, calibration)


def evaluate_selective(
    dataset: EmpiricalDataset,
    model: SelectiveModel,
) -> SelectiveEvaluation:
    correct = unknown = wrong = 0
    for row, target in zip(dataset.features, dataset.targets):
        status, predicted = model.predict(row)
        if status == "UNKNOWN":
            unknown += 1
        elif predicted == target:
            correct += 1
        else:
            wrong += 1
    return SelectiveEvaluation(correct, unknown, wrong)
