from __future__ import annotations

import numpy as np


def logistic_loss_from_logits(y, logits):
    y = np.asarray(y, dtype=np.float64)
    z = np.asarray(logits, dtype=np.float64)
    return np.logaddexp(0.0, z) - y * z


def _sigmoid(z):
    z = np.asarray(z, dtype=np.float64)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def _block_reduce(a, grid, reducer):
    a = np.asarray(a, dtype=np.float32)
    n, d, h, w = a.shape
    gd, gh, gw = (int(v) for v in grid)
    if d % gd or h % gh or w % gw:
        raise ValueError(f'grid {grid} does not divide spatial shape {(d, h, w)}')
    z = a.reshape(n, gd, d // gd, gh, h // gh, gw, w // gw)
    if reducer == 'mean':
        return z.mean(axis=(2, 4, 6))
    if reducer == 'std':
        return z.std(axis=(2, 4, 6))
    if reducer == 'range':
        return z.max(axis=(2, 4, 6)) - z.min(axis=(2, 4, 6))
    raise ValueError(reducer)


def build_structured_feature_bank(inputs, grids=((1, 1, 1), (2, 2, 2), (4, 4, 4), (4, 8, 8))):
    """Build a deterministic finite grammar of scan observables.

    The input is the frozen bilateral tensor [row, channel, depth, height, width].
    No labels or environments are read here, so the feature grammar can be cached once.
    """
    x = np.asarray(inputs, dtype=np.float32)
    if x.ndim != 5:
        raise ValueError('inputs must have shape [n,c,d,h,w]')
    if not np.isfinite(x).all():
        raise ValueError('inputs contain non-finite values')

    columns = []
    names = []
    families = []

    def add(values, name, family):
        v = np.asarray(values, dtype=np.float32)
        if v.ndim == 1:
            v = v[:, None]
        if v.shape[0] != x.shape[0]:
            raise ValueError('feature row mismatch')
        flat = v.reshape(v.shape[0], -1)
        columns.append(flat)
        if flat.shape[1] == 1:
            names.append(name)
            families.append(family)
        else:
            for j in range(flat.shape[1]):
                names.append(f'{name}_{j}')
                families.append(family)

    spatial_axes = (1, 2, 3)
    for c in range(x.shape[1]):
        a = x[:, c]
        flat = a.reshape(len(a), -1)
        mean = flat.mean(1)
        std = flat.std(1) + 1e-6
        qs = np.percentile(flat, [5, 10, 25, 50, 75, 90, 95], axis=1).T.astype(np.float32)
        for j, q in enumerate((5, 10, 25, 50, 75, 90, 95)):
            add(qs[:, j], f'c{c}_q{q}', 'distribution')
        add(mean, f'c{c}_mean', 'intensity')
        add(std, f'c{c}_std', 'contrast')
        add(qs[:, 5] - qs[:, 1], f'c{c}_q90_q10', 'contrast')
        add((qs[:, 5] + 1e-5) / (np.abs(qs[:, 3]) + 1e-5), f'c{c}_q90_med_ratio', 'distribution')

        grad_means = []
        for axis, tag in zip(spatial_axes, ('z', 'y', 'x')):
            g = np.abs(np.diff(a, axis=axis))
            gm = g.reshape(len(a), -1).mean(1)
            gs = g.reshape(len(a), -1).std(1)
            add(gm, f'c{c}_grad_{tag}_mean', 'contrast')
            add(gs, f'c{c}_grad_{tag}_std', 'contrast')
            grad_means.append(gm)
        add(np.stack(grad_means, axis=1), f'c{c}_gradient_axis', 'contrast')

        for grid in grids:
            tag = 'x'.join(str(v) for v in grid)
            add(_block_reduce(a, grid, 'mean'), f'c{c}_grid{tag}_mean', 'spatial')
            add(_block_reduce(a, grid, 'std'), f'c{c}_grid{tag}_std', 'contrast')
            add(_block_reduce(a, grid, 'range'), f'c{c}_grid{tag}_range', 'contrast')

        # Subject-internal z-normalization preserves relative spatial shape while
        # removing global brightness/contrast. Only the finest declared grid is
        # retained to avoid redundant lower-scale copies.
        z = ((a - mean[:, None, None, None]) / std[:, None, None, None]).astype(np.float32)
        fine = grids[-1]
        tag = 'x'.join(str(v) for v in fine)
        add(_block_reduce(z, fine, 'mean'), f'c{c}_z_grid{tag}_mean', 'spatial')

        # Shape and threshold-change observables use fractions of each subject's
        # own maximum, so occupancy/centroid can move rather than being fixed by
        # percentile rank.
        vmax = np.maximum(flat.max(1), 1e-6)
        coords = [
            np.linspace(-1.0, 1.0, a.shape[1], dtype=np.float32)[:, None, None],
            np.linspace(-1.0, 1.0, a.shape[2], dtype=np.float32)[None, :, None],
            np.linspace(-1.0, 1.0, a.shape[3], dtype=np.float32)[None, None, :],
        ]
        occ = []
        centroids = []
        for frac in (0.30, 0.50, 0.70, 0.90):
            mask = a >= (vmax * frac)[:, None, None, None]
            wgt = mask.astype(np.float32)
            den = wgt.sum(axis=(1, 2, 3)) + 1e-6
            o = wgt.mean(axis=(1, 2, 3))
            cen = np.stack([
                (wgt * coords[0]).sum(axis=(1, 2, 3)) / den,
                (wgt * coords[1]).sum(axis=(1, 2, 3)) / den,
                (wgt * coords[2]).sum(axis=(1, 2, 3)) / den,
            ], axis=1)
            add(o, f'c{c}_shape_occ_f{int(frac*100)}', 'shape_change')
            add(cen, f'c{c}_shape_centroid_f{int(frac*100)}', 'shape_change')
            occ.append(o)
            centroids.append(cen)
        occ = np.stack(occ, axis=1)
        centroids = np.stack(centroids, axis=1)
        add(np.diff(occ, axis=1), f'c{c}_shape_occ_delta', 'shape_change')
        add(np.diff(centroids, axis=1).reshape(len(a), -1), f'c{c}_shape_centroid_delta', 'shape_change')

    bank = np.concatenate(columns, axis=1).astype(np.float32, copy=False)
    if bank.shape[1] != len(names) or len(names) != len(families):
        raise RuntimeError('feature metadata mismatch')
    if not np.isfinite(bank).all():
        raise RuntimeError('non-finite generated feature')
    return bank, names, families


def approximate_univariate_consequence(X, y, base_probability, env, discovery_envs):
    """Cheap first-order fixed-offset log-loss screen, environment by environment."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    base = np.clip(np.asarray(base_probability, dtype=np.float64), 1e-6, 1 - 1e-6)
    env = np.asarray(env)
    discovery_envs = tuple(int(e) for e in discovery_envs)
    idx = np.flatnonzero(np.isin(env, discovery_envs))
    mu = X[idx].mean(axis=0)
    sd = X[idx].std(axis=0)
    sd = np.where(sd > 1e-8, sd, 1.0)
    Z = (X - mu) / sd
    gains = []
    signs = []
    for e in discovery_envs:
        take = env == e
        Ze = Z[take]
        r = y[take] - base[take]
        g = (Ze * r[:, None]).mean(axis=0)
        h = (Ze * Ze * (base[take] * (1.0 - base[take]))[:, None]).mean(axis=0) + 1e-8
        gains.append((g * g) / (2.0 * h))
        signs.append(np.sign(g))
    G = np.stack(gains, axis=0)
    S = np.stack(signs, axis=0)
    pos = (S > 0).mean(axis=0)
    neg = (S < 0).mean(axis=0)
    sign_fraction = np.maximum(pos, neg)
    # Median consequence resists one easy site dominating the screen; stable
    # direction breaks ties in favor of recurrent features.
    score = np.median(G, axis=0) * sign_fraction
    return score, sign_fraction


def _spectral_lipschitz(X, l2, iters=18):
    X = np.asarray(X, dtype=np.float64)
    p = X.shape[1]
    if p == 0:
        return 1.0
    v = np.ones(p, dtype=np.float64) / np.sqrt(p)
    eig = 0.0
    for _ in range(iters):
        w = X.T @ (X @ v) / max(len(X), 1)
        nrm = np.linalg.norm(w)
        if nrm < 1e-12:
            return max(float(l2), 1e-3)
        v = w / nrm
        eig = float(v @ (X.T @ (X @ v) / max(len(X), 1)))
    return 0.25 * max(eig, 0.0) + float(l2) + 1e-8


def proximal_offset_logistic(X, y, base_logits, l1=0.002, l2=0.01, max_iter=180, tol=1e-7):
    """FISTA elastic-net logistic regression with a fixed parent logit offset."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    offset = np.asarray(base_logits, dtype=np.float64)
    if X.ndim != 2 or len(X) != len(y) or len(offset) != len(y):
        raise ValueError('shape mismatch')
    if X.shape[1] == 0:
        return np.zeros(0, dtype=np.float64)
    L = _spectral_lipschitz(X, l2)
    step = 1.0 / L
    beta = np.zeros(X.shape[1], dtype=np.float64)
    z = beta.copy()
    t = 1.0
    for _ in range(int(max_iter)):
        prob = _sigmoid(offset + X @ z)
        grad = X.T @ (prob - y) / len(y) + float(l2) * z
        raw = z - step * grad
        new_beta = np.sign(raw) * np.maximum(np.abs(raw) - step * float(l1), 0.0)
        if np.max(np.abs(new_beta - beta)) < tol:
            beta = new_beta
            break
        new_t = 0.5 * (1.0 + np.sqrt(1.0 + 4.0 * t * t))
        z = new_beta + ((t - 1.0) / new_t) * (new_beta - beta)
        beta = new_beta
        t = new_t
    return beta
