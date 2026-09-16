from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

from parkinson_invariant_3d_v1 import load_parent_context, logit_np, sigmoid_np
from parkinson_msi_representation_tournament_v1 import safe_auc
from parkinson_object_relative_geometry_v1 import load_r_map
from parkinson_threshold_trajectory_v3 import (
    CONTRACTION_V2_AUC,
    CONTRACTION_V2_LL,
    DENSE_ANCHOR,
    OLD_ANCHOR,
    load_or_build_trajectory,
)
from realitygraph.geometry_core_contraction import greedy_contract
from realitygraph.msi_minimal_recurrence import environment_recurrence, fit_robust_tiny_model
from realitygraph.object_relative_geometry import subject_relative_geometry_features
from realitygraph.safe_trajectory_gate import residual_gate

WORK = Path('/workspace')
OUT_PATH = WORK / 'parkinson_safe_trajectory_gate_v4.npz'
V3_LL = 0.35281
V3_AUC = 0.92238
V3_LL_PASS = 26


def main():
    p = argparse.ArgumentParser(description='Discovery-stability gate between anchor and trajectory residual.')
    p.add_argument('--core-top', type=int, default=16)
    p.add_argument('--min-agree', type=float, default=0.75)
    p.add_argument('--sizes', type=str, default='0,1,2,3,4,6,8')
    p.add_argument('--shrinkages', type=str, default='0.125,0.25,0.5,0.75')
    p.add_argument('--anchor-shrink', type=float, default=0.5)
    p.add_argument('--contraction-tol', type=float, default=0.00025)
    p.add_argument('--gate-min-wins', type=int, default=7)
    p.add_argument('--gate-min-mean-gain', type=float, default=0.0005)
    p.add_argument('--gate-max-worst-regret', type=float, default=0.002)
    p.add_argument('--max-pairs', type=int, default=0)
    args = p.parse_args()

    from sklearn.metrics import log_loss, roc_auc_score

    sizes = tuple(sorted({int(x) for x in args.sizes.split(',') if int(x) >= 0}))
    shrinkages = tuple(sorted({float(x) for x in args.shrinkages.split(',') if float(x) > 0.0}))

    print('REALITYGRAPH / PARKINSON SAFE TRAJECTORY GATE V4')
    print('--------------------------------------------------')
    print('Goal: keep anchor robustness; invoke dense trajectory only when discovery environments agree')
    print('Gate: wins >=', args.gate_min_wins,
          'mean_gain >=', args.gate_min_mean_gain,
          'worst_regret <=', args.gate_max_worst_regret)
    print('No outer/future label participates in the gate')

    y, env, base = load_parent_context()
    base_logits = logit_np(base)
    parent_ll = float(log_loss(y, base))
    parent_auc = float(roc_auc_score(y, base))
    print('ROWS', len(y), 'PARENT_LL', round(parent_ll, 5), 'PARENT_AUC', round(parent_auc, 5))

    r = load_r_map(len(y))
    trajectory, names, _ = load_or_build_trajectory(r, rebuild=False)
    dense_idx = {n: i for i, n in enumerate(names)}
    anchor_dense_idx = dense_idx[DENSE_ANCHOR]
    geometry, geometry_names, _ = subject_relative_geometry_features(r)
    del r
    anchor = np.asarray(geometry[:, geometry_names.index(OLD_ANCHOR)], dtype=np.float64)
    dense_anchor = np.asarray(trajectory[:, anchor_dense_idx], dtype=np.float64)
    parity = float(np.max(np.abs(anchor - dense_anchor)))
    if parity > 2e-6:
        raise RuntimeError(f'anchor parity failed: {parity}')
    del geometry
    print('TRAJECTORY_BANK', trajectory.shape, 'ANCHOR_PARITY_MAX', f'{parity:.3g}')

    pairs = list(combinations(range(10), 2))
    if args.max_pairs > 0:
        pairs = pairs[:args.max_pairs]

    pred_sum = np.zeros(len(y), dtype=np.float64)
    pred_count = np.zeros(len(y), dtype=np.int64)
    invoked = 0
    ll_pass = 0
    joint_pass = 0
    retained = Counter()
    pair_rows = []

    def outer_metrics(logits, a, b):
        rows = []
        for e in (a, b):
            take = env == e
            prob = sigmoid_np(logits[take])
            rows.append((
                float(log_loss(y[take], base[take]) - log_loss(y[take], prob)),
                float(safe_auc(y[take], prob, roc_auc_score) - safe_auc(y[take], base[take], roc_auc_score)),
            ))
        return rows

    for pair_no, (a, b) in enumerate(pairs, 1):
        discovery = tuple(e for e in range(10) if e not in (a, b))
        print(f'=== PAIR {a},{b} ({pair_no}/{len(pairs)}) ===', flush=True)

        anchor_full = fit_robust_tiny_model(
            anchor[:, None], y, base_logits, env, discovery,
            min_sign_fraction=args.min_agree, shrinkage=args.anchor_shrink,
        )
        anchored_logits = anchor_full['logits']
        exact = environment_recurrence(trajectory, y, anchored_logits, env, discovery)
        valid = np.flatnonzero((exact['sign_fraction'] >= args.min_agree) & (exact['score'] > 0.0))
        valid = valid[valid != anchor_dense_idx]
        if len(valid):
            valid = valid[np.argsort(exact['score'][valid])[::-1]]
        core = tuple(int(j) for j in valid[:min(args.core_top, len(valid))])

        cache = {}

        def eval_subset(feature_tuple):
            key = tuple(int(j) for j in feature_tuple)
            if key in cache:
                return cache[key]
            best = None
            for residual_shrink in (shrinkages if key else (0.0,)):
                held_losses = []
                held_ns = []
                for held in discovery:
                    train_envs = tuple(e for e in discovery if e != held)
                    am = fit_robust_tiny_model(
                        anchor[:, None], y, base_logits, env, train_envs,
                        min_sign_fraction=args.min_agree, shrinkage=args.anchor_shrink,
                    )
                    logits = am['logits']
                    if key:
                        rm = fit_robust_tiny_model(
                            trajectory[:, key], y, logits, env, train_envs,
                            min_sign_fraction=args.min_agree, shrinkage=residual_shrink,
                        )
                        logits = rm['logits']
                    take = env == held
                    held_losses.append(float(log_loss(y[take], sigmoid_np(logits[take]))))
                    held_ns.append(int(take.sum()))
                mean_loss = float(np.average(held_losses, weights=held_ns))
                row = (mean_loss, float(residual_shrink), np.asarray(held_losses, dtype=np.float64))
                if best is None or (row[0], row[1]) < (best[0], best[1]):
                    best = row
            cache[key] = best
            return best

        def score_subset(feature_tuple):
            return eval_subset(feature_tuple)[0]

        candidates = []
        for k in sizes:
            if k <= len(core):
                subset = core[:k]
                mean_loss, shrink, _ = eval_subset(subset)
                candidates.append((mean_loss, k, shrink))
        if not candidates:
            candidates.append((*eval_subset(tuple())[:2], 0))
        _, best_k, _ = min(candidates, key=lambda row: (row[0], row[1], row[2]))
        initial = core[:best_k]
        chosen = greedy_contract(initial, score_subset, tolerance=args.contraction_tol)['features'] if initial else tuple()
        _, residual_shrink, residual_losses = eval_subset(chosen)
        _, _, anchor_losses = eval_subset(tuple())
        gate = residual_gate(
            anchor_losses,
            residual_losses,
            min_wins=args.gate_min_wins,
            min_mean_gain=args.gate_min_mean_gain,
            max_worst_regret=args.gate_max_worst_regret,
        )
        use_residual = bool(chosen) and gate['invoke']
        invoked += int(use_residual)

        logits = anchor_full['logits']
        if use_residual:
            rm = fit_robust_tiny_model(
                trajectory[:, chosen], y, logits, env, discovery,
                min_sign_fraction=args.min_agree, shrinkage=residual_shrink,
            )
            logits = rm['logits']
            for j, coef in zip(chosen, rm['beta']):
                if coef != 0.0:
                    retained[names[j]] += 1

        (lla, auca), (llb, aucb) = outer_metrics(logits, a, b)
        passed = lla > 0.0 and llb > 0.0
        joint = passed and auca >= 0.0 and aucb >= 0.0
        ll_pass += int(passed)
        joint_pass += int(joint)
        future = np.isin(env, (a, b))
        pred_sum[future] += logits[future]
        pred_count[future] += 1
        pair_rows.append((a, b, int(use_residual), len(chosen), residual_shrink,
                          gate['wins'], gate['mean_gain'], gate['worst_gain'],
                          lla, llb, auca, aucb))
        print('GATE', 'RESIDUAL' if use_residual else 'ANCHOR',
              'wins', gate['wins'], '/8',
              'mean', round(gate['mean_gain'], 5),
              'worst', round(gate['worst_gain'], 5),
              'k', len(chosen), 'shrink', residual_shrink,
              'FUTURE_LL', [round(lla, 5), round(llb, 5)],
              'JOINT', int(joint), flush=True)

    covered = pred_count > 0
    ooe_logits = base_logits.copy()
    ooe_logits[covered] = pred_sum[covered] / pred_count[covered]
    prob = sigmoid_np(ooe_logits)
    ooe_ll = float(log_loss(y[covered], prob[covered]))
    ooe_auc = float(roc_auc_score(y[covered], prob[covered]))
    np.savez_compressed(
        OUT_PATH,
        pair_results=np.asarray(pair_rows, dtype=np.float64),
        ensemble_logits=ooe_logits,
        prediction_count=pred_count,
        retained_names=np.asarray([x[0] for x in retained.most_common()], dtype=str),
        retained_counts=np.asarray([x[1] for x in retained.most_common()], dtype=np.int64),
    )

    print()
    print('=== SAFE GATE OUTER FUTURES ===')
    print('PAIRS', len(pairs), '/45', 'RESIDUAL_INVOKED', invoked)
    print('SAFE_LL_PASS_BOTH', ll_pass, '/', len(pairs))
    print('SAFE_JOINT_PASS_BOTH', joint_pass, '/', len(pairs))
    print()
    print('=== SAFE GATE OOE ===')
    print('PARENT LL', round(parent_ll, 5), 'AUC', round(parent_auc, 5))
    print('CONTRACTION_V2 LL', CONTRACTION_V2_LL, 'AUC', CONTRACTION_V2_AUC)
    print('TRAJECTORY_V3 LL', V3_LL, 'AUC', V3_AUC, 'LL_PASS', V3_LL_PASS)
    print('SAFE_GATE LL', round(ooe_ll, 5), 'AUC', round(ooe_auc, 5),
          'LL_DELTA_V3', round(V3_LL - ooe_ll, 5))
    print()
    print('=== INVOKED RESIDUAL RECURRENCE ===')
    for name, count in retained.most_common(20):
        print(name, 'INVOKED', count)
    print()
    print('=== VERDICT ===')
    if len(pairs) == 45 and ooe_ll < V3_LL and ll_pass >= V3_LL_PASS:
        print('SAFE_GATE_COMPOUNDS_TRAJECTORY')
    elif len(pairs) == 45 and ooe_ll <= CONTRACTION_V2_LL and ll_pass > V3_LL_PASS:
        print('SAFE_GATE_TRADES_SMALL_LL_FOR_STRONGER_TRANSFER')
    elif ooe_ll < CONTRACTION_V2_LL:
        print('SAFE_GATE_RETAINS_COMPOUNDED_LL')
    else:
        print('SAFE_GATE_TOO_CONSERVATIVE__KEEP_V3')
    print('OUTPUT', OUT_PATH)


if __name__ == '__main__':
    main()
