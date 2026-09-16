from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

from realitygraph.capacity_control_sweep import CONTROL_FAMILIES, LOW_RANK_SIZES
from realitygraph.spatial_capacity_audit import environment_label_folds
from parkinson_invariant_3d_v1 import (
    build_or_load_inputs,
    load_parent_context,
    load_volume,
    logit_np,
    set_seed,
    sigmoid_np,
)

WORK = Path('/workspace')
OUT_PATH = WORK / 'parkinson_capacity_control_sweep_v1.npz'
KNOWN_HANDCRAFTED_LL = 0.34236
KNOWN_HANDCRAFTED_AUC = 0.92572


def config_list(families):
    configs = []
    for family in families:
        if family == 'lowrank':
            configs.extend((family, int(k)) for k in LOW_RANK_SIZES)
        else:
            configs.append((family, None))
    return configs


def config_name(config):
    family, value = config
    return f'lowrank_k{value}' if family == 'lowrank' else family


def build_model(config, torch, nn, F_torch):
    family, value = config

    class SharedEncoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(
                nn.Conv3d(8, 24, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(6, 24), nn.SiLU(),
                nn.Conv3d(24, 48, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(8, 48), nn.SiLU(),
                nn.Conv3d(48, 64, 3, stride=1, padding=1, bias=False),
                nn.GroupNorm(8, 64), nn.SiLU(),
            )

        def forward(self, x):
            return self.net(x)

    class LowRankSpatial(nn.Module):
        def __init__(self, rank):
            super().__init__()
            self.encoder = SharedEncoder()
            self.rank = int(rank)
            self.channel = nn.Parameter(torch.empty(self.rank, 64))
            self.spatial = nn.Parameter(torch.empty(self.rank, 4 * 8 * 8))
            self.bias = nn.Parameter(torch.zeros(()))
            nn.init.normal_(self.channel, std=1.0 / math.sqrt(64.0))
            nn.init.normal_(self.spatial, std=1.0 / math.sqrt(256.0 * self.rank))

        def forward(self, x):
            h = self.encoder(x).flatten(2)
            return torch.einsum('bcn,rc,rn->b', h, self.channel, self.spatial) + self.bias

        def capacity_penalty(self):
            return torch.zeros((), device=self.channel.device)

    class RegionalPool(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = SharedEncoder()
            self.head = nn.Sequential(
                nn.Linear(64 * 8, 128), nn.SiLU(), nn.Dropout(0.10), nn.Linear(128, 1)
            )

        def forward(self, x):
            h = self.encoder(x)
            pooled = F_torch.adaptive_avg_pool3d(h, (2, 2, 2)).flatten(1)
            return self.head(pooled).squeeze(1)

        def capacity_penalty(self):
            return torch.zeros((), device=next(self.parameters()).device)

    class BoundedAttention(nn.Module):
        def __init__(self, heads=8):
            super().__init__()
            self.encoder = SharedEncoder()
            self.heads = heads
            self.attn = nn.Conv3d(64, heads, 1)
            self.value = nn.Conv3d(64, heads, 1)
            self.position = nn.Parameter(torch.zeros(1, heads, 4, 8, 8))
            self.out = nn.Linear(heads, 1)

        def forward(self, x):
            h = self.encoder(x)
            logits = self.attn(h) + self.position
            weights = torch.softmax(logits.flatten(2), dim=2).reshape_as(logits)
            summaries = (weights * self.value(h)).flatten(2).sum(2)
            return self.out(summaries).squeeze(1)

        def capacity_penalty(self):
            p = self.position
            tv = (
                (p[:, :, 1:] - p[:, :, :-1]).abs().mean()
                + (p[:, :, :, 1:] - p[:, :, :, :-1]).abs().mean()
                + (p[:, :, :, :, 1:] - p[:, :, :, :, :-1]).abs().mean()
            )
            return tv

    class SpatialPyramid(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = SharedEncoder()
            self.reduce = nn.Sequential(nn.Conv3d(64, 8, 1, bias=False), nn.SiLU())
            dims = 8 * (1 + 8 + 64)
            self.head = nn.Sequential(
                nn.Linear(dims, 96), nn.SiLU(), nn.Dropout(0.10), nn.Linear(96, 1)
            )

        def forward(self, x):
            h = self.reduce(self.encoder(x))
            parts = [
                F_torch.adaptive_avg_pool3d(h, (1, 1, 1)).flatten(1),
                F_torch.adaptive_avg_pool3d(h, (2, 2, 2)).flatten(1),
                F_torch.adaptive_avg_pool3d(h, (4, 4, 4)).flatten(1),
            ]
            return self.head(torch.cat(parts, dim=1)).squeeze(1)

        def capacity_penalty(self):
            return torch.zeros((), device=next(self.parameters()).device)

    class SparseTVSpatial(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = SharedEncoder()
            self.value = nn.Conv3d(64, 1, 1, bias=False)
            self.spatial = nn.Parameter(torch.zeros(1, 1, 4, 8, 8))
            self.bias = nn.Parameter(torch.zeros(()))
            nn.init.normal_(self.spatial, std=0.02)

        def forward(self, x):
            v = self.value(self.encoder(x))
            return (v * self.spatial).flatten(1).sum(1) + self.bias

        def capacity_penalty(self):
            w = self.spatial
            l1 = w.abs().mean()
            tv = (
                (w[:, :, 1:] - w[:, :, :-1]).abs().mean()
                + (w[:, :, :, 1:] - w[:, :, :, :-1]).abs().mean()
                + (w[:, :, :, :, 1:] - w[:, :, :, :, :-1]).abs().mean()
            )
            return l1, tv

    if family == 'lowrank':
        return LowRankSpatial(value)
    if family == 'regional':
        return RegionalPool()
    if family == 'attention':
        return BoundedAttention(heads=8)
    if family == 'pyramid':
        return SpatialPyramid()
    if family == 'sparse_tv':
        return SparseTVSpatial()
    raise ValueError(f'unknown family {family}')


def regularization(model, family, attention_tv, sparse_l1, sparse_tv, torch):
    if family == 'attention':
        return attention_tv * model.capacity_penalty()
    if family == 'sparse_tv':
        l1, tv = model.capacity_penalty()
        return sparse_l1 * l1 + sparse_tv * tv
    return torch.zeros((), device=next(model.parameters()).device)


def predict_logits(model, inputs, indices, base_logits, device, batch_size, torch):
    model.eval()
    out = np.empty(len(indices), dtype=np.float64)
    with torch.inference_mode():
        for start in range(0, len(indices), batch_size):
            idx = np.asarray(indices[start:start + batch_size], dtype=np.int64)
            xb = torch.as_tensor(np.asarray(inputs[idx], dtype=np.float32), device=device)
            residual = model(xb)
            logits = torch.as_tensor(base_logits[idx], device=device, dtype=residual.dtype) + residual
            out[start:start + len(idx)] = logits.detach().cpu().numpy()
    return out


def train_model(
    config, inputs, y, base_logits, train_idx, *, epochs, batch_size, lr, seed,
    attention_tv, sparse_l1, sparse_tv, device, torch, nn, F_torch,
):
    set_seed(seed, torch)
    model = build_model(config, torch, nn, F_torch).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    rng = np.random.default_rng(seed)
    train_idx = np.asarray(train_idx, dtype=np.int64)
    family = config[0]
    name = config_name(config).upper()
    for epoch in range(epochs):
        model.train()
        order = rng.permutation(len(train_idx))
        running_task = 0.0
        running_reg = 0.0
        seen = 0
        for start in range(0, len(order), batch_size):
            idx = train_idx[order[start:start + batch_size]]
            xb = torch.as_tensor(np.asarray(inputs[idx], dtype=np.float32), device=device)
            yb = torch.as_tensor(y[idx], device=device, dtype=torch.float32)
            bb = torch.as_tensor(base_logits[idx], device=device, dtype=torch.float32)
            optimizer.zero_grad(set_to_none=True)
            residual = model(xb)
            task = F_torch.binary_cross_entropy_with_logits(bb + residual, yb)
            reg = regularization(model, family, attention_tv, sparse_l1, sparse_tv, torch)
            loss = task + reg
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            running_task += float(task.detach()) * len(idx)
            running_reg += float(reg.detach()) * len(idx)
            seen += len(idx)
        if epoch == 0 or epoch + 1 == epochs:
            print(
                'TRAIN', name, 'EPOCH', epoch + 1, '/', epochs,
                'TASK', round(running_task / max(seen, 1), 6),
                'REG', round(running_reg / max(seen, 1), 6),
                flush=True,
            )
    return model


def metrics(y, base, logits, log_loss, roc_auc_score):
    p = sigmoid_np(logits)
    return {
        'll': float(log_loss(y, p)),
        'auc': float(roc_auc_score(y, p)),
        'll_gain': float(log_loss(y, base) - log_loss(y, p)),
        'auc_gain': float(roc_auc_score(y, p) - roc_auc_score(y, base)),
    }


def score_summary(m):
    return min(m['ll_gain'], m['auc_gain'])


def main():
    parser = argparse.ArgumentParser(description='Compare five ways to control learned 3D capacity without destroying spatial information.')
    parser.add_argument('--epochs', type=int, default=12)
    parser.add_argument('--batch-size', type=int, default=24)
    parser.add_argument('--lr', type=float, default=6e-4)
    parser.add_argument('--folds', type=int, default=5)
    parser.add_argument('--seed', type=int, default=20260916)
    parser.add_argument('--device', default='auto')
    parser.add_argument('--families', default=','.join(CONTROL_FAMILIES))
    parser.add_argument('--attention-tv', type=float, default=1e-4)
    parser.add_argument('--sparse-l1', type=float, default=2e-3)
    parser.add_argument('--sparse-tv', type=float, default=1e-3)
    args = parser.parse_args()

    import torch
    import torch.nn as nn
    import torch.nn.functional as F_torch
    from sklearn.metrics import log_loss, roc_auc_score

    device = torch.device('cuda' if args.device == 'auto' and torch.cuda.is_available() else args.device if args.device != 'auto' else 'cpu')
    families = tuple(x.strip() for x in args.families.split(',') if x.strip())
    unknown = [x for x in families if x not in CONTROL_FAMILIES]
    if unknown:
        raise ValueError(f'unknown families {unknown}; expected {CONTROL_FAMILIES}')
    configs = config_list(families)

    print('REALITYGRAPH / PARKINSON CAPACITY CONTROL SWEEP V1')
    print('----------------------------------------------------')
    print('Question: which capacity control preserves spatial signal and improves OOF LL + AUC?')
    print('Parent fixed: exact G1 + G2 coefficient one')
    print('Shared input: bilateral cache 8 x 16 x 32 x 32')
    print('Shared encoder output: 64 x 4 x 8 x 8')
    print('Families:', families)
    print('Low-rank k:', LOW_RANK_SIZES if 'lowrank' in families else None)
    print('Known handcrafted reference LL', KNOWN_HANDCRAFTED_LL, 'AUC', KNOWN_HANDCRAFTED_AUC)
    print('DEVICE', device, 'EPOCHS', args.epochs, 'FOLDS', args.folds, 'CONFIGS', len(configs))
    print()

    y, env, base = load_parent_context()
    base_logits = logit_np(base)
    volume = load_volume(len(y))
    inputs = build_or_load_inputs(volume, rebuild=False)
    del volume
    folds = environment_label_folds(env, y, n_splits=args.folds, seed=args.seed)
    all_idx = np.arange(len(y), dtype=np.int64)
    parent_ll = float(log_loss(y, base))
    parent_auc = float(roc_auc_score(y, base))
    print('ROWS', len(y), 'PARENT_LL', round(parent_ll, 5), 'PARENT_AUC', round(parent_auc, 5))
    print('FOLD_COUNTS', [int(np.sum(folds == f)) for f in range(args.folds)])

    outputs = {'folds': folds, 'y': y, 'env': env, 'base': base}
    summaries = {}

    for config_index, config in enumerate(configs):
        name = config_name(config)
        print()
        print('=== CONTROL', name.upper(), '===')
        oof_logits = np.empty(len(y), dtype=np.float64)
        for fold in range(args.folds):
            tr = all_idx[folds != fold]
            va = all_idx[folds == fold]
            model = train_model(
                config, inputs, y, base_logits, tr,
                epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
                seed=args.seed + config_index * 1000 + fold,
                attention_tv=args.attention_tv, sparse_l1=args.sparse_l1, sparse_tv=args.sparse_tv,
                device=device, torch=torch, nn=nn, F_torch=F_torch,
            )
            oof_logits[va] = predict_logits(model, inputs, va, base_logits, device, args.batch_size, torch)
            fm = metrics(y[va], base[va], oof_logits[va], log_loss, roc_auc_score)
            print(
                'FOLD', fold, 'N', len(va),
                'LL', round(fm['ll'], 5), 'AUC', round(fm['auc'], 5),
                'LL_GAIN', round(fm['ll_gain'], 5), 'AUC_GAIN', round(fm['auc_gain'], 5),
                flush=True,
            )
            del model
            if device.type == 'cuda':
                torch.cuda.empty_cache()

        oof_m = metrics(y, base, oof_logits, log_loss, roc_auc_score)
        print(
            'OOF', name.upper(), 'LL', round(oof_m['ll'], 5), 'AUC', round(oof_m['auc'], 5),
            'LL_GAIN', round(oof_m['ll_gain'], 5), 'AUC_GAIN', round(oof_m['auc_gain'], 5),
        )

        full_model = train_model(
            config, inputs, y, base_logits, all_idx,
            epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
            seed=args.seed + config_index * 1000 + 999,
            attention_tv=args.attention_tv, sparse_l1=args.sparse_l1, sparse_tv=args.sparse_tv,
            device=device, torch=torch, nn=nn, F_torch=F_torch,
        )
        full_logits = predict_logits(full_model, inputs, all_idx, base_logits, device, args.batch_size, torch)
        full_m = metrics(y, base, full_logits, log_loss, roc_auc_score)
        print(
            'FULL_FIT', name.upper(), 'LL', round(full_m['ll'], 5), 'AUC', round(full_m['auc'], 5),
            'LL_GAIN', round(full_m['ll_gain'], 5), 'AUC_GAIN', round(full_m['auc_gain'], 5),
        )
        outputs[f'{name}_oof_logits'] = oof_logits
        outputs[f'{name}_full_logits'] = full_logits
        summaries[name] = (config, oof_m, full_m)
        del full_model
        if device.type == 'cuda':
            torch.cuda.empty_cache()

    np.savez_compressed(OUT_PATH, **outputs)

    print()
    print('=== FAMILY SUMMARY ===')
    family_winners = {}
    for family in families:
        names = [n for n, (cfg, _, _) in summaries.items() if cfg[0] == family]
        winner = max(names, key=lambda n: score_summary(summaries[n][1]))
        family_winners[family] = winner
        _, oof_m, full_m = summaries[winner]
        print(
            'FAMILY', family.upper(), 'BEST', winner.upper(),
            'OOF_LL', round(oof_m['ll'], 5), 'OOF_AUC', round(oof_m['auc'], 5),
            'OOF_LL_GAIN', round(oof_m['ll_gain'], 5), 'OOF_AUC_GAIN', round(oof_m['auc_gain'], 5),
            'FULL_LL', round(full_m['ll'], 5), 'FULL_AUC', round(full_m['auc'], 5),
            'BEATS_PARENT_BOTH', int(oof_m['ll_gain'] > 0 and oof_m['auc_gain'] > 0),
        )

    best_name = max(summaries, key=lambda n: score_summary(summaries[n][1]))
    best_cfg, best_oof, best_full = summaries[best_name]
    print()
    print('=== VERDICT ===')
    print('BEST_CONTROL', best_name.upper(), 'FAMILY', best_cfg[0].upper())
    print('BEST_OOF LL', round(best_oof['ll'], 5), 'AUC', round(best_oof['auc'], 5), 'LL_GAIN', round(best_oof['ll_gain'], 5), 'AUC_GAIN', round(best_oof['auc_gain'], 5))
    print('BEST_FULL LL', round(best_full['ll'], 5), 'AUC', round(best_full['auc'], 5))
    print('PREVIOUS_FLAT_OOF LL 0.37126 AUC 0.91173')
    if best_oof['ll'] < 0.37126 and best_oof['auc'] > 0.91173:
        print('VERDICT CAPACITY_CONTROL_BEATS_FLAT_ON_BOTH__TAKE_TO_SEALED_TRANSFER')
    elif best_oof['ll_gain'] > 0 and best_oof['auc_gain'] > 0:
        print('VERDICT CAPACITY_CONTROL_ADDS_GENERALIZING_SIGNAL__REFINE_WINNER')
    else:
        print('VERDICT NONE_OF_FIVE_CONTROLS_IMPROVE_BOTH__CHANGE_REPRESENTATION_OR_SUPERVISION')
    print('OUTPUT', OUT_PATH)


if __name__ == '__main__':
    main()
