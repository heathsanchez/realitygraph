from __future__ import annotations

from collections import defaultdict

import numpy as np


def _positive_q90_scale(images: np.ndarray) -> np.ndarray:
    x = np.asarray(images, dtype=np.float64)
    if x.ndim < 2:
        raise ValueError("expected rows plus spatial dimensions")
    out = np.empty_like(x, dtype=np.float64)
    for i in range(len(x)):
        row = x[i]
        positive = row[np.isfinite(row) & (row > 0.0)]
        q = float(np.quantile(positive, 0.90)) if positive.size else 1.0
        if not np.isfinite(q) or q <= 1e-12:
            q = 1.0
        out[i] = row / q
    return out


def _box_mean(images: np.ndarray, size: int) -> np.ndarray:
    x = np.asarray(images, dtype=np.float64)
    if size == 1:
        return x.copy()
    if size <= 0 or size % 2 == 0:
        raise ValueError("box size must be a positive odd integer")
    if x.ndim != 3:
        raise ValueError("box mean expects rows x height x width")
    p = size // 2
    padded = np.pad(x, ((0, 0), (p, p), (p, p)), mode="edge")
    prefix = np.pad(padded, ((0, 0), (1, 0), (1, 0)), mode="constant")
    prefix = prefix.cumsum(axis=1).cumsum(axis=2)
    total = (
        prefix[:, size:, size:]
        - prefix[:, :-size, size:]
        - prefix[:, size:, :-size]
        + prefix[:, :-size, :-size]
    )
    return total / float(size * size)


def build_2d_candidate_families(
    maps: dict[str, np.ndarray],
    *,
    box_sizes: tuple[int, ...] = (1, 5),
) -> dict[str, np.ndarray]:
    """Build label-free local uptake fields used by the pixel sweep.

    Each source is scaled by its own positive q90. The first spatial axis is
    split into left/right halves and the right half is mirrored into the same
    local orientation. No labels, environments, or future outcomes are read.
    """
    out: dict[str, np.ndarray] = {}
    for source in ("R", "X"):
        if source not in maps:
            continue
        x = _positive_q90_scale(np.asarray(maps[source], dtype=np.float64))
        if x.ndim != 3 or x.shape[1] % 2:
            raise ValueError("2D source must be rows x even-height x width")
        half = x.shape[1] // 2
        left0 = x[:, :half, :]
        right0 = np.flip(x[:, half:, :], axis=1)
        for size in box_sizes:
            left = _box_mean(left0, int(size))
            right = _box_mean(right0, int(size))
            prefix = f"{source}_s{int(size)}"
            out[f"{prefix}_left"] = left
            out[f"{prefix}_right"] = right
            out[f"{prefix}_sum"] = left + right
            out[f"{prefix}_diff"] = left - right
            out[f"{prefix}_absdiff"] = np.abs(left - right)
    if not out:
        raise ValueError("no supported map sources")
    if not all(np.isfinite(v).all() for v in out.values()):
        raise ValueError("candidate family contains non-finite values")
    return out


def coarse_volume_family(volume: np.ndarray, *, bins: int = 16) -> np.ndarray:
    """Return a q90-normalized coarse 3D uptake field without labels."""
    v = _positive_q90_scale(np.asarray(volume, dtype=np.float64))
    if v.ndim != 4:
        raise ValueError("volume must be rows x depth x height x width")
    d, h, w = v.shape[1:]
    if bins <= 0 or d % bins or h % bins or w % bins:
        raise ValueError("bins must evenly divide all spatial dimensions")
    fd, fh, fw = d // bins, h // bins, w // bins
    pooled = v.reshape(len(v), bins, fd, bins, fh, bins, fw).mean(axis=(2, 4, 6))
    if not np.isfinite(pooled).all():
        raise ValueError("non-finite coarse volume")
    return pooled


def environment_residual_correlations(
    field: np.ndarray,
    residual: np.ndarray,
    environments: np.ndarray,
    environment_values: tuple[int, ...] | list[int],
) -> np.ndarray:
    """Pearson association of every spatial element with parent residual per env."""
    x = np.asarray(field, dtype=np.float64)
    r = np.asarray(residual, dtype=np.float64)
    env = np.asarray(environments)
    if len(x) != len(r) or len(x) != len(env):
        raise ValueError("row count mismatch")
    flat = x.reshape(len(x), -1)
    rows = []
    for value in tuple(environment_values):
        ids = np.where(env == value)[0]
        if ids.size < 2:
            rows.append(np.zeros(flat.shape[1], dtype=np.float64))
            continue
        xe = flat[ids]
        re = r[ids]
        xc = xe - xe.mean(axis=0, keepdims=True)
        rc = re - re.mean()
        numerator = xc.T @ rc
        denominator = np.sqrt(np.sum(xc * xc, axis=0) * float(np.dot(rc, rc)))
        corr = np.divide(
            numerator,
            denominator,
            out=np.zeros_like(numerator, dtype=np.float64),
            where=denominator > 1e-12,
        )
        corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
        rows.append(corr)
    return np.stack(rows, axis=0)


def _stable_rank_rows(values: np.ndarray):
    mean = values.mean(axis=0)
    sign = np.where(mean >= 0.0, 1.0, -1.0)
    oriented = values * sign[None, :]
    positive = np.sum(oriented > 0.0, axis=0)
    worst = oriented.min(axis=0)
    median = np.median(oriented, axis=0)
    average = oriented.mean(axis=0)
    magnitude = np.mean(np.abs(values), axis=0)
    return positive, worst, median, average, magnitude


def select_stable_candidates(
    associations: dict[str, np.ndarray],
    *,
    train_env_indices: tuple[int, ...] | list[int],
    k: int = 12,
    max_per_family: int = 2,
) -> list[tuple[str, int]]:
    """Select strongest sign-recurrent residual pixels using named env rows only."""
    if k <= 0:
        return []
    train = tuple(int(i) for i in train_env_indices)
    ranked = []
    for family, matrix in associations.items():
        a = np.asarray(matrix, dtype=np.float64)
        if a.ndim != 2:
            raise ValueError("association matrix must be env x candidates")
        values = a[list(train)]
        positive, worst, median, average, magnitude = _stable_rank_rows(values)
        for j in range(a.shape[1]):
            key = (
                int(positive[j]),
                float(worst[j]),
                float(median[j]),
                float(average[j]),
                float(magnitude[j]),
                family,
                -j,
            )
            ranked.append((key, family, j))
    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = []
    counts = defaultdict(int)
    limit = max(1, int(max_per_family))
    for _, family, index in ranked:
        if counts[family] >= limit:
            continue
        selected.append((family, int(index)))
        counts[family] += 1
        if len(selected) >= k:
            break
    return selected


def select_magnitude_candidates(
    associations: dict[str, np.ndarray],
    *,
    train_env_indices: tuple[int, ...] | list[int],
    k: int = 12,
    max_per_family: int = 2,
) -> list[tuple[str, int]]:
    """Ablation selector: magnitude only, deliberately deleting recurrence."""
    if k <= 0:
        return []
    train = tuple(int(i) for i in train_env_indices)
    ranked = []
    for family, matrix in associations.items():
        a = np.asarray(matrix, dtype=np.float64)
        values = a[list(train)]
        mag = np.mean(np.abs(values), axis=0)
        mean = np.abs(values.mean(axis=0))
        for j in range(a.shape[1]):
            ranked.append(((float(mag[j]), float(mean[j]), family, -j), family, j))
    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = []
    counts = defaultdict(int)
    limit = max(1, int(max_per_family))
    for _, family, index in ranked:
        if counts[family] >= limit:
            continue
        selected.append((family, int(index)))
        counts[family] += 1
        if len(selected) >= k:
            break
    return selected


def gather_selected_matrix(
    families: dict[str, np.ndarray],
    selected: list[tuple[str, int]] | tuple[tuple[str, int], ...],
) -> np.ndarray:
    if not selected:
        n = len(next(iter(families.values())))
        return np.zeros((n, 0), dtype=np.float64)
    columns = []
    n = None
    for family, index in selected:
        if family not in families:
            raise KeyError(family)
        flat = np.asarray(families[family], dtype=np.float64).reshape(len(families[family]), -1)
        if index < 0 or index >= flat.shape[1]:
            raise IndexError((family, index))
        if n is None:
            n = len(flat)
        elif len(flat) != n:
            raise ValueError("row count mismatch across families")
        columns.append(flat[:, int(index)])
    return np.stack(columns, axis=1)
