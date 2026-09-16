from __future__ import annotations

from collections import Counter
from itertools import combinations
import numpy as np

# Exact Parkinson loaders / feature definitions / robust fitter already used by
# the previous retained-capability experiments.
exec(open("/workspace/parkinson_finish_fast.py").read().split("def main():")[0])

Q_NAME = "R_q90"
Q_T = 2.02439
Q_D0 = 0.30
Q_D1 = -0.10

# Next orthogonal family after global morphology + global magnitude:
# localized raw/reference structure. R_q95 is retained only as a tail control.
FAMILY = [
    "R_L_grid4x4_1_2_std",
    "GRAD_R_L_grid4x4_1_2_mean",
    "R_q95",
]


def g2_baseline(q, g1):
    delta = np.where(q >= Q_T, Q_D1, Q_D0)
    return sigmoid(logit(g1) + delta)


def future_gain(y, env, base, pred, e):
    m = env == e
    return log_loss(y[m], base[m]) - log_loss(y[m], pred[m])


def fit_candidate(x, y, env, base, discovery_envs):
    return robust_fit_one(
        x,
        y,
        env,
        base,
        discovery_envs,
    )


def law_key(law):
    return (
        law["worst"],
        law["mean"],
        -(abs(law["d0"]) + abs(law["d1"])),
    )


def pair_screen(name, x, y, env, base):
    records = []
    for a, b in combinations(range(10), 2):
        discovery = [e for e in range(10) if e not in (a, b)]
        law = fit_candidate(x, y, env, base, discovery)
        if law is None:
            records.append({
                "pair": (a, b),
                "law": None,
                "gains": [0.0, 0.0],
                "pass": False,
            })
            continue

        pred = apply_law(x, base, law)
        gains = [
            future_gain(y, env, base, pred, a),
            future_gain(y, env, base, pred, b),
        ]
        records.append({
            "pair": (a, b),
            "law": law,
            "gains": gains,
            "pass": min(gains) > 0,
        })
    return records


def summarize_candidate(name, records):
    usable = [r for r in records if r["law"] is not None]
    passes = sum(r["pass"] for r in usable)

    print()
    print("===", name, "PAIR FUTURES ===")
    print("PASSES", passes, "/45")

    for e in range(10):
        vals = []
        fails = []
        for r in usable:
            a, b = r["pair"]
            if e not in (a, b):
                continue
            k = 0 if a == e else 1
            g = r["gains"][k]
            vals.append(g)
            if g <= 0:
                fails.append(b if a == e else a)
        print(
            "ENV", e,
            "POS", sum(v > 0 for v in vals), "/9",
            "MEAN", round(float(np.mean(vals)), 5),
            "WORST", round(float(np.min(vals)), 5),
            "FAILS_WITH", fails,
        )

    laws = [r["law"] for r in usable]
    T = np.asarray([law["threshold"] for law in laws], float)
    D0 = np.asarray([law["d0"] for law in laws], float)
    D1 = np.asarray([law["d1"] for law in laws], float)

    fixed = {
        "threshold": float(np.median(T)),
        "d0": float(np.median(D0)),
        "d1": float(np.median(D1)),
    }

    print(
        "PARAM_MED",
        "T", round(fixed["threshold"], 6),
        "D0", round(fixed["d0"], 3),
        "D1", round(fixed["d1"], 3),
    )
    print(
        "PARAM_Q10",
        "T", round(float(np.quantile(T, .10)), 6),
        "D0", round(float(np.quantile(D0, .10)), 3),
        "D1", round(float(np.quantile(D1, .10)), 3),
    )
    print(
        "PARAM_Q90",
        "T", round(float(np.quantile(T, .90)), 6),
        "D0", round(float(np.quantile(D0, .90)), 3),
        "D1", round(float(np.quantile(D1, .90)), 3),
    )

    return passes, fixed


def fixed_report(name, x, y, env, base, fixed):
    pred = apply_law(x, base, fixed)
    gains = []

    print()
    print("===", name, "FIXED-MEDIAN LAW ===")
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

    print(
        "FULL",
        "LL", round(log_loss(y, pred), 5),
        "AUC", round(roc_auc_score(y, pred), 5),
        "GAIN", round(log_loss(y, base) - log_loss(y, pred), 5),
        "WORST", round(min(gains), 5),
        "POS", sum(g > 0 for g in gains), "/10",
    )

    return {
        "ll": log_loss(y, pred),
        "auc": roc_auc_score(y, pred),
        "gain": log_loss(y, base) - log_loss(y, pred),
        "worst": min(gains),
        "pos": sum(g > 0 for g in gains),
    }


def selector_screen(M, names, y, env, base):
    records = []

    for a, b in combinations(range(10), 2):
        discovery = [e for e in range(10) if e not in (a, b)]
        best = None

        for name in FAMILY:
            j = names.index(name)
            law = fit_candidate(
                M[:, j], y, env, base, discovery
            )
            if law is None:
                continue
            key = law_key(law)
            if best is None or key > best[0]:
                best = (key, name, j, law)

        if best is None:
            records.append({
                "pair": (a, b),
                "name": None,
                "gains": [0.0, 0.0],
                "pass": False,
            })
            continue

        _, name, j, law = best
        pred = apply_law(M[:, j], base, law)
        gains = [
            future_gain(y, env, base, pred, a),
            future_gain(y, env, base, pred, b),
        ]
        records.append({
            "pair": (a, b),
            "name": name,
            "law": law,
            "gains": gains,
            "pass": min(gains) > 0,
        })

    return records


def summarize_selector(records):
    passes = sum(r["pass"] for r in records)
    counts = Counter(
        r["name"] for r in records if r["name"] is not None
    )

    print()
    print("=== DISCOVERY-ONLY FAMILY SELECTOR ===")
    print("PASSES", passes, "/45")
    print("COUNTS", dict(counts))

    for e in range(10):
        vals = []
        fails = []
        for r in records:
            a, b = r["pair"]
            if e not in (a, b):
                continue
            k = 0 if a == e else 1
            g = r["gains"][k]
            vals.append(g)
            if g <= 0:
                fails.append(b if a == e else a)

        print(
            "ENV", e,
            "POS", sum(v > 0 for v in vals), "/9",
            "MEAN", round(float(np.mean(vals)), 5),
            "WORST", round(float(np.min(vals)), 5),
            "FAILS_WITH", fails,
        )

    return passes, counts


def main():
    print("REALITYGRAPH / PARKINSON G3 SPATIAL-FAMILY SCREEN")
    print("---------------------------------------------------")
    print("G1 frozen: L_elong_q95")
    print("G2 frozen: R_q90 T=2.02439 D=[+0.30,-0.10]")
    print("Search space: localized raw/reference structure only")
    print("Tail magnitude R_q95 is a control")
    print("All 45 two-environment futures")
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

    results = {}
    for name in FAMILY:
        j = names.index(name)
        records = pair_screen(
            name, M[:, j], y, env, g2
        )
        passes, fixed = summarize_candidate(name, records)
        metrics = fixed_report(
            name, M[:, j], y, env, g2, fixed
        )
        results[name] = {
            "passes": passes,
            "fixed": fixed,
            **metrics,
        }

    selector_records = selector_screen(
        M, names, y, env, g2
    )
    selector_passes, selector_counts = summarize_selector(
        selector_records
    )

    print()
    print("=== COMPARISON ===")
    for name in FAMILY:
        r = results[name]
        print(
            name,
            "PAIR", r["passes"], "/45",
            "LL", round(r["ll"], 5),
            "AUC", round(r["auc"], 5),
            "GAIN", round(r["gain"], 5),
            "WORST", round(r["worst"], 5),
            "POS", r["pos"], "/10",
        )

    # Family-discovery gate only. If this passes we freeze the winning boundary
    # in a separate prospective test; we do not deploy directly from this run.
    viable = []
    for name, r in results.items():
        if (
            r["passes"] >= 40
            and r["pos"] == 10
            and r["worst"] > 0
            and r["gain"] > 1e-4
        ):
            viable.append((-r["passes"], r["ll"], name))

    print()
    print("=== VERDICT ===")
    if viable:
        viable.sort()
        _, _, winner = viable[0]
        print("SPATIAL_G3_FAMILY_SURVIVES", winner)
        print("FREEZE_ITS_BOUNDARY_AND_RUN_PROSPECTIVE_CAUSAL_TEST_NEXT")
    elif selector_passes >= 40:
        print("SPATIAL_PORTFOLIO_TRANSFERS_BUT_NO_SINGLE_FAMILY_DOMINATES")
        print("COMPILE_SELECTIVE_ROUTER_NEXT")
    else:
        print("NO_SPATIAL_SUMMARY_G3_COMPILES")
        print("MOVE_TO_ALIGNED_RAW_REFERENCE_PIXEL_OPERATOR")


if __name__ == "__main__":
    main()
