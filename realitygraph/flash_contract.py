from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
import json
from pathlib import Path
from typing import Any, Iterable


class FlashEventKind(str, Enum):
    VERIFIED_EQUIVALENCE = "VERIFIED_EQUIVALENCE"
    VERIFIED_SEPARATOR = "VERIFIED_SEPARATOR"
    PROMOTED_CAPABILITY = "PROMOTED_CAPABILITY"
    OBSTRUCTION = "OBSTRUCTION"
    PREFERENCE_CHANGE = "PREFERENCE_CHANGE"
    REVOCATION = "REVOCATION"


@dataclass(frozen=True)
class FlashEvent:
    event_id: str
    kind: FlashEventKind
    source_domain: str
    consequence_key: str
    authority: str
    provenance: tuple[str, ...]
    supersedes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not all((self.event_id, self.source_domain, self.consequence_key, self.authority)):
            raise ValueError("Flash event requires complete identity")
        if len(self.provenance) != len(set(self.provenance)):
            raise ValueError("event provenance must be unique")
        if self.event_id in self.supersedes:
            raise ValueError("event cannot supersede itself")


@dataclass(frozen=True)
class CapabilityState:
    capability_id: str
    semantic_status: str
    economic_status: str
    evidence_id: str
    reason: str

    def __post_init__(self) -> None:
        if self.semantic_status not in {"VERIFIED", "UNKNOWN", "REFUTED"}:
            raise ValueError("unsupported semantic status")
        if self.economic_status not in {"ACTIVE", "RESERVE", "REJECTED"}:
            raise ValueError("unsupported economic status")
        if self.semantic_status != "VERIFIED" and self.economic_status == "ACTIVE":
            raise ValueError("unverified capability cannot be economically active")


@dataclass
class FrontierState:
    frontier_id: str
    domain: str
    base_search_cost: int
    search_cost: int
    route_ids: set[str] = field(default_factory=set)
    base_route_ids: set[str] = field(default_factory=set)
    active_capabilities: set[str] = field(default_factory=set)
    reserve_capabilities: set[str] = field(default_factory=set)
    separators: set[str] = field(default_factory=set)
    obstructions: set[str] = field(default_factory=set)
    touched: int = 0

    def snapshot(self) -> dict[str, Any]:
        return {
            "frontier_id": self.frontier_id,
            "domain": self.domain,
            "base_search_cost": self.base_search_cost,
            "search_cost": self.search_cost,
            "route_ids": sorted(self.route_ids),
            "base_route_ids": sorted(self.base_route_ids),
            "active_capabilities": sorted(self.active_capabilities),
            "reserve_capabilities": sorted(self.reserve_capabilities),
            "separators": sorted(self.separators),
            "obstructions": sorted(self.obstructions),
            "touched": self.touched,
        }


@dataclass(frozen=True)
class DependencyRule:
    rule_id: str
    consequence_key: str
    target_frontier: str
    action: str
    value: str | int | float
    support_event_id: str | None = None


@dataclass(frozen=True)
class ClosureDelta:
    event_id: str
    touched_frontiers: tuple[str, ...]
    changed_frontiers: tuple[str, ...]
    emitted_event_ids: tuple[str, ...]
    iterations: int


class IncrementalFlashRuntime:
    """Small provenance-aware runtime for the six Flash V1 implementation invariants.

    This runtime is intentionally explicit. It never scans or mutates unrelated
    frontiers: only rules indexed by the admitted event consequence key are
    considered. Revocation recomputes the affected dependency cone from surviving
    active events, preserving provenance and allowing previously removed routes to
    reappear.
    """

    def __init__(
        self,
        frontiers: Iterable[FrontierState],
        rules: Iterable[DependencyRule],
        capabilities: Iterable[CapabilityState] = (),
    ) -> None:
        rows = tuple(frontiers)
        if len({x.frontier_id for x in rows}) != len(rows):
            raise ValueError("frontier identities must be unique")
        self.frontiers = {x.frontier_id: x for x in rows}
        self.rules = tuple(rules)
        self.rules_by_key: dict[str, list[DependencyRule]] = {}
        for rule in self.rules:
            if rule.target_frontier not in self.frontiers:
                raise ValueError("rule targets unknown frontier")
            self.rules_by_key.setdefault(rule.consequence_key, []).append(rule)
        self.capabilities = {c.capability_id: c for c in capabilities}
        self.events: dict[str, FlashEvent] = {}
        self.active_event_ids: set[str] = set()
        self.history: list[dict[str, Any]] = []
        self.replayed_events_on_restart = 0

    def _reset_frontier(self, frontier: FrontierState) -> None:
        frontier.search_cost = frontier.base_search_cost
        frontier.route_ids = set(frontier.base_route_ids)
        frontier.active_capabilities.clear()
        frontier.reserve_capabilities.clear()
        frontier.separators.clear()
        frontier.obstructions.clear()

    def _apply_rule(self, rule: DependencyRule) -> bool:
        f = self.frontiers[rule.target_frontier]
        before = f.snapshot()

        if rule.action == "reduce_search":
            f.search_cost = max(0, f.search_cost - int(rule.value))
        elif rule.action == "remove_route":
            f.route_ids.discard(str(rule.value))
        elif rule.action == "add_route":
            f.route_ids.add(str(rule.value))
        elif rule.action == "activate_capability":
            cid = str(rule.value)
            cap = self.capabilities[cid]
            if cap.semantic_status != "VERIFIED":
                raise ValueError("cannot activate unverified capability")
            if cap.economic_status == "ACTIVE":
                f.active_capabilities.add(cid)
                f.reserve_capabilities.discard(cid)
            else:
                f.reserve_capabilities.add(cid)
                f.active_capabilities.discard(cid)
        elif rule.action == "reserve_capability":
            cid = str(rule.value)
            f.reserve_capabilities.add(cid)
            f.active_capabilities.discard(cid)
        elif rule.action == "add_separator":
            f.separators.add(str(rule.value))
        elif rule.action == "add_obstruction":
            f.obstructions.add(str(rule.value))
        else:
            raise ValueError(f"unknown dependency action {rule.action}")

        f.touched += 1
        return before != f.snapshot()

    def admit(self, event: FlashEvent) -> ClosureDelta:
        old = self.events.get(event.event_id)
        if old is not None and old != event:
            raise ValueError("event identity conflict")
        if old == event and event.event_id in self.active_event_ids:
            delta = ClosureDelta(
                event_id=event.event_id,
                touched_frontiers=(),
                changed_frontiers=(),
                emitted_event_ids=(),
                iterations=0,
            )
            self.history.append({"kind": "idempotent-admit", **asdict(delta)})
            return delta
        self.events[event.event_id] = event
        for superseded in event.supersedes:
            self.active_event_ids.discard(superseded)
        self.active_event_ids.add(event.event_id)

        queue = [event]
        touched: set[str] = set()
        changed: set[str] = set()
        emitted: list[str] = []
        iterations = 0

        while queue:
            current = queue.pop(0)
            iterations += 1
            for rule in self.rules_by_key.get(current.consequence_key, ()):
                touched.add(rule.target_frontier)
                if self._apply_rule(rule):
                    changed.add(rule.target_frontier)

        delta = ClosureDelta(
            event_id=event.event_id,
            touched_frontiers=tuple(sorted(touched)),
            changed_frontiers=tuple(sorted(changed)),
            emitted_event_ids=tuple(emitted),
            iterations=iterations,
        )
        self.history.append({"kind": "admit", **asdict(delta)})
        return delta

    def revoke(self, event_id: str, *, reason: str) -> ClosureDelta:
        if event_id not in self.active_event_ids:
            raise KeyError("cannot revoke inactive event")
        event = self.events[event_id]
        affected = {
            r.target_frontier for r in self.rules_by_key.get(event.consequence_key, ())
        }
        self.active_event_ids.remove(event_id)

        for fid in affected:
            self._reset_frontier(self.frontiers[fid])

        surviving = [
            self.events[eid]
            for eid in sorted(self.active_event_ids)
            if any(
                r.target_frontier in affected
                for r in self.rules_by_key.get(self.events[eid].consequence_key, ())
            )
        ]
        for survivor in surviving:
            for rule in self.rules_by_key.get(survivor.consequence_key, ()):
                if rule.target_frontier in affected:
                    self._apply_rule(rule)

        delta = ClosureDelta(
            event_id=f"REVOCATION:{event_id}",
            touched_frontiers=tuple(sorted(affected)),
            changed_frontiers=tuple(sorted(affected)),
            emitted_event_ids=(),
            iterations=1 + len(surviving),
        )
        self.history.append(
            {
                "kind": "revocation",
                "revoked_event_id": event_id,
                "reason": reason,
                **asdict(delta),
            }
        )
        return delta

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": "incremental-flash-runtime-v1",
            "frontiers": {
                key: value.snapshot()
                for key, value in sorted(self.frontiers.items())
            },
            "capabilities": {
                key: asdict(value)
                for key, value in sorted(self.capabilities.items())
            },
            "events": {
                key: {
                    **asdict(value),
                    "kind": value.kind.value,
                }
                for key, value in sorted(self.events.items())
            },
            "active_event_ids": sorted(self.active_event_ids),
            "history": list(self.history),
            "replayed_events_on_restart": self.replayed_events_on_restart,
        }

    def save_compiled_present(self, path: Path) -> None:
        path.write_text(json.dumps(self.snapshot(), indent=2, sort_keys=True) + "\n")

    @classmethod
    def load_compiled_present(
        cls,
        path: Path,
        rules: Iterable[DependencyRule],
    ) -> "IncrementalFlashRuntime":
        data = json.loads(path.read_text())
        frontiers = []
        for row in data["frontiers"].values():
            frontiers.append(
                FrontierState(
                    frontier_id=row["frontier_id"],
                    domain=row["domain"],
                    base_search_cost=int(row["base_search_cost"]),
                    search_cost=int(row["search_cost"]),
                    route_ids=set(row["route_ids"]),
                    base_route_ids=set(row.get("base_route_ids", row["route_ids"])),
                    active_capabilities=set(row["active_capabilities"]),
                    reserve_capabilities=set(row["reserve_capabilities"]),
                    separators=set(row["separators"]),
                    obstructions=set(row["obstructions"]),
                    touched=int(row["touched"]),
                )
            )
        capabilities = [
            CapabilityState(**row)
            for row in data["capabilities"].values()
        ]
        runtime = cls(frontiers, rules, capabilities)
        runtime.events = {
            key: FlashEvent(
                event_id=row["event_id"],
                kind=FlashEventKind(row["kind"]),
                source_domain=row["source_domain"],
                consequence_key=row["consequence_key"],
                authority=row["authority"],
                provenance=tuple(row["provenance"]),
                supersedes=tuple(row.get("supersedes", ())),
            )
            for key, row in data["events"].items()
        }
        runtime.active_event_ids = set(data["active_event_ids"])
        runtime.history = list(data.get("history", []))
        runtime.replayed_events_on_restart = 0
        return runtime
