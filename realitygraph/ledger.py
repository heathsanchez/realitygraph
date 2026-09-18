from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Iterable

from .capability import FiniteCapability
from .capability_graph import CapabilityGraph
from .compiled_present import CompiledPresent
from .memory_graph import MemoryGraphV2, MemoryRevocation
from .meta_memory import RepairRule, RepairRuleStatus
from .mg import Law, MG


@dataclass(frozen=True)
class Event:
    """One immutable causal change.

    Event identity is content-addressed. Parents encode what this event had
    observed, so concurrency is represented rather than guessed from clocks.
    """

    parents: tuple[str, ...]
    kernel: str
    op: str
    target: str
    payload: tuple[tuple[str, str], ...] = ()

    @property
    def id(self) -> str:
        body = {
            "parents": list(self.parents),
            "kernel": self.kernel,
            "op": self.op,
            "target": self.target,
            "payload": list(self.payload),
        }
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()[:16]

    @classmethod
    def add(cls, law: Law, kernel: str, parents: Iterable[str] = ()) -> "Event":
        return cls(
            tuple(sorted(set(parents))),
            kernel,
            "add",
            law.id,
            tuple(sorted({
                "expr": law.expr,
                "scope": law.scope,
                "provenance": law.provenance,
            }.items())),
        )

    @classmethod
    def revoke(
        cls,
        target: str,
        kernel: str,
        parents: Iterable[str] = (),
        reason: str = "",
    ) -> "Event":
        payload = (("reason", reason),) if reason else ()
        return cls(tuple(sorted(set(parents))), kernel, "revoke", target, payload)

    @classmethod
    def promote_capability(
        cls,
        capability: FiniteCapability,
        kernel: str,
        parents: Iterable[str] = (),
    ) -> "Event":
        payload = {
            "input_type": capability.input_type,
            "output_type": capability.output_type,
            "semantics": json.dumps(
                [list(row) for row in capability.semantics],
                sort_keys=True,
                separators=(",", ":"),
            ),
            "guard_inputs": json.dumps(list(capability.guard_inputs), separators=(",", ":")),
            "certificate_id": capability.certificate_id,
            "dependencies": json.dumps(list(capability.dependencies), separators=(",", ":")),
            "authority_snapshot": capability.authority_snapshot,
            "verifier_id": capability.verifier_id,
            "provenance_ids": json.dumps(list(capability.provenance_ids), separators=(",", ":")),
            "cost": str(capability.cost),
        }
        return cls(
            tuple(sorted(set(parents))),
            kernel,
            "promote_capability",
            capability.capability_id,
            tuple(sorted(payload.items())),
        )

    @classmethod
    def revoke_capability(
        cls,
        target: str,
        kernel: str,
        parents: Iterable[str] = (),
        reason: str = "",
    ) -> "Event":
        payload = (("reason", reason),) if reason else ()
        return cls(
            tuple(sorted(set(parents))),
            kernel,
            "revoke_capability",
            target,
            payload,
        )

    @classmethod
    def promote_repair_rule(
        cls,
        rule: RepairRule,
        kernel: str,
        parents: Iterable[str] = (),
    ) -> "Event":
        if rule.status is not RepairRuleStatus.PROMOTED:
            raise ValueError("only promoted repair rules enter active causal memory")
        payload = {
            "obstruction_fingerprint": rule.obstruction_fingerprint,
            "strategy_id": rule.strategy_id,
            "strategy_version": rule.strategy_version,
            "portfolio_digest": rule.portfolio_digest,
            "authority_snapshot": rule.authority_snapshot,
            "verifier_id": rule.verifier_id,
            "interface_digest": rule.interface_digest,
            "source_episode_digests": json.dumps(
                list(rule.source_episode_digests), separators=(",", ":")
            ),
            "source_episode_phases": json.dumps(
                list(rule.source_episode_phases), separators=(",", ":")
            ),
            "status": rule.status.value,
            "selection_cost": str(rule.selection_cost),
            "ablation_handle": rule.ablation_handle,
        }
        return cls(
            tuple(sorted(set(parents))),
            kernel,
            "promote_repair_rule",
            rule.rule_id,
            tuple(sorted(payload.items())),
        )

    @classmethod
    def revoke_repair_rule(
        cls,
        target: str,
        kernel: str,
        parents: Iterable[str] = (),
        reason: str = "",
    ) -> "Event":
        payload = (("reason", reason),) if reason else ()
        return cls(
            tuple(sorted(set(parents))),
            kernel,
            "revoke_repair_rule",
            target,
            payload,
        )

    def law(self) -> Law:
        if self.op != "add":
            raise ValueError("event does not contain a law")
        data = dict(self.payload)
        return Law(
            self.target,
            data["expr"],
            data.get("scope", "*"),
            data.get("provenance", ""),
        )

    def capability(self) -> FiniteCapability:
        if self.op != "promote_capability":
            raise ValueError("event does not contain a capability")
        data = dict(self.payload)
        return FiniteCapability(
            capability_id=self.target,
            input_type=data["input_type"],
            output_type=data["output_type"],
            semantics=tuple(
                (str(a), str(b))
                for a, b in json.loads(data["semantics"])
            ),
            guard_inputs=tuple(str(x) for x in json.loads(data["guard_inputs"])),
            certificate_id=data["certificate_id"],
            dependencies=tuple(str(x) for x in json.loads(data["dependencies"])),
            authority_snapshot=data["authority_snapshot"],
            verifier_id=data["verifier_id"],
            provenance_ids=tuple(str(x) for x in json.loads(data["provenance_ids"])),
            cost=int(data["cost"]),
        )

    def repair_rule(self) -> RepairRule:
        if self.op != "promote_repair_rule":
            raise ValueError("event does not contain a repair rule")
        data = dict(self.payload)
        return RepairRule(
            rule_id=self.target,
            obstruction_fingerprint=data["obstruction_fingerprint"],
            strategy_id=data["strategy_id"],
            strategy_version=data["strategy_version"],
            portfolio_digest=data["portfolio_digest"],
            authority_snapshot=data["authority_snapshot"],
            verifier_id=data["verifier_id"],
            interface_digest=data["interface_digest"],
            source_episode_digests=tuple(
                str(x) for x in json.loads(data["source_episode_digests"])
            ),
            source_episode_phases=tuple(
                str(x) for x in json.loads(data["source_episode_phases"])
            ),
            status=RepairRuleStatus(data["status"]),
            selection_cost=int(data["selection_cost"]),
            ablation_handle=data["ablation_handle"],
        )


class Ledger:
    """Immutable-event causal DAG with deterministic union merge.

    The ledger is evidence/history. MG/MG2 are compressed live projections.
    """

    def __init__(self, events: Iterable[Event] = ()):
        self.events: dict[str, Event] = {}
        for event in events:
            self._insert(event)

    def _insert(self, event: Event) -> Event:
        old = self.events.get(event.id)
        if old is not None and old != event:
            raise ValueError("content-address collision")
        self.events[event.id] = event
        return event

    @property
    def heads(self) -> tuple[str, ...]:
        parents = {p for event in self.events.values() for p in event.parents}
        return tuple(sorted(set(self.events) - parents))

    def append_add(
        self,
        law: Law,
        kernel: str,
        parents: Iterable[str] | None = None,
    ) -> Event:
        event = Event.add(law, kernel, self.heads if parents is None else parents)
        return self._insert(event)

    def append_revoke(
        self,
        target: str,
        kernel: str,
        reason: str = "",
        parents: Iterable[str] | None = None,
    ) -> Event:
        event = Event.revoke(
            target,
            kernel,
            self.heads if parents is None else parents,
            reason,
        )
        return self._insert(event)

    def append_promote_capability(
        self,
        capability: FiniteCapability,
        kernel: str,
        parents: Iterable[str] | None = None,
    ) -> Event:
        event = Event.promote_capability(
            capability,
            kernel,
            self.heads if parents is None else parents,
        )
        return self._insert(event)

    def append_revoke_capability(
        self,
        target: str,
        kernel: str,
        reason: str = "",
        parents: Iterable[str] | None = None,
    ) -> Event:
        event = Event.revoke_capability(
            target,
            kernel,
            self.heads if parents is None else parents,
            reason,
        )
        return self._insert(event)

    def append_promote_repair_rule(
        self,
        rule: RepairRule,
        kernel: str,
        parents: Iterable[str] | None = None,
    ) -> Event:
        event = Event.promote_repair_rule(
            rule,
            kernel,
            self.heads if parents is None else parents,
        )
        return self._insert(event)

    def append_revoke_repair_rule(
        self,
        target: str,
        kernel: str,
        reason: str = "",
        parents: Iterable[str] | None = None,
    ) -> Event:
        event = Event.revoke_repair_rule(
            target,
            kernel,
            self.heads if parents is None else parents,
            reason,
        )
        return self._insert(event)

    def merge(self, other: "Ledger") -> "Ledger":
        return Ledger((*self.events.values(), *other.events.values()))

    def contains(self, ancestor: str, descendant: str) -> bool:
        """True iff ancestor causally precedes descendant."""
        if ancestor == descendant:
            return True
        seen: set[str] = set()
        stack = [descendant]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            event = self.events.get(current)
            if event is None:
                continue
            if ancestor in event.parents:
                return True
            stack.extend(event.parents)
        return False

    def _maximal_events(self, op: str, target: str) -> list[Event]:
        events = [
            e for e in self.events.values()
            if e.op == op and e.target == target
        ]
        return [
            event
            for event in events
            if not any(
                event.id != later.id and self.contains(event.id, later.id)
                for later in events
            )
        ]

    def _maximal_adds(self, target: str) -> list[Event]:
        adds = [e for e in self.events.values() if e.op == "add" and e.target == target]
        revokes = [e for e in self.events.values() if e.op == "revoke" and e.target == target]

        live = [
            add
            for add in adds
            if not any(self.contains(add.id, revoke.id) for revoke in revokes)
        ]

        return [
            add
            for add in live
            if not any(
                add.id != later.id and self.contains(add.id, later.id)
                for later in live
            )
        ]

    def materialize(self, verifier: str = "") -> MG:
        laws: list[Law] = []
        targets = sorted({e.target for e in self.events.values() if e.op == "add"})
        for target in targets:
            versions = self._maximal_adds(target)
            unique: dict[tuple[str, str, str], Event] = {}
            for event in versions:
                law = event.law()
                unique[(law.expr, law.scope, law.provenance)] = event

            ordered = sorted(unique.values(), key=lambda e: e.id)
            for event in ordered:
                law = event.law()
                if len(ordered) == 1:
                    laws.append(law)
                else:
                    laws.append(
                        Law(
                            f"{target}~{event.id[:8]}",
                            law.expr,
                            law.scope,
                            law.provenance or event.id[:12],
                        )
                    )
        return MG(verifier, laws)

    def _typed_projection(
        self,
        *,
        promote_op: str,
        revoke_op: str,
        decode,
    ):
        records = []
        revocations = []

        targets = sorted({
            event.target
            for event in self.events.values()
            if event.op in {promote_op, revoke_op}
        })
        for target in targets:
            promotions = self._maximal_events(promote_op, target)
            if not promotions:
                continue

            decoded = [decode(event) for event in promotions]
            first = decoded[0]
            if any(item != first for item in decoded[1:]):
                raise ValueError(
                    f"causal identity conflict cannot compile to MG2: {target}"
                )

            revokes = [
                event for event in self.events.values()
                if event.op == revoke_op and event.target == target
            ]
            killed = [
                any(self.contains(promotion.id, revoke.id) for revoke in revokes)
                for promotion in promotions
            ]
            if killed and any(killed) and not all(killed):
                raise ValueError(
                    f"mixed causal revocation cannot compile to identity-level MG2: {target}"
                )

            records.append(first)
            if killed and all(killed):
                evidence = "|".join(sorted(revoke.id for revoke in revokes))
                revocations.append((target, evidence))

        return tuple(records), tuple(revocations)

    def materialize_compiled_present(self) -> CompiledPresent:
        """Compress representable causal history into canonical active QCKN state.

        Concurrent same-identity payload conflicts, or a revocation that kills
        only some concurrent versions of one identity, are deliberately refused:
        MG2 has identity-level active state and must not erase those distinctions.
        """

        capabilities, capability_revocations = self._typed_projection(
            promote_op="promote_capability",
            revoke_op="revoke_capability",
            decode=lambda event: event.capability(),
        )
        repair_rules, rule_revocations = self._typed_projection(
            promote_op="promote_repair_rule",
            revoke_op="revoke_repair_rule",
            decode=lambda event: event.repair_rule(),
        )

        graph = CapabilityGraph(tuple(capabilities))
        memory = MemoryGraphV2(
            capabilities=tuple(graph.capabilities),
            repair_rules=tuple(repair_rules),
            revocations=tuple(
                [
                    MemoryRevocation("capability", target, provenance)
                    for target, provenance in capability_revocations
                ]
                + [
                    MemoryRevocation("repair_rule", target, provenance)
                    for target, provenance in rule_revocations
                ]
            ),
        )
        return CompiledPresent(memory)

    def digest(self) -> str:
        ids = "\n".join(sorted(self.events))
        return hashlib.sha256(ids.encode()).hexdigest()[:16]

    def jsonl(self) -> str:
        rows = []
        for event_id in sorted(self.events):
            event = self.events[event_id]
            row = asdict(event)
            row["id"] = event_id
            row["parents"] = list(event.parents)
            row["payload"] = dict(event.payload)
            rows.append(json.dumps(row, sort_keys=True, separators=(",", ":")))
        return "\n".join(rows) + ("\n" if rows else "")
