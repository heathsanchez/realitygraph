"""Reconstruct a gated FLASH closure exclusively through checked admissions.

This is replay of a frozen finite event log, not deserialization of trusted state.
"""
from __future__ import annotations
from .flash import (FlashClosure, FlashEventRuntime, CapabilityAdmissionEvent,
                    CapabilityRevocationEvent, LiveObligation, FlashCompositionRule)
from .clc_lean import LeanCLCChecker, sha


def authenticated_replay(obligations: tuple[LiveObligation, ...],
                         rules: tuple[FlashCompositionRule, ...],
                         events: tuple[object, ...],
                         checker: LeanCLCChecker,
                         *, expected_log_digest: str):
    """No live closure is returned until all events have revalidated."""
    rows = []
    for event in events:
        if isinstance(event, CapabilityAdmissionEvent):
            if event.transport_claim is None:
                raise ValueError("missing persistent CLC claim")
            rows.append({"kind": "admit", "id": event.event_id,
                         "capability": event.capability.__dict__,
                         "oracle": event.oracle,
                         "claim": event.transport_claim.payload(),
                         "support": event.support_ids})
        elif isinstance(event, CapabilityRevocationEvent):
            rows.append({"kind": "revoke", "id": event.event_id,
                         "capability": event.capability_id, "reason": event.reason})
        else:
            raise ValueError("unsupported persistent event")
    if sha(rows) != expected_log_digest:
        raise ValueError("persistent event log identity mismatch")
    closure = FlashClosure(obligations, composition_rules=rules,
                           kernel="clc-lean-v3", clc_checker=checker)
    runtime = FlashEventRuntime(closure)
    for event in events:
        runtime.apply(event)
    return closure, runtime


def event_log_digest(events):
    rows = []
    for event in events:
        if isinstance(event, CapabilityAdmissionEvent):
            if event.transport_claim is None:
                raise ValueError("missing persistent CLC claim")
            rows.append({"kind":"admit", "id":event.event_id,
                         "capability":event.capability.__dict__,
                         "oracle":event.oracle,
                         "claim":event.transport_claim.payload(),
                         "support":event.support_ids})
        elif isinstance(event, CapabilityRevocationEvent):
            rows.append({"kind":"revoke", "id":event.event_id,
                         "capability":event.capability_id, "reason":event.reason})
        else:
            raise ValueError("unsupported persistent event")
    return sha(rows)
