from __future__ import annotations

import numpy as np

CONTROL_FAMILIES = ("lowrank", "regional", "attention", "pyramid", "sparse_tv")
LOW_RANK_SIZES = (4, 8, 16, 32, 64)


def _check_feature_map(x):
    a = np.asarray(x, dtype=float)
    if a.ndim != 4:
        raise ValueError("expected C x D x H x W feature map")
    if not np.isfinite(a).all():
        raise ValueError("feature map contains non-finite values")
    return a


def regional_pool_numpy(x):
    """Eight octant means per channel; preserves coarse 3D location."""
    a = _check_feature_map(x)
    _, d, h, w = a.shape
    if min(d, h, w) < 2:
        raise ValueError("regional pooling requires each spatial axis >= 2")
    ds = (slice(0, d // 2), slice(d // 2, d))
    hs = (slice(0, h // 2), slice(h // 2, h))
    ws = (slice(0, w // 2), slice(w // 2, w))
    pooled = []
    for zd in ds:
        for yh in hs:
            for xw in ws:
                pooled.append(a[:, zd, yh, xw].mean(axis=(1, 2, 3)))
    return np.stack(pooled, axis=1)


def _grid_pool(a, bins):
    _, d, h, w = a.shape
    if d % bins or h % bins or w % bins:
        raise ValueError(f"spatial dimensions {(d, h, w)} must be divisible by bins={bins}")
    dz, hy, wx = d // bins, h // bins, w // bins
    parts = []
    for i in range(bins):
        for j in range(bins):
            for k in range(bins):
                parts.append(
                    a[:, i * dz:(i + 1) * dz, j * hy:(j + 1) * hy, k * wx:(k + 1) * wx].mean(
                        axis=(1, 2, 3)
                    )
                )
    return np.stack(parts, axis=1)


def spatial_pyramid_numpy(x):
    """Concatenate per-channel 1^3, 2^3 and 4^3 pooled descriptors."""
    a = _check_feature_map(x)
    levels = [_grid_pool(a, bins) for bins in (1, 2, 4)]
    return np.concatenate(levels, axis=1)


def total_variation_numpy(x):
    a = np.asarray(x, dtype=float)
    if a.ndim < 3:
        raise ValueError("total variation requires at least 3 spatial dimensions")
    if not np.isfinite(a).all():
        raise ValueError("non-finite values")
    return float(
        np.abs(np.diff(a, axis=-3)).sum()
        + np.abs(np.diff(a, axis=-2)).sum()
        + np.abs(np.diff(a, axis=-1)).sum()
    )
