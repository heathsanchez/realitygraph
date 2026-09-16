from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import roc_auc_score

from parkinson_invariant_3d_v1 import load_parent_context
from realitygraph.latent_wild import (
    apply_two_stream_stack,
    fit_fold_latent,
    fit_two_stream_stack,
    loeo_latent_predictions,
    predict_fold_latent,
)
from realitygraph.logloss_meta import log_loss

WORK = Path('/workspace')
STACK_PATH = WORK / 'dat_parkinsons/work/fixed_resnet18_stack.npy'
V6_NPZ = WORK / 'parkinson_logloss_v6/logloss_tournament_v6.npz'
OUT = WORK / 'parkinson_latent_v8'
MODEL_PATH = OUT / 'latent_model.joblib'
META_PATH = OUT / 'latent_meta.json'
OOF_PATH = OUT / 'latent_v8_oof.npz'

PCA_DIMS = (16, 32, 64, 128)
LOGISTIC_C = (0.01, 0.03, 0.1, 0.3, 1.0)
STACK_RIDGE = (0.001, 0.01, 0.05)
V6_REFERENCE_LL = 0.327251
V6_REFERENCE_AUC = 0.931768


def candidate_grid():
    rows = []
    for dim in PCA_DIMS:
        for C in LOGISTIC_C:
            rows.append((dim, 'logistic', C))
        rows.append((dim, 'prototype', 1.0))
    return rows


def stack_loeo_from_oof(v6, latent, y, env, ridge):
    pred = np.empty(len(y), dtype=np.float64)
    for held in sorted(np.unique(env).tolist()):
        tr = env != held
        te = env == held
        model = fit_two_stream_stack(v6[tr], latent[tr], y[tr], ridge=ridge)
        pred[te] = apply_two_stream_stack(model, v6[te], latent[te])
    return pred


def nested_validate_candidate(X, y, env, v6, pca_dim, learner, C, ridge):
    unique = sorted(np.unique(env).tolist())
    latent_outer = np.empty(len(y), dtype=np.float64)
    stacked_outer = np.empty(len(y), dtype=np.float64)
    outer_stack_params = []

    for outer in unique:
        outer_train = env != outer
        outer_test = env == outer
        inner_latent = np.empty(int(outer_train.sum()), dtype=np.float64)
        outer_idx = np.flatnonzero(outer_train)
        env_train = env[outer_idx]
        y_train = y[outer_idx]
        X_train = X[outer_idx]

        for inner in sorted(np.unique(env_train).tolist()):
            fit = env_train != inner
            take = env_train == inner
            model = fit_fold_latent(X_train[fit], y_train[fit], pca_dim, learner, C)
            inner_latent[take] = predict_fold_latent(model, X_train[take])

        stack = fit_two_stream_stack(
            v6[outer_idx], inner_latent, y_train, ridge=ridge
        )
        deploy_latent = fit_fold_latent(
            X[outer_train], y[outer_train], pca_dim, learner, C
        )
        latent_test = predict_fold_latent(deploy_latent, X[outer_test])
        latent_outer[outer_test] = latent_test
        stacked_outer[outer_test] = apply_two_stream_stack(
            stack, v6[outer_test], latent_test
        )
        outer_stack_params.append({'held': int(outer), 'stack': stack})

    return {
        'latent': latent_outer,
        'stacked': stacked_outer,
        'stack_params': outer_stack_params,
    }


def env_gate_report(y, env, reference, pred):
    total_gain = log_loss(y, reference) - log_loss(y, pred)
    rows = []
    weighted_positive = []
    n = len(y)
    for e in sorted(np.unique(env).tolist()):
        take = env == e
        ref = log_loss(y[take], reference[take])
        new = log_loss(y[take], pred[take])
        gain = ref - new
        contribution = (int(take.sum()) / n) * gain
        rows.append({
            'env': int(e), 'n': int(take.sum()), 'ref_ll': ref,
            'new_ll': new, 'gain': gain, 'weighted_contribution': contribution,
        })
        if contribution > 0:
            weighted_positive.append(contribution)
    max_share = 0.0
    if total_gain > 0 and weighted_positive:
        max_share = max(weighted_positive) / total_gain
    return rows, total_gain, max_share


def main():
    print('REALITYGRAPH / PARKINSON LATENT WILD V8')
    print('-----------------------------------------')
    print('Frozen ResNet stack -> fold-local scaler/PCA -> latent learner -> V6 stack')

    y, env, _ = load_parent_context()
    y = np.asarray(y, dtype=np.int64)
    env = np.asarray(env, dtype=np.int64)
    raw = np.load(STACK_PATH, mmap_mode='r')
    if raw.shape[0] != len(y):
        raise RuntimeError(f'latent rows mismatch: {raw.shape} vs {len(y)}')
    X = np.asarray(raw, dtype=np.float32).reshape(len(y), -1)

    d = np.load(V6_NPZ)
    if 'meta_oof' not in d.files:
        raise RuntimeError(f'meta_oof missing from {V6_NPZ}; keys={d.files}')
    v6 = np.asarray(d['meta_oof'], dtype=np.float64)
    if len(v6) != len(y):
        raise RuntimeError('V6 OOF row mismatch')
    ref_ll = log_loss(y, v6)
    ref_auc = float(roc_auc_score(y, v6))
    print('ROWS', len(y), 'LATENT', X.shape, 'V6_LL', round(ref_ll, 6), 'V6_AUC', round(ref_auc, 6))

    screens = []
    screen_cache = {}
    print('\n=== PRIMARY SCREEN ===')
    for dim, learner, C in candidate_grid():
        result = loeo_latent_predictions(X, y, env, dim, learner, C)
        latent = result['predictions']
        latent_ll = log_loss(y, latent)
        latent_auc = float(roc_auc_score(y, latent))
        for ridge in STACK_RIDGE:
            stacked = stack_loeo_from_oof(v6, latent, y, env, ridge)
            sll = log_loss(y, stacked)
            sauc = float(roc_auc_score(y, stacked))
            key = (dim, learner, C, ridge)
            screens.append((sll, -sauc, dim, learner, C, ridge))
            screen_cache[key] = (latent, stacked, latent_ll, latent_auc, sll, sauc)
        best_local = min(
            (r for r in screens if r[2] == dim and r[3] == learner and r[4] == C),
            key=lambda r: (r[0], r[1]),
        )
        print(
            'CAND', dim, learner, C,
            'LAT_LL', round(latent_ll, 6), 'LAT_AUC', round(latent_auc, 6),
            'BEST_STACK_LL', round(best_local[0], 6), 'RIDGE', best_local[5],
            flush=True,
        )

    screens.sort(key=lambda r: (r[0], r[1], r[2]))
    top = []
    seen_arch = set()
    for row in screens:
        arch = (row[2], row[3], row[4])
        if arch in seen_arch:
            continue
        seen_arch.add(arch)
        top.append(row)
        if len(top) == 3:
            break

    print('\n=== STRICT NESTED CHECK: TOP 3 ===')
    nested_rows = []
    nested_cache = {}
    for screen_row in top:
        _, _, dim, learner, C, ridge = screen_row
        nested = nested_validate_candidate(X, y, env, v6, dim, learner, C, ridge)
        stacked = nested['stacked']
        latent = nested['latent']
        sll = log_loss(y, stacked)
        sauc = float(roc_auc_score(y, stacked))
        lll = log_loss(y, latent)
        lauc = float(roc_auc_score(y, latent))
        key = (dim, learner, C, ridge)
        nested_rows.append((sll, -sauc, dim, learner, C, ridge, lll, lauc))
        nested_cache[key] = nested
        print(
            'NESTED', dim, learner, C, 'RIDGE', ridge,
            'LAT_LL', round(lll, 6), 'LAT_AUC', round(lauc, 6),
            'STACK_LL', round(sll, 6), 'STACK_AUC', round(sauc, 6),
            flush=True,
        )

    nested_rows.sort(key=lambda r: (r[0], r[1], r[2]))
    best = nested_rows[0]
    best_ll, neg_auc, dim, learner, C, ridge, latent_ll, latent_auc = best
    best_auc = -neg_auc
    key = (dim, learner, C, ridge)
    nested = nested_cache[key]
    env_rows, gain, max_share = env_gate_report(y, env, v6, nested['stacked'])
    env_pos = sum(r['gain'] > 0 for r in env_rows)
    independent_ranking = (latent_auc > V6_REFERENCE_AUC) or (best_auc >= V6_REFERENCE_AUC + 0.001)

    print('\n=== BEST STRICT RESULT ===')
    print('ARCH', {'pca_dim': dim, 'learner': learner, 'C': C, 'stack_ridge': ridge})
    print('LATENT_LL', round(latent_ll, 6))
    print('LATENT_AUC', round(latent_auc, 6))
    print('STACK_LL', round(best_ll, 6))
    print('STACK_AUC', round(best_auc, 6))
    print('GAIN_V6', round(gain, 6))
    print('ENV_POS', f'{env_pos}/10')
    print('MAX_GAIN_SHARE', round(max_share, 6))
    for row in env_rows:
        print('ENV', row['env'], 'N', row['n'], 'GAIN', round(row['gain'], 6), 'CONTRIB', round(row['weighted_contribution'], 6))

    gates = {
        'll': best_ll < V6_REFERENCE_LL,
        'auc': best_auc > V6_REFERENCE_AUC,
        'env_pos': env_pos >= 6,
        'gain_concentration': gain > 0 and max_share <= 0.5,
        'independent_ranking': bool(independent_ranking),
    }
    print('GATES', json.dumps(gates, sort_keys=True))

    if not all(gates.values()):
        print('\nLATENT_WILD_FAILS_GATE_KEEP_V6')
        return

    # Final deployment latent model uses all rows; final stack learns only from cross-fitted streams.
    simple_latent = screen_cache[key][0]
    final_latent_model = fit_fold_latent(X, y, dim, learner, C)
    final_stack = fit_two_stream_stack(v6, simple_latent, y, ridge=ridge)

    OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            'version': 'parkinson-latent-wild-v8',
            'feature_shape': [5, 512],
            'flattened_dim': int(X.shape[1]),
            'pca_dim': int(dim),
            'learner_name': learner,
            'C': float(C),
            'model': final_latent_model,
        },
        MODEL_PATH,
        compress=3,
    )
    meta = {
        'version': 'parkinson-latent-wild-v8',
        'pca_dim': int(dim),
        'learner': learner,
        'C': float(C),
        'stack_ridge': float(ridge),
        'stack': final_stack,
        'validation': {
            'v6_ll': float(ref_ll), 'v6_auc': float(ref_auc),
            'latent_nested_ll': float(latent_ll), 'latent_nested_auc': float(latent_auc),
            'stack_nested_ll': float(best_ll), 'stack_nested_auc': float(best_auc),
            'gain_v6': float(gain), 'env_pos': int(env_pos),
            'max_gain_share': float(max_share), 'gates': gates,
        },
    }
    META_PATH.write_text(json.dumps(meta, indent=2, sort_keys=True) + '\n')
    np.savez_compressed(
        OOF_PATH,
        y=y, env=env, v6_oof=v6,
        latent_nested_oof=nested['latent'],
        stacked_nested_oof=nested['stacked'],
        latent_simple_oof=simple_latent,
    )
    print('MODEL', MODEL_PATH)
    print('META', META_PATH)
    print('OOF', OOF_PATH)
    print('\nLATENT_WILD_EARNS_V8_BUILD')


if __name__ == '__main__':
    main()
