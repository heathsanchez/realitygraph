from __future__ import annotations

import base64
import json
import math
from dataclasses import dataclass

from .meta_policy import MetaSearchPolicy, _solve
from .mg import Law, MG


PREFIX = "meta-budget-policy-v1:"
FEATURE_NAMES = (
    "log_feature_count",
    "top_policy_score",
    "top1_top2_score_gap",
    "top2_top3_score_gap",
    "policy_score_std",
    "top_score_z",
)


@dataclass(frozen=True)
class MetaBudgetPolicy:
    feature_names: tuple[str, ...]
    means: tuple[float, ...]
    scales: tuple[float, ...]
    weights: tuple[float, ...]
    intercept: float
    safety_margin: float
    max_budget: int
    training_worlds: int
    base_policy_sha256: str

    def predict_raw(self, features) -> float:
        if len(features) != len(self.weights):
            raise ValueError("budget feature width mismatch")
        z = [
            (float(value) - mean) / scale
            for value, mean, scale in zip(
                features, self.means, self.scales
            )
        ]
        return self.intercept + sum(
            weight * value
            for weight, value in zip(self.weights, z)
        )

    def choose_budget(self, features) -> int:
        raw = self.predict_raw(features) + self.safety_margin
        return max(
            1,
            min(self.max_budget, int(math.ceil(raw))),
        )


def budget_features(
    policy: MetaSearchPolicy,
    world: dict,
) -> tuple[float, ...]:
    scores = sorted(
        (
            policy.score(tuple(item["descriptors"]))
            for item in world["candidates"]
        ),
        reverse=True,
    )
    if not scores:
        raise ValueError("world has no candidates")

    n = len(scores)
    top = scores[0]
    mean = sum(scores) / n
    variance = sum((value - mean) ** 2 for value in scores) / n
    std = math.sqrt(max(variance, 0.0))
    gap12 = top - scores[1] if n > 1 else top
    gap23 = (
        scores[1] - scores[2]
        if n > 2
        else gap12
    )
    return (
        math.log1p(n),
        top,
        gap12,
        gap23,
        std,
        (top - mean) / (std + 1e-9),
    )


def fit_budget_regressor(
    examples: list[tuple[float, ...]],
    targets: list[float],
    *,
    ridge: float = 1.0,
):
    if not examples or len(examples) != len(targets):
        raise ValueError("budget policy requires aligned examples")
    width = len(examples[0])
    if width == 0 or any(len(row) != width for row in examples):
        raise ValueError("inconsistent budget feature width")

    means = []
    scales = []
    for j in range(width):
        column = [row[j] for row in examples]
        mean = sum(column) / len(column)
        variance = sum(
            (value - mean) ** 2 for value in column
        ) / len(column)
        means.append(mean)
        scales.append(max(math.sqrt(variance), 1e-9))

    z = [
        tuple(
            (value - means[j]) / scales[j]
            for j, value in enumerate(row)
        )
        for row in examples
    ]
    intercept = sum(targets) / len(targets)
    centered = [target - intercept for target in targets]

    gram = [[0.0] * width for _ in range(width)]
    rhs = [0.0] * width
    for row, target in zip(z, centered):
        for i in range(width):
            rhs[i] += row[i] * target
            for j in range(width):
                gram[i][j] += row[i] * row[j]
    for i in range(width):
        gram[i][i] += ridge

    weights = _solve(gram, rhs)
    return (
        tuple(means),
        tuple(scales),
        tuple(weights),
        float(intercept),
    )


def budget_to_law(
    policy: MetaBudgetPolicy,
    provenance: str,
) -> Law:
    payload = {
        "features": list(policy.feature_names),
        "means": list(policy.means),
        "scales": list(policy.scales),
        "weights": list(policy.weights),
        "intercept": policy.intercept,
        "safety_margin": policy.safety_margin,
        "max_budget": policy.max_budget,
        "training_worlds": policy.training_worlds,
        "base_policy_sha256": policy.base_policy_sha256,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return Law(
        "cross-domain-budget-policy",
        PREFIX + encoded,
        "cross-domain-search",
        provenance,
    )


def budget_from_memory(memory: MG) -> MetaBudgetPolicy:
    laws = [
        law
        for law in memory.laws.values()
        if law.expr.startswith(PREFIX)
    ]
    if len(laws) != 1:
        raise ValueError(
            "memory must contain exactly one budget policy"
        )
    encoded = laws[0].expr[len(PREFIX):]
    encoded += "=" * (-len(encoded) % 4)
    payload = json.loads(
        base64.urlsafe_b64decode(encoded.encode()).decode()
    )
    return MetaBudgetPolicy(
        tuple(str(x) for x in payload["features"]),
        tuple(float(x) for x in payload["means"]),
        tuple(float(x) for x in payload["scales"]),
        tuple(float(x) for x in payload["weights"]),
        float(payload["intercept"]),
        float(payload["safety_margin"]),
        int(payload["max_budget"]),
        int(payload["training_worlds"]),
        str(payload["base_policy_sha256"]),
    )


def adaptive_memory(
    base_memory: MG,
    budget_policy: MetaBudgetPolicy,
    provenance: str,
) -> MG:
    memory = MG(
        "cross-domain-search-policy-v2",
        base_memory.laws.values(),
    )
    memory.add(budget_to_law(budget_policy, provenance))
    return memory
