from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Iterable

from .capability import FiniteCapability
from .flash import (
    FlashClosure,
    FlashDelta,
    FlashObstruction,
    FutureQuotient,
    ProtectedContinuation,
    QuotientDelta,
)


def _digest(payload: object, prefix: str = "flash-kernel-v1:") -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(prefix.encode() + raw).hexdigest()


@dataclass(frozen=True)
class KernelEvent:
    sequence: int
    kind: str
    event_id: str
    changed_obligations: tuple[str, ...] = ()
    changed_states: tuple[str, ...] = ()
    generated_capabilities: tuple[str, ...] = ()
    discharged: tuple[str, ...] = ()
    reopened: tuple[str, ...] = ()
    pruned_candidate_occurrences: int = 0
    flash_radius: int = 0
    closure_iterations: int = 0


class FlashKernel:
    """Thin global runtime over the frozen FlashClosure and FutureQuotient kernels.

    The object deliberately owns no proposer. Workers may speculate however they
    like. Shared developmental state mutates only through verifier-backed
    capability admissions, exact obstructions, protected continuations, or
    explicit revocation.
    """

    def __init__(
        self,
        closure: FlashClosure,
        *,
        quotients: dict[str, FutureQuotient] | None = None,
        kernel_id: str = "qckn-flash-kernel-v1",
    ) -> None:
        self.closure = closure
        self.quotients = dict(quotients or {})
        self.kernel_id = str(kernel_id)
        self.events: list[KernelEvent] = []
        self.initial_candidate_occurrences = sum(
            len(obligation.candidate_fingerprints)
            for obligation in self.closure.obligations.values()
        )

    def _append_flash(
        self,
        kind: str,
        event_id: str,
        delta: FlashDelta,
    ) -> KernelEvent:
        event = KernelEvent(
            sequence=len(self.events) + 1,
            kind=kind,
            event_id=event_id,
            changed_obligations=delta.changed_obligations,
            generated_capabilities=delta.generated_capabilities,
            discharged=delta.discharged,
            reopened=delta.reopened,
            pruned_candidate_occurrences=delta.pruned_candidate_occurrences,
            flash_radius=delta.flash_radius,
            closure_iterations=delta.iterations,
        )
        self.events.append(event)
        return event

    def _append_quotient(
        self,
        kind: str,
        event_id: str,
        delta: QuotientDelta,
    ) -> KernelEvent:
        event = KernelEvent(
            sequence=len(self.events) + 1,
            kind=kind,
            event_id=event_id,
            changed_states=delta.changed_state_ids,
            flash_radius=len(delta.changed_state_ids),
            closure_iterations=1,
        )
        self.events.append(event)
        return event

    def admit_capability(
        self,
        capability: FiniteCapability,
        *,
        oracle: tuple[tuple[str, str], ...],
        support_ids: Iterable[str] = (),
        origin: str = "verified-external",
    ) -> KernelEvent:
        delta = self.closure.admit_capability(
            capability,
            oracle=oracle,
            support_ids=support_ids,
            origin=origin,
        )
        return self._append_flash("capability", capability.capability_id, delta)

    def admit_obstruction(self, obstruction: FlashObstruction) -> KernelEvent:
        delta = self.closure.admit_obstruction(obstruction)
        return self._append_flash("obstruction", obstruction.obstruction_id, delta)

    def revoke_capability(self, capability_id: str, *, reason: str) -> KernelEvent:
        delta = self.closure.revoke_capability(capability_id, reason=reason)
        return self._append_flash("revocation", capability_id, delta)

    def admit_continuation(
        self,
        domain: str,
        continuation: ProtectedContinuation,
    ) -> KernelEvent:
        if domain not in self.quotients:
            raise KeyError(f"unknown quotient domain: {domain}")
        delta = self.quotients[domain].admit_continuation(continuation)
        return self._append_quotient(
            "continuation",
            f"{domain}:{continuation.continuation_id}",
            delta,
        )

    def revoke_continuation(
        self,
        domain: str,
        continuation_id: str,
        *,
        reason: str,
    ) -> KernelEvent:
        if domain not in self.quotients:
            raise KeyError(f"unknown quotient domain: {domain}")
        delta = self.quotients[domain].revoke_continuation(
            continuation_id,
            reason=reason,
        )
        return self._append_quotient(
            "continuation-revocation",
            f"{domain}:{continuation_id}",
            delta,
        )

    def pending_candidate_search(self) -> int:
        return sum(
            obligation.remaining_search()
            for obligation in self.closure.obligations.values()
        )

    def pruned_candidate_search(self) -> int:
        return sum(
            len(obligation.pruned_fingerprints)
            for obligation in self.closure.obligations.values()
        )

    def cancelled_candidate_search(self) -> int:
        return sum(
            obligation.cancelled_remaining_search
            for obligation in self.closure.obligations.values()
            if obligation.status == "DISCHARGED"
        )

    def current_search_eliminated(self) -> int:
        return (
            self.initial_candidate_occurrences
            - self.pending_candidate_search()
        )

    def open_worker_count(self) -> int:
        return len(self.closure.open_obligation_ids())

    def developmental_value_order(self) -> tuple[tuple[str, float], ...]:
        open_rows = [
            obligation
            for obligation in self.closure.obligations.values()
            if obligation.status == "OPEN"
        ]
        rows: list[tuple[str, float]] = []
        for obligation in open_rows:
            same_contract = [
                other
                for other in open_rows
                if other.contract_key == obligation.contract_key
            ]
            lateral_search = sum(other.remaining_search() for other in same_contract)
            local_cost = max(1, obligation.remaining_search())
            domain_count = len({other.domain for other in same_contract})
            score = float(lateral_search * max(1, domain_count)) / float(local_cost)
            rows.append((obligation.obligation_id, score))
        return tuple(sorted(rows, key=lambda row: (-row[1], row[0])))

    def graph_edges(self) -> tuple[tuple[str, str, str], ...]:
        edges: set[tuple[str, str, str]] = set()
        for capability_id, record in self.closure.capabilities.items():
            for support_id in record.support_ids:
                edges.add((f"cap:{support_id}", f"cap:{capability_id}", "supports"))
            origin = record.origin
            if origin.startswith("composition:"):
                edges.add((origin, f"cap:{capability_id}", "generated"))
        for obligation in self.closure.obligations.values():
            if obligation.solved_by:
                edges.add(
                    (
                        f"cap:{obligation.solved_by}",
                        f"obligation:{obligation.obligation_id}",
                        "discharges",
                    )
                )
            for obstruction in self.closure.obstructions.values():
                if (
                    obstruction.contract_key == obligation.contract_key
                    and obstruction.candidate_fingerprint
                    in obligation.pruned_fingerprints
                ):
                    edges.add(
                        (
                            f"obstruction:{obstruction.obstruction_id}",
                            f"obligation:{obligation.obligation_id}",
                            "prunes",
                        )
                    )
        for domain, quotient in self.quotients.items():
            for continuation_id in quotient.continuations:
                for state_id in quotient.states:
                    edges.add(
                        (
                            f"continuation:{domain}:{continuation_id}",
                            f"state:{domain}:{state_id}",
                            "distinguishes",
                        )
                    )
        return tuple(sorted(edges))

    def snapshot(self) -> dict[str, object]:
        payload = {
            "schema": self.kernel_id,
            "initial_candidate_occurrences": self.initial_candidate_occurrences,
            "pending_candidate_search": self.pending_candidate_search(),
            "pruned_candidate_search": self.pruned_candidate_search(),
            "cancelled_candidate_search": self.cancelled_candidate_search(),
            "current_search_eliminated": self.current_search_eliminated(),
            "open_worker_count": self.open_worker_count(),
            "active_capabilities": list(self.closure.active_capability_ids()),
            "open_obligations": list(self.closure.open_obligation_ids()),
            "discharged_obligations": list(
                self.closure.discharged_obligation_ids()
            ),
            "developmental_value_order": [
                [obligation_id, score]
                for obligation_id, score in self.developmental_value_order()
            ],
            "quotients": {
                domain: [list(group) for group in quotient.classes()]
                for domain, quotient in sorted(self.quotients.items())
            },
            "events": [asdict(event) for event in self.events],
            "edges": [list(edge) for edge in self.graph_edges()],
        }
        payload["digest"] = _digest(payload)
        return payload
