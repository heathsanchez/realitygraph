from __future__ import annotations

from itertools import combinations
import numpy as np

# Exact Parkinson loaders / metrics used by the retained G1/G2 experiments.
exec(open("/workspace/parkinson_finish_fast.py").read().split("def main():")[0])

Q_NAME = "R_q90"
Q_T = 2.02439
Q_D0 = 0.30
Q_D1 = -0.10

# Conservative calibration grammar.  Identity (a=1,b=0) is always present.
A_GRID = np.round(np.linspace(0.60, 1.60, 41), 6)
B_GRID = np.round(np.linspace(-0.30, 0.30, 25), 6)


def g2_baseline(q, g1):
    d = np.where(q >= Q_T, Q_D1, Q_D0)
    return sigmoid(logit(g1) + d)


def apply_cal(base, a, b):
    return sigmoid(a * logit(base) + b)


def fit_family(y, env, base, discovery_envs, family):
    if family == "TEMPERATURE":
        params = [(float(a), 0.0) for a in A_GRID]
    elif family == "BIAS":
        params = [(1.0, float(b)) for b in B_GRID]
    elif family == "AFFINE":
        params = [(float(a), float(b)) for a in A_GRID for b in B_GRID]
    else:
        raise ValueError(family)

    best = None
    for a, b in params:
        pred = apply_cal(base, a, b)
        gains = []
        for e in discovery_envs:
            m = env == e
            gains.append(
                log_loss(y[m], base[m]) - log_loss(y[m], pred[m])
            )

        worst = float(min(gains))
        mean = float(np.mean(gains))
        # Under ties, prefer the calibrator closest to identity.
        complexity = abs(a - 1.0) + abs(b)
        key = (worst, mean, -complexity, -abs(b), -abs(a - 1.0))
        if best is None or key > best[0]:
            best = (key, a, b)

    return best[1], best[2], best[0]


def pair_future(y, env, base, family):
    records = []
    for x, z in combinations(range(10), 2):
        discovery = [e for e in range(10) if e not in (x, z)]
        a, b, obj = fit_family(y, env, base, discovery, family)
        pred = apply_cal(base, a, b)

        gains = []
        for e in (x, z):
            m = env == e
            gains.append(
                log_loss(y[m], base[m]) - log_loss(y[m], pred[m])
            )

        records.append({
            "pair": (x, z),
            "a": a,
            "b": b,
            "disc_worst": obj[0],
            "disc_mean": obj[1],
            "gains": gains,
            "pass": min(gains) > 0,
        })
    return records


def summarize_pairs(family, records):
    passes = sum(r["pass"] for r in records)
    A = np.asarray([r["a"] for r in records], float)
    B = np.asarray([r["b"] for r in records], float)

    print()
    print("===", family, "PAIR FUTURES ===")
    print("PASSES", passes, "/45")

    for e in range(10):
        vals = []
        fails = []
        for r in records:
            x, z = r["pair"]
            if e not in (x, z):
                continue
            k = 0 if x == e else 1
            g = r["gains"][k]
            vals.append(g)
            if g <= 0:
                fails.append(z if x == e else x)

        print(
            "ENV", e,
            "POS", sum(v > 0 for v in vals), "/9",
            "MEAN", round(float(np.mean(vals)), 5),
            "WORST", round(float(np.min(vals)), 5),
            "FAILS_WITH", fails,
        )

    fixed = {
        "a": float(np.median(A)),
        "b": float(np.median(B)),
    }
    print(
        "PARAM_MED",
        "A", round(fixed["a"], 4),
        "B", round(fixed["b"], 4),
    )
    print(
        "PARAM_Q10",
        "A", round(float(np.quantile(A, .10)), 4),
        "B", round(float(np.quantile(B, .10)), 4),
    )
    print(
        "PARAM_Q90",
        "A", round(float(np.quantile(A, .90)), 4),
        "B", round(float(np.quantile(B, .90)), 4),
    )
    return passes, fixed


def fixed_report(family, y, env, base, fixed):
    pred = apply_cal(base, fixed["a"], fixed["b"])
    gains = []

    print()
    print("===", family, "FIXED-MEDIAN CALIBRATOR ===")
    for e in range(10):
        m = env == e
        g = log_loss(y[m], base[m]) - log_loss(y[m], pred[m])
        gains.append(float(g))
        print(
            "ENV", e,
            "GAIN", round(float(g), 5),
            "LL", round(log_loss(y[m], pred[m]), 5),
            "AUC", round(roc_auc_score(y[m], pred[m]), 5),
        )

    out = {
        "pred": pred,
        "ll": log_loss(y, pred),
        "auc": roc_auc_score(y, pred),
        "gain": log_loss(y, base) - log_loss(y, pred),
        "worst": min(gains),
        "pos": sum(g > 0 for g in gains),
        "gains": gains,
    }
    print(
        "FULL",
        "LL", round(out["ll"], 5),
        "AUC", round(out["auc"], 5),
        "GAIN", round(out["gain"], 5),
        "WORST", round(out["worst"], 5),
        "POS", out["pos"], "/10",
    )
    return out


def all_env_fit(family, y, env, base):
    a, b, obj = fit_family(y, env, base, list(range(10)), family)
    pred = apply_cal(base, a, b)
    gains = []
    for e in range(10):
        m = env == e
        gains.append(
            log_loss(y[m], base[m]) - log_loss(y[m], pred[m])
        )

    print()
    print("===", family, "ALL-ENV MAXIMIN ===")
    print("A", round(a, 4), "B", round(b, 4))
    print(
        "FULL",
        "LL", round(log_loss(y, pred), 5),
        "AUC", round(roc_auc_score(y, pred), 5),
        "GAIN", round(log_loss(y, base) - log_loss(y, pred), 5),
        "WORST", round(min(gains), 5),
        "POS", sum(g > 0 for g in gains), "/10",
    )
    return {
        "a": a,
        "b": b,
        "ll": log_loss(y, pred),
        "auc": roc_auc_score(y, pred),
        "gain": log_loss(y, base) - log_loss(y, pred),
        "worst": min(gains),
        "pos": sum(g > 0 for g in gains),
    }


def main():
    print("REALITYGRAPH / PARKINSON FINAL CALIBRATION AUDIT")
    print("--------------------------------------------------")
    print("Frozen backbone: G1 L_elong_q95 + G2 R_q90")
    print("No feature search. No model search. Calibration only.")
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

    families = ["TEMPERATURE", "BIAS", "AFFINE"]
    results = {}

    for family in families:
        records = pair_future(y, env, g2, family)
        passes, fixed = summarize_pairs(family, records)
        fixed_metrics = fixed_report(family, y, env, g2, fixed)
        all_env = all_env_fit(family, y, env, g2)
        results[family] = {
            "passes": passes,
            "fixed": fixed,
            "fixed_metrics": fixed_metrics,
            "all_env": all_env,
        }

    print()
    print("=== CALIBRATION COMPARISON ===")
    for family in families:
        r = results[family]
        m = r["fixed_metrics"]
        print(
            family,
            "PAIR", r["passes"], "/45",
            "A", round(r["fixed"]["a"], 4),
            "B", round(r["fixed"]["b"], 4),
            "LL", round(m["ll"], 5),
            "GAIN", round(m["gain"], 5),
            "WORST", round(m["worst"], 5),
            "POS", m["pos"], "/10",
        )

    viable = []
    for family, r in results.items():
        m = r["fixed_metrics"]
        if (
            r["passes"] >= 40
            and m["gain"] > 1e-4
            and m["worst"] > 0
            and m["pos"] == 10
        ):
            complexity = 1 if family != "AFFINE" else 2
            viable.append((m["ll"], complexity, family, r))

    print()
    print("=== VERDICT ===")
    if viable:
        viable.sort()
        _, _, family, r = viable[0]
        print("CALIBRATION_SURVIVES", family)
        print(
            "FREEZE",
            "A", round(r["fixed"]["a"], 4),
            "B", round(r["fixed"]["b"], 4),
            "LL", round(r["fixed_metrics"]["ll"], 5),
            "PAIR", r["passes"], "/45",
        )
        print("DEPLOYMENT_PARITY_AND_SUBMISSION_NEXT")
    else:
        print("NO_CALIBRATION_SURVIVES")
        print("DEPLOY_FROZEN_G1_PLUS_G2_UNCHANGED")


if __name__ == "__main__":
    main()
