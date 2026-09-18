from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable

from .capability import FiniteCapability
from .capability_graph import CapabilityGraph
from .developmental_types import canonical_digest, canonical_json
from .meta_memory import MetaMemory, RepairRule, RepairRuleStatus
from .mg import Law, MG


@dataclass(frozen=True)
class MemoryLaw:
    law_id: str
    expr: str
    scope: str = "*"
    provenance: str = ""
    verifier_id: str = ""

    def __post_init__(self) -> None:
        if not self.law_id or not self.expr:
            raise ValueError("memory law requires id and expression")

    def payload(self) -> dict[str, object]:
        return {
            "law_id": self.law_id,
            "expr": self.expr,
            "scope": self.scope,
            "provenance": self.provenance,
            "verifier_id": self.verifier_id,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "MemoryLaw":
        return cls(
            law_id=str(payload["law_id"]),
            expr=str(payload["expr"]),
            scope=str(payload.get("scope", "*")),
            provenance=str(payload.get("provenance", "")),
            verifier_id=str(payload.get("verifier_id", "")),
        )


@dataclass(frozen=True)
class MemoryRevocation:
    target_kind: str
    target_id: str
    provenance: str = ""

    def __post_init__(self) -> None:
        if self.target_kind not in {"law", "capability", "repair_rule"}:
            raise ValueError("unsupported revocation target kind")
        if not self.target_id:
            raise ValueError("revocation requires target id")

    @property
    def identity(self) -> tuple[str, str]:
        return self.target_kind, self.target_id

    def payload(self) -> dict[str, object]:
        return {
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "provenance": self.provenance,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "MemoryRevocation":
        return cls(
            target_kind=str(payload["target_kind"]),
            target_id=str(payload["target_id"]),
            provenance=str(payload.get("provenance", "")),
        )


def _capability_payload(capability: FiniteCapability) -> dict[str, object]:
    return {
        "capability_id": capability.capability_id,
        "input_type": capability.input_type,
        "output_type": capability.output_type,
        "semantics": [list(item) for item in capability.semantics],
        "guard_inputs": list(capability.guard_inputs),
        "certificate_id": capability.certificate_id,
        "dependencies": list(capability.dependencies),
        "authority_snapshot": capability.authority_snapshot,
        "verifier_id": capability.verifier_id,
        "provenance_ids": list(capability.provenance_ids),
        "cost": capability.cost,
    }


def _capability_from_payload(payload: dict[str, object]) -> FiniteCapability:
    return FiniteCapability(
        capability_id=str(payload["capability_id"]),
        input_type=str(payload["input_type"]),
        output_type=str(payload["output_type"]),
        semantics=tuple(
            (str(row[0]), str(row[1]))
            for row in payload.get("semantics", ())
        ),
        guard_inputs=tuple(str(x) for x in payload.get("guard_inputs", ())),
        certificate_id=str(payload["certificate_id"]),
        dependencies=tuple(str(x) for x in payload.get("dependencies", ())),
        authority_snapshot=str(payload["authority_snapshot"]),
        verifier_id=str(payload["verifier_id"]),
        provenance_ids=tuple(str(x) for x in payload.get("provenance_ids", ())),
        cost=int(payload["cost"]),
    )


def _merge_records(left, right, identity):
    merged = {}
    for item in (*left, *right):
        key = identity(item)
        prior = merged.get(key)
        if prior is not None and prior != item:
            raise ValueError(f"MG2 identity conflict: {key}")
        merged[key] = item
    return tuple(merged[key] for key in sorted(merged))


@dataclass(frozen=True)
class MemoryGraphV2:
    """Canonical typed active memory.

    The causal ledger remains the history source.  MG2 stores only earned state
    that is allowed to affect future execution.
    """

    laws: tuple[MemoryLaw, ...] = ()
    capabilities: tuple[FiniteCapability, ...] = ()
    repair_rules: tuple[RepairRule, ...] = ()
    revocations: tuple[MemoryRevocation, ...] = ()

    def __post_init__(self) -> None:
        for label, ids in (
            ("law", [item.law_id for item in self.laws]),
            ("capability", [item.capability_id for item in self.capabilities]),
            ("repair_rule", [item.rule_id for item in self.repair_rules]),
        ):
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate {label} identity")

        revocation_ids = [item.identity for item in self.revocations]
        if len(revocation_ids) != len(set(revocation_ids)):
            raise ValueError("duplicate revocation identity")

        if any(rule.status is not RepairRuleStatus.PROMOTED for rule in self.repair_rules):
            raise ValueError("MG2 active repair rules must be promoted")

        # Validates dependency existence and acyclicity for the retained graph.
        CapabilityGraph(tuple(self.capabilities))

    @property
    def revoked_identities(self) -> frozenset[tuple[str, str]]:
        return frozenset(item.identity for item in self.revocations)

    @property
    def active_laws(self) -> tuple[MemoryLaw, ...]:
        revoked = self.revoked_identities
        return tuple(
            law for law in self.laws
            if ("law", law.law_id) not in revoked
        )

    @property
    def active_capabilities(self) -> tuple[FiniteCapability, ...]:
        graph = self.to_capability_graph()
        active = set(graph.active_ids())
        return tuple(
            capability for capability in self.capabilities
            if capability.capability_id in active
        )

    @property
    def active_repair_rules(self) -> tuple[RepairRule, ...]:
        revoked = self.revoked_identities
        return tuple(
            rule for rule in self.repair_rules
            if ("repair_rule", rule.rule_id) not in revoked
        )

    def payload(self) -> dict[str, object]:
        return {
            "version": "MG2",
            "laws": [
                law.payload()
                for law in sorted(self.laws, key=lambda item: item.law_id)
            ],
            "capabilities": [
                _capability_payload(capability)
                for capability in sorted(
                    self.capabilities,
                    key=lambda item: item.capability_id,
                )
            ],
            "repair_rules": [
                rule.payload()
                for rule in sorted(self.repair_rules, key=lambda item: item.rule_id)
            ],
            "revocations": [
                item.payload()
                for item in sorted(
                    self.revocations,
                    key=lambda row: row.identity,
                )
            ],
        }

    def text(self) -> str:
        return canonical_json(self.payload()) + "\n"

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="mg2:")

    @classmethod
    def parse(cls, text: str) -> "MemoryGraphV2":
        payload = json.loads(text)
        if payload.get("version") != "MG2":
            raise ValueError("unsupported memory graph version")
        memory = cls(
            laws=tuple(
                MemoryLaw.from_payload(row)
                for row in payload.get("laws", ())
            ),
            capabilities=tuple(
                _capability_from_payload(row)
                for row in payload.get("capabilities", ())
            ),
            repair_rules=tuple(
                RepairRule.from_payload(row)
                for row in payload.get("repair_rules", ())
            ),
            revocations=tuple(
                MemoryRevocation.from_payload(row)
                for row in payload.get("revocations", ())
            ),
        )
        if memory.text() != text:
            raise ValueError("non-canonical MG2 serialization")
        return memory

    def merge(self, other: "MemoryGraphV2") -> "MemoryGraphV2":
        laws = _merge_records(
            self.laws, other.laws, lambda item: item.law_id
        )
        capabilities = _merge_records(
            self.capabilities,
            other.capabilities,
            lambda item: item.capability_id,
        )
        repair_rules = _merge_records(
            self.repair_rules,
            other.repair_rules,
            lambda item: item.rule_id,
        )

        revocations = {}
        for item in (*self.revocations, *other.revocations):
            prior = revocations.get(item.identity)
            if prior is None:
                revocations[item.identity] = item
            elif prior != item:
                # The revocation fact is monotone.  Keep evidence only when it is
                # identical; differing provenance is a content conflict.
                raise ValueError(f"MG2 revocation conflict: {item.identity}")

        return MemoryGraphV2(
            laws=laws,
            capabilities=capabilities,
            repair_rules=repair_rules,
            revocations=tuple(
                revocations[key] for key in sorted(revocations)
            ),
        )

    @classmethod
    def from_mg1(cls, memory: MG) -> "MemoryGraphV2":
        return cls(
            laws=tuple(
                MemoryLaw(
                    law_id=law.id,
                    expr=law.expr,
                    scope=law.scope,
                    provenance=law.provenance,
                    verifier_id=memory.verifier,
                )
                for law in memory.laws.values()
            )
        )

    def to_mg1(self, *, law_only: bool = False) -> MG:
        if not law_only and (
            self.capabilities or self.repair_rules or self.revocations
        ):
            raise ValueError(
                "whole-memory MG2 -> MG1 would discard typed active memory"
            )
        laws = self.active_laws
        verifiers = {law.verifier_id for law in laws if law.verifier_id}
        if len(verifiers) > 1:
            raise ValueError("MG1 projection requires one compatible verifier")
        verifier = next(iter(verifiers), "")
        return MG(
            verifier,
            (
                Law(
                    law.id if isinstance(law, Law) else law.law_id,
                    law.expr,
                    law.scope,
                    law.provenance,
                )
                for law in laws
            ),
        )

    @classmethod
    def from_capability_graph(
        cls, graph: CapabilityGraph
    ) -> "MemoryGraphV2":
        return cls(
            capabilities=tuple(graph.capabilities),
            revocations=tuple(
                MemoryRevocation("capability", ident)
                for ident in graph.revoked_ids
            ),
        )

    def to_capability_graph(self) -> CapabilityGraph:
        known = {capability.capability_id for capability in self.capabilities}
        revoked = tuple(
            sorted(
                item.target_id
                for item in self.revocations
                if item.target_kind == "capability"
                and item.target_id in known
            )
        )
        return CapabilityGraph(tuple(self.capabilities), revoked)

    @classmethod
    def from_meta_memory(
        cls,
        memory: MetaMemory,
        *,
        promoted_only: bool = True,
        include_revoked: bool = False,
    ) -> "MemoryGraphV2":
        if not promoted_only:
            raise ValueError("MG2 active memory stores promoted repair rules only")
        rules = tuple(
            rule for rule in memory.rules
            if rule.status is RepairRuleStatus.PROMOTED
        )
        revocations = ()
        if include_revoked:
            revocations = tuple(
                MemoryRevocation("repair_rule", rule.rule_id)
                for rule in memory.rules
                if rule.status is RepairRuleStatus.REVOKED
            )
        return cls(repair_rules=rules, revocations=revocations)

    def to_meta_memory(self) -> MetaMemory:
        return MetaMemory(
            rules=tuple(self.active_repair_rules),
            episodes=(),
        )
