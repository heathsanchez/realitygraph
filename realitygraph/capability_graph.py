from __future__ import annotations

from dataclasses import dataclass

from .capability import FiniteCapability


@dataclass(frozen=True)
class CapabilityGraph:
    capabilities: tuple[FiniteCapability, ...]
    revoked_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        ids = [capability.capability_id for capability in self.capabilities]
        if len(ids) != len(set(ids)):
            raise ValueError("capability IDs must be unique")
        known = set(ids)
        for capability in self.capabilities:
            missing = set(capability.dependencies) - known
            if missing:
                raise ValueError(f"capability has missing dependencies: {sorted(missing)}")
        if not set(self.revoked_ids).issubset(known):
            raise ValueError("revoked capability is not present in graph")
        self._topological_order()

    @property
    def capability_map(self) -> dict[str, FiniteCapability]:
        return {capability.capability_id: capability for capability in self.capabilities}

    def _topological_order(self) -> tuple[str, ...]:
        graph = {c.capability_id: set(c.dependencies) for c in self.capabilities}
        order: list[str] = []
        remaining = {key: set(value) for key, value in graph.items()}
        while remaining:
            ready = sorted(key for key, deps in remaining.items() if not deps)
            if not ready:
                raise ValueError("capability dependency cycle")
            for key in ready:
                order.append(key)
                remaining.pop(key)
            for deps in remaining.values():
                deps.difference_update(ready)
        return tuple(order)

    def active_ids(self) -> tuple[str, ...]:
        revoked = set(self.revoked_ids)
        active: list[str] = []
        active_set: set[str] = set()
        for ident in self._topological_order():
            capability = self.capability_map[ident]
            if ident in revoked:
                continue
            if any(dependency not in active_set for dependency in capability.dependencies):
                continue
            active.append(ident)
            active_set.add(ident)
        return tuple(active)

    def ablate(self, capability_id: str) -> "CapabilityGraph":
        if capability_id not in self.capability_map:
            raise ValueError(f"unknown capability: {capability_id}")
        revoked = tuple(sorted(set(self.revoked_ids) | {capability_id}))
        return CapabilityGraph(self.capabilities, revoked)
