from __future__ import annotations

import hashlib
import io
import itertools
import json
import math
import os
import urllib.request
import zipfile
from pathlib import Path

from compiled_transfer_demo import (
    compile_from_discovery,
    qualify_candidate,
    select_columns,
)
from prospective_capability_compounding import (
    exact_restart,
    prior_from_phase_a,
    subset_groups,
)
from recursive_capability_compounding_v2 import (
    compile_residual_from_stage,
    discover_residual,
    exact_residual_restart,
    group_indices,
    probabilities_from_base,
)
from realitygraph.grouped_empirical import GroupedBinaryDataset
from realitygraph.predictive import binary_auc, binary_log_loss
from realitygraph.residual_memory import (
    add_residual_to_memory,
    applicable_residual_laws,
    law_to_residual_model,
    residual_to_law,
)
from realitygraph.retained_capability import (
    ablate_capability,
    applicable_transfer_capabilities,
    only_law,
)
from realitygraph.transfer_memory import law_to_model, model_memory, model_to_law


HAR_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/"
    "00240/UCI%20HAR%20Dataset.zip"
)
EXPECTED_SHA256 = "2045e435c955214b38145fb5fa00776c72814f01b203fec405152dac7d5bfeb0"
RANK_BUDGET = 20
MIN_GAIN = 1e-5


def download() -> bytes:
    req = urllib.request.Request(
        HAR_URL,
        headers={"User-Agent": "RealityGraph/1.0 HAR compounding verifier"},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(
            f"HAR source changed: expected {EXPECTED_SHA256}, got {digest}"
        )
    print(f"HAR_SHA256={digest}")
    return raw


def parse_matrix(text: str):
    return [
        tuple(float(x) for x in line.split())
        for line in text.strip().splitlines()
        if line.strip()
    ]


def parse_ints(text: str):
    return [
        int(line.strip())
        for line in text.strip().splitlines()
        if line.strip()
    ]


def load_har_full() -> GroupedBinaryDataset:
    raw = download()
    digest = hashlib.sha256(raw).hexdigest()

    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        prefix = "UCI HAR Dataset/"
        feature_names = []
        for line in z.read(prefix + "features.txt").decode().strip().splitlines():
            _, name = line.split(maxsplit=1)
            feature_names.append(name)

        X_train = parse_matrix(z.read(prefix + "train/X_train.txt").decode())
        y_train = parse_ints(z.read(prefix + "train/y_train.txt").decode())
        s_train = parse_ints(z.read(prefix + "train/subject_train.txt").decode())
        X_test = parse_matrix(z.read(prefix + "test/X_test.txt").decode())
        y_test = parse_ints(z.read(prefix + "test/y_test.txt").decode())
        s_test = parse_ints(z.read(prefix + "test/subject_test.txt").decode())

    X = X_train + X_test
    activities = y_train + y_test
    subjects = s_train + s_test

    keep = [i for i, a in enumerate(activities) if a in {2, 3}]
    values = tuple(X[i] for i in keep)
    labels = tuple(1 if activities[i] == 2 else 0 for i in keep)
    groups = tuple(f"subject-{subjects[i]:02d}" for i in keep)

    if len(set(groups)) != 30 or len(values[0]) != 561:
        raise AssertionError("HAR schema/grouping drift")

    names = tuple(
        f"{i+1}:{name}"
        for i, name in enumerate(feature_names)
    )

    print(
        f"HAR task rows={len(values)} groups={len(set(groups))} "
        f"probes={len(names)} prevalence={sum(labels)/len(labels):.4f}"
    )

    return GroupedBinaryDataset(
        "UCI HAR upstairs-vs-downstairs / subject-separated",
        "10.24432/C54S4K",
        "CC BY 4.0",
        names,
        values,
        labels,
        groups,
        ((HAR_URL, digest),),
    )


def ordered_groups(dataset, seed):
    groups = sorted(set(dataset.groups))
    return tuple(
        sorted(
            groups,
            key=lambda g: (
                hashlib.sha256(f"{seed}|{g}".encode()).digest(),
                g,
            ),
        )
    )


def stages(dataset, seed):
    groups = ordered_groups(dataset, seed)
    return groups[:12], groups[12:21], groups[21:]


def feature_rank(phase_a):
    """Rank representation using Phase-A labels/groups only.

    Score rewards median within-subject discrimination, worst-subject
    discrimination, and stable direction. No later subject appears here.
    """
    ranked = []
    unique_groups = sorted(set(phase_a.groups))

    for j, name in enumerate(phase_a.probe_names):
        aucs = []
        directions = []
        for group in unique_groups:
            ids = [i for i, g in enumerate(phase_a.groups) if g == group]
            labels = [phase_a.labels[i] for i in ids]
            if len(set(labels)) < 2:
                continue
            values = [phase_a.values[i][j] for i in ids]
            auc = binary_auc(labels, values)
            aucs.append(max(auc, 1.0 - auc))
            directions.append(1 if auc >= 0.5 else -1)

        if len(aucs) < 4:
            continue

        ordered = sorted(aucs)
        median = ordered[len(ordered) // 2]
        worst_q = ordered[max(0, len(ordered) // 5)]
        pos = sum(d > 0 for d in directions)
        neg = len(directions) - pos
        stability = max(pos, neg) / len(directions)

        # Stable cross-subject consequence dominates peak discrimination.
        score = 0.50 * median + 0.35 * worst_q + 0.15 * stability
        ranked.append((score, stability, median, worst_q, j, name))

    ranked.sort(key=lambda x: (-x[0], -x[1], -x[2], x[4]))
    return ranked


def discover_transfer_upto2(dataset, seed):
    calls = 0
    width = len(dataset.probe_names)

    for size in (1, 2):
        survivors = []
        for candidate in itertools.combinations(range(width), size):
            ok, gain, used = qualify_candidate(dataset, candidate, seed)
            calls += used
            if ok:
                survivors.append((gain, candidate))
        if survivors:
            survivors.sort(key=lambda item: (-item[0], item[1]))
            gain, candidate = survivors[0]
            return candidate, gain, calls

    return None, 0.0, calls


def main():
    seed = os.environ.get("REALITYGRAPH_HAR_COMPOUNDING_V2_SEED", "har-v2")
    out = Path(
        os.environ.get(
            "REALITYGRAPH_HAR_COMPOUNDING_V2_RESULT",
            "har-compounding-probe-v2-summary.json",
        )
    )

    full = load_har_full()
    a_groups, b_groups, c_groups = stages(full, seed)
    phase_a_full = subset_groups(full, a_groups)

    ranking = feature_rank(phase_a_full)
    if len(ranking) < RANK_BUDGET:
        raise AssertionError("HAR ranker returned too few features")

    chosen_full = tuple(sorted(item[4] for item in ranking[:RANK_BUDGET]))
    dataset = select_columns(full, chosen_full)
    phase_a = subset_groups(dataset, a_groups)
    phase_b = subset_groups(dataset, b_groups)

    print()
    print("REALITYGRAPH / HAR COMPOUNDING PROBE V2")
    print("---------------------------------------")
    print("representation ranking uses Phase-A subjects only")
    print(f"G1 groups={len(a_groups)} G2 groups={len(b_groups)} future={len(c_groups)}")
    print(f"rank_budget={RANK_BUDGET}")
    print("TOP RANKED")
    for score, stability, median, worst_q, j, name in ranking[:RANK_BUDGET]:
        print(
            f"  {name} score={score:.4f} stability={stability:.3f} "
            f"median_auc={median:.3f} q20_auc={worst_q:.3f}"
        )

    g1, g1_gain, g1_calls = discover_transfer_upto2(
        phase_a, f"{seed}|g1"
    )
    if g1 is None:
        verdict = "HAR_V2_G1_REFUSED"
        out.write_text(json.dumps({
            "source_sha256": EXPECTED_SHA256,
            "verdict": verdict,
        }, indent=2) + "\n")
        print("VERDICT")
        print(verdict)
        return

    original1 = compile_from_discovery(
        phase_a, g1, f"{seed}|g1|compile"
    )
    law1 = model_to_law(
        dataset.source_hashes,
        original1,
        provenance=hashlib.sha256(f"{seed}|g1".encode()).hexdigest()[:12],
    )
    memory1 = exact_restart(model_memory(law1).text())
    matches1 = applicable_transfer_capabilities(
        memory1, dataset.source_hashes, dataset.probe_names
    )
    if len(matches1) != 1:
        raise AssertionError("HAR V2 G1 restart failed")
    model1 = law_to_model(
        only_law(memory1, matches1[0]), dataset.probe_names
    )

    prior = prior_from_phase_a(phase_a)
    base_b = probabilities_from_base(model1, phase_b, prior)

    print(
        f"G1 acquired={[dataset.probe_names[i] for i in g1]} "
        f"mean_gain={g1_gain:.6f} search_calls={g1_calls}"
    )

    g2, g2_gain, warm_calls = discover_residual(
        phase_b,
        base_b,
        f"{seed}|g2|parent={law1.id}",
    )

    cold_b = tuple(prior for _ in phase_b.values)
    cold2, cold_gain, cold_calls = discover_residual(
        phase_b,
        cold_b,
        f"{seed}|g2|cold",
    )

    if g2 is None:
        verdict = "HAR_V2_G1_REAL_BUT_G2_REFUSED"
        summary = {
            "source_sha256": EXPECTED_SHA256,
            "g1_candidate": [dataset.probe_names[i] for i in g1],
            "g1_gain": g1_gain,
            "g1_calls": g1_calls,
            "g2_acquired": False,
            "g2_warm_calls": warm_calls,
            "cold_candidate": (
                None if cold2 is None
                else [dataset.probe_names[i] for i in cold2]
            ),
            "cold_gain": cold_gain,
            "cold_calls": cold_calls,
            "verdict": verdict,
        }
        out.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
        print(
            f"G2 REFUSED warm_calls={warm_calls} "
            f"cold={summary['cold_candidate']} "
            f"cold_gain={cold_gain:.6f} cold_calls={cold_calls}"
        )
        print("VERDICT")
        print(verdict)
        return

    original2 = compile_residual_from_stage(
        phase_b, g2, base_b, f"{seed}|g2|compile"
    )
    law2 = residual_to_law(
        dataset.source_hashes,
        original2,
        parent_law_id=law1.id,
        provenance=hashlib.sha256(
            f"{seed}|g2|{g2}|{g2_gain:.12g}".encode()
        ).hexdigest()[:12],
    )
    memory2 = exact_restart(
        add_residual_to_memory(memory1, law2).text()
    )
    matches2 = applicable_residual_laws(
        memory2, dataset.source_hashes, dataset.probe_names
    )
    if len(matches2) != 1:
        raise AssertionError("HAR V2 G2 restart failed")
    model2 = law_to_residual_model(matches2[0], dataset.probe_names)

    if not exact_residual_restart(
        original2, model2, phase_b, g2, base_b
    ):
        raise AssertionError("HAR V2 residual restart changed predictions")

    parent_deleted = ablate_capability(memory2, law1.id)
    parent_dependency = not applicable_residual_laws(
        parent_deleted, dataset.source_hashes, dataset.probe_names
    )

    print(
        f"G2 acquired={[dataset.probe_names[i] for i in g2]} "
        f"mean_gain={g2_gain:.6f} warm_search_calls={warm_calls}"
    )
    print(
        f"G2 cold_control="
        f"{None if cold2 is None else [dataset.probe_names[i] for i in cold2]} "
        f"gain={cold_gain:.6f} calls={cold_calls}"
    )
    print(f"G2 parent_dependency={parent_dependency}")

    events = []
    all_positive = True
    causal = 0

    for group in c_groups:
        ids = group_indices(dataset, group)
        labels = [dataset.labels[i] for i in ids]
        p1 = [
            model1.predict_values(dataset.values[i], prior)
            for i in ids
        ]
        p2 = [
            model2.predict_values(dataset.values[i], p)
            for i, p in zip(ids, p1)
        ]
        l1 = binary_log_loss(labels, p1)
        l2 = binary_log_loss(labels, p2)
        gain = l1 - l2
        ok = gain > MIN_GAIN
        all_positive &= ok
        causal += int(ok)

        events.append({
            "group": group,
            "rows": len(ids),
            "g1_log_loss": l1,
            "compound_log_loss": l2,
            "g2_gain": gain,
            "causal_child_ablation": ok,
            "future_search_calls": 0,
        })

        print(
            f"future={group} rows={len(ids)} "
            f"G1_LL={l1:.6f} G1+G2_LL={l2:.6f} "
            f"gain={gain:+.6f} child_ablation={ok}"
        )

    gates = {
        "g1_acquired": True,
        "g2_acquired": True,
        "parent_dependency": parent_dependency,
        "all_future_groups_evaluated": len(events) == len(c_groups),
        "all_future_gain_positive": all_positive,
        "causal_child_ablation": causal == len(events),
        "zero_future_search": True,
    }
    passed = all(gates.values())
    verdict = (
        "PASS_EXTERNAL_TWO_GENERATION_CAPABILITY_COMPOUNDING_HAR_V2"
        if passed else
        "FAIL_EXTERNAL_TWO_GENERATION_CAPABILITY_COMPOUNDING_HAR_V2"
    )

    summary = {
        "source_sha256": EXPECTED_SHA256,
        "rank_budget": RANK_BUDGET,
        "g1_groups": a_groups,
        "g2_groups": b_groups,
        "future_groups": c_groups,
        "g1_candidate": [dataset.probe_names[i] for i in g1],
        "g1_gain": g1_gain,
        "g1_calls": g1_calls,
        "g2_candidate": [dataset.probe_names[i] for i in g2],
        "g2_gain": g2_gain,
        "g2_warm_calls": warm_calls,
        "cold_candidate": (
            None if cold2 is None
            else [dataset.probe_names[i] for i in cold2]
        ),
        "cold_gain": cold_gain,
        "cold_calls": cold_calls,
        "events": events,
        "gates": gates,
        "passed": passed,
        "verdict": verdict,
    }
    out.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")

    print()
    print("AGGREGATE")
    for name, ok in gates.items():
        print(f"gate_{name}={int(ok)}")
    print("VERDICT")
    print(verdict)


if __name__ == "__main__":
    main()
