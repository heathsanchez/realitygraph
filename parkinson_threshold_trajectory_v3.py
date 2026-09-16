from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

from parkinson_invariant_3d_v1 import load_parent_context, logit_np, sigmoid_np
from parkinson_msi_representation_tournament_v1 import safe_auc
from parkinson_object_relative_geometry_v1 import load_r_map
from realitygraph.geometry_core_contraction import greedy_contract, removal_ablation
from realitygraph.msi_minimal_recurrence import environment_recurrence, fit_robust_tiny_model
from realitygraph.object_relative_geometry import subject_relative_geometry_features
from realitygraph.threshold_trajectory import dense_threshold_trajectory_features

WORK = Path('/workspace')
CACHE = WORK / 'dat_parkinsons' / 'work' / 'threshold_trajectory_v3.npz'
OUT_PATH = WORK / 'parkinson_threshold_trajectory_v3.npz'
OLD_ANCHOR = 'right_delta_f50_f70_mean_uptake'
DENSE_ANCHOR = 'right_mean_uptake_delta_50_70'
CONTRACTION_V2_LL = 0.35353
CONTRACTION_V2_AUC = 0.92150
CONTRACTION_V2_LL_PASS = 22


def load_or_build_trajectory(r, rebuild=False):
    if CACHE.exists() and not rebuild:
        d = np.load(CACHE, allow_pickle=False)
        X = np.asarray(d['X'], dtype=np.float32)
        names = d['names'].astype(str).tolist()
        families = d['families'].astype(str).tolist()
        if len(X) == len(r) and X.shape[1] == len(names) == len(families):
            print('TRAJECTORY_CACHE', CACHE, X.shape, flush=True)
            return X, names, families
    print('BUILD_DENSE_THRESHOLD_TRAJECTORY', flush=True)
    X, names, families = dense_threshold_trajectory_features(r)
    X = np.asarray(X, dtype=np.float32)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE, X=X, names=np.asarray(names, dtype=str), families=np.asarray(families, dtype=str))
    print('TRAJECTORY_CACHE_WRITTEN', CACHE, X.shape, flush=True)
    return X, names, families


def main():
    parser = argparse.ArgumentParser(description='Anchor-conditional dense threshold trajectory tournament.')
    parser.add_argument('--core-top', type=int, default=16)
    parser.add_argument('--min-agree', type=float, default=0.75)
    parser.add_argument('--sizes', type=str, default='0,1,2,3,4,6,8')
    parser.add_argument('--shrinkages', type=str, default='0.125,0.25,0.5,0.75')
    parser.add_argument('--anchor-shrink', type=float, default=0.5)
    parser.add_argument('--contraction-tol', type=float, default=0.00025)
    parser.add_argument('--max-pairs', type=int, default=0)
    parser.add_argument('--rebuild-cache', action='store_true')
    args = parser.parse_args()

    from sklearn.metrics import log_loss, roc_auc_score

    sizes = tuple(sorted({int(x) for x in args.sizes.split(',') if int(x) >= 0}))
    shrinkages = tuple(sorted({float(x) for x in args.shrinkages.split(',') if float(x) > 0.0}))

    print('REALITYGRAPH / PARKINSON THRESHOLD TRAJECTORY V3')
    print('--------------------------------------------------')
    print('Goal: compound the 45/45 causal anchor by resolving only its 40-80% threshold trajectory')
    print('Anchor mandatory:', OLD_ANCHOR, 'with fixed discovery-only shrink', args.anchor_shrink)
    print('Trajectory: thresholds 40,45,50,55,60,65,70,75,80 in subject-relative rigid frame')
    print('Observables: uptake mean/std, longitudinal q10/q25/q50, widths50/80, centroid, minor spread')
    print('Candidate ranking: residual log-loss consequence conditional on the anchor')
    print('Contraction: discovery-only LOEO; anchor itself is never deletable')
    print('Outer protocol: 8 discovery environments -> 2 future environments, all 45 pairs')
    print('CORE_TOP', args.core_top, 'MIN_AGREE', args.min_agree, 'SIZES', sizes,
          'RESID_SHRINKAGES', shrinkages, 'ANCHOR_SHRINK', args.anchor_shrink,
          'TOL', args.contraction_tol)
    print()

    y, env, base = load_parent_context()
    base_logits = logit_np(base)
    parent_ll = float(log_loss(y, base))
    parent_auc = float(roc_auc_score(y, base))
    print('ROWS', len(y), 'PARENT_LL', round(parent_ll, 5), 'PARENT_AUC', round(parent_auc, 5))

    r = load_r_map(len(y))
    trajectory, names, families = load_or_build_trajectory(r, rebuild=args.rebuild_cache)
    dense_name_to_idx = {n: i for i, n in enumerate(names)}
    if DENSE_ANCHOR not in dense_name_to_idx:
        raise RuntimeError(f'dense anchor missing: {DENSE_ANCHOR}')
    anchor_dense_idx = dense_name_to_idx[DENSE_ANCHOR]

    # One exact semantic parity check against the V1 anchor before using the dense bank.
    geometry, geometry_names, _ = subject_relative_geometry_features(r)
    del r
    old_idx = geometry_names.index(OLD_ANCHOR)
    anchor = np.asarray(geometry[:, old_idx], dtype=np.float64)
    dense_anchor = np.asarray(trajectory[:, anchor_dense_idx], dtype=np.float64)
    max_anchor_diff = float(np.max(np.abs(anchor - dense_anchor)))
    if max_anchor_diff > 2e-6:
        raise RuntimeError(f'anchor parity failed: max diff {max_anchor_diff}')
    del geometry
    print('TRAJECTORY_BANK', trajectory.shape, 'ANCHOR_PARITY_MAX', f'{max_anchor_diff:.3g}')
    print('FAMILIES', dict(sorted(Counter(families).items())))
    print()

    pairs = list(combinations(range(10), 2))
    if args.max_pairs > 0:
        pairs = pairs[:args.max_pairs]

    pred_sum = np.zeros(len(y), dtype=np.float64)
    pred_count = np.zeros(len(y), dtype=np.int64)
    anchor_pred_sum = np.zeros(len(y), dtype=np.float64)
    anchor_pred_count = np.zeros(len(y), dtype=np.int64)
    ll_pass_both = 0
    joint_pass_both = 0
    anchor_ll_pass_both = 0
    anchor_joint_pass_both = 0
    anchor_causal_pairs = 0
    final_size_counts = Counter()
    shrink_counts = Counter()
    retained = Counter()
    signed = Counter()
    causal = Counter()
    pair_rows = []

    def outer_metrics(logits, a, b):
        rows = []
        for e in (a, b):
            take = env == e
            p = sigmoid_np(logits[take])
            rows.append((
                float(log_loss(y[take], base[take]) - log_loss(y[take], p)),
                float(safe_auc(y[take], p, roc_auc_score) - safe_auc(y[take], base[take], roc_auc_score)),
            ))
        return rows

    for pair_no, (a, b) in enumerate(pairs, 1):
        discovery = tuple(e for e in range(10) if e not in (a, b))
        print(f'=== PAIR {a},{b} ({pair_no}/{len(pairs)}) DISCOVERY {discovery} ===', flush=True)

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

        def score_subset(feature_tuple):
            key = tuple(int(j) for j in feature_tuple)
            if key in cache:
                return cache[key][0]
            best = None
            residual_grid = shrinkages if key else (0.0,)
            for residual_shrink in residual_grid:
                loss_sum = 0.0
                n_sum = 0
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
                    p = sigmoid_np(logits[take])
                    loss_sum += float(log_loss(y[take], p)) * int(take.sum())
                    n_sum += int(take.sum())
                row = (loss_sum / max(n_sum, 1), residual_shrink)
                if best is None or row < best:
                    best = row
            cache[key] = best
            return best[0]

        candidates = []
        for k in sizes:
            if k <= len(core):
                subset = core[:k]
                candidates.append((score_subset(subset), k, cache[subset][1]))
        if not candidates:
            candidates.append((score_subset(tuple()), 0, 0.0))
        _, best_k, _ = min(candidates, key=lambda x: (x[0], x[1], x[2]))
        initial = core[:best_k]

        if initial:
            contracted = greedy_contract(initial, score_subset, tolerance=args.contraction_tol)
            chosen = contracted['features']
            removed = contracted['removed']
        else:
            chosen = tuple()
            removed = tuple()
        chosen_loss = score_subset(chosen)
        residual_shrink = cache[chosen][1]

        anchor_final = fit_robust_tiny_model(
            anchor[:, None], y, base_logits, env, discovery,
            min_sign_fraction=args.min_agree, shrinkage=args.anchor_shrink,
        )
        logits = anchor_final['logits']
        residual_final = None
        if chosen:
            residual_final = fit_robust_tiny_model(
                trajectory[:, chosen], y, logits, env, discovery,
                min_sign_fraction=args.min_agree, shrinkage=residual_shrink,
            )
            logits = residual_final['logits']

        (ll_a, auc_a), (ll_b, auc_b) = outer_metrics(logits, a, b)
        ll_pass = ll_a > 0.0 and ll_b > 0.0
        joint = ll_pass and auc_a >= 0.0 and auc_b >= 0.0
        ll_pass_both += int(ll_pass)
        joint_pass_both += int(joint)

        (all_a, aauc_a), (all_b, aauc_b) = outer_metrics(anchor_final['logits'], a, b)
        anchor_ll_pass = all_a > 0.0 and all_b > 0.0
        anchor_joint = anchor_ll_pass and aauc_a >= 0.0 and aauc_b >= 0.0
        anchor_ll_pass_both += int(anchor_ll_pass)
        anchor_joint_pass_both += int(anchor_joint)

        # Discovery-only anchor-removal test: let residuals refit directly on parent.
        no_anchor_best = None
        if chosen:
            for shrink in shrinkages:
                loss_sum = 0.0
                n_sum = 0
                for held in discovery:
                    train_envs = tuple(e for e in discovery if e != held)
                    rm = fit_robust_tiny_model(
                        trajectory[:, chosen], y, base_logits, env, train_envs,
                        min_sign_fraction=args.min_agree, shrinkage=shrink,
                    )
                    take = env == held
                    loss_sum += float(log_loss(y[take], sigmoid_np(rm['logits'][take]))) * int(take.sum())
                    n_sum += int(take.sum())
                loss = loss_sum / max(n_sum, 1)
                if no_anchor_best is None or loss < no_anchor_best:
                    no_anchor_best = loss
        else:
            loss_sum = 0.0
            n_sum = 0
            for held in discovery:
                take = env == held
                loss_sum += float(log_loss(y[take], base[take])) * int(take.sum())
                n_sum += int(take.sum())
            no_anchor_best = loss_sum / max(n_sum, 1)
        anchor_harm = float(no_anchor_best - chosen_loss)
        anchor_causal_pairs += int(anchor_harm > args.contraction_tol)

        ablation_rows = removal_ablation(chosen, score_subset) if len(chosen) >= 2 else []
        for row in ablation_rows:
            if row['harm'] > args.contraction_tol:
                causal[names[row['feature']]] += 1

        final_size_counts[len(chosen)] += 1
        shrink_counts[residual_shrink] += 1
        if residual_final is not None:
            for j, coef in zip(chosen, residual_final['beta']):
                retained[names[j]] += 1
                signed[names[j]] += int(np.sign(coef))

        future = np.isin(env, (a, b))
        pred_sum[future] += logits[future]
        pred_count[future] += 1
        anchor_pred_sum[future] += anchor_final['logits'][future]
        anchor_pred_count[future] += 1

        pair_rows.append((a, b, len(initial), len(chosen), residual_shrink, chosen_loss,
                          ll_a, ll_b, auc_a, auc_b, anchor_harm))
        print('RESIDUAL', len(initial), '->', len(chosen), 'REMOVED', len(removed),
              'SHRINK', residual_shrink, 'DISCOVERY_LOEO_LL', round(chosen_loss, 5),
              'ANCHOR_HARM', round(anchor_harm, 5),
              'FUTURE_LL', [round(ll_a, 5), round(ll_b, 5)],
              'FUTURE_AUC', [round(auc_a, 5), round(auc_b, 5)],
              'LL_PASS', int(ll_pass), 'JOINT', int(joint), flush=True)
        print('CORE', ', '.join(names[j] for j in chosen) if chosen else '(anchor only)', flush=True)

    covered = pred_count > 0
    ooe_logits = base_logits.copy()
    ooe_logits[covered] = pred_sum[covered] / pred_count[covered]
    ooe = sigmoid_np(ooe_logits)
    ooe_ll = float(log_loss(y[covered], ooe[covered]))
    ooe_auc = float(roc_auc_score(y[covered], ooe[covered]))

    anchor_covered = anchor_pred_count > 0
    anchor_ooe_logits = base_logits.copy()
    anchor_ooe_logits[anchor_covered] = anchor_pred_sum[anchor_covered] / anchor_pred_count[anchor_covered]
    anchor_ooe = sigmoid_np(anchor_ooe_logits)
    anchor_ll = float(log_loss(y[anchor_covered], anchor_ooe[anchor_covered]))
    anchor_auc = float(roc_auc_score(y[anchor_covered], anchor_ooe[anchor_covered]))

    recurrence_rows = [(n, c, signed[n], causal[n]) for n, c in retained.most_common()]
    np.savez_compressed(
        OUT_PATH,
        pair_results=np.asarray(pair_rows, dtype=np.float64),
        ensemble_logits=ooe_logits,
        anchor_ensemble_logits=anchor_ooe_logits,
        prediction_count=pred_count,
        recurrence_names=np.asarray([x[0] for x in recurrence_rows], dtype=str),
        recurrence_counts=np.asarray([x[1] for x in recurrence_rows], dtype=np.int64),
        recurrence_signed=np.asarray([x[2] for x in recurrence_rows], dtype=np.int64),
        causal_counts=np.asarray([x[3] for x in recurrence_rows], dtype=np.int64),
        feature_names=np.asarray(names, dtype=str),
        feature_families=np.asarray(families, dtype=str),
    )

    print()
    print('=== THRESHOLD TRAJECTORY OUTER FUTURES ===')
    print('PAIRS_EVALUATED', len(pairs), '/45')
    print('TRAJECTORY_LL_PASS_BOTH', ll_pass_both, '/', len(pairs))
    print('TRAJECTORY_JOINT_PASS_BOTH', joint_pass_both, '/', len(pairs))
    print('CONTRACTION_V2_REFERENCE', CONTRACTION_V2_LL_PASS, '/45 LL')
    print('FINAL_RESIDUAL_SIZE_COUNTS', dict(sorted(final_size_counts.items())))
    print('RESIDUAL_SHRINK_COUNTS', dict(sorted(shrink_counts.items())))
    print('ANCHOR_REMOVAL_CAUSAL', anchor_causal_pairs, '/', len(pairs))
    print()
    print('=== THRESHOLD TRAJECTORY OOE ===')
    print('PARENT LL', round(parent_ll, 5), 'AUC', round(parent_auc, 5))
    print('CONTRACTION_V2 LL', CONTRACTION_V2_LL, 'AUC', CONTRACTION_V2_AUC)
    print('ANCHOR_ONLY LL', round(anchor_ll, 5), 'AUC', round(anchor_auc, 5),
          'LL_PASS_BOTH', anchor_ll_pass_both, 'JOINT', anchor_joint_pass_both)
    print('TRAJECTORY LL', round(ooe_ll, 5), 'AUC', round(ooe_auc, 5),
          'LL_GAIN_PARENT', round(parent_ll - ooe_ll, 5),
          'LL_DELTA_V2', round(CONTRACTION_V2_LL - ooe_ll, 5),
          'AUC_DELTA_V2', round(ooe_auc - CONTRACTION_V2_AUC, 5))
    print()
    print('=== RECURRENT CONDITIONAL TRAJECTORY ===')
    for name, count, sign_sum, causal_count in recurrence_rows[:30]:
        print(name, 'RETAINED', count, 'SIGN_SUM', sign_sum, 'REMOVAL_CAUSAL', causal_count)
    print()
    print('=== VERDICT ===')
    if len(pairs) == 45 and ooe_ll < CONTRACTION_V2_LL and ll_pass_both > CONTRACTION_V2_LL_PASS and anchor_causal_pairs == 45:
        print('THRESHOLD_TRAJECTORY_COMPOUNDS_CAUSAL_CORE')
    elif len(pairs) == 45 and ooe_ll < CONTRACTION_V2_LL:
        print('THRESHOLD_TRAJECTORY_IMPROVES_OOE_BUT_TRANSFER_GATE_NOT_FULLY_MET')
    elif ooe_ll < parent_ll:
        print('THRESHOLD_TRAJECTORY_RETAINS_POSITIVE_SIGNAL__KEEP_CONTRACTION_V2_AS_REFERENCE')
    else:
        print('THRESHOLD_TRAJECTORY_DOES_NOT_COMPOUND__KEEP_CONTRACTION_V2')
    print('OUTPUT', OUT_PATH)


if __name__ == '__main__':
    main()
