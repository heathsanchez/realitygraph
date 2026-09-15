from __future__ import annotations

import hashlib
import io
import json
import os
import random
import statistics
import tarfile
import urllib.request
from collections import Counter
from pathlib import Path

from realitygraph.predictive import (
    PredictiveSplit,
    certify_predictive_batch,
    field_from_matrix,
    sealed_group_split,
)

UPSTREAM_REPO = "YanbiaoLab/equational-challenges"
UPSTREAM_COMMIT = "bed33e36c33fca139d902addd8cb77cd4172fe64"
ARCHIVE_URL = (
    "https://codeload.github.com/YanbiaoLab/equational-challenges/tar.gz/"
    + UPSTREAM_COMMIT
)
DATASETS = {
    "wrong-book-3000": (
        "datasets/wrong-book-3000/wrong-book-3000.jsonl",
        "fb1606578ceafcd1019d96733db4c418596f9884952237e72af2579c382ef1f7",
        2983,
    ),
    "wrong-book-3500": (
        "datasets/wrong-book-3500/wrong-book-3500.jsonl",
        "fca0ccfdb31fd2eae5f6669586309130ccb9e591f19a5142aa6604e81f7023f8",
        3500,
    ),
}
EXPECTED_UNIQUE = 3983
EXPECTED_PROOFS = 3412
EXPECTED_RESIDUAL = 571
EXPECTED_WB3500_EXTENSION = 1000


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _download_archive() -> bytes:
    request = urllib.request.Request(
        ARCHIVE_URL,
        headers={"User-Agent": "RealityGraph/1.0 passive pinned-corpus experiment"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def _read_corpus(raw_archive: bytes):
    with tarfile.open(fileobj=io.BytesIO(raw_archive), mode="r:gz") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
        if not members:
            raise ValueError("external archive contains no files")
        root = members[0].name.split("/", 1)[0]
        by_name = {member.name: member for member in members}

        dataset_rows: dict[str, list[dict[str, object]]] = {}
        source_hashes: dict[str, str] = {}
        for name, (relative_path, expected_hash, expected_rows) in DATASETS.items():
            member = by_name.get(f"{root}/{relative_path}")
            if member is None:
                raise ValueError(f"missing pinned dataset: {relative_path}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"cannot read pinned dataset: {relative_path}")
            raw = stream.read()
            digest = _sha256(raw)
            if digest != expected_hash:
                raise ValueError(
                    f"source changed for {name}: expected {expected_hash}, got {digest}"
                )
            rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
            if len(rows) != expected_rows:
                raise ValueError(
                    f"row count changed for {name}: expected {expected_rows}, got {len(rows)}"
                )
            dataset_rows[name] = rows
            source_hashes[name] = digest

        proof_ids = {
            Path(member.name).stem
            for member in members
            if member.name.startswith(f"{root}/proofs/") and member.name.endswith(".lean")
        }

    wb3000_ids = {str(row["id"]) for row in dataset_rows["wrong-book-3000"]}
    wb3500_ids = {str(row["id"]) for row in dataset_rows["wrong-book-3500"]}
    unique: dict[str, dict[str, object]] = {}
    for name in ("wrong-book-3000", "wrong-book-3500"):
        for row in dataset_rows[name]:
            problem_id = str(row["id"])
            if problem_id not in unique:
                unique[problem_id] = dict(row)

    residual_ids = set(unique) - proof_ids
    if len(unique) != EXPECTED_UNIQUE:
        raise ValueError(f"expected {EXPECTED_UNIQUE} unique problems, got {len(unique)}")
    if len(proof_ids) != EXPECTED_PROOFS:
        raise ValueError(f"expected {EXPECTED_PROOFS} proof files, got {len(proof_ids)}")
    if len(residual_ids) != EXPECTED_RESIDUAL:
        raise ValueError(f"expected {EXPECTED_RESIDUAL} residuals, got {len(residual_ids)}")
    extension = wb3500_ids - wb3000_ids
    if len(extension) != EXPECTED_WB3500_EXTENSION:
        raise ValueError(
            f"expected {EXPECTED_WB3500_EXTENSION} WB3500-only problems, got {len(extension)}"
        )

    return (
        tuple(unique.values()),
        proof_ids,
        wb3000_ids,
        extension,
        source_hashes,
        _sha256(raw_archive),
    )


class _Parser:
    def __init__(self, source: str):
        compact = source.replace(" ", "")
        self.tokens: list[str] = []
        i = 0
        while i < len(compact):
            ch = compact[i]
            if ch in "*()":
                self.tokens.append(ch)
                i += 1
                continue
            if ch.isalpha() or ch == "_":
                j = i + 1
                while j < len(compact) and (compact[j].isalnum() or compact[j] == "_"):
                    j += 1
                self.tokens.append(compact[i:j])
                i = j
                continue
            raise ValueError(f"unexpected token {ch!r} in expression {source!r}")
        self.pos = 0

    def parse(self):
        node = self._expr()
        if self.pos != len(self.tokens):
            raise ValueError(f"unparsed tokens: {self.tokens[self.pos:]}")
        return node

    def _expr(self):
        node = self._atom()
        while self.pos < len(self.tokens) and self.tokens[self.pos] == "*":
            self.pos += 1
            node = ("*", node, self._atom())
        return node

    def _atom(self):
        if self.pos >= len(self.tokens):
            raise ValueError("unexpected end of expression")
        token = self.tokens[self.pos]
        if token == "(":
            self.pos += 1
            node = self._expr()
            if self.pos >= len(self.tokens) or self.tokens[self.pos] != ")":
                raise ValueError("missing closing parenthesis")
            self.pos += 1
            return node
        if token in {"*", ")"}:
            raise ValueError(f"unexpected token {token!r}")
        self.pos += 1
        return ("v", token)


def _tree_stats(node):
    if node[0] == "v":
        return {
            "leaves": 1,
            "apps": 0,
            "depth": 0,
            "left_spine": 0,
            "right_spine": 0,
            "cherries": 0,
            "same_var_siblings": 0,
            "root_left_app": 0,
            "root_right_app": 0,
            "vars": Counter({node[1]: 1}),
        }
    left = _tree_stats(node[1])
    right = _tree_stats(node[2])
    left_leaf = node[1][0] == "v"
    right_leaf = node[2][0] == "v"
    return {
        "leaves": left["leaves"] + right["leaves"],
        "apps": 1 + left["apps"] + right["apps"],
        "depth": 1 + max(left["depth"], right["depth"]),
        "left_spine": 1 + left["left_spine"],
        "right_spine": 1 + right["right_spine"],
        "cherries": left["cherries"] + right["cherries"] + int(left_leaf and right_leaf),
        "same_var_siblings": (
            left["same_var_siblings"]
            + right["same_var_siblings"]
            + int(left_leaf and right_leaf and node[1][1] == node[2][1])
        ),
        "root_left_app": int(not left_leaf),
        "root_right_app": int(not right_leaf),
        "vars": left["vars"] + right["vars"],
    }


def _equation_profile(formula: str) -> dict[str, float]:
    if "=" not in formula:
        raise ValueError(f"not an equation: {formula!r}")
    lhs_text, rhs_text = formula.split("=", 1)
    lhs = _tree_stats(_Parser(lhs_text).parse())
    rhs = _tree_stats(_Parser(rhs_text).parse())
    counts = lhs["vars"] + rhs["vars"]
    lhs_vars = set(lhs["vars"])
    rhs_vars = set(rhs["vars"])
    return {
        "lhs_leaves": float(lhs["leaves"]),
        "rhs_leaves": float(rhs["leaves"]),
        "lhs_apps": float(lhs["apps"]),
        "rhs_apps": float(rhs["apps"]),
        "lhs_depth": float(lhs["depth"]),
        "rhs_depth": float(rhs["depth"]),
        "max_depth": float(max(lhs["depth"], rhs["depth"])),
        "total_apps": float(lhs["apps"] + rhs["apps"]),
        "total_leaves": float(lhs["leaves"] + rhs["leaves"]),
        "distinct_vars": float(len(counts)),
        "max_var_multiplicity": float(max(counts.values())),
        "repetition_excess": float(sum(counts.values()) - len(counts)),
        "overlap_vars": float(len(lhs_vars & rhs_vars)),
        "var_multiset_equal": float(lhs["vars"] == rhs["vars"]),
        "lhs_is_var": float(lhs["apps"] == 0),
        "rhs_is_var": float(rhs["apps"] == 0),
        "rhs_left_spine": float(rhs["left_spine"]),
        "rhs_right_spine": float(rhs["right_spine"]),
        "rhs_cherries": float(rhs["cherries"]),
        "rhs_same_var_siblings": float(rhs["same_var_siblings"]),
        "rhs_root_left_app": float(rhs["root_left_app"]),
        "rhs_root_right_app": float(rhs["root_right_app"]),
    }


PROFILE_FEATURES = (
    "lhs_leaves",
    "rhs_leaves",
    "lhs_depth",
    "rhs_depth",
    "max_depth",
    "total_apps",
    "distinct_vars",
    "max_var_multiplicity",
    "repetition_excess",
    "overlap_vars",
    "var_multiset_equal",
    "lhs_is_var",
    "rhs_is_var",
    "rhs_left_spine",
    "rhs_right_spine",
    "rhs_cherries",
    "rhs_same_var_siblings",
    "rhs_root_left_app",
    "rhs_root_right_app",
)

DELTA_FEATURES = (
    "total_apps",
    "total_leaves",
    "max_depth",
    "distinct_vars",
    "max_var_multiplicity",
    "repetition_excess",
    "overlap_vars",
    "rhs_left_spine",
    "rhs_right_spine",
)


def _pair_features(row: dict[str, object]):
    source = _equation_profile(str(row["equation1"]))
    target = _equation_profile(str(row["equation2"]))
    names: list[str] = []
    values: list[float] = []
    for prefix, profile in (("premise", source), ("conclusion", target)):
        for key in PROFILE_FEATURES:
            names.append(f"{prefix}.{key}")
            values.append(profile[key])
    for key in DELTA_FEATURES:
        names.append(f"delta.{key}")
        values.append(target[key] - source[key])
        names.append(f"abs_delta.{key}")
        values.append(abs(target[key] - source[key]))
    names.extend(("same.lhs_is_var", "same.var_multiset_equal"))
    values.extend(
        (
            float(source["lhs_is_var"] == target["lhs_is_var"]),
            float(source["var_multiset_equal"] == target["var_multiset_equal"]),
        )
    )
    return tuple(names), tuple(values), source, target


def _coarse_equation_family(profile: dict[str, float]):
    return (
        int(profile["lhs_is_var"]),
        3 if profile["distinct_vars"] <= 3 else 4,
        2 if profile["max_var_multiplicity"] <= 2 else 3,
        2 if profile["max_depth"] <= 2 else 3,
    )


def _seed_int(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "big")


def _shuffle(values: list[int], seed: str) -> list[int]:
    out = list(values)
    random.Random(_seed_int(seed)).shuffle(out)
    return out


def _certificate_record(certificate, field, split):
    test_labels = [field.labels[i] for i in split.test]
    return {
        "accepted": certificate.accepted,
        "baseline_log_loss": certificate.sealed_baseline_metrics.log_loss,
        "log_loss": certificate.sealed_metrics.log_loss,
        "gain": (
            certificate.sealed_baseline_metrics.log_loss
            - certificate.sealed_metrics.log_loss
        ),
        "auc": certificate.sealed_metrics.auc,
        "max_group_harm": certificate.sealed_metrics.max_group_harm,
        "test_rows": len(split.test),
        "test_residual_rate": sum(test_labels) / len(test_labels),
        "rules": [
            {
                "probe": rule.probe_name,
                "threshold": rule.threshold,
            }
            for rule in certificate.plan.rules
        ],
        "ablation_log_loss_delta": dict(certificate.plan.ablation_log_loss_delta),
    }


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


def _source_future_split(groups, source_indices, future_indices, seed: str):
    source_groups = sorted({groups[i] for i in source_indices}, key=repr)
    if len(source_groups) < 2:
        raise ValueError("source future split needs at least two source groups")
    ordered = sorted(
        source_groups,
        key=lambda group: hashlib.sha256(f"{seed}|{group!r}".encode()).digest(),
    )
    cut = max(1, min(len(ordered) - 1, int(0.75 * len(ordered))))
    train_groups = set(ordered[:cut])
    cal_groups = set(ordered[cut:])
    train = tuple(i for i in source_indices if groups[i] in train_groups)
    calibration = tuple(i for i in source_indices if groups[i] in cal_groups)
    if not train or not calibration or not future_indices:
        raise ValueError("source/future split produced an empty partition")
    return PredictiveSplit(
        train,
        calibration,
        tuple(future_indices),
        hashlib.sha256(seed.encode()).hexdigest()[:16],
    )


def _aggregate(records):
    if not records:
        return {}
    return {
        "replays": len(records),
        "accepted": sum(int(record["accepted"]) for record in records),
        "mean_gain": statistics.fmean(record["gain"] for record in records),
        "median_gain": statistics.median(record["gain"] for record in records),
        "min_gain": min(record["gain"] for record in records),
        "max_gain": max(record["gain"] for record in records),
        "mean_auc": statistics.fmean(record["auc"] for record in records),
        "mean_max_group_harm": statistics.fmean(
            record["max_group_harm"] for record in records
        ),
    }


def main() -> None:
    raw_archive = _download_archive()
    rows, proof_ids, wb3000_ids, future_ids, source_hashes, archive_hash = _read_corpus(
        raw_archive
    )

    feature_names: tuple[str, ...] | None = None
    values: list[tuple[float, ...]] = []
    labels: list[int] = []
    groups: list[object] = []
    ids: list[str] = []
    for row in rows:
        names, vector, source, target = _pair_features(row)
        if feature_names is None:
            feature_names = names
        elif feature_names != names:
            raise ValueError("feature layout changed between rows")
        problem_id = str(row["id"])
        ids.append(problem_id)
        values.append(vector)
        labels.append(int(problem_id not in proof_ids))
        groups.append((_coarse_equation_family(source), _coarse_equation_family(target)))

    if feature_names is None:
        raise ValueError("parsed no problems")

    field = field_from_matrix(feature_names, values, labels, groups)
    structural_real = []
    structural_shuffle = []
    for replay in range(6):
        seed = f"equational-structural-v1-{replay}"
        split = sealed_group_split(groups, seed, train_fraction=0.60, calibration_fraction=0.20)
        certificate = _fit(field, split)
        structural_real.append(_certificate_record(certificate, field, split))

        shuffled_labels = _shuffle(labels, seed + "-shuffle")
        control_field = field_from_matrix(feature_names, values, shuffled_labels, groups)
        control_certificate = _fit(control_field, split)
        structural_shuffle.append(
            _certificate_record(control_certificate, control_field, split)
        )

    source_indices = [i for i, problem_id in enumerate(ids) if problem_id in wb3000_ids]
    future_indices = [i for i, problem_id in enumerate(ids) if problem_id in future_ids]
    future_real = []
    future_shuffle = []
    for replay in range(6):
        seed = f"equational-future-book-v1-{replay}"
        split = _source_future_split(groups, source_indices, future_indices, seed)
        certificate = _fit(field, split)
        future_real.append(_certificate_record(certificate, field, split))

        control_labels = list(labels)
        source_labels = [labels[i] for i in source_indices]
        shuffled_source = _shuffle(source_labels, seed + "-shuffle")
        for i, label in zip(source_indices, shuffled_source):
            control_labels[i] = label
        control_field = field_from_matrix(feature_names, values, control_labels, groups)
        control_certificate = _fit(control_field, split)
        future_shuffle.append(
            _certificate_record(control_certificate, control_field, split)
        )

    group_sizes: dict[object, int] = {}
    for group in groups:
        group_sizes[group] = group_sizes.get(group, 0) + 1
    ordered_sizes = sorted(group_sizes.values())
    result = {
        "experiment": "realitygraph-equational-residual-v1",
        "upstream": {
            "repository": UPSTREAM_REPO,
            "commit": UPSTREAM_COMMIT,
            "acquisition": "anonymous pinned codeload archive; no fork/star/watch/upstream write",
            "archive_sha256": archive_hash,
            "dataset_sha256": source_hashes,
        },
        "corpus": {
            "unique_directed_problems": len(rows),
            "published_proofs": len(proof_ids),
            "public_residuals": sum(labels),
            "wrong_book_3500_only_future": len(future_ids),
            "residual_rate": sum(labels) / len(labels),
        },
        "representation": {
            "feature_count": len(feature_names),
            "features": list(feature_names),
            "group_count": len(group_sizes),
            "group_size_median": statistics.median(ordered_sizes),
            "group_size_max": max(ordered_sizes),
            "note": "Equation IDs and proof text are excluded from probes; groups hold out coarse source/target structural families.",
        },
        "structural_family_holdout": {
            "real": _aggregate(structural_real),
            "shuffled_control": _aggregate(structural_shuffle),
            "paired_gain_advantage": statistics.fmean(
                real["gain"] - control["gain"]
                for real, control in zip(structural_real, structural_shuffle)
            ),
            "real_replays": structural_real,
            "control_replays": structural_shuffle,
        },
        "wrong_book_future_transfer": {
            "design_source": "Wrong Book 3000 only",
            "sealed_future": "1,000-problem Wrong Book 3500-only extension",
            "real": _aggregate(future_real),
            "shuffled_source_control": _aggregate(future_shuffle),
            "paired_gain_advantage": statistics.fmean(
                real["gain"] - control["gain"]
                for real, control in zip(future_real, future_shuffle)
            ),
            "real_replays": future_real,
            "control_replays": future_shuffle,
        },
    }

    result["signal"] = {
        "structural_boundary_transfer": (
            result["structural_family_holdout"]["real"]["mean_gain"] > 0
            and result["structural_family_holdout"]["paired_gain_advantage"] > 0
        ),
        "future_collection_transfer": (
            result["wrong_book_future_transfer"]["real"]["mean_gain"] > 0
            and result["wrong_book_future_transfer"]["paired_gain_advantage"] > 0
        ),
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    output = Path(
        os.environ.get(
            "REALITYGRAPH_EQUATIONAL_RESULT",
            "results/equational-residual-v1.json",
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
