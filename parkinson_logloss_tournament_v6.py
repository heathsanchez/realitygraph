from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np

from parkinson_final_submission_v5 import DENSE_ANCHOR, fit_final_model
from parkinson_invariant_3d_v1 import load_parent_context, logit_np, sigmoid_np
from parkinson_object_relative_geometry_v1 import load_r_map
from parkinson_threshold_trajectory_v3 import load_or_build_trajectory
from realitygraph.logloss_meta import (
    DEFAULT_FAMILIES,
    apply_family,
    fit_family,
    fit_leave_environment_out,
    log_loss,
)
from realitygraph.msi_minimal_recurrence import fit_robust_tiny_model

WORK = Path('/workspace')
OUT_DIR = WORK / 'parkinson_logloss_v6'
META_PATH = OUT_DIR / 'logloss_model.json'
NPZ_PATH = OUT_DIR / 'logloss_tournament_v6.npz'
V5_REFERENCE_LL = 0.336239


def safe_auc(y, p):
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, p))


def anchor_streams(y, env, base, anchor, *, min_agree=0.75, anchor_shrink=0.5):
    base_logits = logit_np(base)
    all_envs = tuple(int(e) for e in np.unique(env))
    oof_logits = np.empty(len(y), dtype=np.float64)
    for held in all_envs:
        train_envs = tuple(e for e in all_envs if e != held)
        model = fit_robust_tiny_model(
            anchor[:, None], y, base_logits, env, train_envs,
            min_sign_fraction=min_agree, shrinkage=anchor_shrink,
        )
        take = env == held
        oof_logits[take] = model['logits'][take]
    full = fit_robust_tiny_model(
        anchor[:, None], y, base_logits, env, all_envs,
        min_sign_fraction=min_agree, shrinkage=anchor_shrink,
    )
    return sigmoid_np(oof_logits), sigmoid_np(full['logits'])


def env_report(y, env, reference, pred):
    rows = []
    for e in sorted(int(v) for v in np.unique(env)):
        take = env == e
        ref_ll = log_loss(y[take], reference[take])
        new_ll = log_loss(y[take], pred[take])
        rows.append((e, ref_ll - new_ll, new_ll))
    return rows


def nested_family_selector(families, streams, y, env):
    """Outer environment holdout; choose family using only the other environments."""
    env = np.asarray(env)
    y = np.asarray(y)
    unique = tuple(sorted(int(e) for e in np.unique(env)))
    pred = np.empty(len(y), dtype=np.float64)
    selected = []

    for outer in unique:
        train_envs = tuple(e for e in unique if e != outer)
        train_mask = np.isin(env, train_envs)
        best = None
        for family in families:
            inner_pred = np.empty(int(train_mask.sum()), dtype=np.float64)
            train_indices = np.flatnonzero(train_mask)
            train_env_array = env[train_indices]
            train_y = y[train_indices]
            train_streams_all = {k: np.asarray(v)[train_indices] for k, v in streams.items()}

            for inner in train_envs:
                inner_train = train_env_array != inner
                inner_test = train_env_array == inner
                fit_streams = {k: v[inner_train] for k, v in train_streams_all.items()}
                test_streams = {k: v[inner_test] for k, v in train_streams_all.items()}
                params = fit_family(family, fit_streams, train_y[inner_train])
                inner_pred[inner_test] = apply_family(family, params, test_streams)

            ll = log_loss(train_y, inner_pred)
            row = (ll, family)
            if best is None or row < best[:2]:
                best = (ll, family)

        _, family = best
        fit_streams = {k: np.asarray(v)[train_mask] for k, v in streams.items()}
        test_mask = env == outer
        test_streams = {k: np.asarray(v)[test_mask] for k, v in streams.items()}
        params = fit_family(family, fit_streams, y[train_mask])
        pred[test_mask] = apply_family(family, params, test_streams)
        selected.append((outer, family, params))

    return pred, selected


def main():
    parser = argparse.ArgumentParser(description='Nested log-loss minimization tournament over frozen V5 prediction streams.')
    parser.add_argument('--families', default=','.join(DEFAULT_FAMILIES))
    parser.add_argument('--min-agree', type=float, default=0.75)
    parser.add_argument('--anchor-shrink', type=float, default=0.5)
    parser.add_argument('--min-freeze-gain', type=float, default=0.0001)
    args = parser.parse_args()

    families = tuple(x.strip() for x in args.families.split(',') if x.strip())
    print('REALITYGRAPH / PARKINSON LOG-LOSS TOURNAMENT V6')
    print('-------------------------------------------------')
    print('Representation frozen: V5 parent + anchor + two-feature V3 residual')
    print('No new scan features. No test-distribution fitting. Objective: log loss only.')
    print('Families', len(families), families)

    y, env, base = load_parent_context()
    r = load_r_map(len(y))
    trajectory, names, _ = load_or_build_trajectory(r, rebuild=False)
    idx = {name: j for j, name in enumerate(names)}
    anchor = np.asarray(trajectory[:, idx[DENSE_ANCHOR]], dtype=np.float64)

    v5_model, v5_oof, v5_full = fit_final_model(
        y, env, base, trajectory, names, anchor,
        min_agree=args.min_agree,
        anchor_shrink=args.anchor_shrink,
    )
    anchor_oof, anchor_full = anchor_streams(
        y, env, base, anchor,
        min_agree=args.min_agree, anchor_shrink=args.anchor_shrink,
    )
    del r, trajectory

    oof_streams = {
        'parent': np.asarray(base, dtype=np.float64),
        'anchor': np.asarray(anchor_oof, dtype=np.float64),
        'full': np.asarray(v5_oof, dtype=np.float64),
    }
    deployment_streams = {
        'parent': np.asarray(base, dtype=np.float64),
        'anchor': np.asarray(anchor_full, dtype=np.float64),
        'full': np.asarray(v5_full, dtype=np.float64),
    }

    reference_ll = log_loss(y, oof_streams['full'])
    reference_auc = safe_auc(y, oof_streams['full'])
    print('ROWS', len(y), 'V5_LOEO_LL', round(reference_ll, 6), 'V5_LOEO_AUC', round(reference_auc, 6))
    print()

    rows = []
    results = {}
    print('=== PER-FAMILY META-LOEO ===')
    for family in families:
        result = fit_leave_environment_out(family, oof_streams, y, env)
        pred = result['predictions']
        auc = safe_auc(y, pred)
        erows = env_report(y, env, oof_streams['full'], pred)
        pos = sum(g > 0.0 for _, g, _ in erows)
        worst = min(g for _, g, _ in erows)
        gain = reference_ll - result['ll']
        row = (result['ll'], -pos, -worst, family)
        rows.append(row)
        results[family] = {
            'result': result,
            'auc': auc,
            'gain': gain,
            'env_pos': pos,
            'env_worst_gain': worst,
        }
        print(f'{family:30s} LL {result["ll"]:.6f} GAIN {gain:+.6f} AUC {auc:.6f} ENV_POS {pos}/10 WORST {worst:+.6f}', flush=True)

    rows.sort()
    best_family = rows[0][3]
    best = results[best_family]

    print()
    print('=== NESTED FAMILY-SELECTION CHECK ===')
    nested_pred, nested_selected = nested_family_selector(families, oof_streams, y, env)
    nested_ll = log_loss(y, nested_pred)
    nested_auc = safe_auc(y, nested_pred)
    nested_gain = reference_ll - nested_ll
    counts = Counter(family for _, family, _ in nested_selected)
    print('NESTED_SELECTOR_LL', round(nested_ll, 6), 'GAIN', round(nested_gain, 6), 'AUC', round(nested_auc, 6))
    print('NESTED_SELECTED_COUNTS', dict(counts))
    for outer, family, params in nested_selected:
        print('OUTER', outer, 'FAMILY', family, 'PARAMS', json.dumps(params, sort_keys=True))

    # Freeze the single best family by 10-way meta-LOEO, with identity fallback.
    freeze_family = best_family
    if best['gain'] < args.min_freeze_gain:
        freeze_family = 'identity_full'
    freeze_params = fit_family(freeze_family, oof_streams, y)
    meta_oof = results[freeze_family]['result']['predictions'] if freeze_family in results else oof_streams['full']
    deploy_pred = apply_family(freeze_family, freeze_params, deployment_streams)

    meta = {
        'version': 'parkinson-logloss-v6',
        'family': freeze_family,
        'params': freeze_params,
        'source_model_version': v5_model.get('version'),
        'validation': {
            'v5_loeo_ll': reference_ll,
            'v5_loeo_auc': reference_auc,
            'meta_loeo_ll': log_loss(y, meta_oof),
            'meta_loeo_auc': safe_auc(y, meta_oof),
            'meta_loeo_gain': reference_ll - log_loss(y, meta_oof),
            'nested_selector_ll': nested_ll,
            'nested_selector_auc': nested_auc,
            'nested_selector_gain': nested_gain,
        },
        'diagnostic_full_fit': {
            'll': log_loss(y, deploy_pred),
            'auc': safe_auc(y, deploy_pred),
        },
        'families': {
            family: {
                'loeo_ll': float(results[family]['result']['ll']),
                'loeo_auc': float(results[family]['auc']),
                'gain_vs_v5': float(results[family]['gain']),
                'env_pos': int(results[family]['env_pos']),
                'env_worst_gain': float(results[family]['env_worst_gain']),
            }
            for family in families
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    META_PATH.write_text(json.dumps(meta, indent=2, sort_keys=True) + '\n')
    np.savez_compressed(
        NPZ_PATH,
        y=np.asarray(y, dtype=np.int8),
        env=np.asarray(env, dtype=np.int8),
        parent_oof=oof_streams['parent'],
        anchor_oof=oof_streams['anchor'],
        v5_oof=oof_streams['full'],
        meta_oof=np.asarray(meta_oof, dtype=np.float64),
        nested_selector_oof=np.asarray(nested_pred, dtype=np.float64),
        parent_full=deployment_streams['parent'],
        anchor_full=deployment_streams['anchor'],
        v5_full=deployment_streams['full'],
        meta_full=np.asarray(deploy_pred, dtype=np.float64),
    )

    print()
    print('=== FREEZE ===')
    print('BEST_FAMILY', best_family, 'BEST_GAIN', round(float(best['gain']), 6))
    print('FREEZE_FAMILY', freeze_family)
    print('FREEZE_PARAMS', json.dumps(freeze_params, sort_keys=True))
    print('META_LOEO_LL', round(meta['validation']['meta_loeo_ll'], 6))
    print('META_LOEO_AUC', round(meta['validation']['meta_loeo_auc'], 6))
    print('META_LOEO_GAIN_V5', round(meta['validation']['meta_loeo_gain'], 6))
    print('NESTED_SELECTOR_LL', round(nested_ll, 6))
    print('FULL_FIT_DIAGNOSTIC_LL', round(meta['diagnostic_full_fit']['ll'], 6))
    print('META_MODEL', META_PATH)
    print('NPZ', NPZ_PATH)
    print()
    print('=== VERDICT ===')
    if freeze_family == 'identity_full':
        print('NO_LOGLOSS_META_TRICK_EARNS_FREEZE__KEEP_V5')
    else:
        print('LOGLOSS_META_LAYER_EARNS_V6_FREEZE')


if __name__ == '__main__':
    main()
