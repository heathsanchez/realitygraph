from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

from realitygraph.pixel_consequence_atlas import (
    build_2d_candidate_families,
    coarse_volume_family,
    environment_residual_correlations,
    gather_selected_matrix,
    select_magnitude_candidates,
    select_stable_candidates,
)
from realitygraph.ridge_decoder import (
    fit_ridge_residual_decoder,
    joint_evidence_invoke,
    predict_ridge_residual_decoder,
)

# Freeze the verified present. The sweep changes only which local intensity
# coordinates are exposed to the already-bounded residual decoder.
exec(open("/workspace/parkinson_finish_fast.py").read().split("def main():")[0])

WORK = Path("/workspace")
MAP_CANDIDATES = (
    WORK / "pp_signal_maps.npz",
    WORK / "dat_parkinsons" / "work" / "pp_signal_maps.npz",
)
VOLUME_CANDIDATES = (
    WORK / "real64_volume.npz",
    WORK / "dat_parkinsons" / "work" / "real64_volume.npz",
)

Q_NAME = "R_q90"
Q_T = 2.02439
Q_D0 = 0.30
Q_D1 = -0.10
L2 = 1.0
K = 12
MAX_PER_FAMILY = 2
MIN_MEAN_LL = 1e-4
MIN_MEAN_AUC = 0.0
PRIOR_REFERENCE = 3


def g2_baseline(q, g1):
    delta = np.where(q >= Q_T, Q_D1, Q_D0)
    return sigmoid(logit(g1) + delta)


def load_maps():
    path = next((p for p in MAP_CANDIDATES if p.exists()), None)
    if path is None:
        raise FileNotFoundError("pp_signal_maps.npz not found")
    data = np.load(path)
    maps = {"R": np.asarray(data["R"], np.float64), "X": np.asarray(data["X"], np.float64)}
    if maps["R"].shape != maps["X"].shape or maps["R"].ndim != 3:
        raise RuntimeError("invalid R/X map shape")
    if not all(np.isfinite(v).all() for v in maps.values()):
        raise RuntimeError("non-finite maps")
    print("MAPS", path, maps["R"].shape)
    return maps


def load_optional_volume(n_rows):
    path = next((p for p in VOLUME_CANDIDATES if p.exists()), None)
    if path is None:
        print("VOLUME none -- 2D pixel sweep only")
        return None
    data = np.load(path)
    key = "V" if "V" in data.files else data.files[0]
    v = np.asarray(data[key])
    if v.ndim != 4 or len(v) != n_rows or not np.isfinite(v).all():
        print("VOLUME ignored invalid", path, v.shape)
        return None
    print("VOLUME", path, key, v.shape)
    return v


def safe_auc(y, p):
    y = np.asarray(y, int)
    if np.unique(y).size < 2:
        return 0.5
    return roc_auc_score(y, p)


def evaluate_envs(y, env, base, pred, envs):
    ll, auc = [], []
    for e in envs:
        mask = env == e
        ll.append(log_loss(y[mask], base[mask]) - log_loss(y[mask], pred[mask]))
        auc.append(safe_auc(y[mask], pred[mask]) - safe_auc(y[mask], base[mask]))
    return np.asarray(ll, float), np.asarray(auc, float)


def q90_normalize_rows(images):
    out = np.empty_like(np.asarray(images, float))
    for i, row in enumerate(np.asarray(images, float)):
        p = row[row > 0]
        q = float(np.quantile(p, 0.90)) if p.size else 1.0
        out[i] = row / max(q, 1e-9)
    return out


def make_variation_atlas(maps, volume):
    """Unlabelled visual atlas. Selection cannot see y or environment."""
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print("VARIATION_ATLAS skipped", type(exc).__name__, str(exc)[:120])
        return

    r = q90_normalize_rows(maps["R"])
    half = r.shape[1] // 2
    left = r[:, :half]
    right = np.flip(r[:, half:], axis=1)
    descriptors = np.column_stack([
        r.mean((1, 2)), r.std((1, 2)), r.max((1, 2)),
        left.mean((1, 2)), right.mean((1, 2)),
        np.abs(left - right).mean((1, 2)),
        left[:, :, : left.shape[2] // 2].mean((1, 2)),
        left[:, :, left.shape[2] // 2 :].mean((1, 2)),
        right[:, :, : right.shape[2] // 2].mean((1, 2)),
        right[:, :, right.shape[2] // 2 :].mean((1, 2)),
    ])
    mu = descriptors.mean(0)
    sd = np.where(descriptors.std(0) > 1e-9, descriptors.std(0), 1.0)
    z = (descriptors - mu) / sd

    # Deterministic farthest-point sampling of appearance variation only.
    chosen = [int(np.argmax(np.sum(z * z, axis=1)))]
    while len(chosen) < min(12, len(r)):
        d = np.min(
            np.stack([np.sum((z - z[j]) ** 2, axis=1) for j in chosen], axis=1),
            axis=1,
        )
        d[chosen] = -1.0
        chosen.append(int(np.argmax(d)))

    if volume is not None:
        v = q90_normalize_rows(volume[chosen])
        mip = v.max(axis=1)
    else:
        mip = None

    fig, axes = plt.subplots(3, 8 if mip is not None else 4, figsize=(16, 7))
    axes = np.asarray(axes).reshape(3, -1)
    for k, idx in enumerate(chosen):
        row, col = divmod(k, 4)
        ax = axes[row, col * (2 if mip is not None else 1)]
        ax.imshow(r[idx], cmap="gray", vmin=0.0, vmax=1.5)
        ax.set_title(f"row {idx}")
        ax.axis("off")
        if mip is not None:
            ax2 = axes[row, col * 2 + 1]
            ax2.imshow(mip[k], cmap="gray", vmin=0.0, vmax=1.5)
            ax2.set_title("3D MIP")
            ax2.axis("off")
    fig.suptitle("Unlabelled scan variation atlas: q90-normalized numeric uptake")
    fig.tight_layout()
    path = WORK / "pixel_variation_atlas_v1.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print("VARIATION_ATLAS", path, "ROWS", chosen)


def build_families(maps, volume):
    print("BUILDING_2D_PIXEL_FAMILIES", flush=True)
    families = {
        name: np.asarray(value, np.float32)
        for name, value in build_2d_candidate_families(maps, box_sizes=(1, 5)).items()
    }
    if volume is not None:
        print("BUILDING_COARSE_3D_FAMILY", flush=True)
        families["V16_q90"] = np.asarray(coarse_volume_family(volume, bins=16), np.float32)
    print("FAMILIES", len(families), "CANDIDATES", sum(v[0].size for v in families.values()))
    for name in sorted(families):
        print("FAMILY", name, families[name].shape)
    return families


def precompute_associations(families, residual, env):
    associations = {}
    for i, (name, field) in enumerate(sorted(families.items())):
        associations[name] = environment_residual_correlations(
            field, residual, env, tuple(range(10))
        )
        print("ASSOCIATIONS", i + 1, "/", len(families), name, associations[name].shape, flush=True)
    return associations


def fit_selected(families, selected, y, env, base, train_envs):
    matrix = gather_selected_matrix(families, selected)
    model = fit_ridge_residual_decoder(matrix, y, base, env, tuple(train_envs), l2=L2)
    pred = predict_ridge_residual_decoder(model, matrix, base)
    return model, pred


def select_stable(associations, train_envs):
    return select_stable_candidates(
        associations,
        train_env_indices=tuple(train_envs),
        k=K,
        max_per_family=MAX_PER_FAMILY,
    )


def select_magnitude(associations, train_envs):
    return select_magnitude_candidates(
        associations,
        train_env_indices=tuple(train_envs),
        k=K,
        max_per_family=MAX_PER_FAMILY,
    )


def inner_verify(families, associations, y, env, base, discovery):
    ll_gains, auc_gains = [], []
    selected_sets = []
    for held in discovery:
        train = tuple(e for e in discovery if e != held)
        selected = select_stable(associations, train)
        _, pred = fit_selected(families, selected, y, env, base, train)
        ll, auc = evaluate_envs(y, env, base, pred, (held,))
        ll_gains.append(float(ll[0]))
        auc_gains.append(float(auc[0]))
        selected_sets.append(tuple(selected))
    return {
        "joint_positive": int(sum(a > 0 and b > 0 for a, b in zip(ll_gains, auc_gains))),
        "ll_mean": float(np.mean(ll_gains)),
        "ll_worst": float(np.min(ll_gains)),
        "auc_mean": float(np.mean(auc_gains)),
        "auc_worst": float(np.min(auc_gains)),
        "ll_gains": ll_gains,
        "auc_gains": auc_gains,
        "selected_sets": selected_sets,
    }


def joint_pass(ll, auc):
    return bool(np.min(ll) > 0.0 and np.min(auc) > 0.0)


def outer_pair(a, b, families, associations, y, env, base):
    discovery = tuple(e for e in range(10) if e not in (a, b))
    inner = inner_verify(families, associations, y, env, base, discovery)
    invoke = joint_evidence_invoke(
        inner["ll_gains"], inner["auc_gains"],
        min_mean_ll=MIN_MEAN_LL, min_mean_auc=MIN_MEAN_AUC,
    )
    universal = bool(
        all(x > 0 for x in inner["ll_gains"]) and all(x > 0 for x in inner["auc_gains"])
        and inner["ll_mean"] > MIN_MEAN_LL and inner["auc_mean"] > MIN_MEAN_AUC
    )
    reason = "promoted" if universal else "mixed" if invoke else "refuse"
    stable_selected = select_stable(associations, discovery)
    magnitude_selected = select_magnitude(associations, discovery)

    if not invoke:
        return {
            "pair": (a, b), "invoked": False, "reason": reason, "inner": inner,
            "stable_selected": stable_selected, "magnitude_selected": magnitude_selected,
            "stable_ll": [0.0, 0.0], "stable_auc": [0.0, 0.0],
            "magnitude_ll": [0.0, 0.0], "magnitude_auc": [0.0, 0.0],
            "stable_pass": False, "magnitude_pass": False, "recurrence_causal": False,
            "alpha": 0.0, "beta_norm": 0.0,
        }

    model, pred = fit_selected(families, stable_selected, y, env, base, discovery)
    _, mag_pred = fit_selected(families, magnitude_selected, y, env, base, discovery)
    stable_ll, stable_auc = evaluate_envs(y, env, base, pred, (a, b))
    magnitude_ll, magnitude_auc = evaluate_envs(y, env, base, mag_pred, (a, b))
    stable_pass = joint_pass(stable_ll, stable_auc)
    magnitude_pass = joint_pass(magnitude_ll, magnitude_auc)
    return {
        "pair": (a, b), "invoked": True, "reason": reason, "inner": inner,
        "stable_selected": stable_selected, "magnitude_selected": magnitude_selected,
        "stable_ll": [float(x) for x in stable_ll], "stable_auc": [float(x) for x in stable_auc],
        "magnitude_ll": [float(x) for x in magnitude_ll], "magnitude_auc": [float(x) for x in magnitude_auc],
        "stable_pass": stable_pass, "magnitude_pass": magnitude_pass,
        "recurrence_causal": bool(stable_pass and not magnitude_pass),
        "alpha": float(model.alpha), "beta_norm": float(np.linalg.norm(model.beta)),
    }


def candidate_description(families, family, index):
    shape = families[family].shape[1:]
    coord = tuple(int(x) for x in np.unravel_index(int(index), shape))
    return f"{family}@{coord}"


def print_top_stable(families, associations):
    selected = select_stable(associations, tuple(range(10)))
    print()
    print("=== TOP ALL-ENV STABLE CONSEQUENCES ===")
    for rank, (family, index) in enumerate(selected, 1):
        values = associations[family][:, index]
        mean = float(values.mean())
        sign = 1.0 if mean >= 0 else -1.0
        oriented = sign * values
        print(
            "TOP", rank, candidate_description(families, family, index),
            "SIGN", "+" if sign > 0 else "-",
            "CONSISTENCY", int(np.sum(oriented > 0)), "/10",
            "WORST", round(float(oriented.min()), 5),
            "MEAN", round(float(oriented.mean()), 5),
            "ENV", [round(float(x), 4) for x in values],
        )
    return selected


def make_signal_atlas(families, associations, selected):
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print("SIGNAL_ATLAS skipped", type(exc).__name__, str(exc)[:120])
        return
    unique = []
    for family, index in selected:
        if family not in unique:
            unique.append(family)
        if len(unique) >= 6:
            break
    fig, axes = plt.subplots(len(unique), 2, figsize=(10, 3 * max(1, len(unique))))
    axes = np.asarray(axes).reshape(len(unique), 2)
    for row, family in enumerate(unique):
        shape = families[family].shape[1:]
        a = associations[family]
        mean = a.mean(axis=0).reshape(shape)
        consistency = np.maximum(np.sum(a > 0, axis=0), np.sum(a < 0, axis=0)).reshape(shape)
        if len(shape) == 3:
            mean_view = mean[np.argmax(np.max(np.abs(mean), axis=(1, 2)))]
            cons_view = consistency.max(axis=0)
        else:
            mean_view, cons_view = mean, consistency
        axes[row, 0].imshow(mean_view, cmap="coolwarm")
        axes[row, 0].set_title(f"{family}: mean residual corr")
        axes[row, 1].imshow(cons_view, cmap="viridis", vmin=5, vmax=10)
        axes[row, 1].set_title("sign recurrence /10")
        axes[row, 0].axis("off")
        axes[row, 1].axis("off")
    fig.tight_layout()
    path = WORK / "pixel_signal_atlas_v1.png"
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print("SIGNAL_ATLAS", path)


def all_env_audit(name, selected, families, y, env, base):
    model, pred = fit_selected(families, selected, y, env, base, tuple(range(10)))
    ll_gains, auc_gains = evaluate_envs(y, env, base, pred, tuple(range(10)))
    result = {
        "ll": float(log_loss(y, pred)), "auc": float(roc_auc_score(y, pred)),
        "ll_gain": float(log_loss(y, base) - log_loss(y, pred)),
        "auc_gain": float(roc_auc_score(y, pred) - roc_auc_score(y, base)),
        "ll_worst": float(ll_gains.min()), "auc_worst": float(auc_gains.min()),
        "ll_pos": int(np.sum(ll_gains > 0)), "auc_pos": int(np.sum(auc_gains > 0)),
        "joint_pos": int(np.sum((ll_gains > 0) & (auc_gains > 0))),
        "alpha": float(model.alpha), "beta_norm": float(np.linalg.norm(model.beta)),
    }
    print(
        name,
        "LL", round(result["ll"], 5), "AUC", round(result["auc"], 5),
        "LL_GAIN", round(result["ll_gain"], 5), "AUC_GAIN", round(result["auc_gain"], 5),
        "LL_WORST", round(result["ll_worst"], 5), "LL_POS", result["ll_pos"], "/10",
        "AUC_WORST", round(result["auc_worst"], 5), "AUC_POS", result["auc_pos"], "/10",
        "JOINT_POS", result["joint_pos"], "/10",
        "ALPHA", round(result["alpha"], 3), "BETA_NORM", round(result["beta_norm"], 3),
    )
    return result


def main():
    print("REALITYGRAPH / PARKINSON PIXEL CONSEQUENCE ATLAS V1")
    print("-------------------------------------------------")
    print("Present fixed: G1 L_elong_q95 + G2 R_q90")
    print("Numeric uptake sweep: not rendered RGB colour")
    print("2D sources: R/X q90-normalized, left/right/sum/diff/absdiff, scales 1 and 5")
    print("Optional 3D source: q90-normalized 16x16x16 coarse uptake field")
    print("Selector: residual sign recurrence across discovery environments")
    print("Ablation: same candidates/decoder budget, recurrence deleted; magnitude only")
    print("K", K, "MAX_PER_FAMILY", MAX_PER_FAMILY, "L2", L2)
    print("Promotion: lower LL AND higher AUC in both sealed futures")
    print("Future labels never choose candidate pixels or decoder")
    print()

    y, env, canonical, g1 = load_frozen_baseline()
    feature_matrix, feature_names = load_exact_candidate_field()
    q = feature_matrix[:, feature_names.index(Q_NAME)]
    base = g2_baseline(q, g1)
    maps = load_maps()
    if len(maps["R"]) != len(y):
        raise RuntimeError("map/base row mismatch")
    volume = load_optional_volume(len(y))

    make_variation_atlas(maps, volume)
    families = build_families(maps, volume)
    residual = np.asarray(y, float) - np.asarray(base, float)
    associations = precompute_associations(families, residual, env)
    all_selected = print_top_stable(families, associations)
    make_signal_atlas(families, associations, all_selected)

    print()
    print("PARENT LL", round(log_loss(y, base), 5), "AUC", round(roc_auc_score(y, base), 5))
    events = []
    for a, b in combinations(range(10), 2):
        event = outer_pair(a, b, families, associations, y, env, base)
        events.append(event)
        fam_counts = Counter(x[0] for x in event["stable_selected"])
        print(
            "PAIR", f"{a},{b}", "INVOKE", int(event["invoked"]), "REASON", event["reason"],
            "INNER_JOINT", event["inner"]["joint_positive"], "/8",
            "INNER_LL", round(event["inner"]["ll_mean"], 5),
            "INNER_AUC", round(event["inner"]["auc_mean"], 5),
            "STABLE_LL", [round(x, 5) for x in event["stable_ll"]],
            "STABLE_AUC", [round(x, 5) for x in event["stable_auc"]],
            "MAG_LL", [round(x, 5) for x in event["magnitude_ll"]],
            "MAG_AUC", [round(x, 5) for x in event["magnitude_auc"]],
            "STABLE_PASS", int(event["stable_pass"]),
            "MAG_PASS", int(event["magnitude_pass"]),
            "RECURRENCE_CAUSAL", int(event["recurrence_causal"]),
            "FAMILIES", dict(fam_counts),
            "ALPHA", round(event["alpha"], 3), "BETA_NORM", round(event["beta_norm"], 3),
            flush=True,
        )

    invoked = [e for e in events if e["invoked"]]
    stable_passed = [e for e in invoked if e["stable_pass"]]
    magnitude_passed = [e for e in invoked if e["magnitude_pass"]]
    causal = [e for e in invoked if e["recurrence_causal"]]

    print()
    print("=== OUTER TWO-ENVIRONMENT FUTURES ===")
    print("INVOKED", len(invoked), "/45")
    print("STABLE_JOINT_PASS_BOTH", len(stable_passed), "/45")
    print("MAGNITUDE_ABLATION_PASS_BOTH", len(magnitude_passed), "/45")
    print("RECURRENCE_CAUSAL_PASSES", len(causal), "/45")
    print("PRIOR_REFERENCE", PRIOR_REFERENCE, "/45")
    print("DELTA_VS_PRIOR_REFERENCE", len(stable_passed) - PRIOR_REFERENCE)

    for e in range(10):
        ll_values, auc_values = [], []
        for event in invoked:
            a, b = event["pair"]
            if e not in (a, b):
                continue
            j = 0 if a == e else 1
            ll_values.append(event["stable_ll"][j])
            auc_values.append(event["stable_auc"][j])
        print(
            "ENV", e, "INVOKED", len(ll_values), "/9",
            "JOINT_POS", sum(x > 0 and z > 0 for x, z in zip(ll_values, auc_values)),
            "LL_MEAN", round(float(np.mean(ll_values)), 5) if ll_values else None,
            "LL_WORST", round(float(np.min(ll_values)), 5) if ll_values else None,
            "AUC_MEAN", round(float(np.mean(auc_values)), 5) if auc_values else None,
            "AUC_WORST", round(float(np.min(auc_values)), 5) if auc_values else None,
        )

    print()
    print("=== ALL-ENV AUDIT ===")
    stable_selected = select_stable(associations, tuple(range(10)))
    magnitude_selected = select_magnitude(associations, tuple(range(10)))
    stable_audit = all_env_audit("STABLE_PIXEL_BASIS", stable_selected, families, y, env, base)
    magnitude_audit = all_env_audit("MAGNITUDE_ONLY_ABLATION", magnitude_selected, families, y, env, base)

    print()
    print("=== VERDICT ===")
    if len(stable_passed) > PRIOR_REFERENCE and len(stable_passed) > len(magnitude_passed):
        print("PASS_PIXEL_CONSEQUENCE_BASIS_UNLOCKS_TRANSFER")
    elif len(stable_passed) > 0:
        print("PARTIAL_PIXEL_CONSEQUENCE_SIGNAL_NOT_TRANSFER_SAFE")
    else:
        print("PIXEL_SWEEP_DOES_NOT_UNLOCK_TRANSFER")
        print("NEXT__LEARN_NUISANCE_INVARIANT_3D_REPRESENTATION")
    print("STABLE_JOINT_PASSES", len(stable_passed), "/45")
    print("MAGNITUDE_JOINT_PASSES", len(magnitude_passed), "/45")
    print("RECURRENCE_CAUSAL_PASSES", len(causal), "/45")
    print("STABLE_ALL_ENV_LL", round(stable_audit["ll"], 5))
    print("STABLE_ALL_ENV_AUC", round(stable_audit["auc"], 5))
    print("MAG_ALL_ENV_LL", round(magnitude_audit["ll"], 5))
    print("MAG_ALL_ENV_AUC", round(magnitude_audit["auc"], 5))


if __name__ == "__main__":
    main()
