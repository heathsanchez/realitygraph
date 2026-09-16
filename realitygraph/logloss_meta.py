from __future__ import annotations

import math

import numpy as np


def clip_p(p, eps=1e-7):
    return np.clip(np.asarray(p, dtype=np.float64), float(eps), 1.0 - float(eps))


def logit(p):
    q = clip_p(p)
    return np.log(q / (1.0 - q))


def sigmoid(z):
    z = np.asarray(z, dtype=np.float64)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def log_loss(y, p):
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    p = clip_p(p).reshape(-1)
    if len(y) != len(p):
        raise ValueError('shape mismatch')
    return float(np.mean(-(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))))


def _streams(streams):
    required = ('parent', 'anchor', 'full')
    out = {k: clip_p(streams[k]).reshape(-1) for k in required}
    n = len(out['full'])
    if any(len(out[k]) != n for k in required):
        raise ValueError('stream length mismatch')
    return out


def _softmax(v):
    v = np.asarray(v, dtype=np.float64)
    z = v - np.max(v)
    e = np.exp(z)
    return e / np.sum(e)


def apply_family(family, params, streams):
    s = _streams(streams)
    pp, pa, pf = s['parent'], s['anchor'], s['full']
    zp, za, zf = logit(pp), logit(pa), logit(pf)

    if family == 'identity_full':
        out = pf
    elif family == 'temperature_full':
        out = sigmoid(float(params['temperature']) * zf)
    elif family == 'bias_full':
        out = sigmoid(zf + float(params['bias']))
    elif family == 'affine_full':
        out = sigmoid(float(params['temperature']) * zf + float(params['bias']))
    elif family == 'beta_full':
        p = clip_p(pf)
        score = (
            float(params['a']) * np.log(p)
            - float(params['b']) * np.log(1.0 - p)
            + float(params['c'])
        )
        out = sigmoid(score)
    elif family == 'clip_full':
        eps = float(params['eps'])
        out = np.clip(pf, eps, 1.0 - eps)
    elif family == 'blend_parent_full_prob':
        a = float(params['alpha'])
        out = (1.0 - a) * pp + a * pf
    elif family == 'blend_anchor_full_prob':
        a = float(params['alpha'])
        out = (1.0 - a) * pa + a * pf
    elif family == 'blend_parent_full_logit':
        a = float(params['alpha'])
        out = sigmoid((1.0 - a) * zp + a * zf)
    elif family == 'blend_anchor_full_logit':
        a = float(params['alpha'])
        out = sigmoid((1.0 - a) * za + a * zf)
    elif family == 'two_stage_logit':
        a = float(params['anchor_scale'])
        r = float(params['residual_scale'])
        out = sigmoid(zp + a * (za - zp) + r * (zf - za))
    elif family == 'simplex_prob':
        w = np.asarray(params['weights'], dtype=np.float64)
        w = w / max(float(w.sum()), 1e-12)
        out = w[0] * pp + w[1] * pa + w[2] * pf
    elif family == 'simplex_logit':
        w = np.asarray(params['weights'], dtype=np.float64)
        w = w / max(float(w.sum()), 1e-12)
        out = sigmoid(w[0] * zp + w[1] * za + w[2] * zf)
    elif family == 'affine_two_stage':
        a = float(params['anchor_scale'])
        r = float(params['residual_scale'])
        t = float(params['temperature'])
        b = float(params['bias'])
        z = zp + a * (za - zp) + r * (zf - za)
        out = sigmoid(t * z + b)
    elif family.startswith('stack_logit_ridge_'):
        c = np.asarray(params['coef'], dtype=np.float64)
        b = float(params['bias'])
        out = sigmoid(b + c[0] * zp + c[1] * za + c[2] * zf)
    else:
        raise ValueError(f'unknown family: {family}')

    return clip_p(out)


def _minimize_family(family, streams, y):
    from scipy.optimize import minimize

    s = _streams(streams)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    if len(y) != len(s['full']):
        raise ValueError('shape mismatch')

    if family == 'temperature_full':
        x0 = np.array([1.0]); bounds = [(0.25, 3.0)]
        decode = lambda x: {'temperature': float(x[0])}
        starts = [x0, np.array([0.75]), np.array([1.25])]
    elif family == 'bias_full':
        x0 = np.array([0.0]); bounds = [(-2.0, 2.0)]
        decode = lambda x: {'bias': float(x[0])}
        starts = [x0, np.array([-0.2]), np.array([0.2])]
    elif family == 'affine_full':
        x0 = np.array([1.0, 0.0]); bounds = [(0.25, 3.0), (-2.0, 2.0)]
        decode = lambda x: {'temperature': float(x[0]), 'bias': float(x[1])}
        starts = [x0, np.array([0.8, 0.0]), np.array([1.2, 0.0])]
    elif family == 'beta_full':
        x0 = np.array([1.0, 1.0, 0.0]); bounds = [(-4.0, 4.0), (-4.0, 4.0), (-2.0, 2.0)]
        decode = lambda x: {'a': float(x[0]), 'b': float(x[1]), 'c': float(x[2])}
        starts = [x0, np.array([0.8, 0.8, 0.0]), np.array([1.2, 1.2, 0.0])]
    elif family in ('blend_parent_full_prob', 'blend_anchor_full_prob', 'blend_parent_full_logit', 'blend_anchor_full_logit'):
        x0 = np.array([1.0]); bounds = [(0.0, 1.0)]
        decode = lambda x: {'alpha': float(x[0])}
        starts = [x0, np.array([0.5]), np.array([0.8])]
    elif family == 'two_stage_logit':
        x0 = np.array([1.0, 1.0]); bounds = [(0.0, 1.5), (0.0, 1.5)]
        decode = lambda x: {'anchor_scale': float(x[0]), 'residual_scale': float(x[1])}
        starts = [x0, np.array([0.75, 0.75]), np.array([1.0, 0.5])]
    elif family == 'affine_two_stage':
        x0 = np.array([1.0, 1.0, 1.0, 0.0])
        bounds = [(0.0, 1.5), (0.0, 1.5), (0.5, 2.0), (-1.5, 1.5)]
        decode = lambda x: {
            'anchor_scale': float(x[0]), 'residual_scale': float(x[1]),
            'temperature': float(x[2]), 'bias': float(x[3]),
        }
        starts = [x0, np.array([1.0, 0.75, 1.0, 0.0]), np.array([0.75, 0.75, 1.0, 0.0])]
    elif family.startswith('stack_logit_ridge_'):
        x0 = np.array([0.0, 0.0, 1.0, 0.0])
        bounds = [(-2.0, 2.0), (-2.0, 2.0), (-2.0, 3.0), (-1.5, 1.5)]
        decode = lambda x: {'coef': [float(x[0]), float(x[1]), float(x[2])], 'bias': float(x[3])}
        starts = [x0, np.array([0.0, 0.5, 0.5, 0.0]), np.array([0.2, 0.2, 0.8, 0.0])]
    else:
        raise ValueError(f'optimizer unavailable for family: {family}')

    ridge = 0.0
    if family.startswith('stack_logit_ridge_'):
        token = family.rsplit('_', 1)[-1]
        ridge = float(token.replace('p', '.'))
        target = np.array([0.0, 0.0, 1.0, 0.0])
    else:
        target = None

    def objective(x):
        params = decode(x)
        ll = log_loss(y, apply_family(family, params, s))
        if ridge > 0.0:
            ll += ridge * float(np.sum((x - target) ** 2))
        return ll

    best = None
    for start in starts:
        res = minimize(objective, start, method='L-BFGS-B', bounds=bounds, options={'maxiter': 300, 'ftol': 1e-12})
        value = float(objective(res.x))
        if best is None or value < best[0]:
            best = (value, res.x.copy())
    return decode(best[1])


def fit_family(family, streams, y):
    s = _streams(streams)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    if len(y) != len(s['full']):
        raise ValueError('shape mismatch')

    if family == 'identity_full':
        return {}
    if family == 'clip_full':
        grid = [1e-7, 1e-6, 1e-5, 1e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2, 2e-2, 3e-2, 5e-2, 7.5e-2, 1e-1]
        rows = [(log_loss(y, apply_family(family, {'eps': eps}, s)), eps) for eps in grid]
        _, eps = min(rows)
        return {'eps': float(eps)}
    if family in ('simplex_prob', 'simplex_logit'):
        from scipy.optimize import minimize

        def decode(x):
            w = _softmax(x)
            return {'weights': [float(v) for v in w]}

        def objective(x):
            return log_loss(y, apply_family(family, decode(x), s))

        starts = [np.array([-2.0, -2.0, 2.0]), np.zeros(3), np.array([-1.0, 1.0, 1.0])]
        best = None
        for start in starts:
            res = minimize(objective, start, method='BFGS', options={'maxiter': 300, 'gtol': 1e-8})
            value = float(objective(res.x))
            if best is None or value < best[0]:
                best = (value, res.x.copy())
        return decode(best[1])
    return _minimize_family(family, s, y)


def fit_leave_environment_out(family, streams, y, env):
    s = _streams(streams)
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    env = np.asarray(env).reshape(-1)
    if not (len(y) == len(env) == len(s['full'])):
        raise ValueError('shape mismatch')

    pred = np.empty(len(y), dtype=np.float64)
    params = []
    unique = sorted(np.unique(env).tolist())
    for held in unique:
        train = env != held
        test = env == held
        train_streams = {k: v[train] for k, v in s.items()}
        test_streams = {k: v[test] for k, v in s.items()}
        fitted = fit_family(family, train_streams, y[train])
        pred[test] = apply_family(family, fitted, test_streams)
        params.append({'held': int(held) if isinstance(held, (int, np.integer)) else held, 'params': fitted})

    return {
        'family': family,
        'predictions': pred,
        'params_by_fold': params,
        'folds': len(unique),
        'll': log_loss(y, pred),
    }


DEFAULT_FAMILIES = (
    'identity_full',
    'temperature_full',
    'bias_full',
    'affine_full',
    'beta_full',
    'clip_full',
    'blend_parent_full_prob',
    'blend_anchor_full_prob',
    'blend_parent_full_logit',
    'blend_anchor_full_logit',
    'two_stage_logit',
    'simplex_prob',
    'simplex_logit',
    'affine_two_stage',
    'stack_logit_ridge_0p0001',
    'stack_logit_ridge_0p001',
    'stack_logit_ridge_0p01',
    'stack_logit_ridge_0p05',
)
