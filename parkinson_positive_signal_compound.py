from __future__ import annotations

from itertools import combinations
import numpy as np

# Reuse the exact frozen G1 and exact candidate generator already checked in
# parkinson_finish_fast.py.  This keeps the experiment on the same data,
# preprocessing, and morphology semantics as the previous evidence.
exec(open("/workspace/parkinson_finish_fast.py").read().split("def main():")[0])

Q_NAME = "R_q90"
G_NAME = "GRAD_R_q80"

# Frozen from prior independent evidence:
# - Q threshold is the 10/10-positive fixed R_q90 law.
# - G threshold is the recurring centre of the leave-future GRAD_R_q80 fits.
Q_T = 2.02439
G_T = 0.14039

# Only correction magnitudes are learned in this experiment.
DELTA_GRID = np.round(np.linspace(-0.80, 0.80, 33), 10)
MAX_COORD_ITERS = 12
TOL = 1e-12


def cells_for(kind, q, g):
    if kind == "Q":
        return (q >= Q_T).astype(np.int8), 2
    if kind == "G":
        return (g >= G_T).astype(np.int8), 2
    if kind == "QxG":
        return ((q >= Q_T).astype(np.int8) * 2
                + (g >= G_T).astype(np.int8)), 4
    raise ValueError(kind)


def build_loss_tables(y, env, base, cells, n_cells, discovery_envs):
    z = logit(base)
    base_row = row_loss(y, base)

    tables = {}
    counts = {}
    base_loss = {}

    for e in discovery_envs:
        ids_e = np.where(env == e)[0]
        counts[e] = len(ids_e)
        base_loss[e] = float(base_row[ids_e].mean())
        tables[e] = []

        for c in range(n_cells):
            ids = ids_e[cells[ids_e] == c]
            if len(ids) == 0:
                tables[e].append(np.zeros(len(DELTA_GRID), dtype=float))
                continue

            pp = sigmoid(z[ids][None, :] + DELTA_GRID[:, None])
            yy = y[ids][None, :]
            loss = -(
                yy * np.log(clip_p(pp))
                + (1 - yy) * np.log(clip_p(1 - pp))
            ).sum(axis=1)
            tables[e].append(loss)

    return tables, counts, base_loss


def objective(indices, tables, counts, base_loss, discovery_envs):
    gains = []
    for e in discovery_envs:
        total = 0.0
        for c, k in enumerate(indices):
            total += tables[e][c][k]
        new_loss = total / counts[e]
        gains.append(base_loss[e] - new_loss)

    worst = float(np.min(gains))
    mean = float(np.mean(gains))
    l1 = float(sum(abs(DELTA_GRID[k]) for k in indices))
    return worst, mean, -l1


def fit_policy(y, env, base, cells, n_cells, discovery_envs):
    """Exact discrete maximin optimization.

    The first version used one-coordinate-at-a-time ascent from zero.  That
    can falsely declare zero optimal when a useful law requires two or more
    corrections to move together (exactly the known R_q90 +0.30/-0.10 case).
    Here we solve the frozen grid globally.  Two-cell policies are exhaustively
    enumerated.  Four-cell QxG policies are exhaustively enumerated in chunks,
    so the result is still exact without allocating the full 33^4 tensor.
    """
    tables, counts, base_loss = build_loss_tables(
        y, env, base, cells, n_cells, discovery_envs
    )

    envs = list(discovery_envs)
    E = len(envs)
    K = len(DELTA_GRID)

    # loss[c, e, k] = mean-loss contribution of cell c in environment e
    loss = np.zeros((n_cells, E, K), dtype=np.float64)
    base_vec = np.zeros(E, dtype=np.float64)
    for ei, e in enumerate(envs):
        base_vec[ei] = base_loss[e]
        for cc in range(n_cells):
            loss[cc, ei, :] = tables[e][cc] / counts[e]

    def score_totals(total_loss, l1):
        gains = base_vec - total_loss
        worst = np.min(gains, axis=-1)
        mean = np.mean(gains, axis=-1)
        return worst, mean, -l1

    if n_cells == 2:
        total = (
            loss[0, :, :, None].transpose(1, 2, 0)
            + loss[1, :, None, :].transpose(1, 2, 0)
        )
        # total is K x K x E
        l1 = (
            np.abs(DELTA_GRID)[:, None]
            + np.abs(DELTA_GRID)[None, :]
        )
        worst, mean, simplicity = score_totals(total, l1)

        flat = np.arange(K * K)
        # lexicographic: worst, then mean, then smaller L1
        order = np.lexsort((
            flat,
            -simplicity.ravel(),
            -mean.ravel(),
            -worst.ravel(),
        ))
        best = int(order[0])
        i, j = np.unravel_index(best, (K, K))
        indices = [i, j]

    elif n_cells == 4:
        # Exact 33^4 search, chunked over the first-pair state space.
        pair01 = []
        pair23 = []
        pair_l1 = []
        for i in range(K):
            for j in range(K):
                pair01.append(loss[0, :, i] + loss[1, :, j])
                pair23.append(loss[2, :, i] + loss[3, :, j])
                pair_l1.append(abs(DELTA_GRID[i]) + abs(DELTA_GRID[j]))

        pair01 = np.asarray(pair01, dtype=np.float64)
        pair23 = np.asarray(pair23, dtype=np.float64)
        pair_l1 = np.asarray(pair_l1, dtype=np.float64)

        best_key = None
        best_pair = None
        P = K * K
        chunk = 48

        for start in range(0, P, chunk):
            stop = min(start + chunk, P)
            totals = pair01[start:stop, None, :] + pair23[None, :, :]
            gains = base_vec[None, None, :] - totals
            worst = gains.min(axis=2)
            mean = gains.mean(axis=2)
            l1 = pair_l1[start:stop, None] + pair_l1[None, :]

            # Find the best point in this chunk by the exact same lexicographic
            # objective used everywhere else.
            for local_i in range(stop - start):
                for p23 in range(P):
                    key = (
                        float(worst[local_i, p23]),
                        float(mean[local_i, p23]),
                        -float(l1[local_i, p23]),
                        -(start + local_i),
                        -p23,
                    )
                    if best_key is None or key > best_key:
                        best_key = key
                        best_pair = (start + local_i, p23)

        p01, p23 = best_pair
        i0, i1 = divmod(p01, K)
        i2, i3 = divmod(p23, K)
        indices = [i0, i1, i2, i3]

    else:
        raise ValueError(f"unsupported cell count: {n_cells}")

    current_obj = objective(
        indices, tables, counts, base_loss, discovery_envs
    )

    # Backward deletion remains exact: zero any distinction that does not
    # still earn its place under the frozen global optimum.
    zero_k = int(np.argmin(np.abs(DELTA_GRID)))
    changed = True
    while changed:
        changed = False
        for cc in range(n_cells):
            if indices[cc] == zero_k:
                continue
            trial = list(indices)
            trial[cc] = zero_k
            obj = objective(
                trial, tables, counts, base_loss, discovery_envs
            )
            if obj >= current_obj:
                indices = trial
                current_obj = obj
                changed = True

    deltas = np.array([DELTA_GRID[k] for k in indices], dtype=float)
    return deltas, current_obj


def apply_policy(base, cells, deltas):
    return sigmoid(logit(base) + deltas[cells])


def env_gains(y, env, base, pred):
    out = {}
    for e in sorted(np.unique(env)):
        m = env == e
        out[int(e)] = (
            log_loss(y[m], base[m])
            - log_loss(y[m], pred[m])
        )
    return out


def pair_future_test(kind, y, env, base, q, g):
    cells, n_cells = cells_for(kind, q, g)
    records = []

    for a, b in combinations(range(10), 2):
        discovery = [e for e in range(10) if e not in (a, b)]
        deltas, obj = fit_policy(
            y, env, base, cells, n_cells, discovery
        )
        pred = apply_policy(base, cells, deltas)

        gains = []
        for e in (a, b):
            m = env == e
            gains.append(
                log_loss(y[m], base[m])
                - log_loss(y[m], pred[m])
            )

        records.append({
            "pair": (a, b),
            "deltas": deltas,
            "disc_worst": obj[0],
            "disc_mean": obj[1],
            "gains": gains,
            "pass": min(gains) > 0,
        })

    return records, cells, n_cells


def summarize_pairs(kind, records):
    passes = sum(r["pass"] for r in records)
    print()
    print("===", kind, "PAIR FUTURES ===")
    print("PASSES", passes, "/45")

    for e in range(10):
        vals = []
        fails = []
        for r in records:
            a, b = r["pair"]
            if e not in (a, b):
                continue
            k = 0 if a == e else 1
            vals.append(r["gains"][k])
            if r["gains"][k] <= 0:
                fails.append(b if a == e else a)

        print(
            "ENV", e,
            "POS", sum(v > 0 for v in vals), "/9",
            "MEAN", round(float(np.mean(vals)), 5),
            "WORST", round(float(np.min(vals)), 5),
            "FAILS_WITH", fails,
        )

    D = np.stack([r["deltas"] for r in records], axis=0)
    med = np.median(D, axis=0)
    q10 = np.quantile(D, .10, axis=0)
    q90 = np.quantile(D, .90, axis=0)

    print("DELTA_MED", [round(float(x), 3) for x in med])
    print("DELTA_Q10", [round(float(x), 3) for x in q10])
    print("DELTA_Q90", [round(float(x), 3) for x in q90])

    return passes, med


def fixed_policy_report(kind, y, env, base, cells, deltas):
    pred = apply_policy(base, cells, deltas)
    gains = env_gains(y, env, base, pred)

    print()
    print("===", kind, "FIXED-MEDIAN POLICY ===")
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


def full_fit_report(kind, y, env, base, cells, n_cells):
    deltas, obj = fit_policy(
        y, env, base, cells, n_cells, list(range(10))
    )
    pred = apply_policy(base, cells, deltas)
    gains = env_gains(y, env, base, pred)

    print()
    print("===", kind, "ALL-ENV MAXIMIN FIT ===")
    print("DELTAS", [round(float(x), 3) for x in deltas])
    print(
        "FULL",
        "LL", round(log_loss(y, pred), 5),
        "AUC", round(roc_auc_score(y, pred), 5),
        "GAIN", round(log_loss(y, base) - log_loss(y, pred), 5),
        "WORST", round(min(gains.values()), 5),
        "POS", sum(v > 0 for v in gains.values()), "/10",
    )
    return pred, gains, deltas


def main():
    print("REALITYGRAPH / PARKINSON POSITIVE-SIGNAL COMPOUND")
    print("--------------------------------------------------")
    print("G1 frozen: L_elong_q95 capability")
    print("Q frozen boundary:", Q_NAME, "<", Q_T)
    print("G frozen boundary:", G_NAME, "<", G_T)
    print("Only correction magnitudes are allowed to learn.")
    print("Verifier: every natural environment separately.")
    print()

    y, env, canonical, g1 = load_frozen_baseline()
    M, names = load_exact_candidate_field()

    q = M[:, names.index(Q_NAME)]
    g = M[:, names.index(G_NAME)]

    print(
        "G1",
        "LL", round(log_loss(y, g1), 5),
        "AUC", round(roc_auc_score(y, g1), 5),
    )

    # Existing frozen R_q90 comparator.
    rq = apply_law(
        q, g1,
        {"threshold": Q_T, "d0": .30, "d1": -.10}
    )
    rqg = env_gains(y, env, g1, rq)
    print(
        "EXISTING R_q90",
        "LL", round(log_loss(y, rq), 5),
        "AUC", round(roc_auc_score(y, rq), 5),
        "GAIN", round(log_loss(y, g1) - log_loss(y, rq), 5),
        "WORST", round(min(rqg.values()), 5),
        "POS", sum(v > 0 for v in rqg.values()), "/10",
    )

    results = {}

    for kind in ("Q", "G", "QxG"):
        records, cells, n_cells = pair_future_test(
            kind, y, env, g1, q, g
        )
        passes, med = summarize_pairs(kind, records)
        fixed_pred, fixed_gains = fixed_policy_report(
            kind, y, env, g1, cells, med
        )
        full_pred, full_gains, full_deltas = full_fit_report(
            kind, y, env, g1, cells, n_cells
        )

        results[kind] = {
            "passes": passes,
            "fixed_ll": log_loss(y, fixed_pred),
            "fixed_auc": roc_auc_score(y, fixed_pred),
            "fixed_worst": min(fixed_gains.values()),
            "fixed_pos": sum(v > 0 for v in fixed_gains.values()),
            "fixed_deltas": med,
            "full_ll": log_loss(y, full_pred),
            "full_auc": roc_auc_score(y, full_pred),
            "full_worst": min(full_gains.values()),
            "full_deltas": full_deltas,
        }

    print()
    print("=== COMPARISON ===")
    for kind, r in results.items():
        print(
            kind,
            "PAIR", r["passes"], "/45",
            "FIXED_LL", round(r["fixed_ll"], 5),
            "FIXED_AUC", round(r["fixed_auc"], 5),
            "FIXED_WORST", round(r["fixed_worst"], 5),
            "POS", r["fixed_pos"], "/10",
        )

    qres = results["Q"]
    xres = results["QxG"]

    print()
    print("=== VERDICT ===")
    if (
        xres["passes"] >= 40
        and xres["fixed_pos"] == 10
        and xres["fixed_worst"] > 0
        and xres["fixed_ll"] < min(qres["fixed_ll"], log_loss(y, rq)) - 1e-4
    ):
        print("PRECISION_QxG_CAPABILITY_TRANSFERS_AND_BEATS_RQ90")
    elif (
        xres["passes"] > qres["passes"]
        and xres["fixed_pos"] == 10
        and xres["fixed_worst"] > 0
    ):
        print("GRADIENT_STABILIZES_RQ90_BUT_GAIN_IS_SMALL")
    elif (
        qres["passes"] >= 40
        and qres["fixed_pos"] == 10
        and qres["fixed_worst"] > 0
    ):
        print("RQ90_FIXED_BOUNDARY_IS_THE_TRANSFERABLE_CAPABILITY")
    else:
        print("BOUNDARY_SIGNAL_REAL_BUT_NOT_YET_TRANSFER_SAFE")


if __name__ == "__main__":
    main()
