from __future__ import annotations

import numpy as np


def residual_gate(
    anchor_losses,
    residual_losses,
    *,
    min_wins=7,
    min_mean_gain=5e-4,
    max_worst_regret=2e-3,
):
    """Discovery-only gate for invoking a residual trajectory model.

    ``gain = anchor_loss - residual_loss`` so positive is better.  The residual is
    admitted only when it wins in enough discovery environments, has a positive
    mean gain above the declared margin, and has no single-environment regret
    worse than the declared bound.
    """
    a = np.asarray(anchor_losses, dtype=np.float64).reshape(-1)
    r = np.asarray(residual_losses, dtype=np.float64).reshape(-1)
    if len(a) != len(r) or len(a) == 0:
        raise ValueError('anchor/residual losses must have equal non-zero length')
    if not (np.isfinite(a).all() and np.isfinite(r).all()):
        raise ValueError('losses must be finite')
    min_wins = int(min_wins)
    if min_wins < 0 or min_wins > len(a):
        raise ValueError('min_wins out of range')
    if min_mean_gain < 0.0 or max_worst_regret < 0.0:
        raise ValueError('gain/regret thresholds must be non-negative')

    gain = a - r
    wins = int(np.sum(gain > 0.0))
    mean_gain = float(np.mean(gain))
    median_gain = float(np.median(gain))
    worst_gain = float(np.min(gain))
    invoke = bool(
        wins >= min_wins
        and mean_gain >= float(min_mean_gain)
        and worst_gain >= -float(max_worst_regret)
    )
    return {
        'invoke': invoke,
        'wins': wins,
        'mean_gain': mean_gain,
        'median_gain': median_gain,
        'worst_gain': worst_gain,
        'gains': gain,
    }
