from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from realitygraph.logloss_meta import apply_family


def load_meta_model(path):
    return json.loads(Path(path).read_text())


def apply_meta_prediction(parent_probability, anchor_probability, full_probability, meta_model):
    if isinstance(meta_model, (str, Path)):
        meta_model = load_meta_model(meta_model)
    family = str(meta_model['family'])
    params = dict(meta_model.get('params', {}))
    streams = {
        'parent': np.asarray([parent_probability], dtype=np.float64),
        'anchor': np.asarray([anchor_probability], dtype=np.float64),
        'full': np.asarray([full_probability], dtype=np.float64),
    }
    return float(apply_family(family, params, streams)[0])


def component_probabilities(nifti_path, canonical_probability, v5_model, *, already_parent=False):
    """Return frozen parent, anchor-only, and full V5 probabilities for one scan."""
    from parkinson_runtime_patch import (
        _logit,
        _sigmoid,
        load_model,
        parent_probability,
        runtime_signal_map,
    )
    from realitygraph.final_trajectory_model import apply_exported_residual
    from realitygraph.threshold_trajectory import dense_threshold_trajectory_features

    if isinstance(v5_model, (str, Path)):
        v5_model = load_model(v5_model)

    _, r = runtime_signal_map(nifti_path)
    parent = float(canonical_probability) if already_parent else parent_probability(canonical_probability, r)
    base_logit = _logit([parent])

    bank, names, _ = dense_threshold_trajectory_features(r[None, ...])
    index = {name: j for j, name in enumerate(names)}
    anchor_name = v5_model['anchor']['name']
    if anchor_name not in index:
        raise RuntimeError(f'anchor feature missing at runtime: {anchor_name}')
    anchor_values = bank[:, index[anchor_name]]

    residual_names = list(v5_model['residual']['names'])
    missing = [name for name in residual_names if name not in index]
    if missing:
        raise RuntimeError(f'residual feature(s) missing at runtime: {missing}')
    residual_values = (
        bank[:, [index[name] for name in residual_names]]
        if residual_names else np.empty((1, 0), dtype=np.float64)
    )

    anchor_model = dict(v5_model)
    anchor_model['residual'] = {
        'names': [], 'mean': [], 'scale': [], 'beta': [], 'shrinkage': 0.0,
    }
    anchor_logit = apply_exported_residual(base_logit, anchor_values, np.empty((1, 0)), anchor_model)
    full_logit = apply_exported_residual(base_logit, anchor_values, residual_values, v5_model)
    return parent, float(_sigmoid(anchor_logit)[0]), float(_sigmoid(full_logit)[0])


def patch_probability(nifti_path, canonical_probability, v5_model, meta_model, *, already_parent=False):
    parent, anchor, full = component_probabilities(
        nifti_path, canonical_probability, v5_model, already_parent=already_parent
    )
    return apply_meta_prediction(parent, anchor, full, meta_model)
