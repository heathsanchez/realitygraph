from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from acc_developmental_core import ACCResidual


POLICY_VERSION = "acc-generator-controller-v1"


@dataclass(frozen=True)
class GeneratorObservation:
    residual: ACCResidual
    generator_id: str
    baseline_solved: bool
    generated_solved: bool
    official_verified: bool
    baseline_expansions: int
    generated_expansions: int
    generator_cost: int


@dataclass(frozen=True)
class ControllerRule:
    generator_id: str
    field: str
    op: str
    threshold: float

    def matches(self, residual: ACCResidual) -> bool:
        value = getattr(residual, self.field)
        if value is None:
            return False
        numeric = float(value)
        if self.op == ">=":
            return numeric >= self.threshold
        if self.op == "<=":
            return numeric <= self.threshold
        if self.op == "==":
            return numeric == self.threshold
        raise ValueError(f"unsupported controller operator: {self.op}")


@dataclass(frozen=True)
class GeneratorPolicy:
    version: str = POLICY_VERSION
    rules: tuple[ControllerRule, ...] = ()
    rescues: int = 0
    harms: int = 0
    verifier_accepts: int = 0
    expansion_gain: int = 0
    generator_cost: int = 0
    promoted: bool = False

    def canonical_json(self) -> str:
        payload = {
            "version": self.version,
            "rules": [asdict(rule) for rule in self.rules],
            "rescues": self.rescues,
            "harms": self.harms,
            "verifier_accepts": self.verifier_accepts,
            "expansion_gain": self.expansion_gain,
            "generator_cost": self.generator_cost,
            "promoted": self.promoted,
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

    @classmethod
    def from_json(cls, text: str) -> "GeneratorPolicy":
        payload = json.loads(text)
        if payload.get("version") != POLICY_VERSION:
            raise ValueError("unexpected ACC generator policy version")
        policy = cls(
            version=str(payload["version"]),
            rules=tuple(
                ControllerRule(
                    generator_id=str(rule["generator_id"]),
                    field=str(rule["field"]),
                    op=str(rule["op"]),
                    threshold=float(rule["threshold"]),
                )
                for rule in payload.get("rules", ())
            ),
            rescues=int(payload.get("rescues", 0)),
            harms=int(payload.get("harms", 0)),
            verifier_accepts=int(payload.get("verifier_accepts", 0)),
            expansion_gain=int(payload.get("expansion_gain", 0)),
            generator_cost=int(payload.get("generator_cost", 0)),
            promoted=bool(payload.get("promoted", False)),
        )
        if policy.canonical_json() != text:
            raise ValueError("generator policy is not canonical or byte-exact")
        return policy

    def ablate(self) -> "GeneratorPolicy":
        return GeneratorPolicy(
            version=self.version,
            rules=(),
            rescues=0,
            harms=0,
            verifier_accepts=0,
            expansion_gain=0,
            generator_cost=0,
            promoted=False,
        )


_SCALAR_FIELDS = (
    "n",
    "min_total_length",
    "best_depth",
    "capability_expansions",
    "exact_tail_near_hits",
    "orbit_tail_near_hits",
    "plateau_length",
    "max_total_reject_fraction",
    "budget_consumed",
)


def _score_rule(
    rule: ControllerRule,
    observations: Iterable[GeneratorObservation],
) -> tuple[tuple[Any, ...], dict[str, int]] | None:
    invoked = [obs for obs in observations if rule.matches(obs.residual)]
    if not invoked:
        return None

    rescues = sum(
        1
        for obs in invoked
        if (not obs.baseline_solved)
        and obs.generated_solved
        and obs.official_verified
    )
    harms = sum(
        1
        for obs in invoked
        if obs.baseline_solved and not obs.generated_solved
    )
    verifier_accepts = sum(
        1 for obs in invoked if obs.generated_solved and obs.official_verified
    )
    expansion_gain = sum(
        max(0, int(obs.baseline_expansions) - int(obs.generated_expansions))
        for obs in invoked
        if obs.baseline_solved and obs.generated_solved and obs.official_verified
    )
    generator_cost = sum(max(0, int(obs.generator_cost)) for obs in invoked)

    # Promotion is baseline-preserving: any observed lost baseline solve is fatal.
    if rescues <= 0 or harms != 0:
        return None

    metrics = {
        "rescues": rescues,
        "harms": harms,
        "verifier_accepts": verifier_accepts,
        "expansion_gain": expansion_gain,
        "generator_cost": generator_cost,
    }
    key = (
        rescues,
        verifier_accepts,
        expansion_gain,
        -generator_cost,
        -len(invoked),
        rule.generator_id,
        rule.field,
        rule.op,
        -rule.threshold,
    )
    return key, metrics


def _candidate_rules(
    generator_id: str,
    observations: list[GeneratorObservation],
) -> Iterable[ControllerRule]:
    for field in _SCALAR_FIELDS:
        values = sorted(
            {
                float(getattr(obs.residual, field))
                for obs in observations
                if getattr(obs.residual, field) is not None
            }
        )
        for threshold in values:
            yield ControllerRule(generator_id, field, ">=", threshold)
            yield ControllerRule(generator_id, field, "<=", threshold)
            yield ControllerRule(generator_id, field, "==", threshold)


def learn_generator_policy(
    observations: Iterable[GeneratorObservation],
) -> GeneratorPolicy:
    rows = list(observations)
    if not rows:
        return GeneratorPolicy()

    by_generator: dict[str, list[GeneratorObservation]] = {}
    for obs in rows:
        by_generator.setdefault(str(obs.generator_id), []).append(obs)

    best: tuple[tuple[Any, ...], ControllerRule, dict[str, int]] | None = None
    for generator_id in sorted(by_generator):
        group = by_generator[generator_id]
        for rule in _candidate_rules(generator_id, group):
            scored = _score_rule(rule, group)
            if scored is None:
                continue
            key, metrics = scored
            candidate = (key, rule, metrics)
            if best is None or key > best[0]:
                best = candidate

    if best is None:
        return GeneratorPolicy()

    _, rule, metrics = best
    return GeneratorPolicy(
        rules=(rule,),
        rescues=metrics["rescues"],
        harms=metrics["harms"],
        verifier_accepts=metrics["verifier_accepts"],
        expansion_gain=metrics["expansion_gain"],
        generator_cost=metrics["generator_cost"],
        promoted=True,
    )


def apply_policy(
    policy: GeneratorPolicy,
    residual: ACCResidual,
) -> tuple[str, ...]:
    if not policy.promoted:
        return ()
    invoked: list[str] = []
    for rule in policy.rules:
        if rule.matches(residual) and rule.generator_id not in invoked:
            invoked.append(rule.generator_id)
    return tuple(invoked)
