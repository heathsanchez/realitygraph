from __future__ import annotations

import numpy as np

from .canonical_striatal import (
    _align_side,
    _q90_scale,
    _shared_rigid_frame,
    _split_mirrored,
)

_THRESHOLDS = (0.30, 0.50, 0.70, 0.90)


def _weighted_quantile_positions(profile: np.ndarray, positions: np.ndarray, quantiles=(0.1, 0.25, 0.5, 0.75, 0.9)):
    w = np.maximum(np.asarray(profile, dtype=np.float64), 0.0)
    pos = np.asarray(positions, dtype=np.float64)
    total = float(w.sum())
    if total <= 1e-12:
        return np.zeros(len(quantiles), dtype=np.float64)
    cdf = np.cumsum(w) / total
    return np.asarray([float(pos[min(np.searchsorted(cdf, q, side='left'), len(pos)-1)]) for q in quantiles])


def _side_descriptors(side: np.ndarray):
    a = np.maximum(np.asarray(side, dtype=np.float64), 0.0)
    h, w = a.shape
    rr = np.linspace(-1.0, 1.0, h, dtype=np.float64)[:, None]
    cc = np.linspace(-1.0, 1.0, w, dtype=np.float64)[None, :]
    flat = a.ravel()
    finite = flat[np.isfinite(flat)]
    if finite.size == 0:
        finite = np.zeros(1)
    q = np.quantile(finite, [0.25, 0.50, 0.75, 0.90, 0.95])

    vals = [
        float(np.mean(a)),
        float(np.std(a)),
        float(q[0]), float(q[1]), float(q[2]), float(q[3]), float(q[4]),
    ]
    names = ['global_mean', 'global_std', 'q25', 'q50', 'q75', 'q90', 'q95']
    families = ['intensity', 'contrast', 'distribution', 'distribution', 'distribution', 'distribution', 'distribution']

    vmax = max(float(np.max(a)), 1e-8)
    threshold_rows = []
    threshold_names = []
    for frac in _THRESHOLDS:
        mask = a >= frac * vmax
        weight = a * mask
        total = float(weight.sum())
        if total <= 1e-12:
            weight = mask.astype(np.float64)
            total = float(weight.sum())
        if total <= 1e-12:
            total = 1.0

        tr = float(np.sum(weight * rr) / total)
        lo = float(np.sum(weight * cc) / total)
        dr = rr - tr
        dc = cc - lo
        var_t = float(np.sum(weight * dr * dr) / total)
        var_l = float(np.sum(weight * dc * dc) / total)
        cov = float(np.sum(weight * dr * dc) / total)
        eig = np.linalg.eigvalsh(np.array([[var_t, cov], [cov, var_l]], dtype=np.float64))
        minor = float(np.sqrt(max(eig[0], 0.0)))
        major = float(np.sqrt(max(eig[1], 0.0)))
        elong = major / max(minor, 1e-6)
        occ = float(mask.mean())
        selected = a[mask]
        mean_uptake = float(selected.mean()) if selected.size else 0.0
        std_uptake = float(selected.std()) if selected.size else 0.0

        longitudinal_profile = weight.sum(axis=0)
        mass_q = _weighted_quantile_positions(longitudinal_profile, cc.ravel())
        width_80 = float(mass_q[4] - mass_q[0])
        width_50 = float(mass_q[3] - mass_q[1])

        row = [
            occ, tr, lo, minor, major, elong,
            mean_uptake, std_uptake,
            float(mass_q[0]), float(mass_q[1]), float(mass_q[2]),
            float(mass_q[3]), float(mass_q[4]), width_50, width_80,
        ]
        base_names = [
            'occupancy', 'transverse_centroid', 'longitudinal_centroid',
            'minor_spread', 'major_spread', 'elongation',
            'mean_uptake', 'std_uptake',
            'long_mass_q10', 'long_mass_q25', 'long_mass_q50',
            'long_mass_q75', 'long_mass_q90', 'long_width50', 'long_width80',
        ]
        tag = f'f{int(round(frac*100))}'
        vals.extend(row)
        names.extend([f'{tag}_{n}' for n in base_names])
        families.extend([
            'shape', 'shape', 'shape', 'shape', 'shape', 'shape',
            'intensity', 'contrast',
            'profile', 'profile', 'profile', 'profile', 'profile', 'profile', 'profile',
        ])
        threshold_rows.append(np.asarray(row, dtype=np.float64))
        threshold_names = base_names

    rows = np.stack(threshold_rows, axis=0)
    for i in range(len(_THRESHOLDS)-1):
        a_tag = int(round(_THRESHOLDS[i] * 100))
        b_tag = int(round(_THRESHOLDS[i+1] * 100))
        delta = rows[i+1] - rows[i]
        vals.extend(delta.tolist())
        names.extend([f'delta_f{a_tag}_f{b_tag}_{n}' for n in threshold_names])
        families.extend(['threshold_change'] * len(threshold_names))

    return np.asarray(vals, dtype=np.float64), names, families


def subject_relative_geometry_features(maps: np.ndarray):
    """Build a label-free subject-relative bilateral uptake representation.

    Each scan is q90-normalized, the right hemisphere is mirrored, and one rigid
    frame is estimated from the subject's own bilateral uptake body. Descriptors
    are then measured in that intrinsic frame. Bilateral mean, signed asymmetry,
    and absolute asymmetry are explicit so predictive information need not live at
    a fixed scanner-grid coordinate.
    """
    x = np.asarray(maps, dtype=np.float64)
    if x.ndim != 3:
        raise ValueError('maps must be [row, left-right, anterior-posterior]')

    rows = []
    names = None
    families = None
    for image in x:
        normalized = _q90_scale(image)
        left, right = _split_mirrored(normalized)
        center, minor, major = _shared_rigid_frame(left, right)
        la = _align_side(left, center, minor, major)
        ra = _align_side(right, center, minor, major)

        lv, base_names, base_families = _side_descriptors(la)
        rv, right_names, right_families = _side_descriptors(ra)
        if base_names != right_names or base_families != right_families:
            raise RuntimeError('left/right descriptor mismatch')

        mean = 0.5 * (lv + rv)
        asym = lv - rv
        absasym = np.abs(asym)
        row = np.concatenate([lv, rv, mean, asym, absasym])
        rows.append(row)

        if names is None:
            names = (
                [f'left_{n}' for n in base_names]
                + [f'right_{n}' for n in base_names]
                + [f'mean_{n}' for n in base_names]
                + [f'asym_{n}' for n in base_names]
                + [f'absasym_{n}' for n in base_names]
            )
            families = (
                [f'left_{f}' for f in base_families]
                + [f'right_{f}' for f in base_families]
                + [f'bilateral_{f}' for f in base_families]
                + [f'asymmetry_{f}' for f in base_families]
                + [f'absasymmetry_{f}' for f in base_families]
            )

    if rows:
        out = np.stack(rows, axis=0)
    else:
        probe, base_names, base_families = _side_descriptors(np.zeros((16, 16), dtype=np.float64))
        names = (
            [f'left_{n}' for n in base_names]
            + [f'right_{n}' for n in base_names]
            + [f'mean_{n}' for n in base_names]
            + [f'asym_{n}' for n in base_names]
            + [f'absasym_{n}' for n in base_names]
        )
        families = (
            [f'left_{f}' for f in base_families]
            + [f'right_{f}' for f in base_families]
            + [f'bilateral_{f}' for f in base_families]
            + [f'asymmetry_{f}' for f in base_families]
            + [f'absasymmetry_{f}' for f in base_families]
        )
        out = np.empty((0, 5 * len(probe)), dtype=np.float64)

    if out.shape[1] != len(names) or len(names) != len(families):
        raise RuntimeError('feature metadata mismatch')
    if not np.isfinite(out).all():
        raise RuntimeError('non-finite subject-relative geometry feature')
    return out, names, families
