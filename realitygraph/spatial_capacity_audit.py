from __future__ import annotations

import numpy as np


def environment_label_folds(env, y, n_splits=5, seed=0):
    env = np.asarray(env, dtype=np.int64)
    y = np.asarray(y, dtype=np.int64)
    if env.shape != y.shape:
        raise ValueError('env and y must have the same shape')
    if n_splits < 2:
        raise ValueError('n_splits must be at least 2')
    folds = np.empty(len(y), dtype=np.int64)
    rng = np.random.default_rng(seed)
    for e in np.unique(env):
        for label in np.unique(y):
            idx = np.flatnonzero((env == e) & (y == label))
            if not len(idx):
                continue
            idx = idx.copy()
            rng.shuffle(idx)
            folds[idx] = np.arange(len(idx), dtype=np.int64) % n_splits
    return folds
