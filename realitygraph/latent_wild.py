from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


def _clip_p(p, eps=1e-7):
    return np.clip(np.asarray(p, dtype=np.float64), eps, 1.0 - eps)


def _logit(p):
    q = _clip_p(p)
    return np.log(q / (1.0 - q))


def _sigmoid(z):
    z = np.asarray(z, dtype=np.float64)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def _log_loss(y, p):
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    p = _clip_p(p).reshape(-1)
    return float(np.mean(-(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))))


def fit_fold_latent(X_train, y_train, pca_dim, learner, C=0.1):
    X_train = np.asarray(X_train, dtype=np.float64)
    y_train = np.asarray(y_train, dtype=np.int64).reshape(-1)
    if X_train.ndim != 2 or len(X_train) != len(y_train):
        raise ValueError("invalid training shapes")
    n_components = int(min(int(pca_dim), X_train.shape[0] - 1, X_train.shape[1]))
    if n_components < 1:
        raise ValueError("PCA rank must be positive")

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X_train)
    pca = PCA(n_components=n_components, svd_solver="randomized", random_state=0)
    Z = pca.fit_transform(Xs)

    if learner == "logistic":
        estimator = LogisticRegression(
            C=float(C), penalty="l2", solver="lbfgs", max_iter=3000, random_state=0
        )
        estimator.fit(Z, y_train)
        state = {"kind": "logistic", "estimator": estimator}
    elif learner == "prototype":
        if len(np.unique(y_train)) != 2:
            raise ValueError("prototype learner requires both classes")
        mu0 = Z[y_train == 0].mean(axis=0)
        mu1 = Z[y_train == 1].mean(axis=0)
        score = np.sum((Z - mu0) ** 2, axis=1) - np.sum((Z - mu1) ** 2, axis=1)

        def objective(x):
            p = _sigmoid(float(x[0]) * score + float(x[1]))
            return _log_loss(y_train, p)

        best = None
        for start in (np.array([1.0, 0.0]), np.array([0.1, 0.0]), np.array([2.0, 0.0])):
            res = minimize(
                objective,
                start,
                method="L-BFGS-B",
                bounds=[(-10.0, 10.0), (-5.0, 5.0)],
                options={"maxiter": 300, "ftol": 1e-12},
            )
            row = (float(objective(res.x)), res.x.copy())
            if best is None or row[0] < best[0]:
                best = row
        state = {
            "kind": "prototype",
            "mu0": mu0,
            "mu1": mu1,
            "temperature": float(best[1][0]),
            "bias": float(best[1][1]),
        }
    else:
        raise ValueError(f"unknown learner: {learner}")

    return {
        "scaler": scaler,
        "pca": pca,
        "learner": state,
        "pca_dim": n_components,
    }


def predict_fold_latent(model, X_test):
    X_test = np.asarray(X_test, dtype=np.float64)
    Z = model["pca"].transform(model["scaler"].transform(X_test))
    state = model["learner"]
    if state["kind"] == "logistic":
        p = state["estimator"].predict_proba(Z)[:, 1]
    elif state["kind"] == "prototype":
        d0 = np.sum((Z - state["mu0"]) ** 2, axis=1)
        d1 = np.sum((Z - state["mu1"]) ** 2, axis=1)
        score = d0 - d1
        p = _sigmoid(state["temperature"] * score + state["bias"])
    else:
        raise ValueError(f"unknown learner state: {state['kind']}")
    return _clip_p(p)


def loeo_latent_predictions(X, y, env, pca_dim, learner, C=0.1, audit=False):
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.int64).reshape(-1)
    env = np.asarray(env).reshape(-1)
    if not (X.ndim == 2 and len(X) == len(y) == len(env)):
        raise ValueError("shape mismatch")

    pred = np.empty(len(y), dtype=np.float64)
    audit_rows = []
    unique = sorted(np.unique(env).tolist())
    for held in unique:
        train = env != held
        test = env == held
        model = fit_fold_latent(X[train], y[train], pca_dim, learner, C)
        pred[test] = predict_fold_latent(model, X[test])
        if audit:
            audit_rows.append(
                {
                    "held": int(held) if isinstance(held, (int, np.integer)) else held,
                    "fit_envs": [
                        int(v) if isinstance(v, (int, np.integer)) else v
                        for v in sorted(np.unique(env[train]).tolist())
                    ],
                }
            )
    return {"predictions": pred, "folds": len(unique), "audit": audit_rows}


def fit_two_stream_stack(v6, latent, y, ridge=0.01):
    v6 = _clip_p(v6).reshape(-1)
    latent = _clip_p(latent).reshape(-1)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    if not (len(v6) == len(latent) == len(y)):
        raise ValueError("shape mismatch")
    zv6 = _logit(v6)
    zlat = _logit(latent)
    target = np.array([1.0, 0.0, 0.0], dtype=np.float64)

    def objective(x):
        p = _sigmoid(float(x[2]) + float(x[0]) * zv6 + float(x[1]) * zlat)
        return _log_loss(y, p) + float(ridge) * float(np.sum((x - target) ** 2))

    best = None
    for start in (target.copy(), np.array([0.8, 0.2, 0.0]), np.array([1.0, 0.1, 0.0])):
        res = minimize(
            objective,
            start,
            method="L-BFGS-B",
            bounds=[(-2.0, 3.0), (-2.0, 3.0), (-2.0, 2.0)],
            options={"maxiter": 300, "ftol": 1e-12},
        )
        row = (float(objective(res.x)), res.x.copy())
        if best is None or row[0] < best[0]:
            best = row
    x = best[1]
    return {
        "coef_v6": float(x[0]),
        "coef_latent": float(x[1]),
        "bias": float(x[2]),
        "ridge": float(ridge),
    }


def apply_two_stream_stack(model, v6, latent):
    v6 = _clip_p(v6).reshape(-1)
    latent = _clip_p(latent).reshape(-1)
    if len(v6) != len(latent):
        raise ValueError("stream length mismatch")
    z = (
        float(model["bias"])
        + float(model["coef_v6"]) * _logit(v6)
        + float(model["coef_latent"]) * _logit(latent)
    )
    return _clip_p(_sigmoid(z))
