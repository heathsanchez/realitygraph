from __future__ import annotations

from itertools import combinations

import numpy as np
from sklearn.metrics import log_loss

exec(open("/workspace/parkinson_finish_fast.py").read().split("def main():")[0])

T0 = 2.02439
D00 = 0.30
D10 = -0.10
NAME = "R_q90"


def gains_for(q, y, env, frozen):
    return {
        e: float(
            log_loss(y[env == e], frozen[env == e])
            - log_loss(y[env == e], q[env == e])
        )
        for e in range(10)
    }


def evaluate_combo(x, y, env, frozen, discovery, T, D0, D1):
    q = apply_law(
        x,
        frozen,
        {"threshold": float(T), "d0": float(D0), "d1": float(D1)},
    )
    g = gains_for(q, y, env, frozen)
    vals = [g[e] for e in discovery]
    return min(vals), float(np.mean(vals)), q


def choose(candidates):
    best = None
    for item in candidates:
        worst, mean, simplicity, payload = item
        key = (worst, mean, simplicity)
        if best is None or key > best[0]:
            best = (key, payload)
    return best[1]


def fit_fixed_t(x, y, env, frozen, discovery):
    cand = []
    for d0 in DELTAS:
        for d1 in DELTAS:
            worst, mean, _ = evaluate_combo(
                x, y, env, frozen, discovery, T0, d0, d1
            )
            cand.append(
                (worst, mean, -(abs(d0) + abs(d1)),
                 {"threshold": T0, "d0": float(d0), "d1": float(d1)})
            )
    return choose(cand)


def fit_fixed_deltas(x, y, env, frozen, discovery):
    values = x[np.isin(env, discovery)]
    ts = candidate_thresholds(values)
    cand = []
    for t in ts:
        worst, mean, _ = evaluate_combo(
            x, y, env, frozen, discovery, t, D00, D10
        )
        cand.append(
            (worst, mean, -abs(float(t) - T0),
             {"threshold": float(t), "d0": D00, "d1": D10})
        )
    return choose(cand)


def fit_d1_only(x, y, env, frozen, discovery):
    cand = []
    for d1 in DELTAS:
        worst, mean, _ = evaluate_combo(
            x, y, env, frozen, discovery, T0, D00, d1
        )
        cand.append(
            (worst, mean, -abs(float(d1) - D10),
             {"threshold": T0, "d0": D00, "d1": float(d1)})
        )
    return choose(cand)


def fit_d0_only(x, y, env, frozen, discovery):
    cand = []
    for d0 in DELTAS:
        worst, mean, _ = evaluate_combo(
            x, y, env, frozen, discovery, T0, d0, D10
        )
        cand.append(
            (worst, mean, -abs(float(d0) - D00),
             {"threshold": T0, "d0": float(d0), "d1": D10})
        )
    return choose(cand)


def held_gains(x, y, env, frozen, pair, law):
    q = apply_law(x, frozen, law)
    return [
        float(
            log_loss(y[env == e], frozen[env == e])
            - log_loss(y[env == e], q[env == e])
        )
        for e in pair
    ]


def run_regime(label, fitter, x, y, env, frozen):
    print()
    print("===", label, "===")
    records = []

    for pair in combinations(range(10), 2):
        discovery = [e for e in range(10) if e not in pair]
        law = fitter(x, y, env, frozen, discovery)
        gs = held_gains(x, y, env, frozen, pair, law)
        ok = min(gs) > 0
        records.append((pair, law, gs, ok))

        print(
            pair,
            "T", round(law["threshold"], 4),
            "D", round(law["d0"], 2), round(law["d1"], 2),
            "GAINS", round(gs[0], 5), round(gs[1], 5),
            "PASS" if ok else "FAIL",
        )

    print("PASSES", sum(r[-1] for r in records), "/45")

    for e in range(10):
        vals = []
        fails = []
        for pair, law, gs, ok in records:
            if e not in pair:
                continue
            k = 0 if pair[0] == e else 1
            vals.append(gs[k])
            if gs[k] <= 0:
                fails.append(pair[1 - k])

        print(
            "ENV", e,
            "POS", sum(v > 0 for v in vals), "/9",
            "MEAN", round(float(np.mean(vals)), 5),
            "WORST", round(float(np.min(vals)), 5),
            "FAILS_WITH", fails,
        )

    return records


def main():
    y, env, canonical, frozen = load_frozen_baseline()
    M, names = load_exact_candidate_field()
    j = names.index(NAME)
    x = M[:, j]

    print("REALITYGRAPH / SECOND-LAW WITNESS LOCALISATION")
    print("------------------------------------------------")
    print("Feature frozen:", NAME)
    print("Reference law:", T0, D00, D10)
    print()

    q0 = apply_law(
        x, frozen,
        {"threshold": T0, "d0": D00, "d1": D10},
    )
    g0 = gains_for(q0, y, env, frozen)
    print(
        "FULL-FIXED CONTROL",
        "POS", sum(g0[e] > 0 for e in range(10)), "/10",
        "WORST", round(min(g0.values()), 5),
    )

    r_t = run_regime(
        "T FIXED / REFIT BOTH DELTAS",
        fit_fixed_t, x, y, env, frozen
    )
    r_d = run_regime(
        "DELTAS FIXED / REFIT THRESHOLD",
        fit_fixed_deltas, x, y, env, frozen
    )
    r_d1 = run_regime(
        "T + D0 FIXED / REFIT D1 ONLY",
        fit_d1_only, x, y, env, frozen
    )
    r_d0 = run_regime(
        "T + D1 FIXED / REFIT D0 ONLY",
        fit_d0_only, x, y, env, frozen
    )

    scores = {
        "REFIT_BOTH_DELTAS": sum(r[-1] for r in r_t),
        "REFIT_THRESHOLD": sum(r[-1] for r in r_d),
        "REFIT_D1": sum(r[-1] for r in r_d1),
        "REFIT_D0": sum(r[-1] for r in r_d0),
    }

    print()
    print("=== SUMMARY ===")
    for k, v in scores.items():
        print(k, v, "/45")

    best = max(scores, key=scores.get)
    print()
    print("=== VERDICT ===")
    if scores["REFIT_THRESHOLD"] >= 40 and scores["REFIT_BOTH_DELTAS"] < 30:
        print("DELTA_CALIBRATION_IS_THE_WITNESS_DEPENDENT_LAYER")
    elif scores["REFIT_BOTH_DELTAS"] >= 40 and scores["REFIT_THRESHOLD"] < 30:
        print("THRESHOLD_IS_THE_WITNESS_DEPENDENT_LAYER")
    elif scores["REFIT_D1"] >= 40 and scores["REFIT_D0"] < 30:
        print("D0_IS_THE_WITNESS_DEPENDENT_LAYER")
    elif scores["REFIT_D0"] >= 40 and scores["REFIT_D1"] < 30:
        print("D1_IS_THE_WITNESS_DEPENDENT_LAYER")
    elif max(scores.values()) < 30:
        print("ENTIRE_SECOND_LAW_CALIBRATION_IS_WITNESS_DEPENDENT__STOP_CERTIFICATION")
    else:
        print("MIXED_PARAMETER_DEPENDENCE__FREEZE_ONLY_STABLE_COORDINATES")
    print("BEST_REGIME", best, scores[best], "/45")


if __name__ == "__main__":
    main()
