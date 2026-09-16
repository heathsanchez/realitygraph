from __future__ import annotations

from pathlib import Path
import sys

import cv2
import nibabel as nib
import numpy as np
from scipy import ndimage

W = Path("/workspace/dat_parkinsons/work")
CACHE = W / "pp_signal_maps.npz"
STACK = W / "threshold_stack100.npz"
NIFTI = W / "train_niftis"

G1_T = 1.5314126014709473
G1_D0 = 0.90
G1_D1 = -0.15
G2_T = 2.02439
G2_D0 = 0.30
G2_D1 = -0.10


def crop_exact(x, zoom, mm=100):
    """Exact pp_signal_test.py crop semantics. Do not replace with canonical crop_phys."""
    t = np.percentile(x, 90)
    m = np.maximum(x - t, 0)
    c = np.array(ndimage.center_of_mass(m))
    if not np.isfinite(c).all():
        c = (np.array(x.shape) - 1) / 2
    sz = np.maximum(16, np.rint(mm / zoom).astype(int))
    lo = np.floor(c - sz / 2).astype(int)
    hi = lo + sz
    pad = [
        (max(0, -lo[k]), max(0, hi[k] - x.shape[k]))
        for k in range(3)
    ]
    q = np.pad(x, pad)
    lo += np.array([p[0] for p in pad])
    hi = lo + sz
    q = q[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    return ndimage.zoom(q, 64 / np.array(q.shape), order=1)


def runtime_signal_map(path):
    """Exact NIfTI -> (X,R) provenance from pp_signal_test.py."""
    im = nib.as_closest_canonical(nib.load(str(path)))
    a = np.asarray(im.dataobj, np.float32)
    a = np.nan_to_num(a, nan=0, posinf=0, neginf=0)
    a = np.maximum(a, 0)
    z = np.array(im.header.get_zooms()[:3], float)

    lo, hi = np.percentile(a, [5, 99.9])
    x = np.clip((a - lo) / (hi - lo + 1e-6), 0, 1)

    raw = ndimage.gaussian_filter(crop_exact(a, z), .7)
    x = ndimage.gaussian_filter(crop_exact(x, z), .7)

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
    n, lab, st, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), 8
    )
    if n <= 1:
        return np.zeros_like(mask, bool)
    j = 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])
    return lab == j


def l_elong_q95(r):
    A = r[:32]
    t = np.percentile(A, 95)
    C = largest(A >= t)
    xy = np.argwhere(C)
    if len(xy) < 3:
        return 0.0
    Z = xy - xy.mean(0)
    ev = np.sort(np.linalg.eigvalsh(Z.T @ Z / len(Z)))[::-1] + 1e-8
    return float(np.sqrt(ev[0] / ev[1]))


def r_q90(r):
    return float(np.percentile(r, 90))


def branch_g1(v):
    return bool(v >= G1_T)


def branch_g2(v):
    return bool(v >= G2_T)


def delta_g1(v):
    return G1_D1 if branch_g1(v) else G1_D0


def delta_g2(v):
    return G2_D1 if branch_g2(v) else G2_D0


def main():
    D = np.load(STACK, allow_pickle=True)
    uid = D["uid"].astype(str)

    Q = np.load(CACHE)
    Xc = np.asarray(Q["X"], np.float32)
    Rc = np.asarray(Q["R"], np.float32)

    fs = list(NIFTI.rglob("*.nii.gz")) + list(NIFTI.rglob("*.nii"))
    FM = {
        (p.name[:-7] if p.name.endswith(".nii.gz") else p.stem): p
        for p in fs
    }

    if len(uid) != len(Rc):
        raise RuntimeError(f"uid/cache row mismatch: {len(uid)} vs {len(Rc)}")

    missing = [u for u in uid if u not in FM]
    if missing:
        raise RuntimeError(f"missing NIfTI files: {len(missing)} first={missing[:5]}")

    exact_x = 0
    exact_r = 0
    close_x = 0
    close_r = 0
    g1_value_close = 0
    g2_value_close = 0
    g1_branch_match = 0
    g2_branch_match = 0
    both_branch_match = 0

    max_x = 0.0
    max_r = 0.0
    max_g1 = 0.0
    max_g2 = 0.0

    bad = []

    for i, u in enumerate(uid):
        Xr, Rr = runtime_signal_map(FM[u])

        dx = float(np.max(np.abs(Xr.astype(np.float64) - Xc[i].astype(np.float64))))
        dr = float(np.max(np.abs(Rr.astype(np.float64) - Rc[i].astype(np.float64))))
        max_x = max(max_x, dx)
        max_r = max(max_r, dr)

        ex = np.array_equal(Xr, Xc[i])
        er = np.array_equal(Rr, Rc[i])
        cx = np.allclose(Xr, Xc[i], rtol=0, atol=1e-6)
        cr = np.allclose(Rr, Rc[i], rtol=0, atol=1e-6)
        exact_x += int(ex)
        exact_r += int(er)
        close_x += int(cx)
        close_r += int(cr)

        cg1 = l_elong_q95(Rc[i])
        rg1 = l_elong_q95(Rr)
        cg2 = r_q90(Rc[i])
        rg2 = r_q90(Rr)

        dg1 = abs(cg1 - rg1)
        dg2 = abs(cg2 - rg2)
        max_g1 = max(max_g1, dg1)
        max_g2 = max(max_g2, dg2)
        g1_value_close += int(dg1 <= 1e-9)
        g2_value_close += int(dg2 <= 1e-6)

        b1 = branch_g1(cg1) == branch_g1(rg1)
        b2 = branch_g2(cg2) == branch_g2(rg2)
        g1_branch_match += int(b1)
        g2_branch_match += int(b2)
        both_branch_match += int(b1 and b2)

        if not (cr and b1 and b2):
            bad.append((
                i, u, dr,
                cg1, rg1, branch_g1(cg1), branch_g1(rg1),
                cg2, rg2, branch_g2(cg2), branch_g2(rg2),
            ))

        if (i + 1) % 100 == 0 or i + 1 == len(uid):
            print(
                "PARITY", i + 1, "/", len(uid),
                "R_CLOSE", close_r,
                "G1_BRANCH", g1_branch_match,
                "G2_BRANCH", g2_branch_match,
                flush=True,
            )

    n = len(uid)
    print()
    print("=== MAP PARITY ===")
    print("X_EXACT", exact_x, "/", n, "X_ATOL1E-6", close_x, "/", n, "MAX_ABS", max_x)
    print("R_EXACT", exact_r, "/", n, "R_ATOL1E-6", close_r, "/", n, "MAX_ABS", max_r)

    print()
    print("=== FEATURE PARITY ===")
    print("G1_VALUE_CLOSE", g1_value_close, "/", n, "MAX_ABS", max_g1)
    print("G2_VALUE_CLOSE", g2_value_close, "/", n, "MAX_ABS", max_g2)

    print()
    print("=== DECISION PARITY ===")
    print("G1_BRANCH_MATCH", g1_branch_match, "/", n)
    print("G2_BRANCH_MATCH", g2_branch_match, "/", n)
    print("BOTH_BRANCH_MATCH", both_branch_match, "/", n)

    if bad:
        print()
        print("=== FIRST MISMATCHES ===")
        for row in bad[:20]:
            print(row)

    print()
    print("=== DEPLOYMENT CONTRACT ===")
    if close_r == n and both_branch_match == n:
        print("PASS_EXACT_G1_G2_RUNTIME_PARITY")
        print("SAFE_TO_PATCH_CANONICAL_WITH_EXACT_PP_SIGNAL_RUNTIME")
        return 0

    print("FAIL_RUNTIME_PARITY__DO_NOT_SUBMIT_G1_G2_YET")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
