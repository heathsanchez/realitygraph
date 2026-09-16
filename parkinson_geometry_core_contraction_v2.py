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

WORK = Path('/workspace')
OUT_PATH = WORK / 'parkinson_geometry_core_contraction_v2.npz'
ANCHOR_NAME = 'right_delta_f50_f70_mean_uptake'
GEOMETRY_V1_LL = 0.35425
GEOMETRY_V1_AUC = 0.92161
GEOMETRY_V1_LL_PASS = 18


def main():
    parser = argparse.ArgumentParser(
        description='Contract subject-relative geometry to the smallest discovery-certified core.'
    )
    parser.add_argument('--core-top', type=int, default=20)
    parser.add_argument('--min-agree', type=float, default=0.75)
    parser.add_argument('--sizes', type=str, default='2,3,4,6,8,12')
    parser.add_argument('--shrinkages', type=str, default='0.125,0.25,0.5,0.75,1.0')
    parser.add_argument('--contraction-tol', type=float, default=0.0005)
    parser.add_argument('--max-pairs', type=int, default=0)
    args = parser.parse_args()

    from sklearn.metrics import log_loss, roc_auc_score

    sizes = tuple(sorted({int(x) for x in args.sizes.split(',') if int(x) > 0}))
    shrinkages = tuple(sorted({float(x) for x in args.shrinkages.split(',') if float(x) > 0.0}))

    print('REALITYGRAPH / PARKINSON GEOMETRY CORE CONTRACTION V2')
    print('-------------------------------------------------------')
    print('Goal: preserve the subject-relative geometry gain while deleting every dispensable distinction')
    print('Representation fixed: object-relative geometry V1; no grammar expansion')
    print('Selection fixed inside each 8-environment discovery set')
    print('Contraction: greedy deletion under discovery-only LOEO log loss')
    print('Coefficients: environment-wise univariate fits -> majority-sign median')
    print('Outer protocol: 8 discovery environments -> 2 untouched futures, all 45 pairs')
    print('Anchor diagnostic:', ANCHOR_NAME, '(post-V1 diagnostic; not an independent rediscovery claim)')
    print('CORE_TOP', args.core_top, 'MIN_AGREE', args.min_agree,
          'SIZES', sizes, 'SHRINKAGES', shrinkages, 'TOL', args.contraction_tol)
    print()

    y, env, base = load_parent_context()
    base_logits = logit_np(base)
    parent_ll = float(log_loss(y, base))
    parent_auc = float(roc_auc_score(y, base))
    print('ROWS', len(y), 'PARENT_LL', round(parent_ll, 5), 'PARENT_AUC', round(parent_auc, 5))

    r = load_r_map(len(y))
    matrix, names, families = subject_relative_geometry_features(r)
    del r
    name_to_idx = {name: i for i, name in enumerate(names)}
    if ANCHOR_NAME not in name_to_idx:
        raise RuntimeError(f'anchor missing: {ANCHOR_NAME}')
    anchor_idx = name_to_idx[ANCHOR_NAME]
    print('FEATURE_BANK', matrix.shape, 'ANCHOR_INDEX', anchor_idx)
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
    initial_size_counts = Counter()
    final_size_counts = Counter()
    shrink_counts = Counter()
    retained = Counter()
    retained_signed = Counter()
    causal = Counter()
    pair_rows = []

    def outer_metrics(logits, a, b):
        rows = []
        for e in (a, b):
            take = env == e
            pred = sigmoid_np(logits[take])
            ll_gain = float(log_loss(y[take], base[take]) - log_loss(y[take], pred))
            auc_gain = safe_auc(y[take], pred, roc_auc_score) - safe_auc(y[take], base[take], roc_auc_score)
            rows.append((ll_gain, auc_gain))
        return rows

    for pair_no, (a, b) in enumerate(pairs, 1):
        discovery = tuple(e for e in range(10) if e not in (a, b))
        print(f'=== PAIR {a},{b} ({pair_no}/{len(pairs)}) DISCOVERY {discovery} ===', flush=True)

        exact = environment_recurrence(matrix, y, base_logits, env, discovery)
        valid = np.flatnonzero(
            (exact['sign_fraction'] >= args.min_agree) & (exact['score'] > 0.0)
        )
        if len(valid) == 0:
            print('NO RECURRENT GEOMETRY -> PARENT', flush=True)
            future = np.isin(env, (a, b))
            pred_sum[future] += base_logits[future]
            pred_count[future] += 1
            anchor_pred_sum[future] += base_logits[future]
            anchor_pred_count[future] += 1
            continue

        valid = valid[np.argsort(exact['score'][valid])[::-1]]
        core = tuple(int(j) for j in valid[:min(args.core_top, len(valid))])

        cache = {}

        def score_subset(feature_tuple):
            key = tuple(int(j) for j in feature_tuple)
            if key in cache:
                return cache[key][0]
            best = None
            X = matrix[:, key]
            for shrink in shrinkages:
                loss_sum = 0.0
                n_sum = 0
                for held in discovery:
                    train_envs = tuple(e for e in discovery if e != held)
                    model = fit_robust_tiny_model(
                        X, y, base_logits, env, train_envs,
                        min_sign_fraction=args.min_agree,
                        shrinkage=shrink,
                    )
                    take = env == held
                    pred = sigmoid_np(model['logits'][take])
                    loss_sum += float(log_loss(y[take], pred)) * int(take.sum())
                    n_sum += int(take.sum())
                row = (loss_sum / max(n_sum, 1), shrink)
                if best is None or row < best:
                    best = row
            cache[key] = best
            return best[0]

        prefix_candidates = []
        for k in sizes:
            if k <= len(core):
                subset = core[:k]
                prefix_candidates.append((score_subset(subset), k, cache[subset][1]))
        if not prefix_candidates:
            subset = core[:1]
            prefix_candidates.append((score_subset(subset), 1, cache[subset][1]))

        _, initial_k, _ = min(prefix_candidates, key=lambda row: (row[0], row[1], row[2]))
        initial = core[:initial_k]
        contracted = greedy_contract(initial, score_subset, tolerance=args.contraction_tol)
        chosen = contracted['features']
        chosen_loss = contracted['loss']
        chosen_shrink = cache[chosen][1]

        final = fit_robust_tiny_model(
            matrix[:, chosen], y, base_logits, env, discovery,
            min_sign_fraction=args.min_agree,
            shrinkage=chosen_shrink,
        )
        logits = final['logits']
        (ll_a, auc_a), (ll_b, auc_b) = outer_metrics(logits, a, b)
        ll_pass = ll_a > 0.0 and ll_b > 0.0
        joint = ll_pass and auc_a >= 0.0 and auc_b >= 0.0
        ll_pass_both += int(ll_pass)
        joint_pass_both += int(joint)

        ablation_rows = removal_ablation(chosen, score_subset)
        for row in ablation_rows:
            if row['harm'] > args.contraction_tol:
                causal[names[row['feature']]] += 1

        initial_size_counts[len(initial)] += 1
        final_size_counts[len(chosen)] += 1
        shrink_counts[chosen_shrink] += 1
        for j, coef in zip(chosen, final['beta']):
            retained[names[j]] += 1
            retained_signed[names[j]] += int(np.sign(coef))

        # Post-V1 diagnostic: hold the discovered anchor fixed, but choose its
        # shrinkage using only this pair's discovery environments.
        anchor_key = (anchor_idx,)
        anchor_loss = score_subset(anchor_key)
        anchor_shrink = cache[anchor_key][1]
        anchor_model = fit_robust_tiny_model(
            matrix[:, anchor_key], y, base_logits, env, discovery,
            min_sign_fraction=args.min_agree,
            shrinkage=anchor_shrink,
        )
        anchor_logits = anchor_model['logits']
        (all_a, aauc_a), (all_b, aauc_b) = outer_metrics(anchor_logits, a, b)
        anchor_ll_pass = all_a > 0.0 and all_b > 0.0
        anchor_joint = anchor_ll_pass and aauc_a >= 0.0 and aauc_b >= 0.0
        anchor_ll_pass_both += int(anchor_ll_pass)
        anchor_joint_pass_both += int(anchor_joint)

        future = np.isin(env, (a, b))
        pred_sum[future] += logits[future]
        pred_count[future] += 1
        anchor_pred_sum[future] += anchor_logits[future]
        anchor_pred_count[future] += 1

        pair_rows.append((
            a, b, len(initial), len(chosen), chosen_shrink, chosen_loss,
            ll_a, ll_b, auc_a, auc_b,
            anchor_shrink, anchor_loss, all_a, all_b, aauc_a, aauc_b,
        ))

        print('CONTRACT', len(initial), '->', len(chosen),
              'REMOVED', len(contracted['removed']),
              'SHRINK', chosen_shrink, 'DISCOVERY_LOEO_LL', round(chosen_loss, 5),
              'FUTURE_LL', [round(ll_a, 5), round(ll_b, 5)],
              'FUTURE_AUC', [round(auc_a, 5), round(auc_b, 5)],
              'LL_PASS', int(ll_pass), 'JOINT', int(joint), flush=True)
        print('CORE', ', '.join(names[j] for j in chosen), flush=True)
        if ablation_rows:
            print('REMOVAL_HARM', ', '.join(
                f"{names[row['feature']]}:{row['harm']:.5f}" for row in ablation_rows
            ), flush=True)
        print('ANCHOR shrink', anchor_shrink, 'DISCOVERY_LL', round(anchor_loss, 5),
              'FUTURE_LL', [round(all_a, 5), round(all_b, 5)],
              'FUTURE_AUC', [round(aauc_a, 5), round(aauc_b, 5)], flush=True)

    covered = pred_count > 0
    ensemble_logits = base_logits.copy()
    ensemble_logits[covered] = pred_sum[covered] / pred_count[covered]
    ensemble = sigmoid_np(ensemble_logits)
    ooe_ll = float(log_loss(y[covered], ensemble[covered]))
    ooe_auc = float(roc_auc_score(y[covered], ensemble[covered]))

    anchor_covered = anchor_pred_count > 0
    anchor_ensemble_logits = base_logits.copy()
    anchor_ensemble_logits[anchor_covered] = anchor_pred_sum[anchor_covered] / anchor_pred_count[anchor_covered]
    anchor_ensemble = sigmoid_np(anchor_ensemble_logits)
    anchor_ooe_ll = float(log_loss(y[anchor_covered], anchor_ensemble[anchor_covered]))
    anchor_ooe_auc = float(roc_auc_score(y[anchor_covered], anchor_ensemble[anchor_covered]))

    recurrence_rows = [(name, count, retained_signed[name], causal[name]) for name, count in retained.most_common()]
    np.savez_compressed(
        OUT_PATH,
        pair_results=np.asarray(pair_rows, dtype=np.float64),
        ensemble_logits=ensemble_logits,
        anchor_ensemble_logits=anchor_ensemble_logits,
        prediction_count=pred_count,
        recurrence_names=np.asarray([x[0] for x in recurrence_rows], dtype=str),
        recurrence_counts=np.asarray([x[1] for x in recurrence_rows], dtype=np.int64),
        recurrence_signed=np.asarray([x[2] for x in recurrence_rows], dtype=np.int64),
        causal_counts=np.asarray([x[3] for x in recurrence_rows], dtype=np.int64),
    )

    print()
    print('=== CONTRACTION OUTER FUTURES ===')
    print('PAIRS_EVALUATED', len(pairs), '/45')
    print('CONTRACTED_LL_PASS_BOTH', ll_pass_both, '/', len(pairs))
    print('CONTRACTED_JOINT_PASS_BOTH', joint_pass_both, '/', len(pairs))
    print('GEOMETRY_V1_REFERENCE', GEOMETRY_V1_LL_PASS, '/45 LL')
    print('INITIAL_SIZE_COUNTS', dict(sorted(initial_size_counts.items())))
    print('FINAL_SIZE_COUNTS', dict(sorted(final_size_counts.items())))
    print('SHRINK_COUNTS', dict(sorted(shrink_counts.items())))
    print()
    print('=== CONTRACTED OOE ===')
    print('PARENT LL', round(parent_ll, 5), 'AUC', round(parent_auc, 5))
    print('GEOMETRY_V1 LL', GEOMETRY_V1_LL, 'AUC', GEOMETRY_V1_AUC)
    print('CONTRACTED LL', round(ooe_ll, 5), 'AUC', round(ooe_auc, 5),
          'LL_GAIN_PARENT', round(parent_ll - ooe_ll, 5),
          'LL_DELTA_V1', round(GEOMETRY_V1_LL - ooe_ll, 5))
    print()
    print('=== ANCHOR DIAGNOSTIC ===')
    print('ANCHOR', ANCHOR_NAME)
    print('ANCHOR_LL_PASS_BOTH', anchor_ll_pass_both, '/', len(pairs))
    print('ANCHOR_JOINT_PASS_BOTH', anchor_joint_pass_both, '/', len(pairs))
    print('ANCHOR_OOE LL', round(anchor_ooe_ll, 5), 'AUC', round(anchor_ooe_auc, 5),
          'LL_GAIN_PARENT', round(parent_ll - anchor_ooe_ll, 5))
    print()
    print('=== RECURRENT CAUSAL CORE ===')
    for name, count, sign_sum, causal_count in recurrence_rows[:30]:
        print(name, 'RETAINED', count, 'SIGN_SUM', sign_sum, 'REMOVAL_CAUSAL', causal_count)
    print()
    print('=== VERDICT ===')
    if len(pairs) == 45 and ooe_ll < GEOMETRY_V1_LL:
        print('CONTRACTION_COMPOUNDS_GEOMETRY_SIGNAL')
    elif len(pairs) == 45 and ooe_ll <= GEOMETRY_V1_LL + args.contraction_tol:
        print('CONTRACTION_PRESERVES_GEOMETRY_SIGNAL_WITH_SMALLER_INTERFACE')
    elif ooe_ll < parent_ll:
        print('CONTRACTION_RETAINS_POSITIVE_SIGNAL_BUT_LOSES_SOME_V1_GAIN')
    else:
        print('CONTRACTION_TOO_AGGRESSIVE__KEEP_GEOMETRY_V1')
    print('OUTPUT', OUT_PATH)


if __name__ == '__main__':
    main()
