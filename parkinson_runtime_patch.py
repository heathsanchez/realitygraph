from __future__ import annotations

import json
from pathlib import Path

import cv2
import nibabel as nib
import numpy as np
from scipy import ndimage

from realitygraph.final_trajectory_model import apply_exported_residual
from realitygraph.threshold_trajectory import dense_threshold_trajectory_features

G1_T = 1.5314126014709473
G1_D0 = 0.90
G1_D1 = -0.15
G2_T = 2.02439
G2_D0 = 0.30
G2_D1 = -0.10


def _clip_p(p):
    return np.clip(np.asarray(p, dtype=np.float64), 1e-6, 1.0 - 1e-6)


def _logit(p):
    p = _clip_p(p)
    return np.log(p / (1.0 - p))


def _sigmoid(z):
    z = np.asarray(z, dtype=np.float64)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def crop_exact(x, zoom, mm=100):
    t = np.percentile(x, 90)
    m = np.maximum(x - t, 0)
    c = np.array(ndimage.center_of_mass(m))
    if not np.isfinite(c).all():
        c = (np.array(x.shape) - 1) / 2
    sz = np.maximum(16, np.rint(mm / zoom).astype(int))
    lo = np.floor(c - sz / 2).astype(int)
    hi = lo + sz
    pad = [(max(0, -lo[k]), max(0, hi[k] - x.shape[k])) for k in range(3)]
    q = np.pad(x, pad)
    lo += np.array([p[0] for p in pad])
    hi = lo + sz
    q = q[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    return ndimage.zoom(q, 64 / np.array(q.shape), order=1)


def runtime_signal_map(path):
    im = nib.as_closest_canonical(nib.load(str(path)))
    a = np.asarray(im.dataobj, np.float32)
    a = np.nan_to_num(a, nan=0, posinf=0, neginf=0)
    a = np.maximum(a, 0)
    zoom = np.array(im.header.get_zooms()[:3], float)

    lo, hi = np.percentile(a, [5, 99.9])
    x = np.clip((a - lo) / (hi - lo + 1e-6), 0, 1)
    raw = ndimage.gaussian_filter(crop_exact(a, zoom), .7)
    x = ndimage.gaussian_filter(crop_exact(x, zoom), .7)

    hot = np.maximum(x - np.percentile(x, 85), 0)
    zc = int(np.argmax(hot.sum((0, 1))))
    sl = slice(max(0, zc - 3), min(64, zc + 4))
    rr = raw[:, :, sl].mean(2)
    xx = x[:, :, sl].mean(2)

    v = rr[rr > 0]
    if len(v) == 0:
        ref = 1e-6
    else:
        q20, q60 = np.percentile(v, [20, 60])
        mid = v[(v >= q20) & (v <= q60)]
        ref = (np.median(mid) if len(mid) else np.median(v)) + 1e-6
    return xx.astype(np.float32), (rr / ref).astype(np.float32)


def largest(mask):
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if n <= 1:
        return np.zeros_like(mask, bool)
    j = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
    return lab == j


def l_elong_q95(r):
    a = np.asarray(r, dtype=np.float64)[:32]
    t = np.percentile(a, 95)
    c = largest(a >= t)
    xy = np.argwhere(c)
    if len(xy) < 3:
        return 0.0
    z = xy - xy.mean(0)
    ev = np.sort(np.linalg.eigvalsh(z.T @ z / len(z)))[::-1] + 1e-8
    return float(np.sqrt(ev[0] / ev[1]))


def r_q90(r):
    return float(np.percentile(r, 90))


def parent_probability(canonical_probability, r):
    z = float(_logit(float(canonical_probability)))
    z += G1_D1 if l_elong_q95(r) >= G1_T else G1_D0
    z += G2_D1 if r_q90(r) >= G2_T else G2_D0
    return float(_sigmoid(z))


def load_model(path):
    return json.loads(Path(path).read_text())


def patch_probability(nifti_path, canonical_probability, model):
    """Apply frozen G1+G2 and the final threshold-trajectory residual.

    ``canonical_probability`` must be the probability produced by the exact
    pre-existing canonical submission before the RealityGraph patches.
    """
    if isinstance(model, (str, Path)):
        model = load_model(model)
    _, r = runtime_signal_map(nifti_path)
    parent = parent_probability(canonical_probability, r)
    base_logit = _logit([parent])

    bank, names, _ = dense_threshold_trajectory_features(r[None, ...])
    index = {name: j for j, name in enumerate(names)}
    anchor_name = model["anchor"]["name"]
    if anchor_name not in index:
        raise RuntimeError(f"anchor feature missing at runtime: {anchor_name}")
    anchor = bank[:, index[anchor_name]]
    residual_names = model["residual"]["names"]
    missing = [name for name in residual_names if name not in index]
    if missing:
        raise RuntimeError(f"residual feature(s) missing at runtime: {missing}")
    residual = bank[:, [index[name] for name in residual_names]] if residual_names else np.empty((1, 0))
    final_logit = apply_exported_residual(base_logit, anchor, residual, model)
    return float(_sigmoid(final_logit)[0])
