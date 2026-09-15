from __future__ import annotations

import hashlib
import io
import itertools
import json
import math
import random
import re
import statistics
import tarfile
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from equational_residual_demo import (
    UPSTREAM_COMMIT,
    _Parser,
    _coarse_equation_family,
    _download_archive,
    _equation_profile,
    _pair_features,
    _read_corpus,
)
from realitygraph.predictive import (
    binary_auc,
    certify_predictive_batch,
    field_from_matrix,
    sealed_group_split,
)

CHECKPOINT_A = "cd825390fd55e30a425a799983406a4abb4547a5"
CHECKPOINT_B = "9ff9cd90d3875e59f213064374764b95f8c2df54"
CHECKPOINT_C = UPSTREAM_COMMIT
EXPECTED_COUNTS = {
    CHECKPOINT_A: 2774,
    CHECKPOINT_B: 3337,
    CHECKPOINT_C: 3412,
}


def _archive_url(commit: str) -> str:
    return f"https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/{commit}"


def _download(commit: str) -> bytes:
    request = urllib.request.Request(
        _archive_url(commit),
        headers={"User-Agent": "RealityGraph/1.0 passive developmental-transition experiment"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def _archive_files(raw: bytes) -> dict[str, bytes]:
    out: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        if not members:
            raise ValueError("empty archive")
        root = members[0].name.split("/", 1)[0] + "/"
        for member in members:
            stream = archive.extractfile(member)
            if stream is None:
                continue
            relative = member.name[len(root):]
            out[relative] = stream.read()
    return out


def _proof_ids(files: dict[str, bytes]) -> set[str]:
    return {
        Path(path).stem
        for path in files
        if path.startswith("proofs/") and path.endswith(".lean")
    }


def _proof_mechanism(raw: bytes) -> tuple[str, str | None, str]:
    text = raw.decode("utf-8", errors="replace")
    verdict_match = re.search(r"-- Recorded verdict:\s*(true|false)", text)
    verdict = verdict_match.group(1) if verdict_match else "unknown"
    stage_match = re.search(r"^-- stage:([^\r\n]+)", text, flags=re.MULTILINE)
    stage = stage_match.group(1).strip() if stage_match else None

    if verdict == "false":
        if re.search(r"\bFin\s+\d+", text) and "decide" in text:
            family = "finite_decide_countermodel"
        elif "noncomputable def" in text or "noncomputable instance" in text:
            family = "constructed_countermodel"
        else:
            family = "countermodel_other"
    elif verdict == "true":
        if "congrArg" not in text and ".trans" not in text and "\n  calc" not in text:
            family = "direct_or_specialization_proof"
        else:
            family = "equational_derivation"
    else:
        family = "unknown"
    return family, stage, verdict


def _build_feature_table(rows):
    feature_names = None
    vectors = {}
    groups = {}
    profiles = {}
    for row in rows:
        names, values, source, target = _pair_features(row)
        if feature_names is None:
            feature_names = names
        elif feature_names != names:
            raise ValueError("feature layout drift")
        problem_id = str(row["id"])
        vectors[problem_id] = values
        groups[problem_id] = (
            _coarse_equation_family(source),
            _coarse_equation_family(target),
        )
        profiles[problem_id] = (source, target)
    if feature_names is None:
        raise ValueError("no feature rows")
    return feature_names, vectors, groups, profiles


def _field(ids, vectors, groups, labels, feature_names):
    return field_from_matrix(
        feature_names,
        [vectors[problem_id] for problem_id in ids],
        [labels[problem_id] for problem_id in ids],
        [groups[problem_id] for problem_id in ids],
    )


def _fit(field, split):
    return certify_predictive_batch(
        field,
        split,
        max_probes=8,
        max_thresholds=31,
        min_calibration_gain=1e-4,
        min_sealed_gain=1e-4,
        min_support=8,
    )


def _shuffle_labels(labels, seed: str):
    out = list(labels)
    random.Random(int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8], "big")).shuffle(out)
    return out


def _scores(model, field):
    return [model.predict_values(row) for row in field.values]


def _enrichment(labels, scores, k):
    k = min(k, len(labels))
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    base = sum(labels) / len(labels)
    hit_rate = sum(labels[i] for i in order) / k
    return {
        "k": k,
        "hits": sum(labels[i] for i in order),
        "hit_rate": hit_rate,
        "base_rate": base,
        "enrichment": hit_rate / base if base else 0.0,
    }


def _transition_replays(
    source_ids,
    source_labels,
    target_ids,
    target_labels,
    vectors,
    groups,
    feature_names,
    prefix,
    replays=12,
):
    source_field = _field(source_ids, vectors, groups, source_labels, feature_names)
    target_field = _field(target_ids, vectors, groups, target_labels, feature_names)
    real = []
    control = []
    models = []
    for replay in range(replays):
        seed = f"{prefix}-{replay}"
        split = sealed_group_split(
            source_field.groups,
            seed,
            train_fraction=0.62,
            calibration_fraction=0.20,
        )
        cert = _fit(source_field, split)
        scores = _scores(cert.model, target_field)
        record = {
            "replay": replay,
            "source_internal_accepted": cert.accepted,
            "source_internal_auc": cert.sealed_metrics.auc,
            "source_internal_gain": (
                cert.sealed_baseline_metrics.log_loss - cert.sealed_metrics.log_loss
            ),
            "target_auc": binary_auc(target_field.labels, scores),
            "top75": _enrichment(target_field.labels, scores, 75),
            "top150": _enrichment(target_field.labels, scores, 150),
            "rules": [rule.probe_name for rule in cert.plan.rules],
        }
        real.append(record)
        models.append(cert.model)

        shuffled = _shuffle_labels(list(source_field.labels), seed + "-shuffle")
        control_field = field_from_matrix(
            feature_names,
            source_field.values,
            shuffled,
            source_field.groups,
        )
        control_cert = _fit(control_field, split)
        control_scores = _scores(control_cert.model, target_field)
        control.append(
            {
                "replay": replay,
                "target_auc": binary_auc(target_field.labels, control_scores),
                "top75": _enrichment(target_field.labels, control_scores, 75),
                "top150": _enrichment(target_field.labels, control_scores, 150),
                "rules": [rule.probe_name for rule in control_cert.plan.rules],
            }
        )
    return source_field, target_field, real, control, models


def _internal_replays(
    ids,
    labels,
    vectors,
    groups,
    feature_names,
    prefix,
    replays=12,
):
    field = _field(ids, vectors, groups, labels, feature_names)
    real = []
    control = []
    models = []
    for replay in range(replays):
        seed = f"{prefix}-{replay}"
        split = sealed_group_split(
            field.groups,
            seed,
            train_fraction=0.62,
            calibration_fraction=0.20,
        )
        cert = _fit(field, split)
        real.append(
            {
                "replay": replay,
                "accepted": cert.accepted,
                "auc": cert.sealed_metrics.auc,
                "gain": cert.sealed_baseline_metrics.log_loss - cert.sealed_metrics.log_loss,
                "rules": [rule.probe_name for rule in cert.plan.rules],
            }
        )
        models.append(cert.model)

        shuffled = _shuffle_labels(list(field.labels), seed + "-shuffle")
        control_field = field_from_matrix(
            feature_names,
            field.values,
            shuffled,
            field.groups,
        )
        control_cert = _fit(control_field, split)
        control.append(
            {
                "replay": replay,
                "accepted": control_cert.accepted,
                "auc": control_cert.sealed_metrics.auc,
                "gain": (
                    control_cert.sealed_baseline_metrics.log_loss
                    - control_cert.sealed_metrics.log_loss
                ),
                "rules": [rule.probe_name for rule in control_cert.plan.rules],
            }
        )
    return field, real, control, models


def _summary(records, key):
    values = [record[key] for record in records]
    return {
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
    }


def _rule_frequency(records):
    counts = Counter()
    for record in records:
        counts.update(record["rules"])
    return counts.most_common()


def _match(pattern, target, subst):
    if pattern[0] == "v":
        name = pattern[1]
        previous = subst.get(name)
        if previous is None:
            subst[name] = target
            return True
        return previous == target
    if target[0] != "*":
        return False
    return _match(pattern[1], target[1], subst) and _match(pattern[2], target[2], subst)


def _term_text(node):
    if node[0] == "v":
        return node[1]
    return f"({_term_text(node[1])} * {_term_text(node[2])})"


def _specialization_certificate(row):
    s_l, s_r = [part.strip() for part in str(row["equation1"]).split("=", 1)]
    t_l, t_r = [part.strip() for part in str(row["equation2"]).split("=", 1)]
    source = (_Parser(s_l).parse(), _Parser(s_r).parse())
    target = (_Parser(t_l).parse(), _Parser(t_r).parse())
    for orientation, pair in (
        ("direct", target),
        ("symmetric", (target[1], target[0])),
    ):
        subst = {}
        if _match(source[0], pair[0], subst) and _match(source[1], pair[1], subst):
            return {
                "orientation": orientation,
                "substitution": {name: _term_text(term) for name, term in sorted(subst.items())},
            }
    return None


def _eval_term(node, env, table, n):
    if node[0] == "v":
        return env[node[1]]
    a = _eval_term(node[1], env, table, n)
    b = _eval_term(node[2], env, table, n)
    return table[a * n + b]


def _identity_holds(parsed, table, n):
    lhs, rhs, variables = parsed
    for values in itertools.product(range(n), repeat=len(variables)):
        env = dict(zip(variables, values))
        if _eval_term(lhs, env, table, n) != _eval_term(rhs, env, table, n):
            return False
    return True


def _identity_witness_failure(parsed, table, n):
    lhs, rhs, variables = parsed
    for values in itertools.product(range(n), repeat=len(variables)):
        env = dict(zip(variables, values))
        lv = _eval_term(lhs, env, table, n)
        rv = _eval_term(rhs, env, table, n)
        if lv != rv:
            return {"assignment": env, "lhs": lv, "rhs": rv}
    return None


def _parse_identity(formula):
    lhs_text, rhs_text = [part.strip() for part in str(formula).split("=", 1)]
    lhs = _Parser(lhs_text).parse()
    rhs = _Parser(rhs_text).parse()
    variables = tuple(sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", str(formula)))))
    return lhs, rhs, variables


def _order2_countermodel(row):
    source = _parse_identity(row["equation1"])
    target = _parse_identity(row["equation2"])
    for table in itertools.product(range(2), repeat=4):
        if not _identity_holds(source, table, 2):
            continue
        witness = _identity_witness_failure(target, table, 2)
        if witness is not None:
            return {"table": list(table), "target_witness": witness}
    return None


def _zscore_parameters(vectors, ids):
    width = len(vectors[ids[0]])
    means = []
    scales = []
    for j in range(width):
        column = [vectors[problem_id][j] for problem_id in ids]
        mean = statistics.fmean(column)
        variance = statistics.fmean((value - mean) ** 2 for value in column)
        means.append(mean)
        scales.append(math.sqrt(variance) if variance > 1e-12 else 1.0)
    return means, scales


def _distance(a, b, means, scales):
    return sum(((x - y) / s) ** 2 for x, y, s in zip(a, b, scales))


def _route_current(current_ids, donor_ids, mechanisms, vectors, all_ids):
    means, scales = _zscore_parameters(vectors, all_ids)
    routed = {}
    for problem_id in current_ids:
        distances = []
        for donor in donor_ids:
            d = _distance(vectors[problem_id], vectors[donor], means, scales)
            distances.append((d, donor))
        nearest = sorted(distances)[:9]
        votes = Counter(mechanisms[donor] for _, donor in nearest)
        family, count = votes.most_common(1)[0]
        routed[problem_id] = {
            "family": family,
            "votes": count,
            "neighbors": [
                {"id": donor, "family": mechanisms[donor], "distance": distance}
                for distance, donor in nearest[:5]
            ],
        }
    return routed


def main():
    final_raw = _download_archive()
    rows, final_proofs, _, _, source_hashes, final_archive_hash = _read_corpus(final_raw)
    final_files = _archive_files(final_raw)

    checkpoint_files = {}
    proof_sets = {}
    archive_hashes = {}
    for commit in (CHECKPOINT_A, CHECKPOINT_B):
        raw = _download(commit)
        checkpoint_files[commit] = _archive_files(raw)
        proof_sets[commit] = _proof_ids(checkpoint_files[commit])
        archive_hashes[commit] = hashlib.sha256(raw).hexdigest()
    proof_sets[CHECKPOINT_C] = final_proofs
    archive_hashes[CHECKPOINT_C] = final_archive_hash

    for commit, expected in EXPECTED_COUNTS.items():
        actual = len(proof_sets[commit])
        if actual != expected:
            raise ValueError(f"checkpoint {commit}: expected {expected} proofs, got {actual}")

    all_ids = {str(row["id"]) for row in rows}
    if not proof_sets[CHECKPOINT_A] <= proof_sets[CHECKPOINT_B] <= proof_sets[CHECKPOINT_C]:
        raise ValueError("proof chronology is not nested")

    a = proof_sets[CHECKPOINT_A]
    b = proof_sets[CHECKPOINT_B]
    c = proof_sets[CHECKPOINT_C]
    wave1 = b - a
    wave2 = c - b
    residual_a = sorted(all_ids - a)
    residual_b = sorted(all_ids - b)
    residual_c = sorted(all_ids - c)
    if (len(wave1), len(wave2), len(residual_a), len(residual_b), len(residual_c)) != (
        563,
        75,
        1209,
        646,
        571,
    ):
        raise ValueError("unexpected developmental wave counts")

    feature_names, vectors, groups, profiles = _build_feature_table(rows)

    labels_a = {problem_id: int(problem_id in wave1) for problem_id in residual_a}
    labels_b = {problem_id: int(problem_id in wave2) for problem_id in residual_b}

    field_a, field_b, continuation_real, continuation_control, continuation_models = (
        _transition_replays(
            residual_a,
            labels_a,
            residual_b,
            labels_b,
            vectors,
            groups,
            feature_names,
            "equational-wave1-to-wave2-v1",
        )
    )

    _, wave2_internal_real, wave2_internal_control, wave2_models = _internal_replays(
        residual_b,
        labels_b,
        vectors,
        groups,
        feature_names,
        "equational-wave2-internal-v1",
    )

    current_field = field_from_matrix(
        feature_names,
        [vectors[problem_id] for problem_id in residual_c],
        [0 for _ in residual_c],
        [groups[problem_id] for problem_id in residual_c],
    )
    current_scores = []
    for i, problem_id in enumerate(residual_c):
        scores = [model.predict_values(current_field.values[i]) for model in wave2_models]
        current_scores.append(
            {
                "id": problem_id,
                "mean_score": statistics.fmean(scores),
                "score_sd": statistics.pstdev(scores),
            }
        )
    current_scores.sort(key=lambda item: (-item["mean_score"], item["score_sd"], item["id"]))

    mechanism = {}
    stages_wave1 = Counter()
    stages_wave2 = Counter()
    families_wave1 = Counter()
    families_wave2 = Counter()
    verdicts_wave1 = Counter()
    verdicts_wave2 = Counter()
    for label, ids, stage_counter, family_counter, verdict_counter in (
        ("wave1", wave1, stages_wave1, families_wave1, verdicts_wave1),
        ("wave2", wave2, stages_wave2, families_wave2, verdicts_wave2),
    ):
        for problem_id in ids:
            path = f"proofs/{problem_id}.lean"
            raw = final_files.get(path)
            if raw is None:
                raise ValueError(f"missing final proof for {problem_id}")
            family, stage, verdict = _proof_mechanism(raw)
            mechanism[problem_id] = family
            family_counter[family] += 1
            verdict_counter[verdict] += 1
            if stage:
                stage_counter[stage] += 1

    donors = sorted(wave1 | wave2)
    routed = _route_current(residual_c, donors, mechanism, vectors, sorted(all_ids))
    route_counts = Counter(item["family"] for item in routed.values())

    exact_specializations = {}
    exact_order2 = {}
    rows_by_id = {str(row["id"]): row for row in rows}
    for problem_id in residual_c:
        row = rows_by_id[problem_id]
        specialization = _specialization_certificate(row)
        if specialization is not None:
            exact_specializations[problem_id] = specialization
        countermodel = _order2_countermodel(row)
        if countermodel is not None:
            exact_order2[problem_id] = countermodel

    probe_frequency_continuation = _rule_frequency(continuation_real)
    probe_frequency_wave2 = _rule_frequency(wave2_internal_real)

    top_priority = []
    for item in current_scores[:40]:
        problem_id = item["id"]
        source, target = profiles[problem_id]
        top_priority.append(
            {
                **item,
                "route": routed[problem_id],
                "premise_repetition_excess": source["repetition_excess"],
                "premise_rhs_right_spine": source["rhs_right_spine"],
                "premise_rhs_cherries": source["rhs_cherries"],
                "delta_total_apps": target["total_apps"] - source["total_apps"],
            }
        )

    result = {
        "experiment": "realitygraph-equational-development-transition-v1",
        "upstream": {
            "checkpoints": {
                "wave0": CHECKPOINT_A,
                "wave1": CHECKPOINT_B,
                "wave2": CHECKPOINT_C,
            },
            "proof_counts": {
                "wave0": len(a),
                "wave1": len(b),
                "wave2": len(c),
            },
            "archive_sha256": archive_hashes,
            "acquisition": "anonymous pinned codeload archives; no fork/star/watch/upstream write",
            "dataset_sha256": source_hashes,
        },
        "chronology": {
            "wave1_new_certificates": len(wave1),
            "wave2_new_certificates": len(wave2),
            "residual_after_wave0": len(residual_a),
            "residual_after_wave1": len(residual_b),
            "current_residual": len(residual_c),
        },
        "wave1_predicts_wave2": {
            "real_target_auc": _summary(continuation_real, "target_auc"),
            "shuffled_target_auc": _summary(continuation_control, "target_auc"),
            "paired_auc_advantage_mean": statistics.fmean(
                real["target_auc"] - control["target_auc"]
                for real, control in zip(continuation_real, continuation_control)
            ),
            "real_top75_enrichment_mean": statistics.fmean(
                record["top75"]["enrichment"] for record in continuation_real
            ),
            "control_top75_enrichment_mean": statistics.fmean(
                record["top75"]["enrichment"] for record in continuation_control
            ),
            "source_internal_accepts": sum(
                int(record["source_internal_accepted"]) for record in continuation_real
            ),
            "probe_frequency": probe_frequency_continuation,
            "replays": continuation_real,
            "control_replays": continuation_control,
        },
        "wave2_boundary_learnability": {
            "real_auc": _summary(wave2_internal_real, "auc"),
            "control_auc": _summary(wave2_internal_control, "auc"),
            "real_gain": _summary(wave2_internal_real, "gain"),
            "control_gain": _summary(wave2_internal_control, "gain"),
            "accepted": sum(int(record["accepted"]) for record in wave2_internal_real),
            "control_accepted": sum(
                int(record["accepted"]) for record in wave2_internal_control
            ),
            "probe_frequency": probe_frequency_wave2,
        },
        "mechanism_history": {
            "wave1_family_counts": dict(families_wave1),
            "wave2_family_counts": dict(families_wave2),
            "wave1_verdict_counts": dict(verdicts_wave1),
            "wave2_verdict_counts": dict(verdicts_wave2),
            "wave1_stage_counts": dict(stages_wave1.most_common()),
            "wave2_stage_counts": dict(stages_wave2.most_common()),
        },
        "current_571": {
            "route_counts": dict(route_counts),
            "top_priority": top_priority,
            "exact_direct_specializations": exact_specializations,
            "exact_order2_countermodels": exact_order2,
            "exact_collapsed": len(set(exact_specializations) | set(exact_order2)),
        },
    }
    result["signal"] = {
        "development_direction_transfers": (
            result["wave1_predicts_wave2"]["real_target_auc"]["mean"] > 0.5
            and result["wave1_predicts_wave2"]["paired_auc_advantage_mean"] > 0.05
        ),
        "wave2_boundary_is_structured": (
            result["wave2_boundary_learnability"]["real_auc"]["mean"]
            > result["wave2_boundary_learnability"]["control_auc"]["mean"] + 0.05
        ),
        "cheapest_capabilities_collapse_current_residual": result["current_571"][
            "exact_collapsed"
        ]
        > 0,
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    path = Path("results/equational-development-transition-v1.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
