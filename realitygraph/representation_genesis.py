from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Program:
    source: str
    intensity: str
    bilateral: str
    pooling: str


@dataclass(frozen=True)
class ResidualDecoder:
    mean: np.ndarray
    scale: np.ndarray
    direction: np.ndarray
    score_mean: float
    score_scale: float
    delta: float


_SOURCES = ("R", "X")
_INTENSITIES = ("identity", "q90_scale", "support80")
_BILATERAL = ("raw", "sum", "diff", "absdiff")
_POOLING = ("grid4_mean", "grid4_meanstd", "grid8_mean", "profile8")
_DELTA_GRID = np.round(np.linspace(-1.5, 1.5, 61), 10)


def enumerate_programs() -> tuple[Program, ...]:
    return tuple(
        Program(source, intensity, bilateral, pooling)
        for source in _SOURCES
        for intensity in _INTENSITIES
        for bilateral in _BILATERAL
        for pooling in _POOLING
    )


def program_complexity(program: Program) -> tuple[int, int, int, int, str, str, str, str]:
    source_cost = 0 if program.source == "R" else 1
    intensity_cost = {"identity": 0, "q90_scale": 1, "support80": 2}[program.intensity]
    bilateral_cost = {"raw": 0, "sum": 1, "diff": 1, "absdiff": 1}[program.bilateral]
    pooling_cost = {
        "grid4_mean": 0,
        "profile8": 1,
        "grid4_meanstd": 2,
        "grid8_mean": 3,
    }[program.pooling]
    return (
        source_cost + intensity_cost + bilateral_cost + pooling_cost,
        source_cost,
        intensity_cost,
        bilateral_cost + pooling_cost,
        program.source,
        program.intensity,
        program.bilateral,
        program.pooling,
    )


def _positive_quantile(image: np.ndarray, q: float) -> float:
    positive = image[np.isfinite(image) & (image > 0)]
    if positive.size == 0:
        return 1.0
    value = float(np.quantile(positive, q))
    return value if value > 1e-12 else 1.0


def _apply_intensity(images: np.ndarray, mode: str) -> np.ndarray:
    images = np.asarray(images, dtype=np.float64)
    if mode == "identity":
        return images.copy()

    out = np.empty_like(images, dtype=np.float64)
    for i, image in enumerate(images):
        if mode == "q90_scale":
            out[i] = image / _positive_quantile(image, 0.90)
        elif mode == "support80":
            threshold = _positive_quantile(image, 0.80)
            out[i] = (image >= threshold).astype(np.float64)
        else:
            raise ValueError(f"unknown intensity mode: {mode}")
    return out


def _apply_bilateral(images: np.ndarray, mode: str) -> np.ndarray:
    if mode == "raw":
        return images
    if images.shape[1] % 2:
        raise ValueError("bilateral transforms require an even first spatial axis")

    half = images.shape[1] // 2
    left = images[:, :half, :]
    right = np.flip(images[:, half:, :], axis=1)

    if mode == "sum":
        return left + right
    if mode == "diff":
        return left - right
    if mode == "absdiff":
        return np.abs(left - right)
    raise ValueError(f"unknown bilateral mode: {mode}")


def _grid_stat(images: np.ndarray, grid: int, stat: str) -> np.ndarray:
    _, h, w = images.shape
    rows = []
    for i in range(grid):
        y0 = i * h // grid
        y1 = (i + 1) * h // grid
        for j in range(grid):
            x0 = j * w // grid
            x1 = (j + 1) * w // grid
            block = images[:, y0:y1, x0:x1]
            if stat == "mean":
                rows.append(block.mean(axis=(1, 2)))
            elif stat == "std":
                rows.append(block.std(axis=(1, 2)))
            else:
                raise ValueError(stat)
    return np.stack(rows, axis=1)


def _pool(images: np.ndarray, mode: str) -> np.ndarray:
    if mode == "grid4_mean":
        return _grid_stat(images, 4, "mean")
    if mode == "grid4_meanstd":
        return np.concatenate(
            [_grid_stat(images, 4, "mean"), _grid_stat(images, 4, "std")],
            axis=1,
        )
    if mode == "grid8_mean":
        return _grid_stat(images, 8, "mean")
    if mode == "profile8":
        _, h, w = images.shape
        row_features = []
        col_features = []
        for i in range(8):
            y0 = i * h // 8
            y1 = (i + 1) * h // 8
            row_features.append(images[:, y0:y1, :].mean(axis=(1, 2)))
            x0 = i * w // 8
            x1 = (i + 1) * w // 8
            col_features.append(images[:, :, x0:x1].mean(axis=(1, 2)))
        return np.stack(row_features + col_features, axis=1)
    raise ValueError(f"unknown pooling mode: {mode}")


def apply_program(maps: dict[str, np.ndarray], program: Program) -> np.ndarray:
    if program.source not in maps:
        raise KeyError(program.source)
    images = np.asarray(maps[program.source], dtype=np.float64)
    if images.ndim != 3:
        raise ValueError("representation source must be rows x height x width")
    images = _apply_intensity(images, program.intensity)
    images = _apply_bilateral(images, program.bilateral)
    out = _pool(images, program.pooling)
    if not np.isfinite(out).all():
        raise ValueError("representation produced non-finite values")
    return out


def _clip_probability(p: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(p, dtype=np.float64), 1e-6, 1 - 1e-6)


def _logit(p: np.ndarray) -> np.ndarray:
    p = _clip_probability(p)
    return np.log(p / (1.0 - p))


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


def _binary_log_loss(y: np.ndarray, p: np.ndarray) -> float:
    p = _clip_probability(p)
    y = np.asarray(y, dtype=np.float64)
    return float(np.mean(-(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))))


def fit_residual_decoder(
    matrix: np.ndarray,
    labels: np.ndarray,
    baseline: np.ndarray,
    environments: np.ndarray,
    train_environments: tuple[int, ...] | list[int],
) -> ResidualDecoder:
    """Fit one weak, environment-balanced residual direction.

    Only rows whose environment is explicitly listed in ``train_environments``
    may influence standardization, residual direction, or correction magnitude.
    The baseline logit coefficient is fixed at one, so this decoder cannot
    silently replace or globally recalibrate the retained parent model.
    """
    x = np.asarray(matrix, dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64)
    base = _clip_probability(baseline)
    env = np.asarray(environments)

    if x.ndim != 2:
        raise ValueError("residual decoder matrix must be rows x features")
    if len(x) != len(y) or len(x) != len(base) or len(x) != len(env):
        raise ValueError("row count mismatch")
    if not np.isfinite(x).all():
        raise ValueError("non-finite representation")

    train_envs = tuple(train_environments)
    train_mask = np.isin(env, train_envs)
    train_ids = np.where(train_mask)[0]
    if train_ids.size == 0:
        raise ValueError("no training rows")

    mean = x[train_ids].mean(axis=0)
    scale = x[train_ids].std(axis=0)
    scale = np.where(scale > 1e-9, scale, 1.0)
    z = (x - mean[None, :]) / scale[None, :]

    pieces = []
    for value in train_envs:
        ids = np.where(env == value)[0]
        if ids.size == 0:
            continue
        ze = z[ids]
        residual = y[ids] - base[ids]
        ze = ze - ze.mean(axis=0, keepdims=True)
        residual = residual - residual.mean()
        pieces.append(np.mean(ze * residual[:, None], axis=0))

    if not pieces:
        raise ValueError("training environments contain no rows")

    direction = np.mean(np.stack(pieces, axis=0), axis=0)
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-12:
        return ResidualDecoder(
            mean=mean,
            scale=scale,
            direction=np.zeros(x.shape[1], dtype=np.float64),
            score_mean=0.0,
            score_scale=1.0,
            delta=0.0,
        )
    direction = direction / norm

    raw_score = z @ direction
    score_mean = float(raw_score[train_ids].mean())
    score_scale = float(raw_score[train_ids].std())
    if score_scale <= 1e-9:
        score_scale = 1.0
    score = (raw_score - score_mean) / score_scale

    parent_loss = {
        value: _binary_log_loss(y[env == value], base[env == value])
        for value in train_envs
        if np.any(env == value)
    }

    best = None
    for delta in _DELTA_GRID:
        pred = _sigmoid(_logit(base) + float(delta) * score)
        gains = [
            parent_loss[value]
            - _binary_log_loss(y[env == value], pred[env == value])
            for value in train_envs
            if value in parent_loss
        ]
        worst = float(min(gains))
        average = float(np.mean(gains))
        key = (worst, average, -abs(float(delta)))
        if best is None or key > best[0]:
            best = (key, float(delta))

    return ResidualDecoder(
        mean=mean,
        scale=scale,
        direction=direction,
        score_mean=score_mean,
        score_scale=score_scale,
        delta=best[1],
    )


def predict_residual_decoder(
    model: ResidualDecoder,
    matrix: np.ndarray,
    baseline: np.ndarray,
) -> np.ndarray:
    x = np.asarray(matrix, dtype=np.float64)
    base = _clip_probability(baseline)
    if x.ndim != 2 or len(x) != len(base):
        raise ValueError("prediction row count mismatch")
    z = (x - model.mean[None, :]) / model.scale[None, :]
    raw_score = z @ model.direction
    score = (raw_score - model.score_mean) / model.score_scale
    return _sigmoid(_logit(base) + model.delta * score)


def mixed_evidence_invoke(gains, min_mean_gain: float = 0.0) -> bool:
    """Return True only for non-trivial mixed verifier evidence.

    This is the retained selective-representation controller pattern: expand
    representation when evidence contains both a pass and a fail, rather than
    demanding universal success before a representation is even allowed to be
    tested prospectively.  ``min_mean_gain`` prevents pure numerical noise from
    triggering expansion.
    """
    values = np.asarray(tuple(gains), dtype=np.float64)
    if values.size == 0 or not np.isfinite(values).all():
        return False
    return bool(
        np.any(values > 0.0)
        and np.any(values <= 0.0)
        and float(values.mean()) > float(min_mean_gain)
    )
