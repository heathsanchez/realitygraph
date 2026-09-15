from __future__ import annotations

import ast
import hashlib
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import log_loss, roc_auc_score


WORK = Path("/workspace")
TOURNAMENT = WORK / "arbitrary_separator_tournament.py"
RG_RESIDUAL = WORK / "parkinson_realitygraph_residual.py"
RG_META = WORK / "realitygraph-meta"
POLICY_DIRS = [
    RG_META / "meta-policy-out",
    WORK / "meta100x-evidence" / "meta-policy-out",
]

FROZEN_NAME = "L_elong_q95"
FROZEN_T = 1.5314126014709473
FROZEN_D0 = 0.90
FROZEN_D1 = -0.15

# Contracted from the 16,560-feature env1 tournament.
# Transformed duplicates (LOGR/SQRT_R) are intentionally omitted.
CANDIDATES = [
    "GRAD_R_q80",
    "R_q90",
    "R_L_grid4x4_1_2_std",
    "GRAD_R_L_grid4x4_1_2_mean",
    "R_q95",
]

DELTAS = np.linspace(-1.5, 1.5, 61)
MAX_THRESHOLDS = 31


def clip_p(p):
    return np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)


def logit(p):
    p = clip_p(p)
    return np.log(p / (1 - p))


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def row_loss(y, p):
    p = clip_p(p)
    y = np.asarray(y, dtype=float)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def load_frozen_baseline():
    src = RG_RESIDUAL.read_text()
    ns = {}
    exec(
        compile(src.split("field=field_from_matrix")[0], str(RG_RESIDUAL), "exec"),
        ns,
    )

    F = np.asarray(ns["F"], float)
    names = np.asarray(ns["names"])
    y = np.asarray(ns["y"], int)
    env = np.asarray(ns["env"], int)
    base = clip_p(ns["BASE"])

    j = int(np.where(names == FROZEN_NAME)[0][0])
    delta = np.where(F[:, j] >= FROZEN_T, FROZEN_D1, FROZEN_D0)
    frozen = sigmoid(logit(base) + delta)

    return y, env, base, frozen


def load_exact_candidate_field():
    if not TOURNAMENT.exists():
        raise FileNotFoundError(TOURNAMENT)

    src = TOURNAMENT.read_text()
    tree = ast.parse(src, filename=str(TOURNAMENT))

    feature_node = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "features":
            feature_node = node
            break
    if feature_node is None:
        raise RuntimeError("features() not found in arbitrary_separator_tournament.py")

    # Execute only the exact source prefix required to define features().
    # This deliberately excludes the expensive nested tournament below it.
    prefix_nodes = [
        node
        for node in tree.body
        if getattr(node, "end_lineno", 0) <= feature_node.end_lineno
    ]
    prefix = ast.Module(body=prefix_nodes, type_ignores=[])
    ast.fix_missing_locations(prefix)

    ns = {}
    exec(compile(prefix, str(TOURNAMENT), "exec"), ns)

    X = np.asarray(ns["X"], np.float32)
    R = np.asarray(ns["R"], np.float32)
    feature_fn = ns["features"]

    # The retained candidates are not rectangle or morphology features.
    # Delete those expensive branches while preserving the exact describe()
    # implementation for the named retained features.
    if "RECTS" in ns:
        ns["RECTS"] = []
    if "morph" in ns:
        ns["morph"] = lambda *args, **kwargs: None

    original_add = ns["add"]
    wanted = set(CANDIDATES)

    def filtered_add(v, names, val, name):
        if name in wanted:
            original_add(v, names, val, name)

    ns["add"] = filtered_add

    rows = []
    exact_names = None
    for i in range(len(R)):
        vals, names = feature_fn(X[i], R[i], None)
        if exact_names is None:
            exact_names = list(names)
            missing = [name for name in CANDIDATES if name not in exact_names]
            if missing:
                raise RuntimeError(f"contracted candidate(s) missing: {missing}")
        if list(names) != exact_names:
            raise RuntimeError("candidate feature schema drift")
        rows.append(vals)
        if (i + 1) % 250 == 0 or i + 1 == len(R):
            print(f"candidate rows {i+1}/{len(R)}", flush=True)

    M = np.asarray(rows, dtype=np.float64)
    order = [exact_names.index(name) for name in CANDIDATES]
    return M[:, order], list(CANDIDATES)


# Exact descriptor family used by meta-100x-v1.
CORPUS_SEED = "realitygraph-pmlb-meta-v1"


def _hash(seed, value):
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _variance(values, mean):
    return sum((value - mean) ** 2 for value in values) / max(len(values), 1)


def _correlation(xs, ys):
    mx = _mean(xs)
    my = _mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 1e-18 or vy <= 1e-18:
        return 0.0
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / math.sqrt(vx * vy)


def descriptors(values, labels, dataset, feature):
    values = [float(v) for v in values]
    labels = [int(v) for v in labels]

    class0 = [v for v, label in zip(values, labels) if label == 0]
    class1 = [v for v, label in zip(values, labels) if label == 1]
    m0 = _mean(class0)
    m1 = _mean(class1)
    v0 = _variance(class0, m0)
    v1 = _variance(class1, m1)
    pooled = math.sqrt(max((v0 + v1) / 2.0, 0.0))
    effect = abs(m1 - m0) / (pooled + 1e-9)
    corr = abs(_correlation(values, labels))

    ordered = sorted(values)
    median = ordered[len(ordered) // 2]
    left = [label for value, label in zip(values, labels) if value < median]
    right = [label for value, label in zip(values, labels) if value >= median]
    median_gap = abs(_mean(right) - _mean(left)) if left and right else 0.0
    split_balance = (
        2.0 * min(len(left), len(right)) / len(values)
        if values else 0.0
    )

    overall_sign = 1 if m1 >= m0 else -1
    agreements = 0
    valid = 0
    folds = {i: [] for i in range(4)}
    for i, (value, label) in enumerate(zip(values, labels)):
        fold = int.from_bytes(
            _hash(f"{CORPUS_SEED}|stability|{dataset}|{feature}", str(i))[:2],
            "big",
        ) % 4
        folds[fold].append((value, label))

    for members in folds.values():
        c0 = [value for value, label in members if label == 0]
        c1 = [value for value, label in members if label == 1]
        if not c0 or not c1:
            continue
        sign = 1 if _mean(c1) >= _mean(c0) else -1
        valid += 1
        agreements += int(sign == overall_sign)

    sign_stability = agreements / valid if valid else 0.5
    unique_ratio = len(set(values)) / len(values) if values else 0.0

    return (
        effect,
        corr,
        median_gap,
        sign_stability,
        unique_ratio,
        split_balance,
    )


def load_meta_memory():
    if str(RG_META) not in sys.path:
        sys.path.insert(0, str(RG_META))

    try:
        from realitygraph.mg import MG
        from realitygraph.meta_policy import policy_from_memory
        from realitygraph.adaptive_policy import budget_from_memory, budget_features
    except Exception as exc:
        print(f"META UNAVAILABLE: import failed: {exc}")
        return None, None, None

    for root in POLICY_DIRS:
        meta = root / "meta_policy.mg"
        adaptive = root / "adaptive_policy.mg"
        if not meta.exists():
            continue

        policy = policy_from_memory(MG.parse(meta.read_text()))
        budget = None
        if adaptive.exists():
            budget = budget_from_memory(MG.parse(adaptive.read_text()))

        print(f"META MEMORY {root}")
        print(f"  training_worlds={policy.training_worlds}")
        print(f"  fixed_budget={policy.budget}")
        print(f"  adaptive={'YES' if budget is not None else 'NO'}")
        return policy, budget, budget_features

    print("META MEMORY NOT FOUND: using stable-frequency fallback budget=3")
    return None, None, None


def rank_for_future(M, names, y, env, future, policy, adaptive, budget_features_fn):
    discovery = env != future
    rows = []
    dataset = f"parkinson-post-elong-future-{future}"

    for j, name in enumerate(names):
        d = descriptors(M[discovery, j], y[discovery], dataset, j)
        score = policy.score(d) if policy is not None else float(len(names) - j)
        rows.append({
            "name": name,
            "index": j,
            "descriptors": tuple(float(x) for x in d),
            "score": float(score),
        })

    rows.sort(key=lambda r: (-r["score"], r["name"]))

    if policy is None:
        budget = min(3, len(rows))
    elif adaptive is None or budget_features_fn is None:
        budget = min(policy.budget, len(rows))
    else:
        world = {
            "candidates": [
                {"descriptors": r["descriptors"]}
                for r in rows
            ]
        }
        bf = budget_features_fn(policy, world)
        budget = min(adaptive.choose_budget(bf), len(rows))

    return rows[:budget], rows, budget


def candidate_thresholds(values, max_thresholds=MAX_THRESHOLDS):
    unique = np.unique(np.asarray(values, float))
    if len(unique) <= 1:
        return np.array([], float)
    mids = (unique[:-1] + unique[1:]) / 2.0
    if len(mids) <= max_thresholds:
        return mids
    idx = np.linspace(0, len(mids) - 1, max_thresholds).round().astype(int)
    return np.unique(mids[idx])


def robust_fit_one(x, y, env, baseline, discovery_envs):
    discovery_mask = np.isin(env, discovery_envs)
    thresholds = candidate_thresholds(x[discovery_mask])
    if not len(thresholds):
        return None

    z = logit(baseline)
    base_row = row_loss(y, baseline)
    best = None

    for t in thresholds:
        high = x >= t
        gains_by_env = []

        for e in discovery_envs:
            ids = np.where(env == e)[0]
            n = len(ids)
            base_loss = float(base_row[ids].mean())

            lo = ids[~high[ids]]
            hi = ids[high[ids]]

            if len(lo):
                pp0 = sigmoid(z[lo][None, :] + DELTAS[:, None])
                yy0 = y[lo][None, :]
                L0 = -(
                    yy0 * np.log(clip_p(pp0))
                    + (1 - yy0) * np.log(clip_p(1 - pp0))
                ).sum(axis=1)
            else:
                L0 = np.zeros(len(DELTAS))

            if len(hi):
                pp1 = sigmoid(z[hi][None, :] + DELTAS[:, None])
                yy1 = y[hi][None, :]
                L1 = -(
                    yy1 * np.log(clip_p(pp1))
                    + (1 - yy1) * np.log(clip_p(1 - pp1))
                ).sum(axis=1)
            else:
                L1 = np.zeros(len(DELTAS))

            new_loss = (L0[:, None] + L1[None, :]) / n
            gains_by_env.append(base_loss - new_loss)

        G = np.stack(gains_by_env, axis=0)
        worst = G.min(axis=0)
        mean = G.mean(axis=0)

        mw = float(worst.max())
        cand = np.argwhere(worst >= mw - 1e-12)

        best_pair = None
        for a, b in cand:
            key = (
                float(worst[a, b]),
                float(mean[a, b]),
                -float(abs(DELTAS[a]) + abs(DELTAS[b])),
            )
            if best_pair is None or key > best_pair[0]:
                best_pair = (key, int(a), int(b))

        key, a, b = best_pair
        item = {
            "threshold": float(t),
            "d0": float(DELTAS[a]),
            "d1": float(DELTAS[b]),
            "worst": float(key[0]),
            "mean": float(key[1]),
        }

        full_key = (
            item["worst"],
            item["mean"],
            -(abs(item["d0"]) + abs(item["d1"])),
        )
        if best is None or full_key > best[0]:
            best = (full_key, item)

    return None if best is None else best[1]


def apply_law(x, baseline, law):
    delta = np.where(x >= law["threshold"], law["d1"], law["d0"])
    return sigmoid(logit(baseline) + delta)


def main():
    print("REALITYGRAPH / PARKINSON FINISH-FAST")
    print("------------------------------------")
    print("Frozen stage 1: canonical + L_elong_q95 law")
    print("Proposal: meta-100x rank + adaptive budget")
    print("Verifier: environment-maximin residual consequence")
    print()

    y, env, canonical, frozen = load_frozen_baseline()
    print(
        "FROZEN",
        f"LL {log_loss(y, frozen):.5f}",
        f"AUC {roc_auc_score(y, frozen):.5f}",
    )

    M, names = load_exact_candidate_field()
    if len(M) != len(y):
        raise RuntimeError(f"candidate/base row mismatch: {len(M)} vs {len(y)}")
    if not np.isfinite(M).all():
        raise RuntimeError("non-finite contracted candidate field")

    print("CONTRACTED FIELD", M.shape, names)
    policy, adaptive, budget_features_fn = load_meta_memory()

    all_envs = sorted(int(e) for e in np.unique(env))
    out = frozen.copy()
    laws = []

    print()
    print("=== OUTER NATURAL-GROUP FUTURES ===")

    for future in all_envs:
        selected, ranked, budget = rank_for_future(
            M, names, y, env, future,
            policy, adaptive, budget_features_fn,
        )
        print()
        print(
            "FUTURE", future,
            "BUDGET", budget,
            "RANKED",
            [(r["name"], round(r["score"], 4)) for r in ranked],
        )

        discovery_envs = [e for e in all_envs if e != future]
        best = None

        for r in selected:
            law = robust_fit_one(
                M[:, r["index"]],
                y,
                env,
                frozen,
                discovery_envs,
            )
            if law is None:
                continue

            key = (
                law["worst"],
                law["mean"],
                -(abs(law["d0"]) + abs(law["d1"])),
            )
            print(
                "  TEST", r["name"],
                "T", round(law["threshold"], 5),
                "D", round(law["d0"], 3), round(law["d1"], 3),
                "DISC_WORST", round(law["worst"], 5),
                "DISC_MEAN", round(law["mean"], 5),
            )

            if best is None or key > best[0]:
                best = (key, r, law)

        if best is None:
            print("  REFUSE no law")
            continue

        _, r, law = best
        m = env == future
        q = apply_law(M[:, r["index"]], frozen, law)

        b = log_loss(y[m], frozen[m])
        n = log_loss(y[m], q[m])
        gain = b - n

        # If discovery cannot certify non-harm, keep exact frozen baseline.
        accepted = law["worst"] >= -1e-12 and law["mean"] > 1e-4
        if accepted:
            out[m] = q[m]

        law = {
            **law,
            "future": future,
            "name": r["name"],
            "index": r["index"],
            "future_gain": float(gain),
            "accepted": bool(accepted),
            "budget": int(budget),
        }
        laws.append(law)

        print(
            "  CHOSEN", r["name"],
            "FUTURE_GAIN", round(gain, 5),
            "AUC", round(roc_auc_score(y[m], q[m]), 5),
            "VERDICT", "KEEP" if accepted and gain > 0 else (
                "FUTURE_REVERSE" if accepted else "REFUSE"
            ),
        )

    print()
    print("=== CROSS-FUTURE RESULT ===")
    base_ll = log_loss(y, frozen)
    new_ll = log_loss(y, out)
    print("FROZEN LL", round(base_ll, 5), "AUC", round(roc_auc_score(y, frozen), 5))
    print("CROSSFIT LL", round(new_ll, 5), "AUC", round(roc_auc_score(y, out), 5))
    print("GAIN", round(base_ll - new_ll, 5))

    print()
    print("=== PER ENV ===")
    negative = 0
    for e in all_envs:
        m = env == e
        b = log_loss(y[m], frozen[m])
        n = log_loss(y[m], out[m])
        g = b - n
        negative += int(g < -1e-12)
        print(
            e,
            "GAIN", round(g, 5),
            "LL", round(n, 5),
            "AUC", round(roc_auc_score(y[m], out[m]), 5),
        )
    print("NEGATIVE ENVS", negative)

    accepted_laws = [law for law in laws if law["accepted"]]
    counts = Counter(law["name"] for law in accepted_laws)
    print()
    print("=== LAW COUNTS ===")
    for name, count in counts.most_common():
        print(name, count)

    if not counts:
        print()
        print("=== VERDICT ===")
        print("NO_SECOND_LAW_COMPILES__PACKAGE_FROZEN_ELONGATION")
        return

    modal, modal_count = counts.most_common(1)[0]
    modal_laws = [law for law in accepted_laws if law["name"] == modal]

    fixed = {
        "threshold": float(np.median([law["threshold"] for law in modal_laws])),
        "d0": float(np.median([law["d0"] for law in modal_laws])),
        "d1": float(np.median([law["d1"] for law in modal_laws])),
    }
    j = names.index(modal)
    fixed_pred = apply_law(M[:, j], frozen, fixed)

    print()
    print("=== FROZEN SECOND-LAW CANDIDATE ===")
    print(
        modal,
        "COUNT", modal_count,
        "T", round(fixed["threshold"], 6),
        "D0", round(fixed["d0"], 3),
        "D1", round(fixed["d1"], 3),
    )

    fixed_gains = []
    for e in all_envs:
        m = env == e
        g = log_loss(y[m], frozen[m]) - log_loss(y[m], fixed_pred[m])
        fixed_gains.append(float(g))
        print("ENV", e, "GAIN", round(g, 5))

    fixed_ll = log_loss(y, fixed_pred)
    print(
        "FIXED2",
        "LL", round(fixed_ll, 5),
        "AUC", round(roc_auc_score(y, fixed_pred), 5),
        "GAIN", round(base_ll - fixed_ll, 5),
        "WORST_ENV", round(min(fixed_gains), 5),
        "POS", sum(g > 0 for g in fixed_gains), "/10",
    )

    print()
    print("=== ABLATION ===")
    print("REMOVE SECOND LAW ->", round(base_ll, 5))
    print("SECOND LAW GAIN LOST", round(base_ll - fixed_ll, 5))

    print()
    print("=== VERDICT ===")
    if (
        modal_count >= 5
        and fixed_ll < base_ll
        and min(fixed_gains) > 0
    ):
        print("SECOND_FIXED_LAW_IMPROVES_ALL_10__DEPLOYMENT_PARITY_NEXT")
    else:
        print("SECOND_LAW_NOT_UNIVERSAL__STOP_SEARCH_AND_PACKAGE_ELONGATION")


if __name__ == "__main__":
    main()
