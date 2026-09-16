from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

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
OUT_PATH = WORK / 'parkinson_spatial_capacity_audit_v1.npz'
KNOWN_HANDCRAFTED_LL = 0.34236
KNOWN_HANDCRAFTED_AUC = 0.92572


def build_model(kind, torch, nn, F_torch):
    class GapModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Conv3d(8, 32, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(8, 32), nn.SiLU(),
                nn.Conv3d(32, 64, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(8, 64), nn.SiLU(),
                nn.Conv3d(64, 96, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(12, 96), nn.SiLU(),
                nn.Conv3d(96, 128, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(16, 128), nn.SiLU(),
                nn.AdaptiveAvgPool3d(1),
            )
            self.head = nn.Linear(128, 1)

        def forward(self, x):
            return self.head(self.encoder(x).flatten(1)).squeeze(1)

    class SpatialAttentionModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Conv3d(8, 32, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(8, 32), nn.SiLU(),
                nn.Conv3d(32, 64, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(8, 64), nn.SiLU(),
                nn.Conv3d(64, 96, 3, stride=1, padding=1, bias=False),
                nn.GroupNorm(12, 96), nn.SiLU(),
            )
            self.attn = nn.Conv3d(96, 1, 1)
            self.value = nn.Conv3d(96, 1, 1)
            self.position = nn.Parameter(torch.zeros(1, 1, 4, 8, 8))
            self.bias = nn.Parameter(torch.zeros(()))

        def forward(self, x):
            h = self.encoder(x)
            logits = self.attn(h) + self.position
            weights = torch.softmax(logits.flatten(2), dim=2).reshape_as(logits)
            return (weights * self.value(h)).flatten(1).sum(1) + self.bias

    class FlatSpatialModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Conv3d(8, 24, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(6, 24), nn.SiLU(),
                nn.Conv3d(24, 48, 3, stride=2, padding=1, bias=False),
                nn.GroupNorm(8, 48), nn.SiLU(),
                nn.Conv3d(48, 64, 3, stride=1, padding=1, bias=False),
                nn.GroupNorm(8, 64), nn.SiLU(),
            )
            self.head = nn.Sequential(
                nn.Flatten(),
                nn.Linear(64 * 4 * 8 * 8, 128),
                nn.SiLU(),
                nn.Dropout(0.10),
                nn.Linear(128, 1),
            )

        def forward(self, x):
            return self.head(self.encoder(x)).squeeze(1)

    if kind == 'gap':
        return GapModel()
    if kind == 'attention':
        return SpatialAttentionModel()
    if kind == 'flat':
        return FlatSpatialModel()
    raise ValueError(f'unknown model kind {kind}')


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


def train_model(kind, inputs, y, base_logits, train_idx, *, epochs, batch_size, lr, seed, device, torch, nn, F_torch):
    set_seed(seed, torch)
    model = build_model(kind, torch, nn, F_torch).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    rng = np.random.default_rng(seed)
    train_idx = np.asarray(train_idx, dtype=np.int64)
    for epoch in range(epochs):
        model.train()
        order = rng.permutation(len(train_idx))
        running = 0.0
        seen = 0
        for start in range(0, len(order), batch_size):
            idx = train_idx[order[start:start + batch_size]]
            xb = torch.as_tensor(np.asarray(inputs[idx], dtype=np.float32), device=device)
            yb = torch.as_tensor(y[idx], device=device, dtype=torch.float32)
            bb = torch.as_tensor(base_logits[idx], device=device, dtype=torch.float32)
            optimizer.zero_grad(set_to_none=True)
            residual = model(xb)
            loss = F_torch.binary_cross_entropy_with_logits(bb + residual, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            optimizer.step()
            running += float(loss.detach()) * len(idx)
            seen += len(idx)
        if epoch == 0 or epoch + 1 == epochs:
            print('TRAIN', kind.upper(), 'EPOCH', epoch + 1, '/', epochs, 'LOSS', round(running / max(seen, 1), 6), flush=True)
    return model


def metrics(y, base, logits, log_loss, roc_auc_score):
    p = sigmoid_np(logits)
    return {
        'll': float(log_loss(y, p)),
        'auc': float(roc_auc_score(y, p)),
        'll_gain': float(log_loss(y, base) - log_loss(y, p)),
        'auc_gain': float(roc_auc_score(y, p) - roc_auc_score(y, base)),
    }


def main():
    parser = argparse.ArgumentParser(description='Audit whether preserving learned spatial structure can recover residual Parkinson signal before asking for cross-environment transfer.')
    parser.add_argument('--epochs', type=int, default=12)
    parser.add_argument('--batch-size', type=int, default=24)
    parser.add_argument('--lr', type=float, default=6e-4)
    parser.add_argument('--folds', type=int, default=5)
    parser.add_argument('--seed', type=int, default=20260916)
    parser.add_argument('--device', default='auto')
    parser.add_argument('--models', default='gap,attention,flat')
    args = parser.parse_args()

    import torch
    import torch.nn as nn
    import torch.nn.functional as F_torch
    from sklearn.metrics import log_loss, roc_auc_score

    device = torch.device('cuda' if args.device == 'auto' and torch.cuda.is_available() else args.device if args.device != 'auto' else 'cpu')
    kinds = tuple(x.strip() for x in args.models.split(',') if x.strip())
    for kind in kinds:
        if kind not in {'gap', 'attention', 'flat'}:
            raise ValueError(f'unsupported model {kind}')

    print('REALITYGRAPH / PARKINSON SPATIAL CAPACITY AUDIT V1')
    print('---------------------------------------------------')
    print('Question: can learned spatial heads recover known residual signal before transfer is imposed?')
    print('Parent fixed: exact G1 + G2 coefficient one')
    print('Inputs fixed: invariant3d bilateral cache 8 x 16 x 32 x 32')
    print('Arms: GAP collapse vs position-aware spatial attention vs explicit flattened spatial head')
    print('Evaluation: environment+label balanced OOF plus full-fit capacity audit')
    print('KNOWN_HANDCRAFTED_REFERENCE LL', KNOWN_HANDCRAFTED_LL, 'AUC', KNOWN_HANDCRAFTED_AUC)
    print('DEVICE', device, 'MODELS', kinds, 'EPOCHS', args.epochs, 'FOLDS', args.folds)
    print()

    y, env, base = load_parent_context()
    base_logits = logit_np(base)
    volume = load_volume(len(y))
    inputs = build_or_load_inputs(volume, rebuild=False)
    del volume
    folds = environment_label_folds(env, y, n_splits=args.folds, seed=args.seed)
    print('ROWS', len(y), 'PARENT_LL', round(float(log_loss(y, base)), 5), 'PARENT_AUC', round(float(roc_auc_score(y, base)), 5))
    print('FOLD_COUNTS', [int(np.sum(folds == f)) for f in range(args.folds)])

    all_idx = np.arange(len(y), dtype=np.int64)
    outputs = {'folds': folds, 'y': y, 'env': env, 'base': base}
    summaries = {}

    for model_index, kind in enumerate(kinds):
        print()
        print('=== MODEL', kind.upper(), '===')
        oof_logits = np.empty(len(y), dtype=np.float64)
        for fold in range(args.folds):
            tr = all_idx[folds != fold]
            va = all_idx[folds == fold]
            model = train_model(
                kind, inputs, y, base_logits, tr,
                epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
                seed=args.seed + model_index * 1000 + fold,
                device=device, torch=torch, nn=nn, F_torch=F_torch,
            )
            oof_logits[va] = predict_logits(model, inputs, va, base_logits, device, args.batch_size, torch)
            fold_m = metrics(y[va], base[va], oof_logits[va], log_loss, roc_auc_score)
            print('FOLD', fold, 'N', len(va), 'LL', round(fold_m['ll'], 5), 'AUC', round(fold_m['auc'], 5), 'LL_GAIN', round(fold_m['ll_gain'], 5), 'AUC_GAIN', round(fold_m['auc_gain'], 5), flush=True)
            del model
            if device.type == 'cuda':
                torch.cuda.empty_cache()

        oof_m = metrics(y, base, oof_logits, log_loss, roc_auc_score)
        print('OOF', kind.upper(), 'LL', round(oof_m['ll'], 5), 'AUC', round(oof_m['auc'], 5), 'LL_GAIN', round(oof_m['ll_gain'], 5), 'AUC_GAIN', round(oof_m['auc_gain'], 5))

        full_model = train_model(
            kind, inputs, y, base_logits, all_idx,
            epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
            seed=args.seed + model_index * 1000 + 999,
            device=device, torch=torch, nn=nn, F_torch=F_torch,
        )
        full_logits = predict_logits(full_model, inputs, all_idx, base_logits, device, args.batch_size, torch)
        full_m = metrics(y, base, full_logits, log_loss, roc_auc_score)
        print('FULL_FIT', kind.upper(), 'LL', round(full_m['ll'], 5), 'AUC', round(full_m['auc'], 5), 'LL_GAIN', round(full_m['ll_gain'], 5), 'AUC_GAIN', round(full_m['auc_gain'], 5))
        outputs[f'{kind}_oof_logits'] = oof_logits
        outputs[f'{kind}_full_logits'] = full_logits
        summaries[kind] = (oof_m, full_m)
        del full_model
        if device.type == 'cuda':
            torch.cuda.empty_cache()

    np.savez_compressed(OUT_PATH, **outputs)
    print()
    print('=== CAPACITY VERDICT ===')
    for kind in kinds:
        oof_m, full_m = summaries[kind]
        reaches_known = full_m['auc'] >= KNOWN_HANDCRAFTED_AUC and full_m['ll'] <= KNOWN_HANDCRAFTED_LL
        oof_better = oof_m['auc_gain'] > 0 and oof_m['ll_gain'] > 0
        print(kind.upper(), 'REACHES_KNOWN_FULL_FIT', int(reaches_known), 'OOF_BEATS_PARENT_BOTH', int(oof_better))
    best_full_kind = max(kinds, key=lambda k: summaries[k][1]['auc'])
    best_oof_kind = max(kinds, key=lambda k: summaries[k][0]['auc'])
    best_full = summaries[best_full_kind][1]
    best_oof = summaries[best_oof_kind][0]
    print('BEST_FULL', best_full_kind.upper(), 'LL', round(best_full['ll'], 5), 'AUC', round(best_full['auc'], 5))
    print('BEST_OOF', best_oof_kind.upper(), 'LL', round(best_oof['ll'], 5), 'AUC', round(best_oof['auc'], 5))
    if best_full['auc'] < KNOWN_HANDCRAFTED_AUC or best_full['ll'] > KNOWN_HANDCRAFTED_LL:
        print('VERDICT ARCHITECTURE_OR_DOWNSAMPLED_INPUT_CANNOT_RECOVER_KNOWN_SIGNAL')
    elif best_oof['auc_gain'] > 0 and best_oof['ll_gain'] > 0:
        print('VERDICT SPATIAL_CAPACITY_GENERALIZES_WITHIN_ENVIRONMENTS__RETURN_TO_TRANSFER')
    else:
        print('VERDICT SPATIAL_CAPACITY_EXISTS_BUT_GENERALIZATION_IS_THE_OBSTRUCTION')
    print('OUTPUT', OUT_PATH)


if __name__ == '__main__':
    main()
