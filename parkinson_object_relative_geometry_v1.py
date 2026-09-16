from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

from parkinson_invariant_3d_v1 import load_parent_context, logit_np, sigmoid_np
from parkinson_msi_representation_tournament_v1 import safe_auc
from realitygraph.msi_minimal_recurrence import environment_recurrence, fit_robust_tiny_model
from realitygraph.object_relative_geometry import subject_relative_geometry_features

WORK = Path('/workspace')
MAP_CANDIDATES = (
    WORK / 'pp_signal_maps.npz',
    WORK / 'dat_parkinsons' / 'work' / 'pp_signal_maps.npz',
)
OUT_PATH = WORK / 'parkinson_object_relative_geometry_v1.npz'


def load_r_map(n_rows):
    path = next((p for p in MAP_CANDIDATES if p.exists()), None)
    if path is None:
        raise FileNotFoundError('pp_signal_maps.npz not found')
    data = np.load(path)
    if 'R' not in data.files:
        raise RuntimeError(f'R missing from {path}')
    r = np.asarray(data['R'], dtype=np.float64)
    if r.ndim != 3 or len(r) != n_rows or not np.isfinite(r).all():
        raise RuntimeError(f'invalid R map {r.shape}; expected {n_rows} rows')
    print('MAPS', path, r.shape, flush=True)
    return r


def main():
    parser = argparse.ArgumentParser(
        description='Subject-relative uptake geometry tournament for prospective Parkinson log loss.'
    )
    parser.add_argument('--core-top', type=int, default=32)
    parser.add_argument('--min-agree', type=float, default=0.75)
    parser.add_argument('--sizes', type=str, default='1,2,3,4,6,8,12')
    parser.add_argument('--shrinkages', type=str, default='0.125,0.25,0.5,0.75,1.0')
    parser.add_argument('--max-pairs', type=int, default=0)
    args = parser.parse_args()

    from sklearn.metrics import log_loss, roc_auc_score

    sizes = tuple(sorted({int(x) for x in args.sizes.split(',') if int(x) > 0}))
    shrinkages = tuple(sorted({float(x) for x in args.shrinkages.split(',') if float(x) > 0.0}))

    print('REALITYGRAPH / PARKINSON OBJECT-RELATIVE GEOMETRY V1')
    print('--------------------------------------------------------')
    print('Question: does subject-relative uptake geometry transfer where fixed grid coordinates failed?')
    print('Parent: exact G1+G2 fixed logit offset')
    print('Representation: q90 scale -> bilateral mirror -> subject intrinsic rigid frame -> uptake-body geometry')
    print('Families: threshold morphology + intrinsic centroids/spreads + longitudinal mass profiles + bilateral asymmetry')
    print('Selection: exact environment recurrence only; no fixed scanner-grid cells')
    print('Coefficients: independently per discovery environment, majority-sign median')
    print('Model size + shrinkage: leave-one-discovery-environment-out log loss')
    print('Outer protocol: 8 discovery environments -> 2 untouched futures, all 45 pairs')
    print('No future labels choose representation, features, coefficients, size, or shrinkage')
    print('CORE_TOP', args.core_top, 'MIN_AGREE', args.min_agree, 'SIZES', sizes, 'SHRINKAGES', shrinkages)
    print()

    y, env, base = load_parent_context()
    base_logits = logit_np(base)
    parent_ll = float(log_loss(y, base))
    parent_auc = float(roc_auc_score(y, base))
    print('ROWS', len(y), 'PARENT_LL', round(parent_ll, 5), 'PARENT_AUC', round(parent_auc, 5))

    r = load_r_map(len(y))
    print('BUILD_SUBJECT_RELATIVE_GEOMETRY', flush=True)
    matrix, names, families = subject_relative_geometry_features(r)
    del r
    print('FEATURE_BANK', matrix.shape, 'FAMILIES', dict(sorted(Counter(families).items())))
    print()

    pairs = list(combinations(range(10), 2))
    if args.max_pairs > 0:
        pairs = pairs[:args.max_pairs]

    prediction_logit_sum = np.zeros(len(y), dtype=np.float64)
    prediction_count = np.zeros(len(y), dtype=np.int64)
    ll_pass_both = 0
    joint_pass_both = 0
    size_counts = Counter()
    shrink_counts = Counter()
    recurrent = Counter()
    signed = Counter()
    family_counts = Counter()
    pair_rows = []

    for pair_no, (a, b) in enumerate(pairs, 1):
        discovery = tuple(e for e in range(10) if e not in (a, b))
        print(f'=== PAIR {a},{b} ({pair_no}/{len(pairs)}) DISCOVERY {discovery} ===', flush=True)

        exact = environment_recurrence(matrix, y, base_logits, env, discovery)
        valid = np.flatnonzero(exact['sign_fraction'] >= args.min_agree)
        valid = valid[exact['score'][valid] > 0.0]
        if len(valid) == 0:
            print('NO RECURRENT GEOMETRY -> PARENT', flush=True)
            future = np.isin(env, (a, b))
            prediction_logit_sum[future] += base_logits[future]
            prediction_count[future] += 1
            pair_rows.append((a, b, 0, 0.0, parent_ll, 0.0, 0.0, 0.0, 0.0))
            continue

        valid = valid[np.argsort(exact['score'][valid])[::-1]]
        core = valid[:min(args.core_top, len(valid))]
        Xcore = matrix[:, core]

        candidates = []
        for k in sizes:
            if k > len(core):
                continue
            Xk = Xcore[:, :k]
            for shrink in shrinkages:
                loss_sum = 0.0
                n_sum = 0
                for held in discovery:
                    train_envs = tuple(e for e in discovery if e != held)
                    model = fit_robust_tiny_model(
                        Xk, y, base_logits, env, train_envs,
                        min_sign_fraction=args.min_agree,
                        shrinkage=shrink,
                    )
                    take = env == held
                    pred = sigmoid_np(model['logits'][take])
                    loss_sum += float(log_loss(y[take], pred)) * int(take.sum())
                    n_sum += int(take.sum())
                candidates.append((loss_sum / max(n_sum, 1), k, shrink))

        if not candidates:
            print('NO TINY GEOMETRY CANDIDATES -> PARENT', flush=True)
            future = np.isin(env, (a, b))
            prediction_logit_sum[future] += base_logits[future]
            prediction_count[future] += 1
            pair_rows.append((a, b, 0, 0.0, parent_ll, 0.0, 0.0, 0.0, 0.0))
            continue

        cv_ll, best_k, best_shrink = min(candidates, key=lambda t: (t[0], t[1], t[2]))
        chosen = core[:best_k]
        final = fit_robust_tiny_model(
            matrix[:, chosen], y, base_logits, env, discovery,
            min_sign_fraction=args.min_agree,
            shrinkage=best_shrink,
        )
        logits = final['logits']

        pa = sigmoid_np(logits[env == a])
        pb = sigmoid_np(logits[env == b])
        ll_a = float(log_loss(y[env == a], base[env == a]) - log_loss(y[env == a], pa))
        ll_b = float(log_loss(y[env == b], base[env == b]) - log_loss(y[env == b], pb))
        auc_a = safe_auc(y[env == a], pa, roc_auc_score) - safe_auc(y[env == a], base[env == a], roc_auc_score)
        auc_b = safe_auc(y[env == b], pb, roc_auc_score) - safe_auc(y[env == b], base[env == b], roc_auc_score)
        ll_pass = ll_a > 0.0 and ll_b > 0.0
        joint = ll_pass and auc_a >= 0.0 and auc_b >= 0.0
        ll_pass_both += int(ll_pass)
        joint_pass_both += int(joint)
        size_counts[best_k] += 1
        shrink_counts[best_shrink] += 1

        for j, coef in zip(chosen, final['beta']):
            recurrent[names[j]] += 1
            signed[names[j]] += int(np.sign(coef))
            family_counts[families[j]] += 1

        future = np.isin(env, (a, b))
        prediction_logit_sum[future] += logits[future]
        prediction_count[future] += 1
        pair_rows.append((a, b, best_k, best_shrink, cv_ll, ll_a, ll_b, auc_a, auc_b))

        print('CHOSEN k', best_k, 'shrink', best_shrink,
              'DISCOVERY_LOEO_LL', round(cv_ll, 5),
              'FUTURE_LL', [round(ll_a, 5), round(ll_b, 5)],
              'FUTURE_AUC', [round(auc_a, 5), round(auc_b, 5)],
              'LL_PASS', int(ll_pass), 'JOINT', int(joint), flush=True)
        print('CORE', ', '.join(names[j] for j in chosen), flush=True)

    covered = prediction_count > 0
    ensemble_logits = base_logits.copy()
    ensemble_logits[covered] = prediction_logit_sum[covered] / prediction_count[covered]
    ensemble = sigmoid_np(ensemble_logits)
    ooe_ll = float(log_loss(y[covered], ensemble[covered])) if np.any(covered) else parent_ll
    ooe_auc = float(roc_auc_score(y[covered], ensemble[covered])) if np.any(covered) else parent_auc

    recurrence_rows = [(name, count, signed[name]) for name, count in recurrent.most_common()]
    np.savez_compressed(
        OUT_PATH,
        pair_results=np.asarray(pair_rows, dtype=np.float64),
        ensemble_logits=ensemble_logits,
        prediction_count=prediction_count,
        recurrence_names=np.asarray([x[0] for x in recurrence_rows], dtype=str),
        recurrence_counts=np.asarray([x[1] for x in recurrence_rows], dtype=np.int64),
        recurrence_signed=np.asarray([x[2] for x in recurrence_rows], dtype=np.int64),
        feature_names=np.asarray(names, dtype=str),
        feature_families=np.asarray(families, dtype=str),
    )

    print()
    print('=== OUTER TWO-ENVIRONMENT FUTURES ===')
    print('PAIRS_EVALUATED', len(pairs), '/45')
    print('GEOMETRY_LL_PASS_BOTH', ll_pass_both, '/', len(pairs))
    print('GEOMETRY_LL_AUC_NONNEG_PASS_BOTH', joint_pass_both, '/', len(pairs))
    print('PRIOR_HANDCRAFTED_REFERENCE 3 /45')
    print('V2_TINY_REFERENCE 3 /45 LL, 2 /45 joint')
    print()
    print('=== OOE ENSEMBLE ===')
    print('COVERED', int(covered.sum()), '/', len(y), 'PREDICTIONS_MINMAX',
          int(prediction_count[covered].min()) if np.any(covered) else 0,
          int(prediction_count[covered].max()) if np.any(covered) else 0)
    print('PARENT LL', round(parent_ll, 5), 'AUC', round(parent_auc, 5))
    print('GEOMETRY_OOE LL', round(ooe_ll, 5), 'AUC', round(ooe_auc, 5),
          'LL_GAIN', round(parent_ll - ooe_ll, 5), 'AUC_GAIN', round(ooe_auc - parent_auc, 5))
    print('SIZE_COUNTS', dict(sorted(size_counts.items())))
    print('SHRINK_COUNTS', dict(sorted(shrink_counts.items())))
    print('FAMILY_COUNTS', dict(sorted(family_counts.items())))
    print()
    print('=== RECURRENT SUBJECT-RELATIVE REPRESENTATION ===')
    for name, count, sign_sum in recurrence_rows[:30]:
        print(name, 'SELECTED', count, 'SIGN_SUM', sign_sum)
    print()
    print('=== VERDICT ===')
    if len(pairs) == 45 and ooe_ll < parent_ll and ll_pass_both > 3:
        print('SUBJECT_RELATIVE_GEOMETRY_UNLOCKS_PROSPECTIVE_LOG_LOSS')
    elif ooe_ll < parent_ll:
        print('SUBJECT_RELATIVE_GEOMETRY_HAS_POSITIVE_OOE_SIGNAL')
    else:
        print('SUBJECT_RELATIVE_GEOMETRY_DOES_NOT_YET_TRANSFER')
    print('OUTPUT', OUT_PATH)


if __name__ == '__main__':
    main()
