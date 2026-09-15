from __future__ import annotations

import base64
import json
import math
from dataclasses import dataclass

from .mg import Law, MG


PREFIX = "meta-search-policy-v1:"


@dataclass(frozen=True)
class MetaSearchPolicy:
    descriptor_names: tuple[str, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    weights: tuple[float, ...]
    budget: int
    training_worlds: int
    corpus_digest: str

    def score(self, descriptors: tuple[float, ...] | list[float]) -> float:
        if len(descriptors) != len(self.weights):
            raise ValueError("descriptor width mismatch")
        z = [
            (float(value) - mean) / scale
            for value, mean, scale in zip(descriptors, self.means, self.scales)
        ]
        return sum(weight * value for weight, value in zip(self.weights, z))


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    n = len(vector)
    a = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(a[row][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ValueError("singular meta-policy system")
        a[col], a[pivot] = a[pivot], a[col]
        scale = a[col][col]
        a[col] = [value / scale for value in a[col]]
        for row in range(n):
            if row == col:
                continue
            factor = a[row][col]
            if abs(factor) < 1e-18:
                continue
            a[row] = [
                x - factor * y
                for x, y in zip(a[row], a[col])
            ]
    return [a[i][-1] for i in range(n)]


def fit_ridge_ranker(
    examples: list[tuple[float, ...]],
    targets: list[float],
    *,
    ridge: float = 1e-2,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    if not examples or len(examples) != len(targets):
        raise ValueError("meta-policy requires aligned examples and targets")
    width = len(examples[0])
    if width == 0 or any(len(row) != width for row in examples):
        raise ValueError("inconsistent descriptor width")

    means = []
    scales = []
    for j in range(width):
        column = [row[j] for row in examples]
        mean = sum(column) / len(column)
        variance = sum((value - mean) ** 2 for value in column) / len(column)
        means.append(mean)
        scales.append(max(math.sqrt(variance), 1e-9))

    z = [
        tuple((value - means[j]) / scales[j] for j, value in enumerate(row))
        for row in examples
    ]
    gram = [[0.0] * width for _ in range(width)]
    rhs = [0.0] * width
    for row, target in zip(z, targets):
        for i in range(width):
            rhs[i] += row[i] * target
            for j in range(width):
                gram[i][j] += row[i] * row[j]
    for i in range(width):
        gram[i][i] += ridge

    weights = _solve(gram, rhs)
    return tuple(means), tuple(scales), tuple(weights)


def policy_to_law(policy: MetaSearchPolicy, provenance: str) -> Law:
    payload = {
        "descriptors": list(policy.descriptor_names),
        "means": list(policy.means),
        "scales": list(policy.scales),
        "weights": list(policy.weights),
        "budget": policy.budget,
        "training_worlds": policy.training_worlds,
        "corpus_digest": policy.corpus_digest,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return Law(
        "cross-domain-search-policy",
        PREFIX + encoded,
        "pmlb-heldout-datasets",
        provenance,
    )


def policy_from_law(law: Law) -> MetaSearchPolicy:
    if not law.expr.startswith(PREFIX):
        raise ValueError("law is not a meta-search policy")
    encoded = law.expr[len(PREFIX):]
    encoded += "=" * (-len(encoded) % 4)
    payload = json.loads(base64.urlsafe_b64decode(encoded.encode()).decode())
    return MetaSearchPolicy(
        tuple(str(x) for x in payload["descriptors"]),
        tuple(float(x) for x in payload["means"]),
        tuple(float(x) for x in payload["scales"]),
        tuple(float(x) for x in payload["weights"]),
        int(payload["budget"]),
        int(payload["training_worlds"]),
        str(payload["corpus_digest"]),
    )


def policy_memory(policy: MetaSearchPolicy, provenance: str) -> MG:
    return MG("cross-domain-search-policy-v1", (policy_to_law(policy, provenance),))


def policy_from_memory(memory: MG) -> MetaSearchPolicy:
    laws = [
        law for law in memory.laws.values()
        if law.expr.startswith(PREFIX)
    ]
    if len(laws) != 1:
        raise ValueError("memory must contain exactly one meta-search policy")
    return policy_from_law(laws[0])
