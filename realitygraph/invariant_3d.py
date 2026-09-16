from __future__ import annotations

import numpy as np


def robust_views(volume: np.ndarray, *, r_clip: float = 8.0) -> tuple[np.ndarray, np.ndarray]:
    """Return two scale-invariant views of one non-negative 3D uptake volume.

    X preserves percentile-normalized shape/intensity. R preserves uptake relative
    to a subject-internal middle-positive reference, with a fixed log compression.
    No labels or environment information are used.
    """
    a = np.asarray(volume, dtype=np.float32)
    if a.ndim != 3:
        raise ValueError(f"expected 3D volume, got shape {a.shape}")
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    a = np.maximum(a, 0.0)
    pos = a[a > 0]
    if pos.size == 0:
        z = np.zeros_like(a, dtype=np.float32)
        return z, z.copy()

    q05, q999 = np.percentile(pos, [5.0, 99.9])
    scale = max(float(q999 - q05), 1e-6)
    x = np.clip((a - float(q05)) / scale, 0.0, 1.0)

    q20, q60 = np.percentile(pos, [20.0, 60.0])
    middle = pos[(pos >= q20) & (pos <= q60)]
    ref = float(np.median(middle if middle.size else pos))
    ref = max(ref, 1e-6)
    r = np.clip(a / ref, 0.0, float(r_clip))
    r = np.log1p(r) / np.log1p(float(r_clip))

    return x.astype(np.float32, copy=False), r.astype(np.float32, copy=False)


def bilateral_channels(x: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Expose paired hemispheres and their sum/asymmetry as eight 3D channels.

    The first spatial axis is the bilateral axis, matching the existing 64x64
    Parkinson map convention. The right half is mirrored into left coordinates.
    """
    x = np.asarray(x, dtype=np.float32)
    r = np.asarray(r, dtype=np.float32)
    if x.shape != r.shape or x.ndim != 3:
        raise ValueError(f"expected matching 3D views, got {x.shape} and {r.shape}")
    if x.shape[0] % 2:
        raise ValueError("bilateral axis length must be even")

    half = x.shape[0] // 2

    def four(a: np.ndarray) -> tuple[np.ndarray, ...]:
        left = a[:half]
        right = np.flip(a[half:], axis=0)
        mean = 0.5 * (left + right)
        absdiff = np.abs(left - right)
        return left, right, mean, absdiff

    out = np.stack((*four(x), *four(r)), axis=0)
    return out.astype(np.float32, copy=False)


def downsample_mean3d(channels: np.ndarray, *, factor: int = 2) -> np.ndarray:
    """Mean-pool CxDxHxW channels by an integer factor in all spatial axes."""
    a = np.asarray(channels, dtype=np.float32)
    if a.ndim != 4:
        raise ValueError(f"expected CxDxHxW, got shape {a.shape}")
    factor = int(factor)
    if factor < 1:
        raise ValueError("factor must be >= 1")
    if factor == 1:
        return a.copy()
    c, d, h, w = a.shape
    if d % factor or h % factor or w % factor:
        raise ValueError(f"spatial shape {(d, h, w)} not divisible by factor {factor}")
    pooled = a.reshape(
        c,
        d // factor,
        factor,
        h // factor,
        factor,
        w // factor,
        factor,
    ).mean(axis=(2, 4, 6))
    return pooled.astype(np.float32, copy=False)


def group_dro_weights(previous: np.ndarray, losses: np.ndarray, *, eta: float = 0.1) -> np.ndarray:
    """Exponentiated-gradient group-DRO update over natural environments."""
    q = np.asarray(previous, dtype=np.float64)
    l = np.asarray(losses, dtype=np.float64)
    if q.ndim != 1 or l.ndim != 1 or q.shape != l.shape or q.size == 0:
        raise ValueError("previous and losses must be non-empty matching vectors")
    if not np.isfinite(q).all() or not np.isfinite(l).all():
        raise ValueError("non-finite group-DRO inputs")
    if np.any(q <= 0):
        raise ValueError("previous weights must be strictly positive")
    z = np.log(q) + float(eta) * l
    z -= np.max(z)
    out = np.exp(z)
    out /= out.sum()
    return out
