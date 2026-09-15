from __future__ import annotations

import hashlib
import shlex
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .lab import CompiledIdentifier, compile_plan, design_separating_batch


@dataclass(frozen=True)
class EmpiricalSource:
    name: str
    domain: str
    url: str
    doi: str
    parser: str
    feature_names: tuple[str, ...]
    target_name: str
    license: str = "CC BY 4.0"
    expected_sha256: str = ""
    target_kind: str = "categorical"


@dataclass(frozen=True)
class EmpiricalDataset:
    source: EmpiricalSource
    features: tuple[tuple[str, ...], ...]
    targets: tuple[str, ...]
    source_sha256: str


@dataclass(frozen=True)
class IdentityModel:
    dataset: EmpiricalDataset
    identifier: CompiledIdentifier
    class_members: dict[int, tuple[int, ...]]
    representative_rows: tuple[int, ...]
    feature_indices: tuple[int, ...]

    def identify_row(self, row_index: int) -> tuple[str, tuple[int, ...]]:
        row = self.dataset.features[row_index]
        signature = tuple(row[i] for i in self.feature_indices)
        representative = self.identifier.decode(signature)
        members = self.class_members[representative]
        return ("IDENTIFIED" if len(members) == 1 else "UNKNOWN", members)


@dataclass(frozen=True)
class TargetPlan:
    feature_indices: tuple[int, ...]
    design_predictions: int
    conflict_progress: tuple[int, ...]
    decoder: dict[tuple[str, ...], str]
    unresolved_signatures: int
    unresolved_rows: int

    @property
    def exact(self) -> bool:
        return self.unresolved_signatures == 0


def _download(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "RealityGraph/1.0 dataset verifier"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_dataset(
    source: EmpiricalSource,
    cache_dir: str | Path | None = None,
) -> EmpiricalDataset:
    cache_path = None
    raw = None
    if cache_dir is not None:
        cache = Path(cache_dir)
        cache.mkdir(parents=True, exist_ok=True)
        safe = source.name.lower().replace(" ", "-").replace("/", "-")
        cache_path = cache / f"{safe}.data"
        if cache_path.exists():
            raw = cache_path.read_bytes()

    if raw is None:
        raw = _download(source.url)
        if cache_path is not None:
            cache_path.write_bytes(raw)

    digest = hashlib.sha256(raw).hexdigest()
    if source.expected_sha256 and digest != source.expected_sha256:
        raise ValueError(
            f"{source.name}: source SHA-256 changed: "
            f"expected {source.expected_sha256}, got {digest}"
        )

    features, targets = parse_dataset(source, raw.decode("utf-8", errors="strict"))
    return EmpiricalDataset(source, tuple(features), tuple(targets), digest)


def parse_dataset(
    source: EmpiricalSource,
    text: str,
) -> tuple[list[tuple[str, ...]], list[str]]:
    features: list[tuple[str, ...]] = []
    targets: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if source.parser == "iris":
            parts = [p.strip() for p in line.split(",")]
            row, target = parts[:4], parts[4]
        elif source.parser == "wine":
            parts = [p.strip() for p in line.split(",")]
            target, row = parts[0], parts[1:14]
        elif source.parser == "auto-mpg":
            parts = shlex.split(line)
            if len(parts) < 9:
                raise ValueError(f"bad Auto MPG row: {line}")
            target = parts[0]
            row = parts[1:8]  # physical/temporal features; exclude car name
        elif source.parser == "airfoil":
            parts = line.split()
            row, target = parts[:5], parts[5]
        elif source.parser == "abalone":
            parts = [p.strip() for p in line.split(",")]
            row, target = parts[:8], parts[8]
        elif source.parser == "ionosphere":
            parts = [p.strip() for p in line.split(",")]
            row, target = parts[:34], parts[34]
        elif source.parser == "sonar":
            parts = [p.strip() for p in line.split(",")]
            row, target = parts[:60], parts[60]
        elif source.parser == "yacht":
            parts = line.split()
            row, target = parts[:6], parts[6]
        else:
            raise ValueError(f"unsupported parser: {source.parser}")

        if len(row) != len(source.feature_names):
            raise ValueError(
                f"{source.name}: expected {len(source.feature_names)} features, "
                f"got {len(row)}"
            )
        features.append(tuple(row))
        targets.append(target)

    if not features:
        raise ValueError(f"{source.name}: no rows parsed")
    return features, targets


def compile_identity(dataset: EmpiricalDataset) -> tuple[IdentityModel, int]:
    # Full-feature equality is the empirical observational quotient. Identical
    # rows are not artificially separated by record IDs.
    members_by_vector: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for row_index, row in enumerate(dataset.features):
        members_by_vector[row].append(row_index)

    representative_rows = tuple(group[0] for group in members_by_vector.values())
    representatives = tuple(range(len(representative_rows)))
    rep_features = tuple(dataset.features[i] for i in representative_rows)
    actions = tuple(range(len(dataset.source.feature_names)))

    def predict(rep: int, feature_index: int) -> str:
        return rep_features[rep][feature_index]

    plan = design_separating_batch(representatives, actions, predict)
    identifier = compile_plan(dataset.source.name, plan)
    class_members = {
        rep: tuple(members_by_vector[rep_features[rep]])
        for rep in representatives
    }
    model = IdentityModel(
        dataset,
        identifier,
        class_members,
        representative_rows,
        tuple(plan.actions),
    )
    return model, plan.design_predictions


def _target_conflicts(
    signatures: Sequence[tuple[str, ...]],
    targets: Sequence[str],
) -> tuple[int, int, int]:
    buckets: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    for signature, target in zip(signatures, targets):
        buckets[signature][target] += 1

    conflict_pairs = 0
    unresolved_rows = 0
    unresolved_signatures = 0
    for counts in buckets.values():
        if len(counts) <= 1:
            continue
        unresolved_signatures += 1
        size = sum(counts.values())
        unresolved_rows += size
        same_pairs = sum(n * (n - 1) // 2 for n in counts.values())
        conflict_pairs += size * (size - 1) // 2 - same_pairs
    return conflict_pairs, unresolved_signatures, unresolved_rows


def design_target_batch(dataset: EmpiricalDataset) -> TargetPlan:
    """Find an irreducible feature set preserving the dataset target exactly.

    This is a finite-dataset certificate, not a claim of out-of-sample
    generalization. If identical measured signatures carry conflicting targets,
    those signatures remain explicitly unresolved.
    """
    rows = dataset.features
    targets = dataset.targets
    actions = list(range(len(dataset.source.feature_names)))
    columns = {
        action: tuple(row[action] for row in rows)
        for action in actions
    }
    predictions = len(rows) * len(actions)

    selected: list[int] = []
    signatures: list[tuple[str, ...]] = [()] * len(rows)
    conflict, _, _ = _target_conflicts(signatures, targets)
    progress = [conflict]

    while conflict > 0 and actions:
        best = None
        best_signatures = None
        best_metric = None

        for action in actions:
            column = columns[action]
            candidate = [
                signatures[i] + (column[i],)
                for i in range(len(rows))
            ]
            c, unresolved_sigs, unresolved_rows = _target_conflicts(
                candidate, targets
            )
            metric = (c, unresolved_rows, unresolved_sigs)
            if best_metric is None or metric < best_metric:
                best = action
                best_signatures = candidate
                best_metric = metric

        if best is None or best_signatures is None:
            break
        next_conflict = best_metric[0]
        if next_conflict >= conflict:
            break

        selected.append(best)
        actions.remove(best)
        signatures = best_signatures
        conflict = next_conflict
        progress.append(conflict)

    # Backward-delete target-irrelevant features while preserving the achieved
    # consequence partition.
    achieved = _target_conflicts(signatures, targets)[0]
    for action in tuple(reversed(selected)):
        trial = [a for a in selected if a != action]
        trial_signatures = [
            tuple(row[a] for a in trial)
            for row in rows
        ]
        if _target_conflicts(trial_signatures, targets)[0] == achieved:
            selected = trial

    final_signatures = [
        tuple(row[a] for a in selected)
        for row in rows
    ]
    buckets: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    for signature, target in zip(final_signatures, targets):
        buckets[signature][target] += 1

    decoder = {
        signature: next(iter(counts))
        for signature, counts in buckets.items()
        if len(counts) == 1
    }
    _, unresolved_sigs, unresolved_rows = _target_conflicts(
        final_signatures, targets
    )
    return TargetPlan(
        tuple(selected),
        predictions,
        tuple(progress),
        decoder,
        unresolved_sigs,
        unresolved_rows,
    )


def evaluate_target_plan(
    dataset: EmpiricalDataset,
    plan: TargetPlan,
) -> tuple[int, int, int]:
    correct = 0
    unknown = 0
    wrong = 0
    for row, target in zip(dataset.features, dataset.targets):
        signature = tuple(row[a] for a in plan.feature_indices)
        predicted = plan.decoder.get(signature)
        if predicted is None:
            unknown += 1
        elif predicted == target:
            correct += 1
        else:
            wrong += 1
    return correct, unknown, wrong
