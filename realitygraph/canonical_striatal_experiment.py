from __future__ import annotations

import numpy as np


def _joint_pair_pass(ll_gains, auc_gains) -> bool:
    ll = np.asarray(ll_gains, dtype=np.float64)
    auc = np.asarray(auc_gains, dtype=np.float64)
    if ll.shape != (2,) or auc.shape != (2,):
        raise ValueError("future consequence requires exactly two sealed environments")
    if not np.isfinite(ll).all() or not np.isfinite(auc).all():
        raise ValueError("future gains must be finite")
    return bool(np.all(ll > 0.0) and np.all(auc > 0.0))


def future_consequence(aligned_ll, aligned_auc, ablation_ll, ablation_auc):
    """Classify the two-future protected consequence and exact alignment ablation.

    Alignment is causal only when the aligned representation improves both LL and
    AUC in both sealed futures and removing alignment destroys that same protected
    consequence. Future outcomes are classification evidence only; they never
    participate in fitting or invocation.
    """
    aligned_pass = _joint_pair_pass(aligned_ll, aligned_auc)
    ablation_pass = _joint_pair_pass(ablation_ll, ablation_auc)
    return {
        "aligned_pass": aligned_pass,
        "ablation_pass": ablation_pass,
        "alignment_causal": bool(aligned_pass and not ablation_pass),
    }
