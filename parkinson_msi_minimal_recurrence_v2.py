from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

from parkinson_invariant_3d_v1 import (
    build_or_load_inputs,
    load_parent_context,
    load_volume,
    logit_np,
    sigmoid_np,
)
from parkinson_msi_representation_tournament_v1 import (
    load_or_build_bank,
    safe_auc,
    screen_bank,
)
from realitygraph.msi_minimal_recurrence import (
    environment_recurrence,
    fit_robust_tiny_model,
)

WORK = Path('/workspace')
OUT_PATH = WORK / 'parkinson_msi_minimal_recurrence_v2.npz'


def main():
    parser = argparse.ArgumentParser(
        description='Tiny recurrent MSI: environment-wise coefficients, no pooled multivariate fit.'
    )
    parser.add_argument('--screen-top', type=int, default=256)
    parser.add_argument('--core-top', type=int, default=24)
    parser.add_argument('--screen-chunk', type=int, default=2048)
    parser.add_argument('--min-screen-sign', type=float, default=0.625)
    parser.add_argument('--min-agree', type=float, default=0.75)
    parser.add_argument('--sizes', type=str, default='1,2,3,4,6,8')
    parser.add_argument('--shrinkages', type=str, default='0.25,0.5,0.75,1.0')
    parser.add_argument('--max-pairs', type=int, default=0)
    args = parser.parse_args()

    from sklearn.metrics import log_loss, roc_auc_score

    sizes = tuple(sorted({int(x) for x in args.sizes.split(',') if int(x) > 0}))
    shrinkages = tuple(sorted({float(x) for x in args.shrinkages.split(',') if float(x) > 0.0}))

    print('REALITYGRAPH / PARKINSON MSI MINIMAL RECURRENCE V2')
    print('-----------------------------------------------------')
    print('Question: did V1 find the right recurring primitives but combine too many?')
    print('Parent: exact G1+G2 fixed logit offset')
    print('Search: all 10,328 bounded candidates -> recurring core -> 1/2/3/4/6/8 features')
    print('Coefficients: fit separately per discovery environment, majority-sign median only')
    print('Model size + shrinkage: chosen by leave-one-discovery-environment-out log loss')
    print('Outer protocol: 8 discovery environments -> 2 untouched futures, all 45 pairs')
    print('No pooled multivariate coefficient fit; no fitted intercept')
    print('SCREEN_TOP', args.screen_top, 'CORE_TOP', args.core_top,
          'MIN_AGREE', args.min_agree, 'SIZES', sizes, 'SHRINKAGES', shrinkages)
    print()

    y, env, base = load_parent_context()
    base_logits = logit_np(base)
    parent_ll = float(log_loss(y, base))
    parent_auc = float(roc_auc_score(y, base))
    print('ROWS', len(y), 'PARENT_LL', round(parent_ll, 5), 'PARENT_AUC', round(parent_auc, 5))

    volume = load_volume(len(y))
    inputs = build_or_load_inputs(volume, rebuild=False)
    del volume
    bank, names, families = load_or_build_bank(inputs, rebuild=False)
    del inputs
    print('FEATURE_BANK', bank.shape, 'FAMILIES', dict(sorted(Counter(families).items())))
    print()

    pairs = list(combinations(range(10), 2))
    if args.max_pairs > 0:
        pairs = pairs[:args.max_pairs]

    prediction_logit_sum = np.zeros(len(y), dtype=np.float64)
    prediction_count = np.zeros(len(y), dtype=np.int64)
    ll_pass_both = 0
    joint_pass_both = 0
    chosen_size_counts = Counter()
    chosen_shrink_counts = Counter()
    recurrent = Counter()
    signed = Counter()
    pair_rows = []

    for pair_no, (a, b) in enumerate(pairs, 1):
        discovery = tuple(e for e in range(10) if e not in (a, b))
        print(f'=== PAIR {a},{b} ({pair_no}/{len(pairs)}) DISCOVERY {discovery} ===', flush=True)

        scores, _ = screen_bank(
            bank, y, base, env, discovery,
            chunk_size=args.screen_chunk,
            min_sign=args.min_screen_sign,
        )
        finite = np.flatnonzero(np.isfinite(scores))
        if len(finite) == 0:
            print('NO SCREEN SURVIVORS -> PARENT', flush=True)
            continue
        pre = finite[np.argsort(scores[finite])[::-1]][:args.screen_top]
        exact = environment_recurrence(
            np.asarray(bank[:, pre], dtype=np.float32),
            y, base_logits, env, discovery,
        )
        valid = np.flatnonzero(exact['sign_fraction'] >= args.min_agree)
        if len(valid) == 0:
            print('NO EXACT RECURRENT FEATURES -> PARENT', flush=True)
            continue
        valid = valid[np.argsort(exact['score'][valid])[::-1]]
        core_local = valid[:min(args.core_top, len(valid))]
        core = pre[core_local]
        Xcore = np.asarray(bank[:, core], dtype=np.float64)

        # Choose only complexity and fixed shrinkage inside the discovery set.
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
                    loss_sum += float(log_loss(y[take], sigmoid_np(model['logits'][take]))) * int(take.sum())
                    n_sum += int(take.sum())
                candidates.append((loss_sum / max(n_sum, 1), k, shrink))

        if not candidates:
            print('NO TINY CANDIDATES -> PARENT', flush=True)
            continue
        cv_ll, best_k, best_shrink = min(candidates, key=lambda t: (t[0], t[1], t[2]))
        chosen = core[:best_k]
        final = fit_robust_tiny_model(
            np.asarray(bank[:, chosen], dtype=np.float64),
            y, base_logits, env, discovery,
            min_sign_fraction=args.min_agree,
            shrinkage=best_shrink,
        )
        logits = final['logits']

        ll_a = float(log_loss(y[env == a], base[env == a]) - log_loss(y[env == a], sigmoid_np(logits[env == a])))
        ll_b = float(log_loss(y[env == b], base[env == b]) - log_loss(y[env == b], sigmoid_np(logits[env == b])))
        auc_a = safe_auc(y[env == a], sigmoid_np(logits[env == a]), roc_auc_score) - safe_auc(y[env == a], base[env == a], roc_auc_score)
        auc_b = safe_auc(y[env == b], sigmoid_np(logits[env == b]), roc_auc_score) - safe_auc(y[env == b], base[env == b], roc_auc_score)
        ll_pass = ll_a > 0.0 and ll_b > 0.0
        joint = ll_pass and auc_a >= 0.0 and auc_b >= 0.0
        ll_pass_both += int(ll_pass)
        joint_pass_both += int(joint)
        chosen_size_counts[best_k] += 1
        chosen_shrink_counts[best_shrink] += 1

        for j, coef in zip(chosen, final['beta']):
            recurrent[names[j]] += 1
            signed[names[j]] += int(np.sign(coef))

        future = np.isin(env, (a, b))
        prediction_logit_sum[future] += logits[future]
        prediction_count[future] += 1
        pair_rows.append((a, b, best_k, best_shrink, cv_ll, ll_a, ll_b, auc_a, auc_b))

        top_text = ', '.join(names[j] for j in chosen)
        print('CHOSEN k', best_k, 'shrink', best_shrink, 'DISCOVERY_LOEO_LL', round(cv_ll, 5),
              'FUTURE_LL', [round(ll_a, 5), round(ll_b, 5)],
              'FUTURE_AUC', [round(auc_a, 5), round(auc_b, 5)],
              'LL_PASS', int(ll_pass), 'JOINT', int(joint), flush=True)
        print('CORE', top_text, flush=True)

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
    )

    print()
    print('=== OUTER TWO-ENVIRONMENT FUTURES ===')
    print('PAIRS_EVALUATED', len(pairs), '/45')
    print('TINY_LL_PASS_BOTH', ll_pass_both, '/', len(pairs))
    print('TINY_LL_AUC_NONNEG_PASS_BOTH', joint_pass_both, '/', len(pairs))
    print('PRIOR_HANDCRAFTED_REFERENCE 3 /45')
    print('V1_MSI_REFERENCE 1 /45 LL, 0 /45 joint')
    print()
    print('=== OOE ENSEMBLE ===')
    print('COVERED', int(covered.sum()), '/', len(y), 'PREDICTIONS_MINMAX',
          int(prediction_count[covered].min()) if np.any(covered) else 0,
          int(prediction_count[covered].max()) if np.any(covered) else 0)
    print('PARENT LL', round(parent_ll, 5), 'AUC', round(parent_auc, 5))
    print('TINY_OOE LL', round(ooe_ll, 5), 'AUC', round(ooe_auc, 5),
          'LL_GAIN', round(parent_ll - ooe_ll, 5), 'AUC_GAIN', round(ooe_auc - parent_auc, 5))
    print('SIZE_COUNTS', dict(sorted(chosen_size_counts.items())))
    print('SHRINK_COUNTS', dict(sorted(chosen_shrink_counts.items())))
    print()
    print('=== RECURRENT TINY REPRESENTATION ===')
    for name, count, sign_sum in recurrence_rows[:30]:
        print(name, 'SELECTED', count, 'SIGN_SUM', sign_sum)
    print()
    print('=== VERDICT ===')
    if len(pairs) == 45 and ooe_ll < parent_ll and ll_pass_both > 3:
        print('MINIMAL_RECURRENT_MSI_UNLOCKS_PROSPECTIVE_LOG_LOSS')
    elif ooe_ll < parent_ll:
        print('MINIMAL_RECURRENT_MSI_HAS_POSITIVE_OOE_SIGNAL')
    else:
        print('MINIMAL_RECURRENT_MSI_DOES_NOT_TRANSFER__REPRESENTATION_OR_OBJECTIVE_MUST_CHANGE')
    print('OUTPUT', OUT_PATH)


if __name__ == '__main__':
    main()
