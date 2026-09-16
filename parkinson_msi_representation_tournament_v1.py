from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import combinations
import json
from pathlib import Path

import numpy as np

from parkinson_invariant_3d_v1 import (
    build_or_load_inputs,
    load_parent_context,
    load_volume,
    logit_np,
    sigmoid_np,
)
from realitygraph.msi_representation_tournament import (
    approximate_univariate_consequence,
    build_structured_feature_bank,
    logistic_loss_from_logits,
    proximal_offset_logistic,
)

WORK = Path('/workspace')
CACHE_DIR = WORK / 'dat_parkinsons' / 'work'
BANK_PATH = CACHE_DIR / 'msi_representation_bank_v1_f32.npy'
META_PATH = CACHE_DIR / 'msi_representation_bank_v1_meta.json'
OUT_PATH = WORK / 'parkinson_msi_representation_tournament_v1.npz'


def safe_auc(y, p, roc_auc_score):
    y = np.asarray(y, dtype=np.int64)
    if np.unique(y).size < 2:
        return 0.5
    return float(roc_auc_score(y, p))


def fit_intercept(y, logits, max_iter=30):
    y = np.asarray(y, dtype=np.float64)
    z = np.asarray(logits, dtype=np.float64)
    a = 0.0
    for _ in range(max_iter):
        p = sigmoid_np(z + a)
        g = float(np.mean(p - y))
        h = float(np.mean(p * (1.0 - p))) + 1e-8
        step = g / h
        a -= step
        if abs(step) < 1e-8:
            break
    return float(a)


def load_or_build_bank(inputs, rebuild=False):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if BANK_PATH.exists() and META_PATH.exists() and not rebuild:
        bank = np.load(BANK_PATH, mmap_mode='r')
        meta = json.loads(META_PATH.read_text())
        if bank.ndim == 2 and bank.shape[0] == len(inputs) and bank.shape[1] == len(meta['names']):
            print('FEATURE_BANK', BANK_PATH, bank.shape, bank.dtype, flush=True)
            return bank, meta['names'], meta['families']
        print('FEATURE_BANK_REBUILD', bank.shape, 'meta', len(meta.get('names', [])), flush=True)

    print('BUILD_FEATURE_BANK', flush=True)
    bank, names, families = build_structured_feature_bank(inputs)
    np.save(BANK_PATH, bank.astype(np.float32, copy=False))
    META_PATH.write_text(json.dumps({'names': names, 'families': families}, separators=(',', ':')))
    bank = np.load(BANK_PATH, mmap_mode='r')
    counts = Counter(families)
    print('FEATURE_BANK_BUILT', bank.shape, dict(sorted(counts.items())), flush=True)
    return bank, names, families


def screen_bank(bank, y, base, env, discovery, chunk_size, min_sign):
    p = bank.shape[1]
    scores = np.empty(p, dtype=np.float64)
    stability = np.empty(p, dtype=np.float64)
    for start in range(0, p, chunk_size):
        stop = min(start + chunk_size, p)
        s, f = approximate_univariate_consequence(
            np.asarray(bank[:, start:stop], dtype=np.float32),
            y, base, env, discovery,
        )
        scores[start:stop] = s
        stability[start:stop] = f
    scores = np.where(stability >= min_sign, scores, -np.inf)
    return scores, stability


def standardize_discovery(bank, selected, discovery_idx):
    X = np.asarray(bank[:, selected], dtype=np.float64)
    mu = X[discovery_idx].mean(axis=0)
    sd = X[discovery_idx].std(axis=0)
    keep = sd > 1e-8
    if not np.any(keep):
        return np.zeros((len(X), 0), dtype=np.float64), mu[:0], sd[:0], keep
    X = X[:, keep]
    mu = mu[keep]
    sd = sd[keep]
    return (X - mu) / sd, mu, sd, keep


def evaluate_env(y, env, base, logits, target_env, log_loss, roc_auc_score):
    idx = env == target_env
    pred = sigmoid_np(logits[idx])
    yy = y[idx]
    parent = base[idx]
    return (
        float(log_loss(yy, parent) - log_loss(yy, pred)),
        safe_auc(yy, pred, roc_auc_score) - safe_auc(yy, parent, roc_auc_score),
    )


def main():
    parser = argparse.ArgumentParser(
        description='Fast bounded MSI representation tournament optimized for prospective log loss.'
    )
    parser.add_argument('--screen-top', type=int, default=384)
    parser.add_argument('--msi-max', type=int, default=48)
    parser.add_argument('--screen-chunk', type=int, default=2048)
    parser.add_argument('--min-sign', type=float, default=0.625,
                        help='minimum fraction of discovery environments agreeing on univariate direction')
    parser.add_argument('--l1', type=float, default=0.002)
    parser.add_argument('--l2', type=float, default=0.01)
    parser.add_argument('--iterations', type=int, default=160)
    parser.add_argument('--max-pairs', type=int, default=0, help='0 means all 45 outer pairs')
    parser.add_argument('--rebuild-bank', action='store_true')
    args = parser.parse_args()

    from sklearn.metrics import log_loss, roc_auc_score

    print('REALITYGRAPH / PARKINSON MSI REPRESENTATION TOURNAMENT V1')
    print('----------------------------------------------------------')
    print('Authority: prospective log loss for expert is_pathologic label')
    print('Parent: exact G1+G2 fixed logit offset')
    print('Grammar: intensity + distribution + contrast/gradient + multiscale spatial + z-shape + threshold-change')
    print('Screen: full discovery rows, environment-recurring one-step log-loss consequence')
    print('Fit: fixed-offset elastic net; sparse MSI refit; calibration intercept fit on discovery only')
    print('Outer protocol: 8 discovery environments -> 2 untouched futures, all 45 pairs')
    print('No future labels choose features, coefficients, calibration, or hyperparameters')
    print('SCREEN_TOP', args.screen_top, 'MSI_MAX', args.msi_max, 'MIN_SIGN', args.min_sign,
          'L1', args.l1, 'L2', args.l2, 'ITER', args.iterations)
    print()

    y, env, base = load_parent_context()
    base_logits = logit_np(base)
    parent_ll = float(log_loss(y, base))
    parent_auc = float(roc_auc_score(y, base))
    print('ROWS', len(y), 'PARENT_LL', round(parent_ll, 5), 'PARENT_AUC', round(parent_auc, 5))

    volume = load_volume(len(y))
    inputs = build_or_load_inputs(volume, rebuild=False)
    del volume
    bank, names, families = load_or_build_bank(inputs, rebuild=args.rebuild_bank)
    del inputs
    print('CANDIDATES', bank.shape[1])
    print('FAMILIES', dict(sorted(Counter(families).items())))
    print()

    pairs = list(combinations(range(10), 2))
    if args.max_pairs > 0:
        pairs = pairs[:args.max_pairs]

    selected_counts = Counter()
    selected_signed = defaultdict(float)
    family_counts = Counter()
    ll_pass_both = 0
    ll_auc_pass_both = 0
    prediction_logit_sum = np.zeros(len(y), dtype=np.float64)
    prediction_count = np.zeros(len(y), dtype=np.int64)
    per_pair = []

    for pair_no, (a, b) in enumerate(pairs, 1):
        discovery = tuple(e for e in range(10) if e not in (a, b))
        disc_idx = np.flatnonzero(np.isin(env, discovery))
        print(f'=== PAIR {a},{b} ({pair_no}/{len(pairs)}) DISCOVERY {discovery} ===', flush=True)

        scores, stability = screen_bank(
            bank, y, base, env, discovery,
            chunk_size=args.screen_chunk,
            min_sign=args.min_sign,
        )
        finite = np.flatnonzero(np.isfinite(scores))
        if len(finite) == 0:
            print('SCREEN EMPTY -> PARENT', flush=True)
            per_pair.append((a, b, 0, 0, 0.0, 0.0, 0.0, 0.0))
            continue
        order = finite[np.argsort(scores[finite])[::-1]]
        pre = order[:min(args.screen_top, len(order))]
        Z, _, _, keep = standardize_discovery(bank, pre, disc_idx)
        pre = pre[keep]
        if Z.shape[1] == 0:
            print('STANDARDIZED EMPTY -> PARENT', flush=True)
            per_pair.append((a, b, 0, 0, 0.0, 0.0, 0.0, 0.0))
            continue

        beta = proximal_offset_logistic(
            Z[disc_idx], y[disc_idx], base_logits[disc_idx],
            l1=args.l1, l2=args.l2, max_iter=args.iterations,
        )
        nz = np.flatnonzero(np.abs(beta) > 1e-6)
        if len(nz) == 0:
            # The screen found evidence but the sparse joint fit did not earn a
            # retained distinction. Preserve the parent rather than forcing one.
            print('ELASTIC_NET EMPTY -> PARENT', flush=True)
            per_pair.append((a, b, len(pre), 0, 0.0, 0.0, 0.0, 0.0))
            continue

        ranked_nz = nz[np.argsort(np.abs(beta[nz]))[::-1]]
        msi_local = ranked_nz[:min(args.msi_max, len(ranked_nz))]
        Zm = Z[:, msi_local]
        beta_msi = proximal_offset_logistic(
            Zm[disc_idx], y[disc_idx], base_logits[disc_idx],
            l1=args.l1 * 0.5, l2=args.l2, max_iter=args.iterations,
        )
        raw_disc = base_logits[disc_idx] + Zm[disc_idx] @ beta_msi
        intercept = fit_intercept(y[disc_idx], raw_disc)
        logits = base_logits + Zm @ beta_msi + intercept

        selected_global = pre[msi_local]
        for j, coef in zip(selected_global, beta_msi):
            selected_counts[names[j]] += 1
            selected_signed[names[j]] += float(np.sign(coef))
            family_counts[families[j]] += 1

        ll_a, auc_a = evaluate_env(y, env, base, logits, a, log_loss, roc_auc_score)
        ll_b, auc_b = evaluate_env(y, env, base, logits, b, log_loss, roc_auc_score)
        ll_pass = ll_a > 0.0 and ll_b > 0.0
        joint_pass = ll_pass and auc_a >= 0.0 and auc_b >= 0.0
        ll_pass_both += int(ll_pass)
        ll_auc_pass_both += int(joint_pass)

        future_idx = np.flatnonzero(np.isin(env, (a, b)))
        prediction_logit_sum[future_idx] += logits[future_idx]
        prediction_count[future_idx] += 1
        per_pair.append((a, b, len(pre), len(selected_global), ll_a, ll_b, auc_a, auc_b))
        top_text = ', '.join(names[j] for j in selected_global[:5])
        print('SCREENED', len(pre), 'MSI', len(selected_global),
              'LL', [round(ll_a, 5), round(ll_b, 5)],
              'AUC', [round(auc_a, 5), round(auc_b, 5)],
              'LL_PASS', int(ll_pass), 'JOINT', int(joint_pass), flush=True)
        print('TOP', top_text, flush=True)

    covered = prediction_count > 0
    ensemble_logits = base_logits.copy()
    ensemble_logits[covered] = prediction_logit_sum[covered] / prediction_count[covered]
    ensemble = sigmoid_np(ensemble_logits)
    ensemble_ll = float(log_loss(y[covered], ensemble[covered])) if np.any(covered) else parent_ll
    ensemble_auc = float(roc_auc_score(y[covered], ensemble[covered])) if np.any(covered) else parent_auc

    recurrence = []
    for name, count in selected_counts.most_common():
        recurrence.append((name, count, selected_signed[name]))

    np.savez_compressed(
        OUT_PATH,
        pair_results=np.asarray(per_pair, dtype=np.float64),
        ensemble_logits=ensemble_logits,
        prediction_count=prediction_count,
        recurrence_names=np.asarray([r[0] for r in recurrence], dtype=str),
        recurrence_counts=np.asarray([r[1] for r in recurrence], dtype=np.int64),
        recurrence_signed=np.asarray([r[2] for r in recurrence], dtype=np.float64),
    )

    print()
    print('=== OUTER TWO-ENVIRONMENT FUTURES ===')
    print('PAIRS_EVALUATED', len(pairs), '/45')
    print('MSI_LL_PASS_BOTH', ll_pass_both, '/', len(pairs))
    print('MSI_LL_AUC_NONNEG_PASS_BOTH', ll_auc_pass_both, '/', len(pairs))
    print('PRIOR_HANDCRAFTED_REFERENCE 3 /45')
    print()
    print('=== OOE ENSEMBLE ===')
    print('COVERED', int(covered.sum()), '/', len(y), 'PREDICTIONS_MINMAX',
          int(prediction_count[covered].min()) if np.any(covered) else 0,
          int(prediction_count[covered].max()) if np.any(covered) else 0)
    print('PARENT LL', round(parent_ll, 5), 'AUC', round(parent_auc, 5))
    print('MSI_OOE LL', round(ensemble_ll, 5), 'AUC', round(ensemble_auc, 5),
          'LL_GAIN', round(parent_ll - ensemble_ll, 5),
          'AUC_GAIN', round(ensemble_auc - parent_auc, 5))
    print()
    print('=== RECURRENT REPRESENTATION ===')
    for name, count, signed in recurrence[:30]:
        print(name, 'SELECTED', count, 'SIGN_SUM', round(float(signed), 1))
    print('FAMILY_COUNTS', dict(sorted(family_counts.items())))
    print()
    print('=== VERDICT ===')
    if len(pairs) == 45 and ensemble_ll < parent_ll and ll_pass_both > 3:
        print('MSI_REPRESENTATION_IMPROVES_PROSPECTIVE_LOG_LOSS')
    elif ensemble_ll < parent_ll:
        print('MSI_REPRESENTATION_HAS_POSITIVE_OOE_LOG_LOSS_SIGNAL')
    else:
        print('MSI_V1_DOES_NOT_YET_UNLOCK_PROSPECTIVE_LOG_LOSS')
    print('OUTPUT', OUT_PATH)


if __name__ == '__main__':
    main()
