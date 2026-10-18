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


def persistent_event_bytes(events: tuple[object, ...]) -> bytes:
    """Lossless canonical finite admission/revocation log; no closure state."""
    from dataclasses import asdict
    from .clc_lean import canonical_bytes
    records = []
    for e in events:
        if isinstance(e, CapabilityAdmissionEvent):
            if e.transport_claim is None:
                raise ValueError("missing CLC transport in persisted admission")
            records.append({"kind": "admit", "event_id": e.event_id,
                "capability": asdict(e.capability),
                "oracle": [list(x) for x in e.oracle],
                "support_ids": list(e.support_ids), "origin": e.origin,
                "transport_claim": e.transport_claim.payload()})
        elif isinstance(e, CapabilityRevocationEvent):
            records.append({"kind": "revoke", "event_id": e.event_id,
                            "capability_id": e.capability_id, "reason": e.reason})
        else:
            raise ValueError("unsupported persistent event kind")
    return canonical_bytes({"schema": "CLC_FLASH_PERSISTED_EVENTS_V1",
                            "events": records})


def replay_persistent_bytes(raw: bytes, *, expected_sha256: str,
                            obligations: tuple[LiveObligation, ...],
                            rules: tuple[FlashCompositionRule, ...],
                            checker: LeanCLCChecker):
    """Trusted expected content digest + exact typed reconstruction + fresh Lean.

    The digest is a caller-supplied trust anchor, NOT inferred from untrusted
    contents. Protected obligations/rules are externally frozen inputs.
    """
    import hashlib
    import json
    from .capability import FiniteCapability
    from .clc_lean import FiniteCLCForm, FiniteCLCTransport
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("persisted log digest mismatch")
    document = json.loads(raw)
    if set(document) != {"schema", "events"} or document["schema"] != "CLC_FLASH_PERSISTED_EVENTS_V1":
        raise ValueError("invalid persistent schema")
    def form(d):
        return FiniteCLCForm(tuple(d["states"]), tuple(d["tests"]),
                             tuple(d["protected"]), tuple(map(tuple, d["outcomes"])))
    events = []
    for r in document["events"]:
        if r["kind"] == "admit":
            if set(r) != {"kind", "event_id", "capability", "oracle",
                          "support_ids", "origin", "transport_claim"}:
                raise ValueError("unexpected admission fields")
            d = r["capability"]
            cap = FiniteCapability(d["capability_id"], d["input_type"],
                d["output_type"], tuple(map(tuple, d["semantics"])),
                tuple(d["guard_inputs"]), d["certificate_id"],
                tuple(d["dependencies"]), d["authority_snapshot"],
                d["verifier_id"], tuple(d["provenance_ids"]), d["cost"])
            c = r["transport_claim"]
            claim = FiniteCLCTransport(form(c["source"]), form(c["target"]),
                tuple(map(tuple,c["forward"])), tuple(map(tuple,c["pull"])),
                tuple(map(tuple,c["lift"])), c["authority_snapshot"],
                c["verifier_id"], c["input_type"], c["output_type"], c["strict"])
            events.append(CapabilityAdmissionEvent(r["event_id"], cap,
                tuple(map(tuple,r["oracle"])), tuple(r["support_ids"]),
                r["origin"], claim))
        elif r["kind"] == "revoke":
            if set(r) != {"kind", "event_id", "capability_id", "reason"}:
                raise ValueError("unexpected revocation fields")
            events.append(CapabilityRevocationEvent(
                r["event_id"],r["capability_id"],r["reason"]))
        else:
            raise ValueError("unsupported persistent event")
    if persistent_event_bytes(tuple(events)) != raw:
        raise ValueError("noncanonical persisted encoding")
    from copy import deepcopy
    # All state remains quarantined until the complete replay succeeds.
    return authenticated_replay(deepcopy(obligations), rules, tuple(events),
             checker, expected_log_digest=event_log_digest(tuple(events)))
