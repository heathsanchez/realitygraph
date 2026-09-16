from __future__ import annotations

import numpy as np


_FEATURE_ROWS = 4
_FEATURE_COLS = 8


def _q90_scale(image: np.ndarray) -> np.ndarray:
    x = np.asarray(image, dtype=np.float64)
    finite = x[np.isfinite(x) & (x > 0.0)]
    if finite.size == 0:
        return np.zeros_like(x, dtype=np.float64)
    q90 = float(np.quantile(finite, 0.90))
    if not np.isfinite(q90) or q90 <= 1e-12:
        q90 = 1.0
    return np.nan_to_num(x / q90, nan=0.0, posinf=0.0, neginf=0.0)


def _split_mirrored(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if image.ndim != 2 or image.shape[0] % 2:
        raise ValueError("striatal map must be 2D with an even left-right axis")
    half = image.shape[0] // 2
    left = image[:half, :]
    right = np.flip(image[half:, :], axis=0)
    return left, right


def _shared_rigid_frame(left: np.ndarray, right: np.ndarray):
    """Estimate one label-free rigid frame from the bilateral average.

    The same transform is applied to both hemispheres. This removes subject-level
    translation and in-plane orientation while preserving disease-relevant shape,
    size, uptake magnitude, and left-right differences. No anisotropic scale
    normalization is performed.
    """
    symmetric = 0.5 * (left + right)
    h, w = symmetric.shape
    rr, cc = np.meshgrid(
        np.arange(h, dtype=np.float64),
        np.arange(w, dtype=np.float64),
        indexing="ij",
    )

    finite = symmetric[np.isfinite(symmetric)]
    background = float(np.median(finite)) if finite.size else 0.0
    weight = np.maximum(np.nan_to_num(symmetric, nan=background) - background, 0.0)
    total = float(weight.sum())

    if total <= 1e-10:
        center = np.array([(h - 1.0) / 2.0, (w - 1.0) / 2.0], dtype=np.float64)
        major = np.array([0.0, 1.0], dtype=np.float64)
        minor = np.array([1.0, 0.0], dtype=np.float64)
        return center, minor, major

    center = np.array(
        [float(np.sum(weight * rr) / total), float(np.sum(weight * cc) / total)],
        dtype=np.float64,
    )
    dr = rr - center[0]
    dc = cc - center[1]
    covariance = np.array(
        [
            [np.sum(weight * dr * dr), np.sum(weight * dr * dc)],
            [np.sum(weight * dr * dc), np.sum(weight * dc * dc)],
        ],
        dtype=np.float64,
    ) / total

    values, vectors = np.linalg.eigh(covariance)
    if (
        not np.isfinite(values).all()
        or values[-1] <= 1e-10
        or values[-1] <= 1.02 * max(values[0], 1e-12)
    ):
        major = np.array([0.0, 1.0], dtype=np.float64)
    else:
        major = np.asarray(vectors[:, -1], dtype=np.float64)
        major /= max(float(np.linalg.norm(major)), 1e-12)
        # Resolve the PCA sign ambiguity using acquisition orientation only.
        # Never use labels or disease state to choose anterior/posterior direction.
        if float(major[1]) < 0.0:
            major = -major

    minor = np.array([major[1], -major[0]], dtype=np.float64)
    return center, minor, major


def _bilinear(image: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> np.ndarray:
    h, w = image.shape
    valid = (rows >= 0.0) & (rows <= h - 1.0) & (cols >= 0.0) & (cols <= w - 1.0)

    r0 = np.floor(rows).astype(np.int64)
    c0 = np.floor(cols).astype(np.int64)
    r1 = r0 + 1
    c1 = c0 + 1

    r0c = np.clip(r0, 0, h - 1)
    r1c = np.clip(r1, 0, h - 1)
    c0c = np.clip(c0, 0, w - 1)
    c1c = np.clip(c1, 0, w - 1)

    fr = rows - r0
    fc = cols - c0

    out = (
        (1.0 - fr) * (1.0 - fc) * image[r0c, c0c]
        + fr * (1.0 - fc) * image[r1c, c0c]
        + (1.0 - fr) * fc * image[r0c, c1c]
        + fr * fc * image[r1c, c1c]
    )
    return np.where(valid, out, 0.0)


def _align_side(side: np.ndarray, center: np.ndarray, minor: np.ndarray, major: np.ndarray) -> np.ndarray:
    h, w = side.shape
    rr, cc = np.meshgrid(
        np.arange(h, dtype=np.float64),
        np.arange(w, dtype=np.float64),
        indexing="ij",
    )
    out_center_r = (h - 1.0) / 2.0
    out_center_c = (w - 1.0) / 2.0
    transverse = rr - out_center_r
    longitudinal = cc - out_center_c

    source_rows = center[0] + transverse * minor[0] + longitudinal * major[0]
    source_cols = center[1] + transverse * minor[1] + longitudinal * major[1]
    return _bilinear(side, source_rows, source_cols)


def _pool_4x8(side: np.ndarray) -> np.ndarray:
    h, w = side.shape
    rows = []
    for i in range(_FEATURE_ROWS):
        r0 = i * h // _FEATURE_ROWS
        r1 = (i + 1) * h // _FEATURE_ROWS
        for j in range(_FEATURE_COLS):
            c0 = j * w // _FEATURE_COLS
            c1 = (j + 1) * w // _FEATURE_COLS
            rows.append(float(np.mean(side[r0:r1, c0:c1])))
    return np.asarray(rows, dtype=np.float64)


def canonical_striatal_features(maps: np.ndarray) -> np.ndarray:
    """Return a 64-D bilateral uptake field in canonical rigid coordinates.

    Input rows are the frozen R maps. Each row is q90-normalized, the right
    hemisphere is mirrored into left anatomical orientation, one rigid frame is
    estimated from the bilateral average, and both sides are sampled in that same
    frame. The output concatenates 4x8 pooled left and right fields.
    """
    x = np.asarray(maps, dtype=np.float64)
    if x.ndim != 3:
        raise ValueError("maps must be rows x left-right x anterior-posterior")

    features = []
    for image in x:
        normalized = _q90_scale(image)
        left, right = _split_mirrored(normalized)
        center, minor, major = _shared_rigid_frame(left, right)
        left_aligned = _align_side(left, center, minor, major)
        right_aligned = _align_side(right, center, minor, major)
        features.append(
            np.concatenate([_pool_4x8(left_aligned), _pool_4x8(right_aligned)])
        )

    out = np.stack(features, axis=0) if features else np.empty((0, 64), dtype=np.float64)
    if not np.isfinite(out).all():
        raise ValueError("canonical representation produced non-finite values")
    return out


def unaligned_striatal_features(maps: np.ndarray) -> np.ndarray:
    """Exact representation ablation: same q90 normalization and pooling, no alignment."""
    x = np.asarray(maps, dtype=np.float64)
    if x.ndim != 3:
        raise ValueError("maps must be rows x left-right x anterior-posterior")

    features = []
    for image in x:
        normalized = _q90_scale(image)
        left, right = _split_mirrored(normalized)
        features.append(np.concatenate([_pool_4x8(left), _pool_4x8(right)]))

    out = np.stack(features, axis=0) if features else np.empty((0, 64), dtype=np.float64)
    if not np.isfinite(out).all():
        raise ValueError("unaligned representation produced non-finite values")
    return out
