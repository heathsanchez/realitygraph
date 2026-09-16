from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path

import numpy as np

from realitygraph.representation_genesis import (
    apply_program,
    enumerate_programs,
    program_complexity,
)
from realitygraph.ridge_decoder import (
    fit_ridge_residual_decoder,
    joint_evidence_invoke,
    predict_ridge_residual_decoder,
)

# Freeze the already verified Parkinson present.  This experiment changes only
# the decoder over the same 96 Representation Genesis V1 matrices.
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
PREFILTER = 8
MIN_MEAN_LL = 1e-4
MIN_MEAN_AUC = 0.0
WEAK_DECODER_REFERENCE_PASS_BOTH = 3


def g2_baseline(q, g1):
    delta = np.where(q >= Q_T, Q_D1, Q_D0)
    return sigmoid(logit(g1) + delta)


def load_maps():
    path = next((p for p in MAP_CANDIDATES if p.exists()), None)
    if path is None:
        raise FileNotFoundError("pp_signal_maps.npz not found")
    data = np.load(path)
    maps = {
        "X": np.asarray(data["X"], np.float64),
        "R": np.asarray(data["R"], np.float64),
    }
    if maps["X"].shape != maps["R"].shape:
        raise RuntimeError("X/R map shape mismatch")
    if maps["R"].ndim != 3:
        raise RuntimeError(f"unexpected map shape {maps['R'].shape}")
    if not all(np.isfinite(v).all() for v in maps.values()):
        raise RuntimeError("non-finite signal maps")
    print("MAPS", path, maps["R"].shape)
    return maps


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


def program_name(program):
    return "/".join((program.source, program.intensity, program.bilateral, program.pooling))


def fit_program(program, matrices, y, env, base, train_envs, cache):
    key = (program, tuple(train_envs))
    if key not in cache:
        model = fit_ridge_residual_decoder(
            matrices[program], y, base, env, tuple(train_envs), l2=L2
        )
        pred = predict_ridge_residual_decoder(model, matrices[program], base)
        cache[key] = (model, pred)
    return cache[key]


def cheap_discovery_rank(programs, matrices, y, env, base, discovery, cache):
    ranked = []
    for program in programs:
        model, pred = fit_program(program, matrices, y, env, base, discovery, cache)
        ll, auc = evaluate_envs(y, env, base, pred, discovery)
        joint = int(np.sum((ll > 0.0) & (auc > 0.0)))
        key = (
            joint,
            float(ll.min()),
            float(auc.min()),
            float(ll.mean()),
            float(auc.mean()),
            -program_complexity(program)[0],
        )
        ranked.append((key, program, float(model.alpha), float(np.linalg.norm(model.beta))))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[:PREFILTER]


def inner_verify(program, matrices, y, env, base, discovery, cache):
    ll_gains = []
    auc_gains = []
    alphas = []
    beta_norms = []

    for held in discovery:
        train = tuple(e for e in discovery if e != held)
        model, pred = fit_program(program, matrices, y, env, base, train, cache)
        ll, auc = evaluate_envs(y, env, base, pred, (held,))
        ll_gains.append(float(ll[0]))
        auc_gains.append(float(auc[0]))
        alphas.append(float(model.alpha))
        beta_norms.append(float(np.linalg.norm(model.beta)))

    joint = int(sum(a > 0.0 and b > 0.0 for a, b in zip(ll_gains, auc_gains)))
    return {
        "program": program,
        "joint_positive": joint,
        "ll_positive": int(sum(x > 0.0 for x in ll_gains)),
        "auc_positive": int(sum(x > 0.0 for x in auc_gains)),
        "ll_worst": float(min(ll_gains)),
        "ll_mean": float(np.mean(ll_gains)),
        "auc_worst": float(min(auc_gains)),
        "auc_mean": float(np.mean(auc_gains)),
        "alpha_median": float(np.median(alphas)),
        "beta_norm_median": float(np.median(beta_norms)),
        "ll_gains": ll_gains,
        "auc_gains": auc_gains,
    }


def verifier_key(record):
    return (
        record["joint_positive"],
        record["ll_worst"],
        record["auc_worst"],
        record["ll_mean"],
        record["auc_mean"],
        -program_complexity(record["program"])[0],
    )


def outer_pair(a, b, programs, matrices, y, env, base, cache):
    discovery = tuple(e for e in range(10) if e not in (a, b))
    shortlist = cheap_discovery_rank(
        programs, matrices, y, env, base, discovery, cache
    )
    verified = [
        inner_verify(program, matrices, y, env, base, discovery, cache)
        for _, program, _, _ in shortlist
    ]
    verified.sort(key=verifier_key, reverse=True)
    best = verified[0]

    invoke = joint_evidence_invoke(
        best["ll_gains"],
        best["auc_gains"],
        min_mean_ll=MIN_MEAN_LL,
        min_mean_auc=MIN_MEAN_AUC,
    )
    universal = bool(
        all(x > 0.0 for x in best["ll_gains"])
        and all(x > 0.0 for x in best["auc_gains"])
        and best["ll_mean"] > MIN_MEAN_LL
        and best["auc_mean"] > MIN_MEAN_AUC
    )
    reason = "promoted" if universal else "mixed" if invoke else "refuse"

    if not invoke:
        return {
            "pair": (a, b),
            "invoked": False,
            "reason": reason,
            "program": best["program"],
            "inner": best,
            "future_ll": [0.0, 0.0],
            "future_auc": [0.0, 0.0],
            "ll_pass": False,
            "auc_pass": False,
            "pass": False,
            "alpha": 0.0,
            "beta_norm": 0.0,
        }

    model, pred = fit_program(
        best["program"], matrices, y, env, base, discovery, cache
    )
    future_ll, future_auc = evaluate_envs(y, env, base, pred, (a, b))
    ll_pass = bool(np.min(future_ll) > 0.0)
    auc_pass = bool(np.min(future_auc) > 0.0)

    return {
        "pair": (a, b),
        "invoked": True,
        "reason": reason,
        "program": best["program"],
        "inner": best,
        "future_ll": [float(x) for x in future_ll],
        "future_auc": [float(x) for x in future_auc],
        "ll_pass": ll_pass,
        "auc_pass": auc_pass,
        "pass": bool(ll_pass and auc_pass),
        "alpha": float(model.alpha),
        "beta_norm": float(np.linalg.norm(model.beta)),
    }


def summarize_events(events):
    invoked = [e for e in events if e["invoked"]]
    joint_passed = [e for e in invoked if e["pass"]]
    ll_passed = [e for e in invoked if e["ll_pass"]]
    auc_passed = [e for e in invoked if e["auc_pass"]]
    counts = Counter(program_name(e["program"]) for e in invoked)
    pass_counts = Counter(program_name(e["program"]) for e in joint_passed)

    print()
    print("=== OUTER TWO-ENVIRONMENT FUTURES ===")
    print("INVOKED", len(invoked), "/45")
    print("LL_PASS_BOTH", len(ll_passed), "/45")
    print("AUC_PASS_BOTH", len(auc_passed), "/45")
    print("JOINT_PASS_BOTH", len(joint_passed), "/45")
    print("JOINT_PRECISION", round(len(joint_passed) / max(1, len(invoked)), 4))
    print("WEAK_DECODER_REFERENCE_JOINT_PASS_BOTH", WEAK_DECODER_REFERENCE_PASS_BOTH, "/45")
    print("DECODER_DELTA_JOINT_PASSES", len(joint_passed) - WEAK_DECODER_REFERENCE_PASS_BOTH)

    for e in range(10):
        ll_values = []
        auc_values = []
        for event in events:
            a, b = event["pair"]
            if e not in (a, b) or not event["invoked"]:
                continue
            k = 0 if a == e else 1
            ll_values.append(event["future_ll"][k])
            auc_values.append(event["future_auc"][k])
        print(
            "ENV", e,
            "INVOKED", len(ll_values), "/9",
            "JOINT_POS", sum(x > 0 and z > 0 for x, z in zip(ll_values, auc_values)),
            "LL_MEAN", round(float(np.mean(ll_values)), 5) if ll_values else None,
            "LL_WORST", round(float(np.min(ll_values)), 5) if ll_values else None,
            "AUC_MEAN", round(float(np.mean(auc_values)), 5) if auc_values else None,
            "AUC_WORST", round(float(np.min(auc_values)), 5) if auc_values else None,
        )

    print()
    print("=== DECODER + REPRESENTATION RECURRENCE ===")
    for name, count in counts.most_common():
        print(name, "INVOKED", count, "JOINT_PASSED", pass_counts[name])

    return invoked, joint_passed, counts, pass_counts


def all_env_candidate(program, matrix, y, env, base):
    model = fit_ridge_residual_decoder(
        matrix, y, base, env, tuple(range(10)), l2=L2
    )
    pred = predict_ridge_residual_decoder(model, matrix, base)
    ll_gains, auc_gains = evaluate_envs(y, env, base, pred, tuple(range(10)))
    return {
        "program": program,
        "alpha": float(model.alpha),
        "beta_norm": float(np.linalg.norm(model.beta)),
        "ll": log_loss(y, pred),
        "auc": roc_auc_score(y, pred),
        "ll_gain": log_loss(y, base) - log_loss(y, pred),
        "auc_gain": roc_auc_score(y, pred) - roc_auc_score(y, base),
        "ll_worst": float(ll_gains.min()),
        "ll_pos": int(sum(ll_gains > 0.0)),
        "auc_worst": float(auc_gains.min()),
        "auc_pos": int(sum(auc_gains > 0.0)),
    }


def main():
    print("REALITYGRAPH / PARKINSON RIDGE DECODER V2")
    print("------------------------------------------")
    print("Present fixed: G1 L_elong_q95 + G2 R_q90")
    print("Representations frozen: exact 96 Genesis V1 programs")
    print("Only change: environment-balanced ridge-logistic residual decoder")
    print("Parent logit coefficient fixed at one; no intercept/global recalibration")
    print("Promotion target: lower LL AND higher AUC")
    print("Future labels never choose representation or decoder")
    print()

    y, env, canonical, g1 = load_frozen_baseline()
    feature_matrix, feature_names = load_exact_candidate_field()
    q = feature_matrix[:, feature_names.index(Q_NAME)]
    base = g2_baseline(q, g1)
    maps = load_maps()

    if len(y) != len(maps["R"]):
        raise RuntimeError("map/base row mismatch")

    programs = tuple(sorted(enumerate_programs(), key=program_complexity))
    matrices = {}
    for i, program in enumerate(programs):
        matrices[program] = apply_program(maps, program)
        if (i + 1) % 16 == 0 or i + 1 == len(programs):
            print("COMPILED_PROGRAMS", i + 1, "/", len(programs), flush=True)

    print()
    print(
        "PARENT",
        "LL", round(log_loss(y, base), 5),
        "AUC", round(roc_auc_score(y, base), 5),
        "PROGRAMS", len(programs),
        "L2", L2,
    )

    cache = {}
    events = []
    for a, b in combinations(range(10), 2):
        event = outer_pair(a, b, programs, matrices, y, env, base, cache)
        events.append(event)
        print(
            "PAIR", f"{a},{b}",
            "INVOKE", int(event["invoked"]),
            "REASON", event["reason"],
            "PROGRAM", program_name(event["program"]),
            "INNER_JOINT", event["inner"]["joint_positive"], "/8",
            "INNER_LL", round(event["inner"]["ll_mean"], 5),
            "INNER_AUC", round(event["inner"]["auc_mean"], 5),
            "FUTURE_LL", [round(x, 5) for x in event["future_ll"]],
            "FUTURE_AUC", [round(x, 5) for x in event["future_auc"]],
            "ALPHA", round(event["alpha"], 3),
            "BETA_NORM", round(event["beta_norm"], 3),
            "PASS", int(event["pass"]),
            flush=True,
        )

    invoked, passed, counts, pass_counts = summarize_events(events)

    print()
    print("=== RECURRENT DECODER AUDIT ===")
    recurrent = []
    for name, count in counts.most_common(10):
        program = next(p for p in programs if program_name(p) == name)
        result = all_env_candidate(program, matrices[program], y, env, base)
        recurrent.append((count, pass_counts[name], result))
        print(
            name,
            "RECURRENCE", count,
            "PAIR_JOINT_PASSES", pass_counts[name],
            "ALPHA", round(result["alpha"], 3),
            "BETA_NORM", round(result["beta_norm"], 3),
            "LL", round(result["ll"], 5),
            "AUC", round(result["auc"], 5),
            "LL_GAIN", round(result["ll_gain"], 5),
            "AUC_GAIN", round(result["auc_gain"], 5),
            "LL_WORST", round(result["ll_worst"], 5),
            "LL_POS", result["ll_pos"], "/10",
            "AUC_WORST", round(result["auc_worst"], 5),
            "AUC_POS", result["auc_pos"], "/10",
        )

    strong = [
        (count, pair_passes, r)
        for count, pair_passes, r in recurrent
        if (
            count >= 6
            and pair_passes / max(1, count) >= 0.75
            and r["ll_gain"] > 1e-4
            and r["auc_gain"] > 0.0
            and r["ll_worst"] > 0.0
            and r["ll_pos"] == 10
            and r["auc_worst"] > 0.0
            and r["auc_pos"] == 10
        )
    ]

    print()
    print("=== VERDICT ===")
    if len(passed) >= 30 and strong:
        strong.sort(
            key=lambda item: (
                -item[0],
                -item[1],
                item[2]["ll"],
                -item[2]["auc"],
                program_complexity(item[2]["program"]),
            )
        )
        winner = strong[0][2]
        print("PASS_RIDGE_DECODER_UNLOCKS_REPRESENTATION_V2")
        print("WINNER", program_name(winner["program"]))
        print("ALL_ENV_LL", round(winner["ll"], 5), "AUC", round(winner["auc"], 5))
        print("FREEZE_DECODER_AND_RUN_INDEPENDENT_PARITY_NEXT")
    elif len(passed) > WEAK_DECODER_REFERENCE_PASS_BOTH:
        print("PARTIAL_RIDGE_DECODER_SIGNAL_NOT_TRANSFER_SAFE")
        print("JOINT_PASSES", len(passed), "/45")
        print("DECODER_HELPED_BUT_DID_NOT_COMPILE")
    else:
        print("RIDGE_DECODER_DOES_NOT_UNLOCK_REPRESENTATION")
        print("JOINT_PASSES", len(passed), "/45")
        print("CHANGE_REPRESENTATION__DO_NOT_ADD_MORE_DECODER_COMPLEXITY")


if __name__ == "__main__":
    main()
