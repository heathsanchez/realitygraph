from __future__ import annotations

from pathlib import Path
from itertools import combinations
import hashlib
import numpy as np

exec(open("/workspace/parkinson_finish_fast.py").read().split("def main():")[0])

WORK = Path("/workspace")

Q_NAME = "R_q90"
Q_T = 2.02439
Q_D0 = 0.30
Q_D1 = -0.10

# Existing train-side prediction artifacts.  This script never treats an array
# as valid merely because it exists: it must be finite, length 1362, and
# probability-valued.  OOF provenance still has to be respected when deciding
# whether a survivor is deployable.
FILES = [
    WORK / "retained_oof.npy",
    WORK / "fixed_resnet18_stack.npy",
    WORK / "fixed_resnet18_7z.npy",
    WORK / "volume3d_probe_oof.npz",
    WORK / "dat_parkinsons" / "work" / "retained_oof.npy",
    WORK / "dat_parkinsons" / "work" / "fixed_resnet18_stack.npy",
    WORK / "dat_parkinsons" / "work" / "fixed_resnet18_7z.npy",
    WORK / "dat_parkinsons" / "work" / "volume3d_probe_oof.npz",
]

ALPHAS = np.round(np.linspace(0.0, 1.0, 41), 6)
TOL = 1e-12


def g2_baseline(q, g1):
    d = np.where(q >= Q_T, Q_D1, Q_D0)
    return sigmoid(logit(g1) + d)


def array_id(arr):
    return hashlib.sha256(np.asarray(arr, np.float64).tobytes()).hexdigest()[:12]


def candidate_arrays(n):
    out = []
    seen = set()

    for path in FILES:
        if not path.exists():
            continue

        try:
            if path.suffix == ".npy":
                items = [(path.stem, np.load(path))]
            else:
                z = np.load(path)
                items = [(f"{path.stem}:{k}", z[k]) for k in z.files]
        except Exception as exc:
            print("SKIP_LOAD", path, repr(exc))
            continue

        for name, arr in items:
            a = np.asarray(arr).squeeze()
            if a.ndim != 1 or len(a) != n:
                continue
            if not np.isfinite(a).all():
                continue

            lo = float(a.min())
            hi = float(a.max())
            if lo < 0.0 or hi > 1.0:
                print(
                    "SKIP_NOT_PROB",
                    str(path), name,
                    "MIN", round(lo, 5),
                    "MAX", round(hi, 5),
                )
                continue

            key = array_id(a)
            if key in seen:
                continue
            seen.add(key)

            out.append({
                "name": name,
                "path": str(path),
                "id": key,
                "p": clip_p(a.astype(float)),
            })

    return out


def blend_logit(base, other, alpha):
    z = (1.0 - alpha) * logit(base) + alpha * logit(other)
    return sigmoid(z)


def robust_alpha(y, env, base, other, discovery_envs):
    best = None

    for alpha in ALPHAS:
        pred = blend_logit(base, other, alpha)
        gains = []
        for e in discovery_envs:
            m = env == e
            gains.append(
                log_loss(y[m], base[m])
                - log_loss(y[m], pred[m])
            )

        worst = float(min(gains))
        mean = float(np.mean(gains))
        # Prefer less intervention under ties.
        key = (worst, mean, -float(alpha))
        if best is None or key > best[0]:
            best = (key, float(alpha))

    return best[1], best[0]


def pair_future(y, env, base, other):
    records = []

    for a, b in combinations(range(10), 2):
        discovery = [e for e in range(10) if e not in (a, b)]
        alpha, obj = robust_alpha(
            y, env, base, other, discovery
        )
        pred = blend_logit(base, other, alpha)

        gains = []
        for e in (a, b):
            m = env == e
            gains.append(
                log_loss(y[m], base[m])
                - log_loss(y[m], pred[m])
            )

        records.append({
            "pair": (a, b),
            "alpha": alpha,
            "disc_worst": obj[0],
            "disc_mean": obj[1],
            "gains": gains,
            "pass": min(gains) > 0,
        })

    return records


def summarize_pair(records):
    passes = sum(r["pass"] for r in records)
    A = np.asarray([r["alpha"] for r in records], float)
    return {
        "passes": passes,
        "alpha_med": float(np.median(A)),
        "alpha_q10": float(np.quantile(A, .10)),
        "alpha_q90": float(np.quantile(A, .90)),
    }


def fixed_alpha_report(y, env, base, other, alpha):
    pred = blend_logit(base, other, alpha)
    gains = []

    for e in range(10):
        m = env == e
        gains.append(
            log_loss(y[m], base[m])
            - log_loss(y[m], pred[m])
        )

    return {
        "pred": pred,
        "ll": log_loss(y, pred),
        "auc": roc_auc_score(y, pred),
        "gain": log_loss(y, base) - log_loss(y, pred),
        "worst": float(min(gains)),
        "pos": int(sum(g > 0 for g in gains)),
        "gains": gains,
    }


def all_env_alpha(y, env, base, other):
    alpha, obj = robust_alpha(
        y, env, base, other, list(range(10))
    )
    return alpha, obj


def residual_complementarity(y, base, other):
    # Descriptive only: correlation of candidate logit with current model and
    # correlation of candidate-minus-base direction with current residual.
    zb = logit(base)
    zo = logit(other)

    corr = float(np.corrcoef(zb, zo)[0, 1])
    delta = zo - zb
    residual = y.astype(float) - base
    if np.std(delta) <= 1e-12 or np.std(residual) <= 1e-12:
        rcorr = 0.0
    else:
        rcorr = float(np.corrcoef(delta, residual)[0, 1])

    return corr, rcorr


def main():
    print("REALITYGRAPH / PARKINSON COMPLEMENTARY STACK AUDIT")
    print("----------------------------------------------------")
    print("Frozen backbone: G1 L_elong_q95 + G2 R_q90")
    print("Stack search: one non-negative convex logit weight only")
    print("Verifier: all 45 leave-two-environment futures")
    print()

    y, env, canonical, g1 = load_frozen_baseline()
    M, names = load_exact_candidate_field()
    q = M[:, names.index(Q_NAME)]
    g2 = g2_baseline(q, g1)

    print(
        "G1+G2",
        "LL", round(log_loss(y, g2), 5),
        "AUC", round(roc_auc_score(y, g2), 5),
    )

    candidates = candidate_arrays(len(y))
    print("CANDIDATES", len(candidates))

    if not candidates:
        print("VERDICT")
        print("NO_OOF_PREDICTION_ARTIFACTS_FOUND")
        return

    results = []

    for c in candidates:
        p = c["p"]
        corr, rcorr = residual_complementarity(
            y, g2, p
        )

        print()
        print(
            "===", c["name"], c["id"], "===",
        )
        print("PATH", c["path"])
        print(
            "ALONE",
            "LL", round(log_loss(y, p), 5),
            "AUC", round(roc_auc_score(y, p), 5),
            "LOGIT_CORR_G2", round(corr, 5),
            "DELTA_RESID_CORR", round(rcorr, 5),
        )

        records = pair_future(
            y, env, g2, p
        )
        s = summarize_pair(records)

        fixed = fixed_alpha_report(
            y, env, g2, p, s["alpha_med"]
        )
        ae_alpha, ae_obj = all_env_alpha(
            y, env, g2, p
        )
        ae = fixed_alpha_report(
            y, env, g2, p, ae_alpha
        )

        print(
            "PAIR",
            s["passes"], "/45",
            "ALPHA_MED", round(s["alpha_med"], 3),
            "Q10", round(s["alpha_q10"], 3),
            "Q90", round(s["alpha_q90"], 3),
        )
        print(
            "FIXED_MED",
            "LL", round(fixed["ll"], 5),
            "AUC", round(fixed["auc"], 5),
            "GAIN", round(fixed["gain"], 5),
            "WORST", round(fixed["worst"], 5),
            "POS", fixed["pos"], "/10",
        )
        print(
            "ALL_ENV_ALPHA", round(ae_alpha, 3),
            "LL", round(ae["ll"], 5),
            "AUC", round(ae["auc"], 5),
            "GAIN", round(ae["gain"], 5),
            "WORST", round(ae["worst"], 5),
            "POS", ae["pos"], "/10",
        )

        results.append({
            **c,
            "corr": corr,
            "rcorr": rcorr,
            **s,
            "fixed": fixed,
            "all_env_alpha": ae_alpha,
            "all_env": ae,
        })

    print()
    print("=== STACK COMPARISON ===")
    for r in sorted(
        results,
        key=lambda x: (-x["passes"], x["fixed"]["ll"])
    ):
        print(
            r["name"], r["id"],
            "PAIR", r["passes"], "/45",
            "A", round(r["alpha_med"], 3),
            "LL", round(r["fixed"]["ll"], 5),
            "GAIN", round(r["fixed"]["gain"], 5),
            "WORST", round(r["fixed"]["worst"], 5),
            "POS", r["fixed"]["pos"], "/10",
            "CORR", round(r["corr"], 4),
        )

    viable = [
        r for r in results
        if (
            r["passes"] >= 40
            and r["alpha_med"] > 0
            and r["fixed"]["gain"] > 1e-4
            and r["fixed"]["worst"] > 0
            and r["fixed"]["pos"] == 10
        )
    ]

    print()
    print("=== VERDICT ===")
    if viable:
        viable.sort(
            key=lambda r: (-r["passes"], r["fixed"]["ll"])
        )
        r = viable[0]
        print("COMPLEMENTARY_STACK_SURVIVES", r["name"], r["id"])
        print(
            "FREEZE_ALPHA", round(r["alpha_med"], 3),
            "LL", round(r["fixed"]["ll"], 5),
            "AUC", round(r["fixed"]["auc"], 5),
            "PAIR", r["passes"], "/45",
        )
        print("PROVENANCE_AND_DEPLOYMENT_PARITY_NEXT")
    else:
        print("NO_COMPLEMENTARY_MODEL_STACK_COMPILES")
        print("RETAIN_G1_PLUS_G2__CALIBRATION_ONLY_OR_DEPLOY")


if __name__ == "__main__":
    main()
