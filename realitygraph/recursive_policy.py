from __future__ import annotations

import base64
import json
import math
from dataclasses import dataclass

from .meta_policy import MetaSearchPolicy, _solve
from .mg import Law, MG


PREFIX = "recursive-search-policy-v1:"
BUDGET_FEATURE_NAMES = (
    "log_feature_count",
    "top_recursive_score",
    "top1_top2_score_gap",
    "top2_top3_score_gap",
    "recursive_score_std",
    "top_score_z",
)
TRUST_FEATURE_NAMES = (
    "cal_gain",
    "recursive_score",
    "top1_top2_score_gap",
    "recursive_score_std",
    "budget_fraction",
    "cal_gain_margin",
    "effect_size",
    "abs_correlation",
)


@dataclass(frozen=True)
class RecursiveSearchPolicy:
    descriptor_names: tuple[str, ...]
    rank_means: tuple[float, ...]
    rank_scales: tuple[float, ...]
    rank_weights: tuple[float, ...]
    rank_blend: float
    budget_feature_names: tuple[str, ...]
    budget_means: tuple[float, ...]
    budget_scales: tuple[float, ...]
    budget_weights: tuple[float, ...]
    budget_intercept: float
    budget_safety_margin: float
    max_budget: int
    trust_feature_names: tuple[str, ...]
    trust_means: tuple[float, ...]
    trust_scales: tuple[float, ...]
    trust_weights: tuple[float, ...]
    trust_intercept: float
    trust_threshold: float
    training_worlds: int
    generation: int
    parent_sha256: str

    def task_score(self, descriptors) -> float:
        if len(descriptors) != len(self.rank_weights):
            raise ValueError("recursive rank descriptor width mismatch")
        z = [
            (float(value) - mean) / scale
            for value, mean, scale in zip(
                descriptors, self.rank_means, self.rank_scales
            )
        ]
        return sum(
            weight * value for weight, value in zip(self.rank_weights, z)
        )

    def score(self, base: MetaSearchPolicy, descriptors) -> float:
        return (
            (1.0 - self.rank_blend) * base.score(descriptors)
            + self.rank_blend * self.task_score(descriptors)
        )

    def choose_budget(self, features) -> int:
        if len(features) != len(self.budget_weights):
            raise ValueError("recursive budget feature width mismatch")
        z = [
            (float(value) - mean) / scale
            for value, mean, scale in zip(
                features, self.budget_means, self.budget_scales
            )
        ]
        raw = self.budget_intercept + sum(
            weight * value
            for weight, value in zip(self.budget_weights, z)
        )
        raw += self.budget_safety_margin
        return max(1, min(self.max_budget, int(math.ceil(raw))))

    def trust_score(self, features) -> float:
        if len(features) != len(self.trust_weights):
            raise ValueError("recursive trust feature width mismatch")
        z = [
            (float(value) - mean) / scale
            for value, mean, scale in zip(
                features, self.trust_means, self.trust_scales
            )
        ]
        return self.trust_intercept + sum(
            weight * value
            for weight, value in zip(self.trust_weights, z)
        )


def fit_ridge_with_intercept(examples, targets, *, ridge=1.0):
    if not examples or len(examples) != len(targets):
        raise ValueError("requires aligned examples and targets")
    width = len(examples[0])
    if width == 0 or any(len(row) != width for row in examples):
        raise ValueError("inconsistent feature width")

    means = []
    scales = []
    for j in range(width):
        column = [float(row[j]) for row in examples]
        mean = sum(column) / len(column)
        variance = sum(
            (value - mean) ** 2 for value in column
        ) / len(column)
        means.append(mean)
        scales.append(max(math.sqrt(variance), 1e-9))

    z = [
        tuple(
            (float(value) - means[j]) / scales[j]
            for j, value in enumerate(row)
        )
        for row in examples
    ]
    intercept = sum(float(y) for y in targets) / len(targets)
    centered = [float(y) - intercept for y in targets]

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


def recursive_order(policy, base, world):
    return sorted(
        world["candidates"],
        key=lambda item: (
            -policy.score(base, tuple(item["descriptors"])),
            item["feature"],
        ),
    )


def recursive_budget_features(policy, base, world):
    scores = sorted(
        (
            policy.score(base, tuple(item["descriptors"]))
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
    gap23 = scores[1] - scores[2] if n > 2 else gap12
    return (
        math.log1p(n),
        top,
        gap12,
        gap23,
        std,
        (top - mean) / (std + 1e-9),
    )


def recursive_trust_features(
    policy,
    base,
    world,
    selected,
    best,
    budget,
):
    scores = sorted(
        (
            policy.score(base, tuple(item["descriptors"]))
            for item in world["candidates"]
        ),
        reverse=True,
    )
    mean = sum(scores) / len(scores)
    variance = sum((value - mean) ** 2 for value in scores) / len(scores)
    std = math.sqrt(max(variance, 0.0))
    gap12 = scores[0] - scores[1] if len(scores) > 1 else scores[0]
    best_score = policy.score(base, tuple(best["descriptors"]))
    cal_values = sorted(
        (float(item["cal_gain"]) for item in selected),
        reverse=True,
    )
    cal_margin = (
        cal_values[0] - cal_values[1]
        if len(cal_values) > 1
        else cal_values[0]
    )
    descriptors = tuple(float(x) for x in best["descriptors"])
    return (
        float(best["cal_gain"]),
        best_score,
        gap12,
        std,
        budget / max(policy.max_budget, 1),
        cal_margin,
        descriptors[0] if descriptors else 0.0,
        descriptors[1] if len(descriptors) > 1 else 0.0,
    )


def recursive_to_law(policy, provenance):
    payload = {
        "descriptor_names": list(policy.descriptor_names),
        "rank_means": list(policy.rank_means),
        "rank_scales": list(policy.rank_scales),
        "rank_weights": list(policy.rank_weights),
        "rank_blend": policy.rank_blend,
        "budget_feature_names": list(policy.budget_feature_names),
        "budget_means": list(policy.budget_means),
        "budget_scales": list(policy.budget_scales),
        "budget_weights": list(policy.budget_weights),
        "budget_intercept": policy.budget_intercept,
        "budget_safety_margin": policy.budget_safety_margin,
        "max_budget": policy.max_budget,
        "trust_feature_names": list(policy.trust_feature_names),
        "trust_means": list(policy.trust_means),
        "trust_scales": list(policy.trust_scales),
        "trust_weights": list(policy.trust_weights),
        "trust_intercept": policy.trust_intercept,
        "trust_threshold": policy.trust_threshold,
        "training_worlds": policy.training_worlds,
        "generation": policy.generation,
        "parent_sha256": policy.parent_sha256,
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return Law(
        "recursive-search-policy",
        PREFIX + encoded,
        "future-cross-domain-search",
        provenance,
    )


def recursive_from_memory(memory):
    laws = [
        law
        for law in memory.laws.values()
        if law.expr.startswith(PREFIX)
    ]
    if not laws:
        return None
    if len(laws) != 1:
        raise ValueError(
            "memory must contain at most one recursive policy"
        )
    encoded = laws[0].expr[len(PREFIX):]
    encoded += "=" * (-len(encoded) % 4)
    payload = json.loads(
        base64.urlsafe_b64decode(encoded.encode()).decode()
    )
    return RecursiveSearchPolicy(
        tuple(payload["descriptor_names"]),
        tuple(map(float, payload["rank_means"])),
        tuple(map(float, payload["rank_scales"])),
        tuple(map(float, payload["rank_weights"])),
        float(payload["rank_blend"]),
        tuple(payload["budget_feature_names"]),
        tuple(map(float, payload["budget_means"])),
        tuple(map(float, payload["budget_scales"])),
        tuple(map(float, payload["budget_weights"])),
        float(payload["budget_intercept"]),
        float(payload["budget_safety_margin"]),
        int(payload["max_budget"]),
        tuple(payload["trust_feature_names"]),
        tuple(map(float, payload["trust_means"])),
        tuple(map(float, payload["trust_scales"])),
        tuple(map(float, payload["trust_weights"])),
        float(payload["trust_intercept"]),
        float(payload["trust_threshold"]),
        int(payload["training_worlds"]),
        int(payload["generation"]),
        str(payload["parent_sha256"]),
    )


def recursive_memory(parent, policy, provenance):
    laws = [
        law
        for law in parent.laws.values()
        if not law.expr.startswith(PREFIX)
    ]
    out = MG("cross-domain-search-policy-v3", laws)
    out.add(recursive_to_law(policy, provenance))
    return out
