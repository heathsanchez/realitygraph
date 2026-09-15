from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import os
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path


PMLB_COMMIT = "7c1f4bdc00136dc2e55c87fa6b8ba6e8af6d1a68"
SUMMARY_URL = (
    "https://raw.githubusercontent.com/EpistasisLab/pmlb/"
    f"{PMLB_COMMIT}/pmlb/all_summary_stats.tsv"
)
DATA_URL = (
    "https://github.com/EpistasisLab/pmlb/raw/"
    f"{PMLB_COMMIT}/datasets/{{name}}/{{name}}.tsv.gz"
)
CORPUS_SEED = "realitygraph-pmlb-meta-v1"
DESCRIPTOR_NAMES = (
    "effect_size",
    "abs_correlation",
    "median_gap",
    "sign_stability",
    "unique_ratio",
    "split_balance",
)


def _download(url: str, attempts: int = 4, timeout: int = 45) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "RealityGraph/1.0 meta-policy experiment"},
    )
    last = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (TimeoutError, OSError, urllib.error.URLError) as exc:
            last = exc
            if attempt + 1 < attempts:
                import time
                time.sleep(2 ** attempt)
    raise RuntimeError(f"download failed: {url}") from last


def _hash(seed: str, value: str) -> bytes:
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()


def corpus_manifest(summary_raw: bytes) -> list[dict]:
    reader = csv.DictReader(io.StringIO(summary_raw.decode("utf-8")), delimiter="\t")
    primary = []
    extension = []
    for row in reader:
        if row.get("task") != "classification":
            continue
        name = row["dataset"]
        if name.startswith("_deprecated_"):
            continue
        try:
            n = int(float(row["n_instances"]))
            f = int(float(row["n_features"]))
            c = int(float(row["n_classes"]))
        except (TypeError, ValueError):
            continue
        meta = {
            "dataset": name,
            "n_instances": n,
            "n_features": f,
            "n_classes": c,
        }
        if 80 <= n <= 20000 and 2 <= f <= 180 and 2 <= c <= 26:
            primary.append(meta)
        elif 40 <= n <= 100000 and 2 <= f <= 1000 and 2 <= c <= 100:
            extension.append(meta)

    def order_key(row):
        return (_hash(CORPUS_SEED, row["dataset"]), row["dataset"])

    primary.sort(key=order_key)
    extension.sort(key=order_key)
    if len(primary) != 126:
        raise AssertionError(
            f"frozen PMLB primary corpus drifted: expected 126, got {len(primary)}"
        )
    eligible = primary + extension
    if len(eligible) < 140:
        raise AssertionError(
            f"extended PMLB eligibility produced only {len(eligible)} datasets"
        )
    return eligible[:140]

def _parse_dataset(raw_gz: bytes) -> tuple[list[str], list[list[float]], list[float]]:
    text = gzip.decompress(raw_gz).decode("utf-8")
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    header = next(reader)
    if "target" not in header:
        raise ValueError("PMLB dataset lacks target column")
    target_i = header.index("target")
    feature_names = [name for i, name in enumerate(header) if i != target_i]
    rows = []
    targets = []

    for row in reader:
        if not row or target_i >= len(row):
            continue
        try:
            target = float(row[target_i])
        except (ValueError, TypeError):
            continue
        if not math.isfinite(target):
            continue

        values = []
        for i in range(len(header)):
            if i == target_i:
                continue
            cell = row[i].strip() if i < len(row) else ""
            try:
                value = float(cell) if cell != "" else float("nan")
            except ValueError:
                value = float("nan")
            values.append(value)
        rows.append(values)
        targets.append(target)

    if len(rows) < 20:
        raise ValueError("too few target-valid rows")

    keep = []
    medians = {}
    for j in range(len(feature_names)):
        finite = sorted(
            row[j] for row in rows
            if j < len(row) and math.isfinite(row[j])
        )
        if not finite:
            continue
        keep.append(j)
        medians[j] = finite[len(finite) // 2]

    if len(keep) < 2:
        raise ValueError("fewer than two usable feature columns")

    cleaned = []
    for row in rows:
        cleaned.append([
            row[j] if math.isfinite(row[j]) else medians[j]
            for j in keep
        ])
    return [feature_names[j] for j in keep], cleaned, targets


def _binary_labels(targets: list[float]) -> list[int]:
    counts = Counter(targets)
    classes = sorted(counts)
    if len(classes) < 2:
        raise ValueError("classification dataset has fewer than two classes")
    if len(classes) == 2:
        positive = classes[1]
    else:
        total = len(targets)
        positive = min(
            classes,
            key=lambda cls: (abs(counts[cls] / total - 0.5), cls),
        )
    labels = [int(value == positive) for value in targets]
    positives = sum(labels)
    if positives == 0 or positives == len(labels):
        raise ValueError("binary reduction collapsed target")
    return labels


def _sample_and_cap(
    name: str,
    feature_names: list[str],
    rows: list[list[float]],
    labels: list[int],
    *,
    max_rows: int = 1000,
    max_features: int = 32,
):
    indices = list(range(len(rows)))
    indices.sort(key=lambda i: _hash(f"{CORPUS_SEED}|rows|{name}", str(i)))
    indices = sorted(indices[:max_rows])

    feature_indices = list(range(len(feature_names)))
    feature_indices.sort(
        key=lambda j: _hash(
            f"{CORPUS_SEED}|features|{name}",
            f"{j}|{feature_names[j]}",
        )
    )
    feature_indices = sorted(feature_indices[:max_features])

    sampled_rows = [
        [rows[i][j] for j in feature_indices]
        for i in indices
    ]
    sampled_labels = [labels[i] for i in indices]
    anon_names = [f"f{k}" for k in range(len(feature_indices))]
    return anon_names, sampled_rows, sampled_labels


def _stratified_split(name: str, labels: list[int]):
    by_label = {0: [], 1: []}
    for i, label in enumerate(labels):
        by_label[label].append(i)

    train, calibration, test = [], [], []
    for label, members in by_label.items():
        ordered = sorted(
            members,
            key=lambda i: _hash(
                f"{CORPUS_SEED}|split|{name}|{label}",
                str(i),
            ),
        )
        n = len(ordered)
        n_train = max(1, int(0.60 * n))
        n_cal = max(1, int(0.20 * n))
        if n_train + n_cal >= n:
            n_cal = max(1, n - n_train - 1)
        train.extend(ordered[:n_train])
        calibration.extend(ordered[n_train:n_train + n_cal])
        test.extend(ordered[n_train + n_cal:])
    if not train or not calibration or not test:
        raise ValueError("empty PMLB partition")
    return tuple(sorted(train)), tuple(sorted(calibration)), tuple(sorted(test))


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _variance(values, mean):
    return sum((value - mean) ** 2 for value in values) / max(len(values), 1)


def _correlation(xs: list[float], ys: list[int]) -> float:
    mx = _mean(xs)
    my = _mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 1e-18 or vy <= 1e-18:
        return 0.0
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / math.sqrt(vx * vy)


def _descriptors(values: list[float], labels: list[int], dataset: str, feature: int):
    class0 = [value for value, label in zip(values, labels) if label == 0]
    class1 = [value for value, label in zip(values, labels) if label == 1]
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


def _clip(p: float) -> float:
    return min(max(p, 1e-9), 1.0 - 1e-9)


def _log_loss(labels: list[int], probabilities: list[float]) -> float:
    if not labels:
        return 0.0
    return -sum(
        label * math.log(_clip(p))
        + (1 - label) * math.log(_clip(1.0 - p))
        for label, p in zip(labels, probabilities)
    ) / len(labels)


def _candidate_thresholds(values: list[float], max_thresholds: int = 15):
    unique = sorted(set(values))
    if len(unique) <= 1:
        return ()
    mids = [(a + b) / 2.0 for a, b in zip(unique, unique[1:])]
    if len(mids) <= max_thresholds:
        return tuple(mids)
    picked = []
    for i in range(max_thresholds):
        j = round(i * (len(mids) - 1) / (max_thresholds - 1))
        picked.append(mids[j])
    return tuple(dict.fromkeys(picked))


def _fit_probabilities(values, labels, threshold):
    left = [label for value, label in zip(values, labels) if value < threshold]
    right = [label for value, label in zip(values, labels) if value >= threshold]
    if not left or not right:
        return None
    lp = (sum(left) + 1.0) / (len(left) + 2.0)
    rp = (sum(right) + 1.0) / (len(right) + 2.0)
    return lp, rp


def _best_threshold(train_values, train_labels):
    thresholds = _candidate_thresholds(train_values)
    best = None
    for threshold in thresholds:
        probs = _fit_probabilities(train_values, train_labels, threshold)
        if probs is None:
            continue
        lp, rp = probs
        predictions = [rp if value >= threshold else lp for value in train_values]
        loss = _log_loss(train_labels, predictions)
        key = (loss, threshold)
        if best is None or key < best[0]:
            best = (key, threshold)
    return (None, len(thresholds)) if best is None else (best[1], len(thresholds))


def _evaluate_feature(rows, labels, feature, train, calibration, test):
    train_values = [rows[i][feature] for i in train]
    train_labels = [labels[i] for i in train]
    cal_values = [rows[i][feature] for i in calibration]
    cal_labels = [labels[i] for i in calibration]
    test_values = [rows[i][feature] for i in test]
    test_labels = [labels[i] for i in test]

    threshold, threshold_evals = _best_threshold(train_values, train_labels)
    if threshold is None:
        return {
            "cal_gain": 0.0,
            "test_gain": 0.0,
            "threshold_evals": threshold_evals,
        }

    train_probs = _fit_probabilities(train_values, train_labels, threshold)
    lp, rp = train_probs
    prior = (sum(train_labels) + 1.0) / (len(train_labels) + 2.0)
    baseline_cal = _log_loss(cal_labels, [prior] * len(cal_labels))
    model_cal = _log_loss(
        cal_labels,
        [rp if value >= threshold else lp for value in cal_values],
    )
    cal_gain = baseline_cal - model_cal

    fit_values = train_values + cal_values
    fit_labels = train_labels + cal_labels
    fit_probs = _fit_probabilities(fit_values, fit_labels, threshold)
    lp2, rp2 = fit_probs
    prior2 = (sum(fit_labels) + 1.0) / (len(fit_labels) + 2.0)
    baseline_test = _log_loss(test_labels, [prior2] * len(test_labels))
    model_test = _log_loss(
        test_labels,
        [rp2 if value >= threshold else lp2 for value in test_values],
    )
    test_gain = baseline_test - model_test
    return {
        "cal_gain": cal_gain,
        "test_gain": test_gain,
        "threshold_evals": threshold_evals,
    }


def main():
    index = int(os.environ["REALITYGRAPH_PMLB_INDEX"])
    out_path = Path(
        os.environ.get(
            "REALITYGRAPH_PMLB_RESULT",
            f"results/pmlb-world-{index:03d}.json",
        )
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    summary_raw = _download(SUMMARY_URL)
    summary_sha = hashlib.sha256(summary_raw).hexdigest()
    manifest = corpus_manifest(summary_raw)
    if not 0 <= index < len(manifest):
        raise ValueError("PMLB world index outside manifest")

    meta = manifest[index]
    name = meta["dataset"]
    role = "train" if index < 100 else "heldout"
    raw = _download(DATA_URL.format(name=name))
    source_sha = hashlib.sha256(raw).hexdigest()
    feature_names, rows, targets = _parse_dataset(raw)
    labels = _binary_labels(targets)
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
    cold_false_law = best["cal_gain"] > 1e-4 and best["test_gain"] <= 1e-4

    result = {
        "index": index,
        "role": role,
        "dataset": name,
        "pmlb_commit": PMLB_COMMIT,
        "summary_sha256": summary_sha,
        "source_sha256": source_sha,
        "rows": len(rows),
        "features": len(anon_names),
        "classes_original": meta["n_classes"],
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
        "cold_search_cost": sum(item["threshold_evals"] for item in features),
    }
    out_path.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")

    print(
        f"PMLB_WORLD index={index:03d} role={role} dataset={name} "
        f"rows={len(rows)} features={len(anon_names)}"
    )
    print(
        f"cold_best=f{best['feature']} cal_gain={best['cal_gain']:.6f} "
        f"test_gain={best['test_gain']:.6f} false_law={cold_false_law} "
        f"search_cost={result['cold_search_cost']}"
    )
    print(
        f"source_sha256={source_sha} summary_sha256={summary_sha} "
        f"out={out_path}"
    )


if __name__ == "__main__":
    main()
