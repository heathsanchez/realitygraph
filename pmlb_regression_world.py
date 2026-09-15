from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path

from pmlb_meta_world import (
    DATA_URL,
    DESCRIPTOR_NAMES,
    PMLB_COMMIT,
    SUMMARY_URL,
    _descriptors,
    _download,
    _evaluate_feature,
    _parse_dataset,
    _sample_and_cap,
    _stratified_split,
)

REGRESSION_CORPUS_SEED = "realitygraph-pmlb-regression-transfer-v1"


def _hash(value: str) -> bytes:
    return hashlib.sha256(
        f"{REGRESSION_CORPUS_SEED}|{value}".encode()
    ).digest()


def regression_manifest(summary_raw: bytes) -> list[dict]:
    reader = csv.DictReader(
        io.StringIO(summary_raw.decode("utf-8")),
        delimiter="\t",
    )
    eligible = []
    for row in reader:
        if row.get("task") != "regression":
            continue
        name = row["dataset"]
        if name.startswith("_deprecated_"):
            continue
        try:
            n = int(float(row["n_instances"]))
            f = int(float(row["n_features"]))
        except (TypeError, ValueError):
            continue
        if not (80 <= n <= 20000):
            continue
        if not (2 <= f <= 180):
            continue
        eligible.append({
            "dataset": name,
            "n_instances": n,
            "n_features": f,
        })

    eligible.sort(
        key=lambda row: (_hash(row["dataset"]), row["dataset"])
    )
    if len(eligible) < 40:
        raise AssertionError(
            f"regression eligibility produced only {len(eligible)} datasets"
        )
    return eligible[:40]


def _balanced_binary_labels(targets: list[float]) -> tuple[list[int], float]:
    unique = sorted(set(targets))
    if len(unique) < 2:
        raise ValueError("regression target has fewer than two distinct values")

    best = None
    n = len(targets)
    for left, right in zip(unique, unique[1:]):
        threshold = (left + right) / 2.0
        positives = sum(value >= threshold for value in targets)
        if positives == 0 or positives == n:
            continue
        key = (abs(positives / n - 0.5), threshold)
        if best is None or key < best[0]:
            best = (key, threshold)

    if best is None:
        raise ValueError("could not construct non-degenerate binary target")

    threshold = best[1]
    labels = [int(value >= threshold) for value in targets]
    return labels, threshold


def main():
    index = int(os.environ["REALITYGRAPH_PMLB_REGRESSION_INDEX"])
    out_path = Path(
        os.environ.get(
            "REALITYGRAPH_PMLB_REGRESSION_RESULT",
            f"results/pmlb-regression-world-{index:03d}.json",
        )
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    summary_raw = _download(SUMMARY_URL)
    summary_sha = hashlib.sha256(summary_raw).hexdigest()
    manifest = regression_manifest(summary_raw)
    if not 0 <= index < len(manifest):
        raise ValueError("regression world index outside manifest")

    meta = manifest[index]
    name = meta["dataset"]
    raw = _download(DATA_URL.format(name=name))
    source_sha = hashlib.sha256(raw).hexdigest()
    feature_names, rows, targets = _parse_dataset(raw)
    labels, target_threshold = _balanced_binary_labels(targets)

    anon_names, rows, labels = _sample_and_cap(
        name,
        feature_names,
        rows,
        labels,
    )
    train, calibration, test = _stratified_split(name, labels)

    features = []
    for feature in range(len(anon_names)):
        train_values = [rows[i][feature] for i in train]
        train_labels = [labels[i] for i in train]
        descriptors = _descriptors(
            train_values,
            train_labels,
            name,
            feature,
        )
        evaluation = _evaluate_feature(
            rows,
            labels,
            feature,
            train,
            calibration,
            test,
        )
        features.append({
            "feature": feature,
            "descriptors": list(descriptors),
            **evaluation,
        })

    best = max(
        features,
        key=lambda item: (item["cal_gain"], -item["feature"]),
    )
    cold_false_law = (
        best["cal_gain"] > 1e-4
        and best["test_gain"] <= 1e-4
    )

    result = {
        "index": index,
        "role": "heldout-regression",
        "source_task": "regression",
        "dataset": name,
        "pmlb_commit": PMLB_COMMIT,
        "summary_sha256": summary_sha,
        "source_sha256": source_sha,
        "rows": len(rows),
        "features": len(anon_names),
        "target_threshold": target_threshold,
        "positive_rate": sum(labels) / len(labels),
        "train_rows": len(train),
        "calibration_rows": len(calibration),
        "test_rows": len(test),
        "descriptor_names": list(DESCRIPTOR_NAMES),
        "candidates": features,
        "cold_best_feature": best["feature"],
        "cold_best_cal_gain": best["cal_gain"],
        "cold_best_test_gain": best["test_gain"],
        "cold_false_law": cold_false_law,
        "cold_search_cost": sum(
            item["threshold_evals"] for item in features
        ),
    }
    out_path.write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n"
    )

    print(
        f"PMLB_REGRESSION_WORLD index={index:03d} dataset={name} "
        f"rows={len(rows)} features={len(anon_names)} "
        f"positive_rate={result['positive_rate']:.4f}"
    )
    print(
        f"cold_best=f{best['feature']} "
        f"cal_gain={best['cal_gain']:.6f} "
        f"test_gain={best['test_gain']:.6f} "
        f"false_law={cold_false_law} "
        f"search_cost={result['cold_search_cost']}"
    )
    print(
        f"source_sha256={source_sha} "
        f"summary_sha256={summary_sha} out={out_path}"
    )


if __name__ == "__main__":
    main()
