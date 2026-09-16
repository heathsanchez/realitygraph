from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RidgeResidualDecoder:
    mean: np.ndarray
    scale: np.ndarray
    beta: np.ndarray
    alpha: float
    l2: float


_ALPHA_GRID = np.round(np.linspace(0.0, 1.5, 31), 10)


def _clip_probability(p: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(p, dtype=np.float64), 1e-6, 1.0 - 1e-6)


def _logit(p: np.ndarray) -> np.ndarray:
    p = _clip_probability(p)
    return np.log(p / (1.0 - p))


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


def _binary_log_loss(y: np.ndarray, p: np.ndarray) -> float:
    p = _clip_probability(p)
    y = np.asarray(y, dtype=np.float64)
    return float(np.mean(-(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))))


def _balanced_weights(env: np.ndarray, train_envs: tuple[int, ...], train_ids: np.ndarray) -> np.ndarray:
    """Equal total influence per natural environment, with total weight n_train."""
    weights = np.zeros(len(env), dtype=np.float64)
    n_train = len(train_ids)
    present = [e for e in train_envs if np.any(env == e)]
    if not present:
        raise ValueError("training environments contain no rows")
    target = n_train / len(present)
    for value in present:
        ids = np.where(env == value)[0]
        weights[ids] = target / len(ids)
    return weights


def _objective(z: np.ndarray, y: np.ndarray, offset: np.ndarray, weights: np.ndarray, beta: np.ndarray, l2: float) -> float:
    eta = offset + z @ beta
    # Stable logistic negative log likelihood: log(1+exp(eta)) - y*eta.
    nll = np.logaddexp(0.0, eta) - y * eta
    return float(np.sum(weights * nll) + 0.5 * l2 * np.dot(beta, beta))


def _fit_beta(z: np.ndarray, y: np.ndarray, offset: np.ndarray, weights: np.ndarray, l2: float) -> np.ndarray:
    p = z.shape[1]
    beta = np.zeros(p, dtype=np.float64)
    eye = np.eye(p, dtype=np.float64)

    if not np.any(np.abs(z) > 1e-12):
        return beta

    for _ in range(30):
        eta = offset + z @ beta
        prob = _sigmoid(eta)
        gradient = z.T @ (weights * (prob - y)) + l2 * beta
        curvature = weights * prob * (1.0 - prob)
        hessian = z.T @ (curvature[:, None] * z) + (l2 + 1e-8) * eye
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(hessian, gradient, rcond=None)[0]

        if float(np.linalg.norm(step)) < 1e-8:
            break

        current = _objective(z, y, offset, weights, beta, l2)
        scale = 1.0
        accepted = False
        for _ in range(12):
            candidate = beta - scale * step
            if _objective(z, y, offset, weights, candidate, l2) <= current + 1e-12:
                beta = candidate
                accepted = True
                break
            scale *= 0.5
        if not accepted:
            break
        if float(np.linalg.norm(scale * step)) < 1e-7:
            break

    return beta


def fit_ridge_residual_decoder(
    matrix: np.ndarray,
    labels: np.ndarray,
    baseline: np.ndarray,
    environments: np.ndarray,
    train_environments: tuple[int, ...] | list[int],
    *,
    l2: float = 1.0,
) -> RidgeResidualDecoder:
    """Fit a bounded multivariate residual decoder with the parent logit fixed.

    The decoder may only add ``alpha * X beta`` to the existing baseline logit.
    It has no intercept and no coefficient on the parent prediction, so it cannot
    silently recalibrate or replace the retained G1+G2 system. Standardization,
    coefficient fitting, and shrinkage selection use only named train environments.
    Natural environments receive equal total weight during coefficient fitting.
    """
    x = np.asarray(matrix, dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64)
    base = _clip_probability(baseline)
    env = np.asarray(environments)

    if x.ndim != 2:
        raise ValueError("ridge decoder matrix must be rows x features")
    if len(x) != len(y) or len(x) != len(base) or len(x) != len(env):
        raise ValueError("row count mismatch")
    if not np.isfinite(x).all():
        raise ValueError("non-finite representation")
    if not np.isfinite(l2) or l2 <= 0:
        raise ValueError("l2 must be positive and finite")

    train_envs = tuple(train_environments)
    train_mask = np.isin(env, train_envs)
    train_ids = np.where(train_mask)[0]
    if train_ids.size == 0:
        raise ValueError("no training rows")

    mean = x[train_ids].mean(axis=0)
    raw_scale = x[train_ids].std(axis=0)
    active = raw_scale > 1e-9
    scale = np.where(active, raw_scale, 1.0)
    standardized = (x - mean[None, :]) / scale[None, :]
    standardized[:, ~active] = 0.0

    weights_all = _balanced_weights(env, train_envs, train_ids)
    z_train = standardized[train_ids]
    y_train = y[train_ids]
    offset_train = _logit(base[train_ids])
    weights_train = weights_all[train_ids]

    beta = _fit_beta(z_train, y_train, offset_train, weights_train, float(l2))
    if float(np.linalg.norm(beta)) <= 1e-12:
        return RidgeResidualDecoder(mean, scale, np.zeros(x.shape[1]), 0.0, float(l2))

    score = standardized @ beta
    parent_loss = {
        value: _binary_log_loss(y[env == value], base[env == value])
        for value in train_envs
        if np.any(env == value)
    }

    best = None
    for alpha in _ALPHA_GRID:
        pred = _sigmoid(_logit(base) + float(alpha) * score)
        gains = [
            parent_loss[value] - _binary_log_loss(y[env == value], pred[env == value])
            for value in train_envs
            if value in parent_loss
        ]
        mean_gain = float(np.mean(gains))
        worst_gain = float(np.min(gains))
        key = (mean_gain, worst_gain, -abs(float(alpha)))
        if best is None or key > best[0]:
            best = (key, float(alpha))

    alpha = best[1]
    if alpha == 0.0:
        beta = np.zeros_like(beta)
    return RidgeResidualDecoder(mean, scale, beta, alpha, float(l2))


def predict_ridge_residual_decoder(
    model: RidgeResidualDecoder,
    matrix: np.ndarray,
    baseline: np.ndarray,
) -> np.ndarray:
    x = np.asarray(matrix, dtype=np.float64)
    base = _clip_probability(baseline)
    if x.ndim != 2 or len(x) != len(base):
        raise ValueError("prediction row count mismatch")
    standardized = (x - model.mean[None, :]) / model.scale[None, :]
    score = standardized @ model.beta
    return _sigmoid(_logit(base) + model.alpha * score)
