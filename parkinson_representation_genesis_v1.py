from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

from realitygraph.representation_genesis import (
    apply_program,
    enumerate_programs,
    fit_residual_decoder,
    predict_residual_decoder,
    program_complexity,
)

# Keep the already verified Parkinson present fixed.  Representation genesis is
# allowed to explain only the residual around G1+G2.
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

PREFILTER = 10
MIN_DISCOVERY_GAIN = 1e-4


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


def fit_program(matrix, y, env, base, train_envs):
    model = fit_residual_decoder(matrix, y, base, env, tuple(train_envs))
    pred = predict_residual_decoder(model, matrix, base)
    return model, pred


def cheap_discovery_rank(programs, matrices, y, env, base, discovery):
    ranked = []
    for program in programs:
        model, pred = fit_program(matrices[program], y, env, base, discovery)
        gains, aucs = evaluate_envs(y, env, base, pred, discovery)
        key = (
            float(gains.min()),
            float(gains.mean()),
            float(aucs.mean()),
            -program_complexity(program)[0],
        )
        ranked.append((key, program, model.delta))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[:PREFILTER]


def inner_verify(program, matrix, y, env, base, discovery):
    ll_gains = []
    auc_gains = []
    deltas = []

    for held in discovery:
        train = tuple(e for e in discovery if e != held)
        model, pred = fit_program(matrix, y, env, base, train)
        gains, aucs = evaluate_envs(y, env, base, pred, (held,))
        ll_gains.append(float(gains[0]))
        auc_gains.append(float(aucs[0]))
        deltas.append(float(model.delta))

    return {
        "program": program,
        "positive": int(sum(x > 0 for x in ll_gains)),
        "worst": float(min(ll_gains)),
        "mean": float(np.mean(ll_gains)),
        "auc_mean": float(np.mean(auc_gains)),
        "auc_worst": float(min(auc_gains)),
        "delta_median": float(np.median(deltas)),
        "ll_gains": ll_gains,
        "auc_gains": auc_gains,
    }


def verifier_key(record):
    # Consequence first: protect worst discovery environment, then average
    # log loss, then AUC.  Complexity only breaks evidential ties.
    complexity = program_complexity(record["program"])[0]
    return (
        record["worst"],
        record["mean"],
        record["auc_mean"],
        -complexity,
    )


def program_name(program):
    return "/".join((program.source, program.intensity, program.bilateral, program.pooling))


def outer_pair(a, b, programs, matrices, y, env, base):
    discovery = tuple(e for e in range(10) if e not in (a, b))
    shortlist = cheap_discovery_rank(programs, matrices, y, env, base, discovery)

    verified = [
        inner_verify(program, matrices[program], y, env, base, discovery)
        for _, program, _ in shortlist
    ]
    verified.sort(key=verifier_key, reverse=True)
    best = verified[0]

    # Refusal is a first-class outcome.  A generated representation does not
    # get to touch the two unseen environments unless every inner discovery
    # future improved and the mean gain is non-trivial.
    invoke = best["worst"] > 0 and best["mean"] > MIN_DISCOVERY_GAIN
    if not invoke:
        return {
            "pair": (a, b),
            "invoked": False,
            "program": best["program"],
            "inner": best,
            "future_ll": [0.0, 0.0],
            "future_auc": [0.0, 0.0],
            "pass": False,
            "delta": 0.0,
        }

    model, pred = fit_program(
        matrices[best["program"]], y, env, base, discovery
    )
    future_ll, future_auc = evaluate_envs(y, env, base, pred, (a, b))

    return {
        "pair": (a, b),
        "invoked": True,
        "program": best["program"],
        "inner": best,
        "future_ll": [float(x) for x in future_ll],
        "future_auc": [float(x) for x in future_auc],
        "pass": bool(np.min(future_ll) > 0),
        "delta": float(model.delta),
    }


def summarize_events(events):
    invoked = [e for e in events if e["invoked"]]
    passed = [e for e in invoked if e["pass"]]
    counts = Counter(program_name(e["program"]) for e in invoked)
    pass_counts = Counter(program_name(e["program"]) for e in passed)

    print()
    print("=== OUTER TWO-ENVIRONMENT FUTURES ===")
    print("INVOKED", len(invoked), "/45")
    print("PASS_BOTH", len(passed), "/45")
    print(
        "PASS_PRECISION",
        round(len(passed) / max(1, len(invoked)), 4),
    )

    for e in range(10):
        attempted = []
        for event in events:
            a, b = event["pair"]
            if e not in (a, b) or not event["invoked"]:
                continue
            k = 0 if a == e else 1
            attempted.append(event["future_ll"][k])
        print(
            "ENV", e,
            "INVOKED", len(attempted), "/9",
            "POS", sum(x > 0 for x in attempted),
            "MEAN", round(float(np.mean(attempted)), 5) if attempted else None,
            "WORST", round(float(np.min(attempted)), 5) if attempted else None,
        )

    print()
    print("=== REPRESENTATION RECURRENCE ===")
    for name, count in counts.most_common():
        print(name, "INVOKED", count, "PASSED", pass_counts[name])

    return invoked, passed, counts, pass_counts


def all_env_candidate(program, matrix, y, env, base):
    model, pred = fit_program(matrix, y, env, base, tuple(range(10)))
    gains, aucs = evaluate_envs(y, env, base, pred, tuple(range(10)))
    return {
        "program": program,
        "delta": float(model.delta),
        "ll": log_loss(y, pred),
        "auc": roc_auc_score(y, pred),
        "gain": log_loss(y, base) - log_loss(y, pred),
        "worst": float(gains.min()),
        "pos": int(sum(gains > 0)),
        "auc_mean": float(aucs.mean()),
        "auc_worst": float(aucs.min()),
    }


def main():
    print("REALITYGRAPH / PARKINSON REPRESENTATION GENESIS V1")
    print("----------------------------------------------------")
    print("Present fixed: G1 L_elong_q95 + G2 R_q90")
    print("Generator: deterministic representation programs")
    print("Decoder: one environment-balanced residual direction")
    print("Selector: discovery-only nested natural-environment verifier")
    print("Future labels never choose a representation")
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
    )

    events = []
    for index, (a, b) in enumerate(combinations(range(10), 2), start=1):
        event = outer_pair(a, b, programs, matrices, y, env, base)
        events.append(event)
        print(
            "PAIR", f"{a},{b}",
            "INVOKE", int(event["invoked"]),
            "PROGRAM", program_name(event["program"]),
            "INNER_WORST", round(event["inner"]["worst"], 5),
            "INNER_MEAN", round(event["inner"]["mean"], 5),
            "FUTURE_LL", [round(x, 5) for x in event["future_ll"]],
            "FUTURE_AUC", [round(x, 5) for x in event["future_auc"]],
            "PASS", int(event["pass"]),
            flush=True,
        )

    invoked, passed, counts, pass_counts = summarize_events(events)

    print()
    print("=== RECURRENT PROGRAM AUDIT ===")
    recurrent = []
    for name, count in counts.most_common(8):
        program = next(p for p in programs if program_name(p) == name)
        result = all_env_candidate(program, matrices[program], y, env, base)
        recurrent.append((count, pass_counts[name], result))
        print(
            name,
            "RECURRENCE", count,
            "PAIR_PASSES", pass_counts[name],
            "DELTA", round(result["delta"], 3),
            "LL", round(result["ll"], 5),
            "AUC", round(result["auc"], 5),
            "GAIN", round(result["gain"], 5),
            "WORST", round(result["worst"], 5),
            "POS", result["pos"], "/10",
            "AUC_WORST", round(result["auc_worst"], 5),
        )

    print()
    print("=== VERDICT ===")
    strong = [
        (count, pair_passes, r)
        for count, pair_passes, r in recurrent
        if (
            count >= 8
            and pair_passes / max(1, count) >= 0.90
            and r["gain"] > 1e-4
            and r["worst"] > 0
            and r["pos"] == 10
            and r["auc_worst"] > -0.01
        )
    ]

    if len(passed) >= 40 and strong:
        strong.sort(key=lambda item: (-item[0], item[2]["ll"], program_complexity(item[2]["program"])))
        _, _, winner = strong[0]
        print("PASS_REPRESENTATION_GENESIS_V1")
        print("RECURRENT_PROGRAM", program_name(winner["program"]))
        print(
            "ALL_ENV",
            "LL", round(winner["ll"], 5),
            "AUC", round(winner["auc"], 5),
            "DELTA", round(winner["delta"], 3),
        )
        print("FREEZE_PROGRAM_AND_RUN_INDEPENDENT_DEPLOYMENT_PARITY_NEXT")
    elif strong:
        strong.sort(key=lambda item: (-item[0], item[2]["ll"]))
        winner = strong[0][2]
        print("REPRESENTATION_SIGNAL_RECURS_BUT_CONTROLLER_NOT_UNIVERSAL")
        print("BEST_RECURRENT_PROGRAM", program_name(winner["program"]))
        print("DO_NOT_DEPLOY_YET__TEST_FROZEN_PROGRAM_SEPARATELY")
    else:
        print("NO_GENERATED_REPRESENTATION_COMPILES")
        print("RETAIN_G1_PLUS_G2__REPRESENTATION_GRAMMAR_INADEQUATE_OR_SIGNAL_SATURATED")


if __name__ == "__main__":
    main()
