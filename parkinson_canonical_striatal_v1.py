from __future__ import annotations

from itertools import combinations
from pathlib import Path

import numpy as np

from realitygraph.canonical_striatal import (
    canonical_striatal_features,
    unaligned_striatal_features,
)
from realitygraph.canonical_striatal_experiment import future_consequence
from realitygraph.ridge_decoder import (
    fit_ridge_residual_decoder,
    joint_evidence_invoke,
    predict_ridge_residual_decoder,
)

# Freeze the verified present. This experiment changes representation coordinates
# only: G1+G2, decoder family, environment split, and promotion metrics are fixed.
exec(open("/workspace/parkinson_finish_fast.py").read().split("def main():")[0])

WORK = Path("/workspace")
MAP_CANDIDATES = (
    WORK / "pp_signal_maps.npz",
    WORK / "dat_parkinsons" / "work" / "pp_signal_maps.npz",
)

Q_NAME = "R_q90"
Q_T = 2.02439
Q_D0 = 0.30
Q_D1 = -0.10
L2 = 1.0
MIN_MEAN_LL = 1e-4
MIN_MEAN_AUC = 0.0
PRIOR_WEAK_REFERENCE = 3


def g2_baseline(q, g1):
    delta = np.where(q >= Q_T, Q_D1, Q_D0)
    return sigmoid(logit(g1) + delta)


def load_r_map():
    path = next((p for p in MAP_CANDIDATES if p.exists()), None)
    if path is None:
        raise FileNotFoundError("pp_signal_maps.npz not found")
    data = np.load(path)
    r = np.asarray(data["R"], np.float64)
    if r.ndim != 3 or not np.isfinite(r).all():
        raise RuntimeError(f"invalid R map {r.shape}")
    print("MAPS", path, r.shape)
    return r


def safe_auc(y, p):
    y = np.asarray(y, int)
    if np.unique(y).size < 2:
        return 0.5
    return roc_auc_score(y, p)


def evaluate_envs(y, env, base, pred, envs):
    ll = []
    auc = []
    for e in envs:
        mask = env == e
        ll.append(log_loss(y[mask], base[mask]) - log_loss(y[mask], pred[mask]))
        auc.append(safe_auc(y[mask], pred[mask]) - safe_auc(y[mask], base[mask]))
    return np.asarray(ll, float), np.asarray(auc, float)


def fit_predict(matrix, y, env, base, train_envs):
    model = fit_ridge_residual_decoder(
        matrix, y, base, env, tuple(train_envs), l2=L2
    )
    pred = predict_ridge_residual_decoder(model, matrix, base)
    return model, pred


def inner_verify(matrix, y, env, base, discovery):
    ll_gains = []
    auc_gains = []
    alphas = []
    beta_norms = []
    for held in discovery:
        train = tuple(e for e in discovery if e != held)
        model, pred = fit_predict(matrix, y, env, base, train)
        ll, auc = evaluate_envs(y, env, base, pred, (held,))
        ll_gains.append(float(ll[0]))
        auc_gains.append(float(auc[0]))
        alphas.append(float(model.alpha))
        beta_norms.append(float(np.linalg.norm(model.beta)))

    return {
        "joint_positive": int(sum(a > 0.0 and b > 0.0 for a, b in zip(ll_gains, auc_gains))),
        "ll_positive": int(sum(x > 0.0 for x in ll_gains)),
        "auc_positive": int(sum(x > 0.0 for x in auc_gains)),
        "ll_mean": float(np.mean(ll_gains)),
        "ll_worst": float(np.min(ll_gains)),
        "auc_mean": float(np.mean(auc_gains)),
        "auc_worst": float(np.min(auc_gains)),
        "alpha_median": float(np.median(alphas)),
        "beta_norm_median": float(np.median(beta_norms)),
        "ll_gains": ll_gains,
        "auc_gains": auc_gains,
    }


def outer_pair(a, b, aligned, ablation, y, env, base):
    discovery = tuple(e for e in range(10) if e not in (a, b))
    inner = inner_verify(aligned, y, env, base, discovery)

    invoke = joint_evidence_invoke(
        inner["ll_gains"],
        inner["auc_gains"],
        min_mean_ll=MIN_MEAN_LL,
        min_mean_auc=MIN_MEAN_AUC,
    )
    universal = bool(
        all(x > 0.0 for x in inner["ll_gains"])
        and all(x > 0.0 for x in inner["auc_gains"])
        and inner["ll_mean"] > MIN_MEAN_LL
        and inner["auc_mean"] > MIN_MEAN_AUC
    )
    reason = "promoted" if universal else "mixed" if invoke else "refuse"

    if not invoke:
        return {
            "pair": (a, b), "invoked": False, "reason": reason, "inner": inner,
            "aligned_ll": [0.0, 0.0], "aligned_auc": [0.0, 0.0],
            "ablation_ll": [0.0, 0.0], "ablation_auc": [0.0, 0.0],
            "aligned_pass": False, "ablation_pass": False,
            "alignment_causal": False, "alpha": 0.0, "beta_norm": 0.0,
        }

    model, aligned_pred = fit_predict(aligned, y, env, base, discovery)
    _, ablation_pred = fit_predict(ablation, y, env, base, discovery)

    aligned_ll, aligned_auc = evaluate_envs(y, env, base, aligned_pred, (a, b))
    ablation_ll, ablation_auc = evaluate_envs(y, env, base, ablation_pred, (a, b))
    consequence = future_consequence(aligned_ll, aligned_auc, ablation_ll, ablation_auc)

    return {
        "pair": (a, b), "invoked": True, "reason": reason, "inner": inner,
        "aligned_ll": [float(x) for x in aligned_ll],
        "aligned_auc": [float(x) for x in aligned_auc],
        "ablation_ll": [float(x) for x in ablation_ll],
        "ablation_auc": [float(x) for x in ablation_auc],
        **consequence,
        "alpha": float(model.alpha),
        "beta_norm": float(np.linalg.norm(model.beta)),
    }


def all_env_audit(name, matrix, y, env, base):
    model, pred = fit_predict(matrix, y, env, base, tuple(range(10)))
    ll_gains, auc_gains = evaluate_envs(y, env, base, pred, tuple(range(10)))
    result = {
        "name": name,
        "ll": float(log_loss(y, pred)),
        "auc": float(roc_auc_score(y, pred)),
        "ll_gain": float(log_loss(y, base) - log_loss(y, pred)),
        "auc_gain": float(roc_auc_score(y, pred) - roc_auc_score(y, base)),
        "ll_worst": float(ll_gains.min()),
        "ll_pos": int(np.sum(ll_gains > 0.0)),
        "auc_worst": float(auc_gains.min()),
        "auc_pos": int(np.sum(auc_gains > 0.0)),
        "joint_pos": int(np.sum((ll_gains > 0.0) & (auc_gains > 0.0))),
        "alpha": float(model.alpha),
        "beta_norm": float(np.linalg.norm(model.beta)),
    }
    print(
        name,
        "LL", round(result["ll"], 5),
        "AUC", round(result["auc"], 5),
        "LL_GAIN", round(result["ll_gain"], 5),
        "AUC_GAIN", round(result["auc_gain"], 5),
        "LL_WORST", round(result["ll_worst"], 5),
        "LL_POS", result["ll_pos"], "/10",
        "AUC_WORST", round(result["auc_worst"], 5),
        "AUC_POS", result["auc_pos"], "/10",
        "JOINT_POS", result["joint_pos"], "/10",
        "ALPHA", round(result["alpha"], 3),
        "BETA_NORM", round(result["beta_norm"], 3),
    )
    return result


def main():
    print("REALITYGRAPH / PARKINSON CANONICAL STRIATAL V1")
    print("-----------------------------------------------")
    print("Present fixed: G1 L_elong_q95 + G2 R_q90")
    print("Representation change only: shared bilateral rigid canonical coordinates")
    print("Intensity: frozen R field with positive q90 scaling")
    print("Right side mirrored; one frame estimated from bilateral average")
    print("Rigid translation + orientation normalized; physical scale/shape preserved")
    print("Field: 4x8 left + 4x8 right = 64 features")
    print("Exact ablation: same normalization/pooling with alignment deleted")
    print("Decoder fixed: environment-balanced ridge residual, parent logit coefficient one")
    print("Promotion target: lower LL AND higher AUC in both sealed futures")
    print("Future labels never choose invocation, representation, alignment, or decoder")
    print()

    y, env, canonical, g1 = load_frozen_baseline()
    feature_matrix, feature_names = load_exact_candidate_field()
    q = feature_matrix[:, feature_names.index(Q_NAME)]
    base = g2_baseline(q, g1)
    r = load_r_map()
    if len(r) != len(y):
        raise RuntimeError("map/base row mismatch")

    print("BUILDING_CANONICAL_REPRESENTATION", flush=True)
    aligned = canonical_striatal_features(r)
    print("BUILDING_UNALIGNED_ABLATION", flush=True)
    ablation = unaligned_striatal_features(r)
    print("REPRESENTATION_SHAPES", aligned.shape, ablation.shape)
    print(
        "PARENT",
        "LL", round(log_loss(y, base), 5),
        "AUC", round(roc_auc_score(y, base), 5),
        "L2", L2,
    )

    events = []
    for a, b in combinations(range(10), 2):
        event = outer_pair(a, b, aligned, ablation, y, env, base)
        events.append(event)
        print(
            "PAIR", f"{a},{b}",
            "INVOKE", int(event["invoked"]),
            "REASON", event["reason"],
            "INNER_JOINT", event["inner"]["joint_positive"], "/8",
            "INNER_LL", round(event["inner"]["ll_mean"], 5),
            "INNER_AUC", round(event["inner"]["auc_mean"], 5),
            "ALIGNED_LL", [round(x, 5) for x in event["aligned_ll"]],
            "ALIGNED_AUC", [round(x, 5) for x in event["aligned_auc"]],
            "ABLATION_LL", [round(x, 5) for x in event["ablation_ll"]],
            "ABLATION_AUC", [round(x, 5) for x in event["ablation_auc"]],
            "ALIGNED_PASS", int(event["aligned_pass"]),
            "ABLATION_PASS", int(event["ablation_pass"]),
            "ALIGNMENT_CAUSAL", int(event["alignment_causal"]),
            "ALPHA", round(event["alpha"], 3),
            "BETA_NORM", round(event["beta_norm"], 3),
            flush=True,
        )

    invoked = [e for e in events if e["invoked"]]
    aligned_passed = [e for e in invoked if e["aligned_pass"]]
    ablation_passed = [e for e in invoked if e["ablation_pass"]]
    causal = [e for e in invoked if e["alignment_causal"]]

    print()
    print("=== OUTER TWO-ENVIRONMENT FUTURES ===")
    print("INVOKED", len(invoked), "/45")
    print("ALIGNED_JOINT_PASS_BOTH", len(aligned_passed), "/45")
    print("ABLATION_JOINT_PASS_BOTH", len(ablation_passed), "/45")
    print("ALIGNMENT_CAUSAL_PASSES", len(causal), "/45")
    print("PRIOR_WEAK_REPRESENTATION_REFERENCE", PRIOR_WEAK_REFERENCE, "/45")
    print("DELTA_VS_PRIOR_REFERENCE", len(aligned_passed) - PRIOR_WEAK_REFERENCE)

    for e in range(10):
        ll_values = []
        auc_values = []
        for event in invoked:
            a, b = event["pair"]
            if e not in (a, b):
                continue
            k = 0 if a == e else 1
            ll_values.append(event["aligned_ll"][k])
            auc_values.append(event["aligned_auc"][k])
        print(
            "ENV", e,
            "INVOKED", len(ll_values), "/9",
            "JOINT_POS", int(sum(x > 0.0 and z > 0.0 for x, z in zip(ll_values, auc_values))),
            "LL_MEAN", round(float(np.mean(ll_values)), 5) if ll_values else None,
            "LL_WORST", round(float(np.min(ll_values)), 5) if ll_values else None,
            "AUC_MEAN", round(float(np.mean(auc_values)), 5) if auc_values else None,
            "AUC_WORST", round(float(np.min(auc_values)), 5) if auc_values else None,
        )

    print()
    print("=== ALL-ENV AUDIT ===")
    aligned_audit = all_env_audit("CANONICAL_ALIGNED", aligned, y, env, base)
    ablation_audit = all_env_audit("ALIGNMENT_DELETED", ablation, y, env, base)

    print()
    print("=== VERDICT ===")
    if len(aligned_passed) > PRIOR_WEAK_REFERENCE and len(aligned_passed) > len(ablation_passed) and len(causal) > 0:
        print("CANONICAL_ALIGNMENT_IMPROVES_PROSPECTIVE_TRANSFER")
    elif len(causal) > 0 and len(aligned_passed) > len(ablation_passed):
        print("ALIGNMENT_CAUSAL_BUT_NOT_ABOVE_PRIOR_REFERENCE")
    else:
        print("CANONICAL_ALIGNMENT_DOES_NOT_UNLOCK_TRANSFER")
    print("ALIGNED_JOINT_PASSES", len(aligned_passed), "/45")
    print("ABLATION_JOINT_PASSES", len(ablation_passed), "/45")
    print("ALIGNMENT_CAUSAL_PASSES", len(causal), "/45")
    print("ALIGNED_ALL_ENV_LL", round(aligned_audit["ll"], 5))
    print("ALIGNED_ALL_ENV_AUC", round(aligned_audit["auc"], 5))
    print("ALIGNMENT_DELETED_ALL_ENV_LL", round(ablation_audit["ll"], 5))
    print("ALIGNMENT_DELETED_ALL_ENV_AUC", round(ablation_audit["auc"], 5))


if __name__ == "__main__":
    main()
