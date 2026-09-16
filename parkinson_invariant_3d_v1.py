from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path
import random

import numpy as np

from realitygraph.invariant_3d import (
    bilateral_channels,
    downsample_mean3d,
    group_dro_weights,
    robust_views,
)

WORK = Path('/workspace')
VOLUME_CANDIDATES = (
    WORK / 'real64_volume.npz',
    WORK / 'dat_parkinsons' / 'work' / 'real64_volume.npz',
)
CACHE_PATH = WORK / 'dat_parkinsons' / 'work' / 'invariant3d_bilateral_f16.npy'
PARENT_SCRIPT = WORK / 'parkinson_finish_fast.py'
Q_NAME = 'R_q90'
Q_T = 2.02439
Q_D0 = 0.30
Q_D1 = -0.10
PRIOR_REFERENCE = 3


def sigmoid_np(z):
    z = np.asarray(z, dtype=np.float64)
    out = np.empty_like(z)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def logit_np(p):
    p = np.clip(np.asarray(p, dtype=np.float64), 1e-6, 1.0 - 1e-6)
    return np.log(p / (1.0 - p))


def g2_baseline(q, g1):
    delta = np.where(np.asarray(q) >= Q_T, Q_D1, Q_D0)
    return sigmoid_np(logit_np(g1) + delta)


def load_parent_context():
    if not PARENT_SCRIPT.exists():
        raise FileNotFoundError(
            f'{PARENT_SCRIPT} not found; this experiment deliberately reuses the exact G1+G2 parent runtime'
        )
    namespace = {'__name__': '_parkinson_finish_fast_context_'}
    source = PARENT_SCRIPT.read_text()
    exec(compile(source.split('def main():')[0], str(PARENT_SCRIPT), 'exec'), namespace)
    if 'load_frozen_baseline' not in namespace or 'load_exact_candidate_field' not in namespace:
        raise RuntimeError('parkinson_finish_fast.py does not expose the expected frozen baseline loaders')
    y, env, canonical, g1 = namespace['load_frozen_baseline']()
    feature_matrix, feature_names = namespace['load_exact_candidate_field']()
    if Q_NAME not in feature_names:
        raise RuntimeError(f'{Q_NAME} missing from frozen candidate field')
    q = np.asarray(feature_matrix[:, feature_names.index(Q_NAME)], dtype=np.float64)
    base = g2_baseline(q, np.asarray(g1, dtype=np.float64))
    y = np.asarray(y, dtype=np.int64)
    env = np.asarray(env, dtype=np.int64)
    if len(y) != len(base) or len(env) != len(y):
        raise RuntimeError('frozen parent row mismatch')
    unique_env = tuple(int(e) for e in np.unique(env))
    if unique_env != tuple(range(10)):
        raise RuntimeError(f'expected natural environments 0..9, got {unique_env}')
    return y, env, base


def load_volume(n_rows):
    path = next((p for p in VOLUME_CANDIDATES if p.exists()), None)
    if path is None:
        raise FileNotFoundError('real64_volume.npz not found in expected workspace locations')
    data = np.load(path)
    key = 'V' if 'V' in data.files else data.files[0]
    volume = np.asarray(data[key])
    if volume.ndim != 4 or len(volume) != n_rows:
        raise RuntimeError(f'invalid volume shape {volume.shape}; expected ({n_rows}, D, H, W)')
    if volume.shape[1:] != (64, 64, 64):
        raise RuntimeError(f'expected 64x64x64 volumes, got {volume.shape[1:]}')
    if not np.isfinite(volume).all():
        raise RuntimeError('non-finite values in real64 volume')
    print('VOLUME', path, key, volume.shape, volume.dtype, flush=True)
    return volume


def build_or_load_inputs(volume, rebuild=False):
    expected = (len(volume), 8, 16, 32, 32)
    if CACHE_PATH.exists() and not rebuild:
        cached = np.load(CACHE_PATH, mmap_mode='r')
        if cached.shape == expected and cached.dtype == np.float16:
            print('INPUT_CACHE', CACHE_PATH, cached.shape, cached.dtype, flush=True)
            return cached
        print('INPUT_CACHE_REBUILD', cached.shape, cached.dtype, 'expected', expected, flush=True)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = np.lib.format.open_memmap(CACHE_PATH, mode='w+', dtype=np.float16, shape=expected)
    for i in range(len(volume)):
        x, r = robust_views(volume[i])
        channels = bilateral_channels(x, r)
        out[i] = downsample_mean3d(channels, factor=2).astype(np.float16)
        if (i + 1) % 100 == 0 or i + 1 == len(volume):
            print('PREPROCESS', i + 1, '/', len(volume), flush=True)
    out.flush()
    del out
    cached = np.load(CACHE_PATH, mmap_mode='r')
    print('INPUT_CACHE_BUILT', CACHE_PATH, cached.shape, cached.dtype, flush=True)
    return cached


def set_seed(seed, torch):
    random.seed(seed)
    np.random.seed(seed & 0xFFFFFFFF)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_model(torch, nn, F_torch):
    class BilateralInvariant3D(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Conv3d(8, 32, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(8, 32),
                nn.SiLU(),
                nn.Conv3d(32, 64, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(8, 64),
                nn.SiLU(),
                nn.Conv3d(64, 96, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(12, 96),
                nn.SiLU(),
                nn.Conv3d(96, 128, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(16, 128),
                nn.SiLU(),
                nn.AdaptiveAvgPool3d(1),
            )
            self.project = nn.Linear(128, 64)
            self.head = nn.Linear(64, 1)

        def forward(self, x):
            h = self.encoder(x).flatten(1)
            h = F_torch.silu(self.project(h))
            z = F_torch.normalize(h, dim=1, eps=1e-6)
            score = self.head(h).squeeze(1)
            return score, z

    return BilateralInvariant3D()


def augment_3d(x, torch, F_torch):
    b = x.shape[0]
    device = x.device
    dtype = x.dtype
    angle = np.deg2rad(6.0)
    a = (torch.rand((b, 3), device=device, dtype=dtype) * 2.0 - 1.0) * angle
    ax, ay, az = a[:, 0], a[:, 1], a[:, 2]
    cx, sx = torch.cos(ax), torch.sin(ax)
    cy, sy = torch.cos(ay), torch.sin(ay)
    cz, sz = torch.cos(az), torch.sin(az)
    one = torch.ones_like(cx)
    zero = torch.zeros_like(cx)
    rx = torch.stack([one, zero, zero, zero, cx, -sx, zero, sx, cx], dim=1).reshape(b, 3, 3)
    ry = torch.stack([cy, zero, sy, zero, one, zero, -sy, zero, cy], dim=1).reshape(b, 3, 3)
    rz = torch.stack([cz, -sz, zero, sz, cz, zero, zero, zero, one], dim=1).reshape(b, 3, 3)
    rot = torch.bmm(rz, torch.bmm(ry, rx))
    theta = torch.zeros((b, 3, 4), device=device, dtype=dtype)
    theta[:, :, :3] = rot
    theta[:, :, 3] = (torch.rand((b, 3), device=device, dtype=dtype) * 2.0 - 1.0) * 0.08
    grid = F_torch.affine_grid(theta, x.shape, align_corners=False)
    out = F_torch.grid_sample(x, grid, mode='bilinear', padding_mode='zeros', align_corners=False)
    gamma = 0.9 + 0.2 * torch.rand((b, 1, 1, 1, 1), device=device, dtype=dtype)
    scale = 0.9 + 0.2 * torch.rand((b, 1, 1, 1, 1), device=device, dtype=dtype)
    out = torch.clamp(out, 0.0, 1.0)
    out = torch.pow(out + 1e-6, gamma) * scale
    out = out + 0.01 * torch.randn_like(out)
    return torch.clamp(out, 0.0, 1.0)


def numpy_logistic_loss(y, logits):
    y = np.asarray(y, dtype=np.float64)
    z = np.asarray(logits, dtype=np.float64)
    return np.logaddexp(0.0, z) - y * z


def predict_logits(model, inputs, indices, base_logits, device, batch_size, torch):
    model.eval()
    result = np.empty(len(indices), dtype=np.float64)
    with torch.inference_mode():
        for start in range(0, len(indices), batch_size):
            batch_idx = np.asarray(indices[start:start + batch_size], dtype=np.int64)
            xb = torch.as_tensor(np.asarray(inputs[batch_idx], dtype=np.float32), device=device)
            score, _ = model(xb)
            result[start:start + len(batch_idx)] = (
                torch.as_tensor(base_logits[batch_idx], device=device, dtype=score.dtype) + score
            ).detach().cpu().numpy()
    return result


def train_arm(
    inputs,
    y,
    env,
    base_logits,
    train_envs,
    *,
    invariant,
    epochs,
    batch_size,
    lr,
    consistency_weight,
    dro_eta,
    seed,
    device,
    torch,
    nn,
    F_torch,
):
    set_seed(seed, torch)
    model = build_model(torch, nn, F_torch).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    train_envs = tuple(int(e) for e in train_envs)
    train_idx = np.flatnonzero(np.isin(env, train_envs)).astype(np.int64)
    env_to_local = {e: j for j, e in enumerate(train_envs)}
    local = np.array([env_to_local[int(env[i])] for i in train_idx], dtype=np.int64)
    counts = np.bincount(local, minlength=len(train_envs)).astype(np.float64)
    q = np.ones(len(train_envs), dtype=np.float64) / len(train_envs)
    rng = np.random.default_rng(seed)

    for epoch in range(epochs):
        model.train()
        order = rng.permutation(len(train_idx))
        running_task = 0.0
        running_cons = 0.0
        seen = 0
        for start in range(0, len(order), batch_size):
            pos = order[start:start + batch_size]
            idx = train_idx[pos]
            xb = torch.as_tensor(np.asarray(inputs[idx], dtype=np.float32), device=device)
            yb = torch.as_tensor(y[idx], device=device, dtype=torch.float32)
            bb = torch.as_tensor(base_logits[idx], device=device, dtype=torch.float32)
            optimizer.zero_grad(set_to_none=True)

            if invariant:
                x1 = augment_3d(xb, torch, F_torch)
                x2 = augment_3d(xb, torch, F_torch)
                s1, z1 = model(x1)
                s2, z2 = model(x2)
                loss1 = F_torch.binary_cross_entropy_with_logits(bb + s1, yb, reduction='none')
                loss2 = F_torch.binary_cross_entropy_with_logits(bb + s2, yb, reduction='none')
                task_vec = 0.5 * (loss1 + loss2)
                local_batch = local[pos]
                sample_w = q[local_batch] / np.maximum(counts[local_batch], 1.0)
                sample_w = sample_w / max(float(sample_w.mean()), 1e-12)
                wt = torch.as_tensor(sample_w, device=device, dtype=task_vec.dtype)
                task = (task_vec * wt).sum() / wt.sum()
                consistency = (1.0 - (z1 * z2).sum(dim=1)).mean()
                loss = task + consistency_weight * consistency
            else:
                score, _ = model(xb)
                task = F_torch.binary_cross_entropy_with_logits(bb + score, yb)
                consistency = torch.zeros((), device=device)
                loss = task

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            running_task += float(task.detach()) * len(idx)
            running_cons += float(consistency.detach()) * len(idx)
            seen += len(idx)

        if invariant:
            clean_logits = predict_logits(model, inputs, train_idx, base_logits, device, batch_size, torch)
            per_env_loss = np.array([
                numpy_logistic_loss(y[train_idx[local == j]], clean_logits[local == j]).mean()
                for j in range(len(train_envs))
            ])
            q = group_dro_weights(q, per_env_loss, eta=dro_eta)
        if epoch == 0 or epoch + 1 == epochs:
            q_text = [round(float(v), 4) for v in q] if invariant else None
            print(
                'TRAIN', 'INVARIANT' if invariant else 'ERM',
                'EPOCH', epoch + 1, '/', epochs,
                'TASK', round(running_task / max(seen, 1), 6),
                'CONS', round(running_cons / max(seen, 1), 6),
                'DRO', q_text,
                flush=True,
            )
    return model


def safe_auc(y, p, roc_auc_score):
    y = np.asarray(y, dtype=np.int64)
    if np.unique(y).size < 2:
        return 0.5
    return float(roc_auc_score(y, p))


def evaluate_environment(y, env, base, model_logits, indices, target_env, log_loss, roc_auc_score):
    idx = np.asarray(indices, dtype=np.int64)
    take = idx[env[idx] == target_env]
    positions = np.flatnonzero(env[idx] == target_env)
    pred = sigmoid_np(model_logits[positions])
    base_p = base[take]
    yy = y[take]
    ll_gain = float(log_loss(yy, base_p) - log_loss(yy, pred))
    auc_gain = safe_auc(yy, pred, roc_auc_score) - safe_auc(yy, base_p, roc_auc_score)
    return ll_gain, auc_gain


def joint_pass(ll, auc):
    return bool(np.min(ll) > 0.0 and np.min(auc) > 0.0)


def parse_pair(text):
    a, b = (int(x.strip()) for x in text.split(',', 1))
    if not (0 <= a < b <= 9):
        raise argparse.ArgumentTypeError('pair must be a,b with 0 <= a < b <= 9')
    return a, b


def main():
    parser = argparse.ArgumentParser(description='Learn a nuisance-invariant bilateral 3D residual on top of frozen G1+G2.')
    parser.add_argument('--epochs', type=int, default=6)
    parser.add_argument('--batch-size', type=int, default=16)
    parser.add_argument('--lr', type=float, default=8e-4)
    parser.add_argument('--consistency', type=float, default=0.25)
    parser.add_argument('--dro-eta', type=float, default=0.5)
    parser.add_argument('--seed', type=int, default=20260916)
    parser.add_argument('--max-pairs', type=int, default=0, help='0 means all 45 sealed pairs')
    parser.add_argument('--only-pair', type=parse_pair, default=None)
    parser.add_argument('--rebuild-cache', action='store_true')
    parser.add_argument('--device', default='auto')
    args = parser.parse_args()

    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F_torch
    except Exception as exc:
        raise RuntimeError('PyTorch is required for parkinson-invariant-3d-v1') from exc
    from sklearn.metrics import log_loss, roc_auc_score

    if args.epochs < 1 or args.batch_size < 1:
        raise ValueError('epochs and batch-size must be positive')
    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)

    print('REALITYGRAPH / PARKINSON INVARIANT 3D V1')
    print('------------------------------------------')
    print('Parent fixed: exact G1 L_elong_q95 + G2 R_q90')
    print('Input: real 64^3 uptake volume -> scale-invariant X/R views')
    print('Bilateral channels: L, mirror(R), mean, absdiff for X and R')
    print('Learned arm: compact 3D CNN + paired-view consistency + natural-environment group DRO')
    print('Ablation: same compact 3D CNN trained by clean ERM only')
    print('Future labels never train, tune, early-stop, or choose an arm')
    print('DEVICE', device, 'CUDA', torch.cuda.is_available())
    print('EPOCHS', args.epochs, 'BATCH', args.batch_size, 'LR', args.lr, 'CONSISTENCY', args.consistency, 'DRO_ETA', args.dro_eta)
    print()

    y, env, base = load_parent_context()
    base_logits = logit_np(base)
    print('ROWS', len(y), 'ENVS', {int(e): int(np.sum(env == e)) for e in range(10)})
    print('PARENT LL', round(float(log_loss(y, base)), 5), 'AUC', round(float(roc_auc_score(y, base)), 5))
    volume = load_volume(len(y))
    inputs = build_or_load_inputs(volume, rebuild=args.rebuild_cache)
    del volume

    pairs = list(combinations(range(10), 2))
    if args.only_pair is not None:
        pairs = [args.only_pair]
    elif args.max_pairs > 0:
        pairs = pairs[:args.max_pairs]

    inv_passes = 0
    erm_passes = 0
    causal_passes = 0
    inv_logit_sum = np.zeros(len(y), dtype=np.float64)
    erm_logit_sum = np.zeros(len(y), dtype=np.float64)
    prediction_count = np.zeros(len(y), dtype=np.int64)

    for pair_index, (a, b) in enumerate(pairs, 1):
        discovery = tuple(e for e in range(10) if e not in (a, b))
        future_idx = np.flatnonzero(np.isin(env, (a, b))).astype(np.int64)
        print()
        print('=== PAIR', f'{a},{b}', f'({pair_index}/{len(pairs)})', 'DISCOVERY', discovery, '===', flush=True)
        pair_seed = args.seed + 1009 * a + 9176 * b

        inv_model = train_arm(
            inputs, y, env, base_logits, discovery,
            invariant=True, epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
            consistency_weight=args.consistency, dro_eta=args.dro_eta, seed=pair_seed,
            device=device, torch=torch, nn=nn, F_torch=F_torch,
        )
        inv_logits = predict_logits(inv_model, inputs, future_idx, base_logits, device, args.batch_size, torch)
        del inv_model
        if device.type == 'cuda':
            torch.cuda.empty_cache()

        erm_model = train_arm(
            inputs, y, env, base_logits, discovery,
            invariant=False, epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
            consistency_weight=0.0, dro_eta=0.0, seed=pair_seed,
            device=device, torch=torch, nn=nn, F_torch=F_torch,
        )
        erm_logits = predict_logits(erm_model, inputs, future_idx, base_logits, device, args.batch_size, torch)
        del erm_model
        if device.type == 'cuda':
            torch.cuda.empty_cache()

        inv_ll, inv_auc, erm_ll, erm_auc = [], [], [], []
        for e in (a, b):
            llg, aucg = evaluate_environment(y, env, base, inv_logits, future_idx, e, log_loss, roc_auc_score)
            inv_ll.append(llg); inv_auc.append(aucg)
            llg, aucg = evaluate_environment(y, env, base, erm_logits, future_idx, e, log_loss, roc_auc_score)
            erm_ll.append(llg); erm_auc.append(aucg)

        inv_pass = joint_pass(inv_ll, inv_auc)
        erm_pass = joint_pass(erm_ll, erm_auc)
        causal = bool(inv_pass and not erm_pass)
        inv_passes += int(inv_pass)
        erm_passes += int(erm_pass)
        causal_passes += int(causal)
        inv_logit_sum[future_idx] += inv_logits
        erm_logit_sum[future_idx] += erm_logits
        prediction_count[future_idx] += 1

        print(
            'PAIR', f'{a},{b}',
            'INVARIANT_LL', [round(float(x), 5) for x in inv_ll],
            'INVARIANT_AUC', [round(float(x), 5) for x in inv_auc],
            'ERM_LL', [round(float(x), 5) for x in erm_ll],
            'ERM_AUC', [round(float(x), 5) for x in erm_auc],
            'INVARIANT_PASS', int(inv_pass),
            'ERM_PASS', int(erm_pass),
            'INVARIANCE_CAUSAL', int(causal),
            flush=True,
        )

    covered = prediction_count > 0
    print()
    print('=== OUTER TWO-ENVIRONMENT FUTURES ===')
    print('PAIRS_EVALUATED', len(pairs), '/45')
    print('INVARIANT_JOINT_PASS_BOTH', inv_passes, '/', len(pairs))
    print('ERM_JOINT_PASS_BOTH', erm_passes, '/', len(pairs))
    print('INVARIANCE_CAUSAL_PASSES', causal_passes, '/', len(pairs))
    print('PRIOR_HANDCRAFTED_REFERENCE', PRIOR_REFERENCE, '/45')

    inv_ooe = sigmoid_np(inv_logit_sum[covered] / prediction_count[covered])
    erm_ooe = sigmoid_np(erm_logit_sum[covered] / prediction_count[covered])
    yy = y[covered]
    bb = base[covered]
    inv_ll = float(log_loss(yy, inv_ooe))
    inv_auc = safe_auc(yy, inv_ooe, roc_auc_score)
    erm_ll = float(log_loss(yy, erm_ooe))
    erm_auc = safe_auc(yy, erm_ooe, roc_auc_score)
    base_ll = float(log_loss(yy, bb))
    base_auc = safe_auc(yy, bb, roc_auc_score)

    print()
    print('=== OUT-OF-ENVIRONMENT ENSEMBLE AUDIT ===')
    print('COVERED', int(covered.sum()), '/', len(y), 'PREDICTIONS_PER_ROW_MINMAX', int(prediction_count[covered].min()), int(prediction_count[covered].max()))
    print('PARENT_OOE LL', round(base_ll, 5), 'AUC', round(base_auc, 5))
    print('INVARIANT_3D_OOE LL', round(inv_ll, 5), 'AUC', round(inv_auc, 5), 'LL_GAIN', round(base_ll - inv_ll, 5), 'AUC_GAIN', round(inv_auc - base_auc, 5))
    print('ERM_3D_OOE LL', round(erm_ll, 5), 'AUC', round(erm_auc, 5), 'LL_GAIN', round(base_ll - erm_ll, 5), 'AUC_GAIN', round(erm_auc - base_auc, 5))

    print()
    print('=== VERDICT ===')
    full = len(pairs) == 45 and bool(np.all(prediction_count == 9))
    unlocked = (
        full
        and inv_passes > PRIOR_REFERENCE
        and inv_passes > erm_passes
        and causal_passes > 0
        and inv_ll < base_ll
        and inv_auc > base_auc
    )
    if unlocked:
        print('PASS_NUISANCE_INVARIANT_3D_UNLOCKS_TRANSFER')
    elif inv_passes > 0 or (inv_ll < base_ll and inv_auc > base_auc):
        print('PARTIAL_INVARIANT_3D_SIGNAL__NOT_YET_TRANSFER_CERTIFIED')
    else:
        print('INVARIANT_3D_DOES_NOT_UNLOCK_TRANSFER')
    print('INVARIANT_JOINT_PASSES', inv_passes, '/', len(pairs))
    print('ERM_JOINT_PASSES', erm_passes, '/', len(pairs))
    print('INVARIANCE_CAUSAL_PASSES', causal_passes, '/', len(pairs))
    print('INVARIANT_OOE_LL', round(inv_ll, 5))
    print('INVARIANT_OOE_AUC', round(inv_auc, 5))


if __name__ == '__main__':
    main()
