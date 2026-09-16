from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

# Exact frozen Parkinson machinery already used by G1/G2/G3 screens.
exec(open("/workspace/parkinson_finish_fast.py").read().split("def main():")[0])

WORK = Path("/workspace")
MAP_CANDIDATES = [
    WORK / "pp_signal_maps.npz",
    WORK / "dat_parkinsons" / "work" / "pp_signal_maps.npz",
]

Q_NAME = "R_q90"
Q_T = 2.02439
Q_D0 = 0.30
Q_D1 = -0.10

MIN_GAIN = 1e-6


def g2_baseline(q, g1):
    d = np.where(q >= Q_T, Q_D1, Q_D0)
    return sigmoid(logit(g1) + d)


def load_R():
    path = next((p for p in MAP_CANDIDATES if p.exists()), None)
    if path is None:
        raise FileNotFoundError(
            "pp_signal_maps.npz not found in expected workspace locations"
        )

    z = np.load(path)
    if "R" not in z.files:
        raise KeyError(f"{path}: expected key 'R', found {z.files}")
    R = np.asarray(z["R"], np.float32)

    if R.ndim != 3 or R.shape[1:] != (64, 64):
        raise RuntimeError(f"unexpected R shape: {R.shape}")
    if not np.isfinite(R).all():
        raise RuntimeError("non-finite R maps")

    print("MAPS", path, "R", R.shape)
    return R


def shift_zero(img, dy, dx):
    h, w = img.shape
    out = np.zeros_like(img)

    ys0 = max(0, -dy)
    ys1 = min(h, h - dy)
    yd0 = max(0, dy)
    yd1 = yd0 + (ys1 - ys0)

    xs0 = max(0, -dx)
    xs1 = min(w, w - dx)
    xd0 = max(0, dx)
    xd1 = xd0 + (xs1 - xs0)

    if ys1 > ys0 and xs1 > xs0:
        out[yd0:yd1, xd0:xd1] = img[ys0:ys1, xs0:xs1]
    return out


def positive_quantile(img, q, fallback=1.0):
    pos = img[np.isfinite(img) & (img > 0)]
    if len(pos) == 0:
        return fallback
    v = float(np.quantile(pos, q))
    return v if v > 1e-8 else fallback


def align_scale_free(R):
    """Label-free per-scan alignment and scale removal.

    G2 already owns global uptake magnitude.  G3 therefore receives only
    within-scan spatial structure: center high-uptake support and divide by
    each scan's positive-pixel q90.
    """
    n, h, w = R.shape
    out = np.zeros_like(R, dtype=np.float32)
    yy, xx = np.mgrid[:h, :w]

    for i in range(n):
        img = np.maximum(R[i], 0)
        q80 = positive_quantile(img, .80)
        q90 = positive_quantile(img, .90)

        weights = np.maximum(img - q80, 0)
        s = float(weights.sum())
        if s <= 1e-8:
            weights = img
            s = float(weights.sum())

        if s > 1e-8:
            cy = float((weights * yy).sum() / s)
            cx = float((weights * xx).sum() / s)
        else:
            cy = (h - 1) / 2
            cx = (w - 1) / 2

        dy = int(round((h - 1) / 2 - cy))
        dx = int(round((w - 1) / 2 - cx))
        aligned = shift_zero(img, dy, dx)

        z = aligned / q90
        out[i] = np.clip(z, 0, 3)

    return out


def representations(R):
    Z = align_scale_free(R)
    mirror = Z[:, :, ::-1]

    # Three deliberately tiny orthogonal pixel grammars.
    rel = Z
    absdiff = np.abs(Z - mirror)
    support = (Z >= 0.80).astype(np.float32)

    return {
        "RELATIVE_UPTAKE": rel,
        "MIRROR_ABSDIFF": absdiff,
        "HIGH_UPTAKE_SUPPORT": support,
    }


def environment_balanced_template(X, residual, env, discovery_envs):
    """Learn one residual spatial operator without between-centre confounding.

    Template = equal-environment average of within-environment covariance
    between the frozen G1+G2 residual and each pixel.
    """
    h, w = X.shape[1:]
    pieces = []

    for e in discovery_envs:
        ids = np.where(env == e)[0]
        Xe = X[ids].astype(np.float64)
        re = residual[ids].astype(np.float64)

        re = re - re.mean()
        Xe = Xe - Xe.mean(axis=0, keepdims=True)

        t = np.mean(Xe * re[:, None, None], axis=0)
        pieces.append(t)

    template = np.mean(np.stack(pieces, axis=0), axis=0)
    template = gaussian_filter(template, sigma=1.0)

    norm = float(np.sqrt(np.sum(template * template)))
    if norm <= 1e-12:
        return np.zeros((h, w), dtype=np.float64)
    return template / norm


def score_template(X, template, discovery_ids):
    # Discovery-only centering.  The same center is applied untouched to future.
    mean_map = X[discovery_ids].mean(axis=0, dtype=np.float64)
    centered = X.astype(np.float64) - mean_map[None, :, :]
    return np.tensordot(centered, template, axes=((1, 2), (0, 1)))


def pair_future_family(name, X, y, env, base):
    records = []
    templates = []

    for a, b in combinations(range(10), 2):
        discovery_envs = [e for e in range(10) if e not in (a, b)]
        discovery_ids = np.where(np.isin(env, discovery_envs))[0]

        residual = y.astype(float) - base
        template = environment_balanced_template(
            X, residual, env, discovery_envs
        )
        score = score_template(X, template, discovery_ids)

        law = robust_fit_one(
            score,
            y,
            env,
            base,
            discovery_envs,
        )

        if law is None:
            records.append({
                "pair": (a, b),
                "gain_a": 0.0,
                "gain_b": 0.0,
                "pass": False,
                "law": None,
            })
            continue

        pred = apply_law(score, base, law)

        ma = env == a
        mb = env == b
        ga = log_loss(y[ma], base[ma]) - log_loss(y[ma], pred[ma])
        gb = log_loss(y[mb], base[mb]) - log_loss(y[mb], pred[mb])

        records.append({
            "pair": (a, b),
            "gain_a": float(ga),
            "gain_b": float(gb),
            "pass": ga > MIN_GAIN and gb > MIN_GAIN,
            "law": law,
        })
        templates.append(template)

    return records, templates


def summarize_pairs(name, records):
    passes = sum(r["pass"] for r in records)
    print()
    print("===", name, "PAIR FUTURES ===")
    print("PASSES", passes, "/45")

    for e in range(10):
        vals = []
        fails = []
        for r in records:
            a, b = r["pair"]
            if e == a:
                g = r["gain_a"]
                other = b
            elif e == b:
                g = r["gain_b"]
                other = a
            else:
                continue
            vals.append(g)
            if g <= MIN_GAIN:
                fails.append(other)

        print(
            "ENV", e,
            "POS", sum(v > MIN_GAIN for v in vals), "/9",
            "MEAN", round(float(np.mean(vals)), 5),
            "WORST", round(float(np.min(vals)), 5),
            "FAILS_WITH", fails,
        )

    laws = [r["law"] for r in records if r["law"] is not None]
    if laws:
        T = np.asarray([x["threshold"] for x in laws])
        D0 = np.asarray([x["d0"] for x in laws])
        D1 = np.asarray([x["d1"] for x in laws])
        print(
            "LAW_MED",
            "T", round(float(np.median(T)), 6),
            "D0", round(float(np.median(D0)), 3),
            "D1", round(float(np.median(D1)), 3),
        )

    return passes


def template_stability(templates):
    if len(templates) < 2:
        return 0.0, 0.0

    V = np.stack([t.ravel() for t in templates])
    C = V @ V.T
    tri = C[np.triu_indices(len(V), 1)]
    return float(np.median(tri)), float(np.min(tri))


def all_env_compiled(name, X, y, env, base):
    all_envs = list(range(10))
    ids = np.arange(len(y))
    residual = y.astype(float) - base

    template = environment_balanced_template(
        X, residual, env, all_envs
    )
    score = score_template(X, template, ids)
    law = robust_fit_one(score, y, env, base, all_envs)

    if law is None:
        return None

    pred = apply_law(score, base, law)
    gains = {}
    for e in all_envs:
        m = env == e
        gains[e] = log_loss(y[m], base[m]) - log_loss(y[m], pred[m])

    print()
    print("===", name, "ALL-ENV COMPILED OPERATOR ===")
    print(
        "LAW",
        "T", round(law["threshold"], 6),
        "D0", round(law["d0"], 3),
        "D1", round(law["d1"], 3),
    )
    for e in all_envs:
        print("ENV", e, "GAIN", round(float(gains[e]), 5))
    print(
        "FULL",
        "LL", round(log_loss(y, pred), 5),
        "AUC", round(roc_auc_score(y, pred), 5),
        "GAIN", round(log_loss(y, base) - log_loss(y, pred), 5),
        "WORST", round(min(gains.values()), 5),
        "POS", sum(v > 0 for v in gains.values()), "/10",
    )

    return {
        "law": law,
        "ll": log_loss(y, pred),
        "auc": roc_auc_score(y, pred),
        "gain": log_loss(y, base) - log_loss(y, pred),
        "worst": min(gains.values()),
        "pos": sum(v > 0 for v in gains.values()),
    }


def main():
    print("REALITYGRAPH / PARKINSON G3 ALIGNED PIXEL OPERATOR")
    print("----------------------------------------------------")
    print("G1 frozen: L_elong_q95")
    print("G2 frozen: R_q90 T=2.02439 D=[+0.30,-0.10]")
    print("G3 learns one environment-balanced residual template.")
    print("No future-environment labels enter template or law fitting.")
    print()

    y, env, canonical, g1 = load_frozen_baseline()
    M, names = load_exact_candidate_field()
    q = M[:, names.index(Q_NAME)]
    g2 = g2_baseline(q, g1)

    R = load_R()
    if len(R) != len(y):
        raise RuntimeError(f"map/base row mismatch: {len(R)} vs {len(y)}")

    reps = representations(R)

    print(
        "G1+G2",
        "LL", round(log_loss(y, g2), 5),
        "AUC", round(roc_auc_score(y, g2), 5),
    )

    results = {}
    for name, X in reps.items():
        records, templates = pair_future_family(
            name, X, y, env, g2
        )
        passes = summarize_pairs(name, records)
        med_corr, min_corr = template_stability(templates)
        print(
            "TEMPLATE_STABILITY",
            "MED_COS", round(med_corr, 4),
            "MIN_COS", round(min_corr, 4),
        )

        compiled = all_env_compiled(
            name, X, y, env, g2
        )

        results[name] = {
            "passes": passes,
            "template_med_cos": med_corr,
            "template_min_cos": min_corr,
            "compiled": compiled,
        }

    print()
    print("=== PIXEL FAMILY COMPARISON ===")
    for name, r in results.items():
        c = r["compiled"]
        print(
            name,
            "PAIR", r["passes"], "/45",
            "MED_COS", round(r["template_med_cos"], 4),
            "LL", None if c is None else round(c["ll"], 5),
            "GAIN", None if c is None else round(c["gain"], 5),
            "WORST", None if c is None else round(c["worst"], 5),
            "POS", None if c is None else f'{c["pos"]}/10',
        )

    viable = []
    for name, r in results.items():
        c = r["compiled"]
        if c is None:
            continue
        if (
            r["passes"] >= 40
            and r["template_med_cos"] > 0.80
            and c["pos"] == 10
            and c["worst"] > 0
            and c["gain"] > 1e-4
        ):
            viable.append((-r["passes"], c["ll"], name))

    print()
    print("=== VERDICT ===")
    if viable:
        viable.sort()
        _, _, winner = viable[0]
        print("ALIGNED_PIXEL_G3_SURVIVES", winner)
        print("FREEZE_TEMPLATE_GRAMMAR_AND_RUN_DEPLOYMENT_PARITY")
    else:
        print("NO_ALIGNED_PIXEL_G3_COMPILES")
        print("RETAIN_G1_PLUS_G2__NEXT_TEST_COMPLEMENTARY_MODEL_STACKING")


if __name__ == "__main__":
    main()
