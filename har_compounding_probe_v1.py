from __future__ import annotations

import hashlib
import io
import json
import os
import urllib.request
import zipfile
from pathlib import Path

from compiled_transfer_demo import (
    compile_from_discovery,
    discover_minimal_transfer,
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
from realitygraph.predictive import binary_log_loss
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
EXPECTED_SHA256 = ""
TOP_VARIANCE_FEATURES = 32
MIN_GAIN = 1e-5


def download() -> bytes:
    req = urllib.request.Request(
        HAR_URL,
        headers={"User-Agent": "RealityGraph/1.0 HAR compounding verifier"},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read()
    digest = hashlib.sha256(raw).hexdigest()
    if EXPECTED_SHA256 and digest != EXPECTED_SHA256:
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


def load_har() -> GroupedBinaryDataset:
    raw = download()
    digest = hashlib.sha256(raw).hexdigest()

    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        prefix = "UCI HAR Dataset/"
        features_raw = z.read(prefix + "features.txt").decode()
        feature_names = []
        for line in features_raw.strip().splitlines():
            _, name = line.split(maxsplit=1)
            feature_names.append(name)

        X_train = parse_matrix(
            z.read(prefix + "train/X_train.txt").decode()
        )
        y_train = parse_ints(
            z.read(prefix + "train/y_train.txt").decode()
        )
        s_train = parse_ints(
            z.read(prefix + "train/subject_train.txt").decode()
        )

        X_test = parse_matrix(
            z.read(prefix + "test/X_test.txt").decode()
        )
        y_test = parse_ints(
            z.read(prefix + "test/y_test.txt").decode()
        )
        s_test = parse_ints(
            z.read(prefix + "test/subject_test.txt").decode()
        )

    X = X_train + X_test
    activities = y_train + y_test
    subjects = s_train + s_test

    # Frozen task before looking at any outcomes: distinguish the two
    # mechanically similar locomotion classes, upstairs vs downstairs.
    keep = [i for i, a in enumerate(activities) if a in {2, 3}]
    values_full = [X[i] for i in keep]
    labels = [1 if activities[i] == 2 else 0 for i in keep]
    groups = [f"subject-{subjects[i]:02d}" for i in keep]

    if len(set(groups)) != 30:
        raise AssertionError("HAR subject grouping drift")
    if len(values_full[0]) != 561:
        raise AssertionError("HAR feature width drift")

    # Label-free representation contraction: top-variance features globally
    # within the external task. This does not inspect the target labels.
    means = []
    variances = []
    for j in range(561):
        col = [row[j] for row in values_full]
        mean = sum(col) / len(col)
        var = sum((x - mean) ** 2 for x in col) / len(col)
        means.append(mean)
        variances.append(var)

    chosen = sorted(
        range(561),
        key=lambda j: (-variances[j], j),
    )[:TOP_VARIANCE_FEATURES]
    chosen = tuple(sorted(chosen))

    values = tuple(
        tuple(row[j] for j in chosen)
        for row in values_full
    )
    probe_names = tuple(
        f"{j+1}:{feature_names[j]}"
        for j in chosen
    )

    print(
        f"HAR task rows={len(values)} groups={len(set(groups))} "
        f"probes={len(probe_names)} prevalence={sum(labels)/len(labels):.4f}"
    )
    print("HAR chosen probes")
    for name in probe_names:
        print(" ", name)

    return GroupedBinaryDataset(
        "UCI HAR upstairs-vs-downstairs / subject-separated",
        "10.24432/C54S4K",
        "CC BY 4.0",
        probe_names,
        values,
        tuple(labels),
        tuple(groups),
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


def main():
    seed = os.environ.get("REALITYGRAPH_HAR_COMPOUNDING_SEED", "har-v1")
    out = Path(
        os.environ.get(
            "REALITYGRAPH_HAR_COMPOUNDING_RESULT",
            "har-compounding-probe-v1-summary.json",
        )
    )
    dataset = load_har()
    a_groups, b_groups, c_groups = stages(dataset, seed)
    phase_a = subset_groups(dataset, a_groups)
    phase_b = subset_groups(dataset, b_groups)

    print()
    print("REALITYGRAPH / HAR COMPOUNDING PROBE V1")
    print("---------------------------------------")
    print(f"G1 groups={len(a_groups)} G2 groups={len(b_groups)} future={len(c_groups)}")

    # G1
    candidate1, gain1, calls1 = discover_minimal_transfer(
        phase_a, f"{seed}|g1"
    )
    if candidate1 is None:
        verdict = "HAR_G1_REFUSED"
        out.write_text(json.dumps({"verdict": verdict}, indent=2) + "\n")
        print("VERDICT")
        print(verdict)
        return

    original1 = compile_from_discovery(
        phase_a, candidate1, f"{seed}|g1|compile"
    )
    law1 = model_to_law(
        dataset.source_hashes,
        original1,
        provenance=hashlib.sha256(f"{seed}|g1".encode()).hexdigest()[:12],
    )
    memory1 = exact_restart(model_memory(law1).text())
    match1 = applicable_transfer_capabilities(
        memory1, dataset.source_hashes, dataset.probe_names
    )
    if len(match1) != 1:
        raise AssertionError("HAR G1 restart/applicability failed")
    model1 = law_to_model(
        only_law(memory1, match1[0]), dataset.probe_names
    )
    prior = prior_from_phase_a(phase_a)
    base_b = probabilities_from_base(model1, phase_b, prior)

    print(
        f"G1 acquired={[dataset.probe_names[i] for i in candidate1]} "
        f"mean_gain={gain1:.6f} search_calls={calls1}"
    )

    # G2 residual around G1.
    candidate2, gain2, warm_calls = discover_residual(
        phase_b, base_b, f"{seed}|g2|parent={law1.id}"
    )

    cold_b = tuple(prior for _ in phase_b.values)
    cold2, cold_gain, cold_calls = discover_residual(
        phase_b, cold_b, f"{seed}|g2|cold"
    )

    if candidate2 is None:
        verdict = "HAR_G1_REAL_BUT_G2_RESIDUAL_REFUSED"
        summary = {
            "source_sha256": dataset.source_hashes[0][1],
            "g1_candidate": [dataset.probe_names[i] for i in candidate1],
            "g1_gain": gain1,
            "g1_calls": calls1,
            "g2_acquired": False,
            "warm_calls": warm_calls,
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
            f"cold={summary['cold_candidate']} cold_gain={cold_gain:.6f}"
        )
        print("VERDICT")
        print(verdict)
        return

    original2 = compile_residual_from_stage(
        phase_b,
        candidate2,
        base_b,
        f"{seed}|g2|compile",
    )
    law2 = residual_to_law(
        dataset.source_hashes,
        original2,
        parent_law_id=law1.id,
        provenance=hashlib.sha256(
            f"{seed}|g2|{candidate2}|{gain2:.12g}".encode()
        ).hexdigest()[:12],
    )
    memory2 = exact_restart(
        add_residual_to_memory(memory1, law2).text()
    )
    matches2 = applicable_residual_laws(
        memory2, dataset.source_hashes, dataset.probe_names
    )
    if len(matches2) != 1:
        raise AssertionError("HAR G2 restart/applicability failed")
    model2 = law_to_residual_model(matches2[0], dataset.probe_names)

    if not exact_residual_restart(
        original2, model2, phase_b, candidate2, base_b
    ):
        raise AssertionError("HAR G2 prediction restart failed")

    parent_deleted = ablate_capability(memory2, law1.id)
    parent_dependency = not applicable_residual_laws(
        parent_deleted, dataset.source_hashes, dataset.probe_names
    )

    print(
        f"G2 acquired={[dataset.probe_names[i] for i in candidate2]} "
        f"mean_gain={gain2:.6f} warm_calls={warm_calls}"
    )
    print(
        f"G2 cold_control="
        f"{None if cold2 is None else [dataset.probe_names[i] for i in cold2]} "
        f"gain={cold_gain:.6f} calls={cold_calls}"
    )
    print(f"G2 parent_dependency={parent_dependency}")

    # Prospective future.
    events = []
    all_positive = True
    causal = 0

    for group in c_groups:
        ids = group_indices(dataset, group)
        labels = [dataset.labels[i] for i in ids]
        g1 = [
            model1.predict_values(dataset.values[i], prior)
            for i in ids
        ]
        g12 = [
            model2.predict_values(dataset.values[i], p)
            for i, p in zip(ids, g1)
        ]
        l1 = binary_log_loss(labels, g1)
        l12 = binary_log_loss(labels, g12)
        delta = l1 - l12
        ok = delta > MIN_GAIN
        all_positive &= ok
        causal += int(ok)
        events.append({
            "group": group,
            "rows": len(ids),
            "g1_log_loss": l1,
            "g1_g2_log_loss": l12,
            "gain": delta,
            "causal_child_ablation": ok,
            "future_search_calls": 0,
        })
        print(
            f"future={group} rows={len(ids)} "
            f"G1_LL={l1:.6f} G1+G2_LL={l12:.6f} "
            f"gain={delta:+.6f} child_ablation={ok}"
        )

    gates = {
        "g1_acquired": True,
        "g2_acquired": True,
        "parent_dependency": parent_dependency,
        "future_events": len(events) == len(c_groups),
        "all_future_gain_positive": all_positive,
        "causal_child_ablation": causal == len(events),
        "zero_future_search": True,
    }
    passed = all(gates.values())
    verdict = (
        "PASS_EXTERNAL_TWO_GENERATION_CAPABILITY_COMPOUNDING_HAR_V1"
        if passed else
        "FAIL_EXTERNAL_TWO_GENERATION_CAPABILITY_COMPOUNDING_HAR_V1"
    )

    summary = {
        "source_sha256": dataset.source_hashes[0][1],
        "g1_groups": a_groups,
        "g2_groups": b_groups,
        "future_groups": c_groups,
        "g1_candidate": [dataset.probe_names[i] for i in candidate1],
        "g1_gain": gain1,
        "g1_calls": calls1,
        "g2_candidate": [dataset.probe_names[i] for i in candidate2],
        "g2_gain": gain2,
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
