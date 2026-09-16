from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path

import numpy as np

from parkinson_invariant_3d_v1 import load_parent_context, logit_np, sigmoid_np
from parkinson_object_relative_geometry_v1 import load_r_map
from parkinson_threshold_trajectory_v3 import load_or_build_trajectory
from realitygraph.final_trajectory_model import export_model
from realitygraph.geometry_core_contraction import greedy_contract
from realitygraph.msi_minimal_recurrence import environment_recurrence, fit_robust_tiny_model
from realitygraph.object_relative_geometry import subject_relative_geometry_features

WORK = Path('/workspace')
ROOT = Path(__file__).resolve().parent
OUT_DIR = WORK / 'parkinson_final_submission_v5'
MODEL_PATH = OUT_DIR / 'model.json'
BUNDLE_PATH = WORK / 'parkinson_final_submission_v5_patch_bundle.zip'
OLD_ANCHOR = 'right_delta_f50_f70_mean_uptake'
DENSE_ANCHOR = 'right_mean_uptake_delta_50_70'


def _jsonable_model(anchor_model, residual_model, residual_names, *, selection, metrics):
    if residual_model is None:
        residual = {
            'names': [], 'mean': [], 'scale': [], 'beta': [], 'shrinkage': 0.0,
        }
    else:
        residual = {
            'names': list(residual_names),
            'mean': residual_model['mean'].tolist(),
            'scale': residual_model['scale'].tolist(),
            'beta': residual_model['beta'].tolist(),
            'shrinkage': float(residual_model['shrinkage']),
        }
    return {
        'version': 'parkinson-threshold-trajectory-v3-final-all-envs',
        'parent': {
            'name': 'canonical+G1+G2',
            'g1': {'feature': 'L_elong_q95', 'threshold': 1.5314126014709473, 'd0': 0.90, 'd1': -0.15},
            'g2': {'feature': 'R_q90', 'threshold': 2.02439, 'd0': 0.30, 'd1': -0.10},
        },
        'anchor': {
            'name': DENSE_ANCHOR,
            'mean': anchor_model['mean'].tolist(),
            'scale': anchor_model['scale'].tolist(),
            'beta': anchor_model['beta'].tolist(),
            'shrinkage': float(anchor_model['shrinkage']),
        },
        'residual': residual,
        'selection': selection,
        'metrics': metrics,
    }


def fit_final_model(y, env, base, trajectory, names, anchor, *, core_top=16,
                    min_agree=0.75, sizes=(0,1,2,3,4,6,8),
                    shrinkages=(0.125,0.25,0.5,0.75), anchor_shrink=0.5,
                    contraction_tol=0.00025):
    from sklearn.metrics import log_loss, roc_auc_score

    y = np.asarray(y, dtype=np.int64)
    env = np.asarray(env, dtype=np.int64)
    base = np.asarray(base, dtype=np.float64)
    base_logits = logit_np(base)
    trajectory = np.asarray(trajectory, dtype=np.float64)
    anchor = np.asarray(anchor, dtype=np.float64).reshape(-1)
    all_envs = tuple(int(e) for e in np.unique(env))
    if all_envs != tuple(range(10)):
        raise RuntimeError(f'expected environments 0..9, got {all_envs}')

    anchor_full = fit_robust_tiny_model(
        anchor[:, None], y, base_logits, env, all_envs,
        min_sign_fraction=min_agree, shrinkage=anchor_shrink,
    )
    anchored_logits = anchor_full['logits']

    exact = environment_recurrence(trajectory, y, anchored_logits, env, all_envs)
    name_to_idx = {n: i for i, n in enumerate(names)}
    anchor_dense_idx = name_to_idx[DENSE_ANCHOR]
    valid = np.flatnonzero((exact['sign_fraction'] >= min_agree) & (exact['score'] > 0.0))
    valid = valid[valid != anchor_dense_idx]
    if len(valid):
        valid = valid[np.argsort(exact['score'][valid])[::-1]]
    core = tuple(int(j) for j in valid[:min(core_top, len(valid))])

    cache = {}

    def score_subset(feature_tuple):
        key = tuple(int(j) for j in feature_tuple)
        if key in cache:
            return cache[key][0]
        grid = shrinkages if key else (0.0,)
        best = None
        for residual_shrink in grid:
            loss_sum = 0.0
            n_sum = 0
            for held in all_envs:
                train_envs = tuple(e for e in all_envs if e != held)
                am = fit_robust_tiny_model(
                    anchor[:, None], y, base_logits, env, train_envs,
                    min_sign_fraction=min_agree, shrinkage=anchor_shrink,
                )
                logits = am['logits']
                if key:
                    rm = fit_robust_tiny_model(
                        trajectory[:, key], y, logits, env, train_envs,
                        min_sign_fraction=min_agree, shrinkage=residual_shrink,
                    )
                    logits = rm['logits']
                take = env == held
                p = sigmoid_np(logits[take])
                loss_sum += float(log_loss(y[take], p)) * int(take.sum())
                n_sum += int(take.sum())
            row = (loss_sum / max(n_sum, 1), float(residual_shrink))
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
    _, best_k, _ = min(candidates, key=lambda row: (row[0], row[1], row[2]))
    initial = core[:best_k]
    if initial:
        contracted = greedy_contract(initial, score_subset, tolerance=contraction_tol)
        chosen = tuple(contracted['features'])
        removed = tuple(contracted['removed'])
    else:
        chosen, removed = tuple(), tuple()
    loeo_ll = float(score_subset(chosen))
    residual_shrink = float(cache[chosen][1])

    anchor_final = fit_robust_tiny_model(
        anchor[:, None], y, base_logits, env, all_envs,
        min_sign_fraction=min_agree, shrinkage=anchor_shrink,
    )
    full_logits = anchor_final['logits']
    residual_final = None
    if chosen:
        residual_final = fit_robust_tiny_model(
            trajectory[:, chosen], y, full_logits, env, all_envs,
            min_sign_fraction=min_agree, shrinkage=residual_shrink,
        )
        full_logits = residual_final['logits']

    oof_logits = np.zeros(len(y), dtype=np.float64)
    anchor_oof_logits = np.zeros(len(y), dtype=np.float64)
    for held in all_envs:
        train_envs = tuple(e for e in all_envs if e != held)
        am = fit_robust_tiny_model(
            anchor[:, None], y, base_logits, env, train_envs,
            min_sign_fraction=min_agree, shrinkage=anchor_shrink,
        )
        logits = am['logits']
        take = env == held
        anchor_oof_logits[take] = logits[take]
        if chosen:
            rm = fit_robust_tiny_model(
                trajectory[:, chosen], y, logits, env, train_envs,
                min_sign_fraction=min_agree, shrinkage=residual_shrink,
            )
            logits = rm['logits']
        oof_logits[take] = logits[take]

    parent_ll = float(log_loss(y, base))
    parent_auc = float(roc_auc_score(y, base))
    anchor_oof = sigmoid_np(anchor_oof_logits)
    final_oof = sigmoid_np(oof_logits)
    full_pred = sigmoid_np(full_logits)
    metrics = {
        'parent_ll': parent_ll,
        'parent_auc': parent_auc,
        'anchor_loeo_ll': float(log_loss(y, anchor_oof)),
        'anchor_loeo_auc': float(roc_auc_score(y, anchor_oof)),
        'final_loeo_ll': float(log_loss(y, final_oof)),
        'final_loeo_auc': float(roc_auc_score(y, final_oof)),
        'full_fit_ll': float(log_loss(y, full_pred)),
        'full_fit_auc': float(roc_auc_score(y, full_pred)),
    }
    selection = {
        'core_top': int(core_top),
        'initial_size': int(len(initial)),
        'final_size': int(len(chosen)),
        'removed': [names[j] for j in removed],
        'residual_names': [names[j] for j in chosen],
        'residual_shrinkage': residual_shrink,
        'anchor_shrinkage': float(anchor_shrink),
        'loeo_ll': loeo_ll,
        'min_agree': float(min_agree),
        'contraction_tol': float(contraction_tol),
    }
    model = _jsonable_model(
        anchor_final, residual_final, [names[j] for j in chosen],
        selection=selection, metrics=metrics,
    )
    return model, final_oof, full_pred


def build_patch_bundle(model):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    export_model(model, MODEL_PATH)
    shutil.copy2(ROOT / 'parkinson_runtime_patch.py', OUT_DIR / 'parkinson_runtime_patch.py')
    pkg = OUT_DIR / 'realitygraph'
    pkg.mkdir(exist_ok=True)
    (pkg / '__init__.py').write_text('')
    for name in ('canonical_striatal.py', 'object_relative_geometry.py', 'threshold_trajectory.py', 'final_trajectory_model.py'):
        shutil.copy2(ROOT / 'realitygraph' / name, pkg / name)
    (OUT_DIR / 'INTEGRATE.txt').write_text(
        'Integrate with the existing canonical submission, before any old RealityGraph patches:\n\n'
        'from pathlib import Path\n'
        'from parkinson_runtime_patch import load_model, patch_probability\n\n'
        'MODEL = load_model(Path(__file__).with_name("model.json"))\n\n'
        '# inside the per-scan prediction path:\n'
        '# canonical_prob = <existing canonical model probability>\n'
        '# pred = patch_probability(filepath, canonical_prob, MODEL)\n\n'
        'If the canonical submission already applies G1+G2, use patch_probability(..., already_parent=True).\n'
    )
    if BUNDLE_PATH.exists():
        BUNDLE_PATH.unlink()
    with zipfile.ZipFile(BUNDLE_PATH, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUT_DIR.rglob('*')):
            if path.is_file():
                zf.write(path, path.relative_to(OUT_DIR))
    return BUNDLE_PATH


def main():
    parser = argparse.ArgumentParser(description='Freeze V3 on all 10 environments and export the runtime patch bundle.')
    parser.add_argument('--core-top', type=int, default=16)
    parser.add_argument('--min-agree', type=float, default=0.75)
    parser.add_argument('--sizes', default='0,1,2,3,4,6,8')
    parser.add_argument('--shrinkages', default='0.125,0.25,0.5,0.75')
    parser.add_argument('--anchor-shrink', type=float, default=0.5)
    parser.add_argument('--contraction-tol', type=float, default=0.00025)
    args = parser.parse_args()

    sizes = tuple(sorted({int(x) for x in args.sizes.split(',') if int(x) >= 0}))
    shrinkages = tuple(sorted({float(x) for x in args.shrinkages.split(',') if float(x) > 0.0}))

    print('REALITYGRAPH / PARKINSON FINAL SUBMISSION V5')
    print('---------------------------------------------')
    print('Freeze: V3 anchor-conditional threshold trajectory; all 10 training environments')
    print('Selection: 10-way leave-one-environment-out; then fit frozen interface on all rows')
    print('No V4 safe gate: primary competition authority is log loss')

    y, env, base = load_parent_context()
    r = load_r_map(len(y))
    trajectory, names, _ = load_or_build_trajectory(r, rebuild=False)
    name_to_idx = {n: i for i, n in enumerate(names)}
    if DENSE_ANCHOR not in name_to_idx:
        raise RuntimeError(f'dense anchor missing: {DENSE_ANCHOR}')
    dense_anchor = np.asarray(trajectory[:, name_to_idx[DENSE_ANCHOR]], dtype=np.float64)

    geometry, geometry_names, _ = subject_relative_geometry_features(r)
    old_anchor = np.asarray(geometry[:, geometry_names.index(OLD_ANCHOR)], dtype=np.float64)
    parity = float(np.max(np.abs(old_anchor - dense_anchor)))
    if parity > 2e-6:
        raise RuntimeError(f'anchor parity failed: {parity}')
    del geometry, r
    print('ROWS', len(y), 'TRAJECTORY', trajectory.shape, 'ANCHOR_PARITY_MAX', f'{parity:.3g}')

    model, oof_pred, full_pred = fit_final_model(
        y, env, base, trajectory, names, dense_anchor,
        core_top=args.core_top, min_agree=args.min_agree,
        sizes=sizes, shrinkages=shrinkages,
        anchor_shrink=args.anchor_shrink, contraction_tol=args.contraction_tol,
    )
    bundle = build_patch_bundle(model)

    print()
    print('=== FINAL FROZEN INTERFACE ===')
    print('ANCHOR', model['anchor']['name'], 'BETA', model['anchor']['beta'], 'SHRINK', model['anchor']['shrinkage'])
    print('RESIDUAL', model['residual']['names'])
    print('RESIDUAL_BETA', [round(float(x), 6) for x in model['residual']['beta']])
    print('RESIDUAL_SHRINK', model['residual']['shrinkage'])
    print('SELECTION', json.dumps(model['selection'], sort_keys=True))
    print()
    print('=== FINAL VALIDATION ===')
    for k, v in model['metrics'].items():
        print(k.upper(), round(float(v), 6))
    print('MODEL', MODEL_PATH)
    print('PATCH_BUNDLE', bundle)
    print('NEXT: patch the existing canonical main.py, then run the official runtime smoke test.')


if __name__ == '__main__':
    main()
