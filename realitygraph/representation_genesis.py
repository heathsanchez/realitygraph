from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Program:
    source: str
    intensity: str
    bilateral: str
    pooling: str


_SOURCES = ("R", "X")
_INTENSITIES = ("identity", "q90_scale", "support80")
_BILATERAL = ("raw", "sum", "diff", "absdiff")
_POOLING = ("grid4_mean", "grid4_meanstd", "grid8_mean", "profile8")


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
    n, h, w = images.shape
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
        n, h, w = images.shape
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
