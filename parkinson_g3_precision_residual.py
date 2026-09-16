from __future__ import annotations

from itertools import combinations
import numpy as np

# Reuse the exact Parkinson loaders and metric implementations already checked
# in the finish-fast / positive-signal experiments.
exec(open("/workspace/parkinson_finish_fast.py").read().split("def main():")[0])

Q_NAME = "R_q90"
G_NAME = "GRAD_R_q80"

# Frozen G2 law recovered exactly by the corrected 45-pair experiment.
Q_T = 2.02439
Q_D0 = 0.30
Q_D1 = -0.10

# Frozen gradient boundary from the repeated env1 tournament family.
G_T = 0.14039

# G3 is deliberately tiny.  We only allow residual corrections around the
# already frozen G1+G2 system.
GRID = np.round(np.linspace(-0.60, 0.80, 29), 10)
TOL = 1e-12


def g2_baseline(q, g1):
    delta = np.where(q >= Q_T, Q_D1, Q_D0)
    return sigmoid(logit(g1) + delta)


def state_masks(q, g):
    qh = q >= Q_T
    gh = g >= G_T
    return qh, gh


def policy_design(name, qh, gh):
    """Return integer state ids and the number of learnable residual cells.

    Every family preserves exact G1+G2 predictions outside its stated residual
    support.  This prevents the G3 search from silently recalibrating G2.
    """
    n = len(qh)

    if name == "XOR_SHARED":
        # One shared correction iff magnitude and boundary disagree.
        active = np.logical_xor(qh, gh)
        state = np.where(active, 0, -1).astype(np.int8)
        return state, 1

    if name == "DISAGREE_SEPARATE":
        # Separate correction for the two disagreement directions:
        # 0 = q-low / grad-high
        # 1 = q-high / grad-low
        state = np.full(n, -1, dtype=np.int8)
        state[(~qh) & gh] = 0
        state[qh & (~gh)] = 1
        return state, 2

    if name == "QLOW_GHIGH_ONLY":
        state = np.where((~qh) & gh, 0, -1).astype(np.int8)
        return state, 1

    if name == "QHIGH_GLOW_ONLY":
        state = np.where(qh & (~gh), 0, -1).astype(np.int8)
        return state, 1

    if name == "GRAD_RESIDUAL":
        # One residual correction by gradient state, but still around frozen G2.
        state = gh.astype(np.int8)
        return state, 2

    raise ValueError(name)


def precompute(y, env, base, state, n_cells, discovery_envs):
    z = logit(base)
    base_row = row_loss(y, base)

    envs = list(discovery_envs)
    E = len(envs)
    K = len(GRID)

    base_loss = np.zeros(E, dtype=float)
    const_loss = np.zeros(E, dtype=float)
    cell_loss = np.zeros((n_cells, E, K), dtype=float)

    for ei, e in enumerate(envs):
        ids_e = np.where(env == e)[0]
        n = len(ids_e)
        base_loss[ei] = float(base_row[ids_e].mean())

        inactive = ids_e[state[ids_e] < 0]
        if len(inactive):
            const_loss[ei] = float(base_row[inactive].sum()) / n

        for c in range(n_cells):
            ids = ids_e[state[ids_e] == c]
            if len(ids) == 0:
                continue
            pp = sigmoid(z[ids][None, :] + GRID[:, None])
            yy = y[ids][None, :]
            loss = -(
                yy * np.log(clip_p(pp))
                + (1 - yy) * np.log(clip_p(1 - pp))
            ).sum(axis=1) / n
            cell_loss[c, ei, :] = loss

    return base_loss, const_loss, cell_loss


def objective_from_losses(base_loss, const_loss, cell_loss, indices):
    total = const_loss.copy()
    for c, k in enumerate(indices):
        total += cell_loss[c, :, k]
    gains = base_loss - total
    worst = float(np.min(gains))
    mean = float(np.mean(gains))
    l1 = float(sum(abs(GRID[k]) for k in indices))
    return worst, mean, -l1


def fit_exact(y, env, base, state, n_cells, discovery_envs):
    base_loss, const_loss, cell_loss = precompute(
        y, env, base, state, n_cells, discovery_envs
    )
    K = len(GRID)

    if n_cells == 1:
        best = None
        for a in range(K):
            obj = objective_from_losses(
                base_loss, const_loss, cell_loss, [a]
            )
            key = (*obj, -a)
            if best is None or key > best[0]:
                best = (key, [a])
        indices = best[1]

    elif n_cells == 2:
        best = None
        for a in range(K):
            for b in range(K):
                obj = objective_from_losses(
                    base_loss, const_loss, cell_loss, [a, b]
                )
                key = (*obj, -a, -b)
                if best is None or key > best[0]:
                    best = (key, [a, b])
        indices = best[1]

    else:
        raise ValueError(n_cells)

    obj = objective_from_losses(
        base_loss, const_loss, cell_loss, indices
    )

    # Backward deletion: a residual cell survives only if zeroing it does not
    # improve the frozen lexicographic verifier objective.
    zero = int(np.argmin(np.abs(GRID)))
    changed = True
    while changed:
        changed = False
        for c in range(n_cells):
            if indices[c] == zero:
                continue
            trial = list(indices)
            trial[c] = zero
            trial_obj = objective_from_losses(
                base_loss, const_loss, cell_loss, trial
            )
            if trial_obj >= obj:
                indices = trial
                obj = trial_obj
                changed = True

    deltas = np.array([GRID[k] for k in indices], dtype=float)
    return deltas, obj


def apply_policy(base, state, deltas):
    correction = np.zeros(len(base), dtype=float)
    for c, delta in enumerate(deltas):
        correction[state == c] = delta
    return sigmoid(logit(base) + correction)


def gains_by_env(y, env, base, pred):
    out = {}
    for e in sorted(np.unique(env)):
        m = env == e
        out[int(e)] = (
            log_loss(y[m], base[m])
            - log_loss(y[m], pred[m])
        )
    return out


def pair_future(name, y, env, base, state, n_cells):
    records = []
    for a, b in combinations(range(10), 2):
        discovery = [e for e in range(10) if e not in (a, b)]
        deltas, obj = fit_exact(
            y, env, base, state, n_cells, discovery
        )
        pred = apply_policy(base, state, deltas)

        future_gains = []
        for e in (a, b):
            m = env == e
            future_gains.append(
                log_loss(y[m], base[m])
                - log_loss(y[m], pred[m])
            )

        records.append({
            "pair": (a, b),
            "deltas": deltas,
            "disc_worst": obj[0],
            "disc_mean": obj[1],
            "future_gains": future_gains,
            "pass": min(future_gains) > 0,
        })

    return records


def summarize_pair(name, records):
    passes = sum(r["pass"] for r in records)
    D = np.stack([r["deltas"] for r in records])
    med = np.median(D, axis=0)

    print()
    print("===", name, "PAIR FUTURES ===")
    print("PASSES", passes, "/45")

    for e in range(10):
        vals = []
        fails = []
        for r in records:
            a, b = r["pair"]
            if e not in (a, b):
                continue
            k = 0 if a == e else 1
            g = r["future_gains"][k]
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

    print("DELTA_MED", [round(float(x), 3) for x in med])
    print(
        "DELTA_Q10",
        [round(float(x), 3) for x in np.quantile(D, .10, axis=0)],
    )
    print(
        "DELTA_Q90",
        [round(float(x), 3) for x in np.quantile(D, .90, axis=0)],
    )
    return passes, med


def fixed_report(name, y, env, base, state, deltas):
    pred = apply_policy(base, state, deltas)
    gains = gains_by_env(y, env, base, pred)

    print()
    print("===", name, "FIXED-MEDIAN G3 ===")
    print("DELTAS", [round(float(x), 3) for x in deltas])
    for e in range(10):
        m = env == e
        print(
            "ENV", e,
            "GAIN", round(float(gains[e]), 5),
            "LL", round(log_loss(y[m], pred[m]), 5),
            "AUC", round(roc_auc_score(y[m], pred[m]), 5),
        )

    print(
        "FULL",
        "LL", round(log_loss(y, pred), 5),
        "AUC", round(roc_auc_score(y, pred), 5),
        "GAIN", round(log_loss(y, base) - log_loss(y, pred), 5),
        "WORST", round(min(gains.values()), 5),
        "POS", sum(v > 0 for v in gains.values()), "/10",
    )
    return pred, gains


def main():
    print("REALITYGRAPH / PARKINSON G3 PRECISION RESIDUAL")
    print("-----------------------------------------------")
    print("G1 frozen: L_elong_q95")
    print("G2 frozen: R_q90 T=2.02439 D=[+0.30,-0.10]")
    print("G3 may alter only residual states around frozen G1+G2.")
    print("No threshold search. No G1/G2 recalibration.")
    print()

    y, env, canonical, g1 = load_frozen_baseline()
    M, names = load_exact_candidate_field()
    q = M[:, names.index(Q_NAME)]
    g = M[:, names.index(G_NAME)]

    g2 = g2_baseline(q, g1)
    qh, gh = state_masks(q, g)

    print(
        "G1",
        "LL", round(log_loss(y, g1), 5),
        "AUC", round(roc_auc_score(y, g1), 5),
    )
    print(
        "G1+G2",
        "LL", round(log_loss(y, g2), 5),
        "AUC", round(roc_auc_score(y, g2), 5),
        "GAIN_FROM_G1", round(log_loss(y, g1) - log_loss(y, g2), 5),
    )

    # State census matters: we want to know exactly where the remaining
    # evidence lives rather than treating gradient as a generic feature.
    print()
    print("=== STATE CENSUS ===")
    for label, mask in [
        ("QLOW_GLOW", (~qh) & (~gh)),
        ("QLOW_GHIGH", (~qh) & gh),
        ("QHIGH_GLOW", qh & (~gh)),
        ("QHIGH_GHIGH", qh & gh),
    ]:
        ids = np.where(mask)[0]
        prev = float(np.mean(y[ids])) if len(ids) else float("nan")
        print(label, "N", len(ids), "PREV", round(prev, 5))

    families = [
        "XOR_SHARED",
        "DISAGREE_SEPARATE",
        "QLOW_GHIGH_ONLY",
        "QHIGH_GLOW_ONLY",
        "GRAD_RESIDUAL",
    ]

    results = {}
    for name in families:
        state, n_cells = policy_design(name, qh, gh)
        records = pair_future(
            name, y, env, g2, state, n_cells
        )
        passes, med = summarize_pair(name, records)
        pred, gains = fixed_report(
            name, y, env, g2, state, med
        )

        results[name] = {
            "passes": passes,
            "ll": log_loss(y, pred),
            "auc": roc_auc_score(y, pred),
            "gain": log_loss(y, g2) - log_loss(y, pred),
            "worst": min(gains.values()),
            "pos": sum(v > 0 for v in gains.values()),
            "deltas": med,
        }

    print()
    print("=== G3 COMPARISON ===")
    for name in families:
        r = results[name]
        print(
            name,
            "PAIR", r["passes"], "/45",
            "LL", round(r["ll"], 5),
            "AUC", round(r["auc"], 5),
            "GAIN", round(r["gain"], 5),
            "WORST", round(r["worst"], 5),
            "POS", r["pos"], "/10",
            "D", [round(float(x), 3) for x in r["deltas"]],
        )

    # Conservative compile rule.  Pair-future recurrence must be at least as
    # strong as the now-established G2 result (43/45) unless the law is a
    # single-cell specialization with strictly positive 10/10 fixed gains.
    viable = []
    for name, r in results.items():
        if (
            r["passes"] >= 43
            and r["pos"] == 10
            and r["worst"] > 0
            and r["gain"] > 1e-4
        ):
            viable.append((r["ll"], name, r))

    print()
    print("=== VERDICT ===")
    if viable:
        viable.sort()
        _, name, r = viable[0]
        print("G3_COMPILES", name)
        print(
            "FROZEN_G3",
            "DELTAS", [round(float(x), 3) for x in r["deltas"]],
            "LL", round(r["ll"], 5),
            "AUC", round(r["auc"], 5),
            "PAIR", r["passes"], "/45",
            "WORST", round(r["worst"], 5),
        )
    else:
        print("NO_G3_GRADIENT_RESIDUAL_COMPILES")
        print("RETAIN_G1_PLUS_G2_AND_MOVE_TO_NEXT_ORTHOGONAL_FAMILY")


if __name__ == "__main__":
    main()
