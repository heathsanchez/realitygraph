from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def _as_finite_list(values, name):
    arr = np.asarray(values, dtype=np.float64).reshape(-1)
    if not np.isfinite(arr).all():
        raise ValueError(f"non-finite {name}")
    return [float(x) for x in arr]


def normalize_export_model(model):
    anchor = dict(model.get("anchor", {}))
    residual = dict(model.get("residual", {}))

    if not anchor.get("name"):
        raise ValueError("anchor name required")
    anchor_mean = _as_finite_list(anchor.get("mean", []), "anchor mean")
    anchor_scale = _as_finite_list(anchor.get("scale", []), "anchor scale")
    anchor_beta = _as_finite_list(anchor.get("beta", []), "anchor beta")
    if not (len(anchor_mean) == len(anchor_scale) == len(anchor_beta) == 1):
        raise ValueError("anchor parameters must be length 1")
    if anchor_scale[0] <= 0.0:
        raise ValueError("anchor scale must be positive")
    anchor_shrinkage = float(anchor.get("shrinkage", 0.0))
    if not np.isfinite(anchor_shrinkage):
        raise ValueError("non-finite anchor shrinkage")

    residual_names = [str(x) for x in residual.get("names", [])]
    residual_mean = _as_finite_list(residual.get("mean", []), "residual mean")
    residual_scale = _as_finite_list(residual.get("scale", []), "residual scale")
    residual_beta = _as_finite_list(residual.get("beta", []), "residual beta")
    if not (len(residual_names) == len(residual_mean) == len(residual_scale) == len(residual_beta)):
        raise ValueError("residual parameter length mismatch")
    if any(x <= 0.0 for x in residual_scale):
        raise ValueError("residual scales must be positive")
    residual_shrinkage = float(residual.get("shrinkage", 0.0))
    if not np.isfinite(residual_shrinkage):
        raise ValueError("non-finite residual shrinkage")

    out = {
        "version": str(model.get("version", "parkinson-threshold-trajectory-v3-final")),
        "anchor": {
            "name": str(anchor["name"]),
            "mean": anchor_mean,
            "scale": anchor_scale,
            "beta": anchor_beta,
            "shrinkage": anchor_shrinkage,
        },
        "residual": {
            "names": residual_names,
            "mean": residual_mean,
            "scale": residual_scale,
            "beta": residual_beta,
            "shrinkage": residual_shrinkage,
        },
    }
    for key in ("selection", "metrics", "parent"):
        if key in model:
            out[key] = model[key]
    return out


def export_model(model, path):
    out = normalize_export_model(model)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def apply_exported_residual(base_logits, anchor_values, residual_values, model):
    spec = normalize_export_model(model)
    base = np.asarray(base_logits, dtype=np.float64).reshape(-1)
    anchor = np.asarray(anchor_values, dtype=np.float64).reshape(-1)
    if len(anchor) != len(base):
        raise ValueError("anchor/base row mismatch")

    a = spec["anchor"]
    z = base + a["shrinkage"] * ((anchor - a["mean"][0]) / a["scale"][0]) * a["beta"][0]

    r = spec["residual"]
    X = np.asarray(residual_values, dtype=np.float64)
    if len(r["names"]) == 0:
        if X.size not in (0, len(base) * 0):
            X = X.reshape(len(base), -1)
            if X.shape[1] != 0:
                raise ValueError("residual values supplied for empty residual model")
        return z
    if X.ndim == 1:
        X = X[:, None]
    if X.shape != (len(base), len(r["names"])):
        raise ValueError("residual matrix shape mismatch")
    mean = np.asarray(r["mean"], dtype=np.float64)
    scale = np.asarray(r["scale"], dtype=np.float64)
    beta = np.asarray(r["beta"], dtype=np.float64)
    z = z + r["shrinkage"] * (((X - mean) / scale) @ beta)
    return z
