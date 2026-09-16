from __future__ import annotations

import numpy as np

from .msi_representation_tournament import logistic_loss_from_logits


def _sigmoid(z):
    z = np.asarray(z, dtype=np.float64)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def fit_univariate_offset(x, y, base_logits, max_iter=40, tol=1e-8):
    """Fit one residual logit coefficient against a fixed parent offset.

    Returns (beta, log-loss gain). No intercept is fit here; recurrence should
    measure the feature's own directional consequence rather than site prevalence.
    """
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    offset = np.asarray(base_logits, dtype=np.float64).reshape(-1)
    if not (len(x) == len(y) == len(offset)):
        raise ValueError('shape mismatch')
    if len(x) == 0:
        return 0.0, 0.0
    if not (np.isfinite(x).all() and np.isfinite(y).all() and np.isfinite(offset).all()):
        raise ValueError('non-finite input')

    beta = 0.0
    parent = float(logistic_loss_from_logits(y, offset).mean())
    for _ in range(int(max_iter)):
        p = _sigmoid(offset + beta * x)
        g = float(np.mean(x * (p - y)))
        h = float(np.mean((x * x) * p * (1.0 - p))) + 1e-10
        step = g / h
        new_beta = beta - step
        if abs(new_beta - beta) < tol:
            beta = new_beta
            break
        beta = new_beta

    fitted = float(logistic_loss_from_logits(y, offset + beta * x).mean())
    gain = parent - fitted
    if not np.isfinite(beta) or not np.isfinite(gain) or gain <= 0.0:
        return 0.0, 0.0
    return float(beta), float(gain)


def _fit_many_univariate_offset(X, y, base_logits, max_iter=30, tol=1e-8):
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    offset = np.asarray(base_logits, dtype=np.float64).reshape(-1)
    if X.ndim != 2 or len(X) != len(y) or len(offset) != len(y):
        raise ValueError('shape mismatch')
    if X.shape[1] == 0:
        return np.zeros(0), np.zeros(0)

    beta = np.zeros(X.shape[1], dtype=np.float64)
    for _ in range(int(max_iter)):
        logits = offset[:, None] + X * beta[None, :]
        p = _sigmoid(logits)
        g = np.mean(X * (p - y[:, None]), axis=0)
        h = np.mean((X * X) * p * (1.0 - p), axis=0) + 1e-10
        step = g / h
        new_beta = beta - step
        if np.max(np.abs(new_beta - beta)) < tol:
            beta = new_beta
            break
        beta = new_beta

    parent = float(logistic_loss_from_logits(y, offset).mean())
    fitted = logistic_loss_from_logits(
        y[:, None], offset[:, None] + X * beta[None, :]
    ).mean(axis=0)
    gains = parent - fitted
    bad = (~np.isfinite(beta)) | (~np.isfinite(gains)) | (gains <= 0.0)
    beta = np.where(bad, 0.0, beta)
    gains = np.where(bad, 0.0, gains)
    return beta, gains


def environment_recurrence(X, y, base_logits, env, discovery_envs, max_iter=30):
    """Exact univariate residual consequences per discovery environment.

    All features are standardized once using only the declared discovery rows.
    The returned score rewards median log-loss gain and stable coefficient sign.
    """
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    offset = np.asarray(base_logits, dtype=np.float64)
    env = np.asarray(env)
    discovery_envs = tuple(int(e) for e in discovery_envs)
    if X.ndim != 2 or len(X) != len(y) or len(env) != len(y) or len(offset) != len(y):
        raise ValueError('shape mismatch')
    idx = np.flatnonzero(np.isin(env, discovery_envs))
    if len(idx) == 0:
        raise ValueError('empty discovery set')

    mu = X[idx].mean(axis=0)
    sd = X[idx].std(axis=0)
    sd = np.where(sd > 1e-8, sd, 1.0)
    Z = (X - mu) / sd

    betas = []
    gains = []
    for e in discovery_envs:
        take = env == e
        b, g = _fit_many_univariate_offset(
            Z[take], y[take], offset[take], max_iter=max_iter
        )
        betas.append(b)
        gains.append(g)
    betas = np.stack(betas, axis=0)
    gains = np.stack(gains, axis=0)

    pos = (betas > 0.0).mean(axis=0)
    neg = (betas < 0.0).mean(axis=0)
    sign_fraction = np.maximum(pos, neg)
    score = np.median(gains, axis=0) * sign_fraction
    return {
        'mean': mu,
        'scale': sd,
        'betas': betas,
        'gains': gains,
        'sign_fraction': sign_fraction,
        'score': score,
    }


def robust_median_beta(betas, min_sign_fraction=0.75):
    """Aggregate environment coefficients using only the majority direction."""
    betas = np.asarray(betas, dtype=np.float64)
    if betas.ndim != 2:
        raise ValueError('betas must be [environment, feature]')
    if betas.shape[0] == 0:
        return np.zeros(betas.shape[1], dtype=np.float64)
    out = np.zeros(betas.shape[1], dtype=np.float64)
    for j in range(betas.shape[1]):
        col = betas[:, j]
        pos = float(np.mean(col > 0.0))
        neg = float(np.mean(col < 0.0))
        if max(pos, neg) < float(min_sign_fraction):
            continue
        majority_positive = pos >= neg
        keep = col > 0.0 if majority_positive else col < 0.0
        if np.any(keep):
            out[j] = float(np.median(col[keep]))
    return out


def fit_robust_tiny_model(
    X,
    y,
    base_logits,
    env,
    discovery_envs,
    *,
    min_sign_fraction=0.75,
    shrinkage=1.0,
    max_iter=30,
):
    """Fit a tiny residual model without pooled multivariate coefficient fitting.

    Each feature is fit independently inside every discovery environment. Only a
    stable majority direction survives, and its coefficient is the median of the
    agreeing environments. A fixed shrinkage scalar can be selected by nested
    discovery-only validation; no pooled intercept is introduced.
    """
    stats = environment_recurrence(
        X, y, base_logits, env, discovery_envs, max_iter=max_iter
    )
    beta = robust_median_beta(
        stats['betas'], min_sign_fraction=min_sign_fraction
    )
    Z = (np.asarray(X, dtype=np.float64) - stats['mean']) / stats['scale']
    logits = np.asarray(base_logits, dtype=np.float64) + float(shrinkage) * (Z @ beta)
    return {
        'mean': stats['mean'],
        'scale': stats['scale'],
        'beta': beta,
        'sign_fraction': stats['sign_fraction'],
        'score': stats['score'],
        'logits': logits,
        'shrinkage': float(shrinkage),
    }
