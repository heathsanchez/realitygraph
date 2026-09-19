from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DomainContract:
    domain: str
    authority_snapshot: str
    verifier_id: str

    def __post_init__(self) -> None:
        if not self.domain or not self.authority_snapshot or not self.verifier_id:
            raise ValueError("domain contract requires domain, authority, and verifier")


@dataclass(frozen=True)
class TypedCost:
    unit: str
    amount: float

    def __post_init__(self) -> None:
        if not self.unit:
            raise ValueError("typed cost requires unit")
        if self.amount < 0:
            raise ValueError("typed cost must be non-negative")


@dataclass(frozen=True)
class EvidenceEvent:
    event_id: str
    domain: str
    consequence_kind: str
    consequence_key: str
    authority_snapshot: str
    verifier_id: str
    provenance: str
    avoided_cost: TypedCost | None = None

    def __post_init__(self) -> None:
        if not all(
            (
                self.event_id,
                self.domain,
                self.consequence_kind,
                self.consequence_key,
                self.authority_snapshot,
                self.verifier_id,
                self.provenance,
            )
        ):
            raise ValueError("evidence event requires complete identity and provenance")


@dataclass(frozen=True)
class BridgeCertificate:
    bridge_id: str
    source_domain: str
    source_kind: str
    source_key: str
    destination_domain: str
    destination_kind: str
    destination_key: str
    bridge_authority_snapshot: str
    bridge_verifier_id: str
    certificate_id: str

    def __post_init__(self) -> None:
        if not all(
            (
                self.bridge_id,
                self.source_domain,
                self.source_kind,
                self.source_key,
                self.destination_domain,
                self.destination_kind,
                self.destination_key,
                self.bridge_authority_snapshot,
                self.bridge_verifier_id,
                self.certificate_id,
            )
        ):
            raise ValueError("bridge certificate requires complete exact boundary")


@dataclass(frozen=True, order=True)
class CrossDomainEdge:
    source_event_id: str
    source_domain: str
    destination_domain: str
    destination_kind: str
    destination_key: str
    bridge_id: str
    certificate_id: str


@dataclass(frozen=True)
class BusDelta:
    event_id: str
    affected_domains: tuple[str, ...]
    cross_domain_edges: tuple[CrossDomainEdge, ...]


class GlobalFlashBus:
    """Conservative cross-repo event router.

    Domain events enter only through their declared local authority. Cross-domain
    consequences exist only when an independently admitted exact bridge matches
    the event kind and key. Cost units remain typed and are never silently added.
    """

    def __init__(
        self,
        *,
        domain_contracts: Iterable[DomainContract],
        bridge_contract: DomainContract,
    ) -> None:
        contracts = tuple(domain_contracts)
        if not contracts:
            raise ValueError("global flash bus requires domain contracts")
        domains = [row.domain for row in contracts]
        if len(domains) != len(set(domains)):
            raise ValueError("domain contracts must be unique")
        if bridge_contract.domain != "bridge":
            raise ValueError("bridge contract must use bridge domain")
        self.domain_contracts = {row.domain: row for row in contracts}
        self.bridge_contract = bridge_contract
        self.events: dict[str, EvidenceEvent] = {}
        self.bridges: dict[str, BridgeCertificate] = {}
        self._edges: set[CrossDomainEdge] = set()

    def _event_contract_valid(self, event: EvidenceEvent) -> bool:
        contract = self.domain_contracts.get(event.domain)
        return bool(
            contract
            and contract.authority_snapshot == event.authority_snapshot
            and contract.verifier_id == event.verifier_id
        )

    def _bridge_contract_valid(self, bridge: BridgeCertificate) -> bool:
        return (
            bridge.bridge_authority_snapshot == self.bridge_contract.authority_snapshot
            and bridge.bridge_verifier_id == self.bridge_contract.verifier_id
            and bridge.source_domain in self.domain_contracts
            and bridge.destination_domain in self.domain_contracts
            and bridge.source_domain != bridge.destination_domain
        )

    @staticmethod
    def _matches(event: EvidenceEvent, bridge: BridgeCertificate) -> bool:
        return (
            event.domain == bridge.source_domain
            and event.consequence_kind == bridge.source_kind
            and event.consequence_key == bridge.source_key
        )

    def _materialize_for_event(self, event: EvidenceEvent) -> tuple[CrossDomainEdge, ...]:
        created: list[CrossDomainEdge] = []
        for bridge in self.bridges.values():
            if not self._matches(event, bridge):
                continue
            edge = CrossDomainEdge(
                source_event_id=event.event_id,
                source_domain=event.domain,
                destination_domain=bridge.destination_domain,
                destination_kind=bridge.destination_kind,
                destination_key=bridge.destination_key,
                bridge_id=bridge.bridge_id,
                certificate_id=bridge.certificate_id,
            )
            if edge not in self._edges:
                self._edges.add(edge)
                created.append(edge)
        return tuple(sorted(created))

    def admit_event(self, event: EvidenceEvent) -> BusDelta:
        if not self._event_contract_valid(event):
            raise ValueError("domain authority/verifier mismatch")
        old = self.events.get(event.event_id)
        if old is not None and old != event:
            raise ValueError("event identity conflict")
        self.events[event.event_id] = event
        created = self._materialize_for_event(event)
        affected = {event.domain}
        affected.update(edge.destination_domain for edge in created)
        return BusDelta(
            event_id=event.event_id,
            affected_domains=tuple(sorted(affected)),
            cross_domain_edges=created,
        )

    def admit_bridge(self, bridge: BridgeCertificate) -> tuple[CrossDomainEdge, ...]:
        if not self._bridge_contract_valid(bridge):
            raise ValueError("bridge authority/verifier mismatch")
        old = self.bridges.get(bridge.bridge_id)
        if old is not None and old != bridge:
            raise ValueError("bridge identity conflict")
        self.bridges[bridge.bridge_id] = bridge
        created: list[CrossDomainEdge] = []
        for event in self.events.values():
            created.extend(self._materialize_for_event(event))
        return tuple(sorted(set(created)))

    def cross_domain_edges(self) -> tuple[CrossDomainEdge, ...]:
        return tuple(sorted(self._edges))

    def avoided_costs_by_unit(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for event in self.events.values():
            if event.avoided_cost is None:
                continue
            unit = event.avoided_cost.unit
            totals[unit] = totals.get(unit, 0.0) + event.avoided_cost.amount
        return dict(sorted(totals.items()))

    def scalar_avoided_cost(self) -> float:
        totals = self.avoided_costs_by_unit()
        if len(totals) > 1:
            raise ValueError("typed costs require an explicit conversion contract")
        return next(iter(totals.values()), 0.0)
