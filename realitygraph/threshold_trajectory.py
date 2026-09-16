from __future__ import annotations

import numpy as np

from .canonical_striatal import (
    _align_side,
    _q90_scale,
    _shared_rigid_frame,
    _split_mirrored,
)
from .object_relative_geometry import _weighted_quantile_positions

THRESHOLDS = np.asarray([0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80], dtype=np.float64)
OBSERVABLES = (
    'mean_uptake',
    'std_uptake',
    'long_mass_q10',
    'long_mass_q25',
    'long_mass_q50',
    'long_width50',
    'long_width80',
    'longitudinal_centroid',
    'minor_spread',
)


def _tag(x: float) -> int:
    return int(round(100.0 * float(x)))


def _curve_meta(thresholds: np.ndarray, prefix: str):
    t = np.asarray(thresholds, dtype=np.float64)
    names = []
    families = []
    for x in t:
        names.append(f'{prefix}_level_{_tag(x)}')
        families.append('trajectory_level')
    for a, b in zip(t[:-1], t[1:]):
        names.append(f'{prefix}_delta_{_tag(a)}_{_tag(b)}')
        families.append('trajectory_delta')
    for x in t[1:-1]:
        names.append(f'{prefix}_curv_{_tag(x)}')
        families.append('trajectory_curvature')
    for a, b in ((0.40, 0.60), (0.45, 0.65), (0.50, 0.70), (0.55, 0.75), (0.60, 0.80)):
        if np.any(np.isclose(t, a)) and np.any(np.isclose(t, b)):
            names.append(f'{prefix}_delta_{_tag(a)}_{_tag(b)}')
            families.append('trajectory_span')
    names.extend([
        f'{prefix}_slope',
        f'{prefix}_auc',
        f'{prefix}_max_abs_delta',
        f'{prefix}_max_abs_delta_at',
        f'{prefix}_curvature_energy',
    ])
    families.extend(['trajectory_summary'] * 5)
    return names, families


def curve_features(values, thresholds=THRESHOLDS, *, prefix='curve'):
    """Encode one threshold response curve with levels, derivatives and summaries."""
    v = np.asarray(values, dtype=np.float64).reshape(-1)
    t = np.asarray(thresholds, dtype=np.float64).reshape(-1)
    if len(v) != len(t) or len(v) < 3:
        raise ValueError('values and thresholds must have equal length >= 3')
    if not (np.isfinite(v).all() and np.isfinite(t).all()):
        raise ValueError('non-finite curve')
    dt = np.diff(t)
    if np.any(dt <= 0.0):
        raise ValueError('thresholds must be strictly increasing')

    names, _ = _curve_meta(t, prefix)
    out = list(v)
    delta = np.diff(v)
    out.extend(delta.tolist())

    first = delta / dt
    curv = []
    for i in range(1, len(t) - 1):
        denom = 0.5 * (dt[i - 1] + dt[i])
        curv.append((first[i] - first[i - 1]) / max(float(denom), 1e-12))
    out.extend(curv)

    for a, b in ((0.40, 0.60), (0.45, 0.65), (0.50, 0.70), (0.55, 0.75), (0.60, 0.80)):
        ia = np.flatnonzero(np.isclose(t, a))
        ib = np.flatnonzero(np.isclose(t, b))
        if len(ia) and len(ib):
            out.append(float(v[ib[0]] - v[ia[0]]))

    tc = t - float(t.mean())
    slope = float(np.dot(tc, v - float(v.mean())) / max(float(np.dot(tc, tc)), 1e-12))
    auc = float(np.trapezoid(v, t) / max(float(t[-1] - t[0]), 1e-12))
    abs_delta = np.abs(delta)
    j = int(np.argmax(abs_delta))
    max_abs_delta = float(abs_delta[j])
    max_abs_delta_at = float(0.5 * (t[j] + t[j + 1]))
    curvature_energy = float(np.mean(np.square(curv))) if curv else 0.0
    out.extend([slope, auc, max_abs_delta, max_abs_delta_at, curvature_energy])

    arr = np.asarray(out, dtype=np.float64)
    if len(arr) != len(names) or not np.isfinite(arr).all():
        raise RuntimeError('curve feature metadata mismatch or non-finite value')
    return arr, names


def _threshold_observables(side: np.ndarray, frac: float):
    a = np.maximum(np.asarray(side, dtype=np.float64), 0.0)
    h, w = a.shape
    rr = np.linspace(-1.0, 1.0, h, dtype=np.float64)[:, None]
    cc = np.linspace(-1.0, 1.0, w, dtype=np.float64)[None, :]
    vmax = max(float(np.max(a)), 1e-12)
    mask = a >= float(frac) * vmax
    weight = a * mask
    total = float(weight.sum())
    if total <= 1e-12:
        weight = mask.astype(np.float64)
        total = max(float(weight.sum()), 1.0)

    selected = a[mask]
    mean_uptake = float(selected.mean()) if selected.size else 0.0
    std_uptake = float(selected.std()) if selected.size else 0.0
    longitudinal_profile = weight.sum(axis=0)
    mass_q = _weighted_quantile_positions(longitudinal_profile, cc.ravel())
    long_width50 = float(mass_q[3] - mass_q[1])
    long_width80 = float(mass_q[4] - mass_q[0])
    longitudinal_centroid = float(np.sum(weight * cc) / total)

    transverse_centroid = float(np.sum(weight * rr) / total)
    dr = rr - transverse_centroid
    dc = cc - longitudinal_centroid
    var_t = float(np.sum(weight * dr * dr) / total)
    var_l = float(np.sum(weight * dc * dc) / total)
    cov = float(np.sum(weight * dr * dc) / total)
    eig = np.linalg.eigvalsh(np.asarray([[var_t, cov], [cov, var_l]], dtype=np.float64))
    minor_spread = float(np.sqrt(max(float(eig[0]), 0.0)))

    return np.asarray([
        mean_uptake,
        std_uptake,
        float(mass_q[0]),
        float(mass_q[1]),
        float(mass_q[2]),
        long_width50,
        long_width80,
        longitudinal_centroid,
        minor_spread,
    ], dtype=np.float64)


def _side_trajectory(side: np.ndarray, thresholds=THRESHOLDS):
    t = np.asarray(thresholds, dtype=np.float64)
    return np.stack([_threshold_observables(side, x) for x in t], axis=0)


def dense_threshold_trajectory_features(maps: np.ndarray, thresholds=THRESHOLDS):
    """Dense 40--80% threshold trajectories in the subject's intrinsic uptake frame."""
    x = np.asarray(maps, dtype=np.float64)
    t = np.asarray(thresholds, dtype=np.float64)
    if x.ndim != 3:
        raise ValueError('maps must be [row, left-right, anterior-posterior]')

    all_rows = []
    names = None
    families = None
    for image in x:
        normalized = _q90_scale(image)
        left, right = _split_mirrored(normalized)
        center, minor, major = _shared_rigid_frame(left, right)
        la = _align_side(left, center, minor, major)
        ra = _align_side(right, center, minor, major)
        trajectories = {
            'left': _side_trajectory(la, t),
            'right': _side_trajectory(ra, t),
        }
        trajectories['mean'] = 0.5 * (trajectories['left'] + trajectories['right'])

        row_parts = []
        row_names = []
        row_families = []
        for view in ('right', 'mean', 'left'):
            block = trajectories[view]
            for j, observable in enumerate(OBSERVABLES):
                prefix = f'{view}_{observable}'
                vals, nms = curve_features(block[:, j], t, prefix=prefix)
                _, fams = _curve_meta(t, prefix)
                row_parts.append(vals)
                row_names.extend(nms)
                row_families.extend([f'{view}_{f}' for f in fams])
        all_rows.append(np.concatenate(row_parts))
        if names is None:
            names = row_names
            families = row_families
        elif names != row_names or families != row_families:
            raise RuntimeError('trajectory metadata changed across rows')

    if all_rows:
        out = np.stack(all_rows, axis=0)
    else:
        probe = np.zeros((16, 16), dtype=np.float64)
        block = _side_trajectory(probe, t)
        row_parts = []
        names = []
        families = []
        for view in ('right', 'mean', 'left'):
            for j, observable in enumerate(OBSERVABLES):
                prefix = f'{view}_{observable}'
                vals, nms = curve_features(block[:, j], t, prefix=prefix)
                _, fams = _curve_meta(t, prefix)
                row_parts.append(vals)
                names.extend(nms)
                families.extend([f'{view}_{f}' for f in fams])
        out = np.empty((0, sum(len(v) for v in row_parts)), dtype=np.float64)

    if out.shape[1] != len(names) or len(names) != len(families):
        raise RuntimeError('trajectory feature metadata mismatch')
    if not np.isfinite(out).all():
        raise RuntimeError('non-finite trajectory feature')
    return out, names, families
