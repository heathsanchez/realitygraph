from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .capability_graph import CapabilityGraph
from .developmental_types import ResultKind, canonical_digest, canonical_json
from .grammar import GrammarDelta


@dataclass(frozen=True)
class FrozenBoundary:
    world_manifest_digest: str
    obligation_ids: tuple[str, ...]
    language_digest: str
    substrate_digest: str
    verifier_digest: str
    protected_consequence_digest: str
    resource_envelope: str

    def __post_init__(self) -> None:
        if not self.world_manifest_digest or not self.language_digest:
            raise ValueError("frozen boundary requires manifest and language digests")
        if not self.substrate_digest or not self.verifier_digest:
            raise ValueError("frozen boundary requires substrate and verifier digests")
        if not self.protected_consequence_digest or not self.resource_envelope:
            raise ValueError("frozen boundary requires protected consequence and resource envelope")
        if not self.obligation_ids or len(self.obligation_ids) != len(set(self.obligation_ids)):
            raise ValueError("frozen boundary requires unique obligations")

    def payload(self) -> dict[str, Any]:
        return {
            "world_manifest_digest": self.world_manifest_digest,
            "obligation_ids": list(self.obligation_ids),
            "language_digest": self.language_digest,
            "substrate_digest": self.substrate_digest,
            "verifier_digest": self.verifier_digest,
            "protected_consequence_digest": self.protected_consequence_digest,
            "resource_envelope": self.resource_envelope,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="frozen-boundary-v1:")

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "FrozenBoundary":
        return cls(
            world_manifest_digest=str(payload["world_manifest_digest"]),
            obligation_ids=tuple(str(x) for x in payload["obligation_ids"]),
            language_digest=str(payload["language_digest"]),
            substrate_digest=str(payload["substrate_digest"]),
            verifier_digest=str(payload["verifier_digest"]),
            protected_consequence_digest=str(payload["protected_consequence_digest"]),
            resource_envelope=str(payload["resource_envelope"]),
        )


@dataclass(frozen=True)
class TerminalRecord:
    obligation_id: str
    kind: ResultKind
    certificate_digest: str
    replayable: bool
    detail: str = ""

    def payload(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "kind": self.kind.value,
            "certificate_digest": self.certificate_digest,
            "replayable": self.replayable,
            "detail": self.detail,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "TerminalRecord":
        return cls(
            obligation_id=str(payload["obligation_id"]),
            kind=ResultKind(str(payload["kind"])),
            certificate_digest=str(payload["certificate_digest"]),
            replayable=bool(payload["replayable"]),
            detail=str(payload.get("detail", "")),
        )


@dataclass(frozen=True)
class AdmissionEvidence:
    delta_id: str
    restart_evidence: str
    ablation_evidence: str

    def __post_init__(self) -> None:
        if not self.delta_id or not self.restart_evidence or not self.ablation_evidence:
            raise ValueError("admission evidence requires delta, restart, and ablation evidence")

    def payload(self) -> dict[str, str]:
        return {
            "delta_id": self.delta_id,
            "restart_evidence": self.restart_evidence,
            "ablation_evidence": self.ablation_evidence,
        }


@dataclass(frozen=True)
class ClosureCertificate:
    status: str
    boundary: FrozenBoundary
    terminal_records: tuple[TerminalRecord, ...]
    grammar_delta_ids: tuple[str, ...]
    active_capability_ids: tuple[str, ...]
    admission_evidence: tuple[AdmissionEvidence, ...]
    replay_digest: str

    def __post_init__(self) -> None:
        if self.status != "CLOSED_BOUNDED":
            raise ValueError("unsupported closure status")
        if not self.replay_digest:
            raise ValueError("closure certificate requires replay digest")

    def payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "boundary": self.boundary.payload(),
            "terminal_records": [record.payload() for record in self.terminal_records],
            "grammar_delta_ids": list(self.grammar_delta_ids),
            "active_capability_ids": list(self.active_capability_ids),
            "admission_evidence": [item.payload() for item in self.admission_evidence],
            "replay_digest": self.replay_digest,
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="closure-certificate-v1:")

    def text(self) -> str:
        return canonical_json({"version": "closure-certificate-v1", **self.payload()}) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "ClosureCertificate":
        payload = json.loads(text)
        if payload.pop("version", None) != "closure-certificate-v1":
            raise ValueError("unsupported closure certificate version")
        cert = cls(
            status=str(payload["status"]),
            boundary=FrozenBoundary.from_payload(payload["boundary"]),
            terminal_records=tuple(TerminalRecord.from_payload(row) for row in payload["terminal_records"]),
            grammar_delta_ids=tuple(str(x) for x in payload["grammar_delta_ids"]),
            active_capability_ids=tuple(str(x) for x in payload["active_capability_ids"]),
            admission_evidence=tuple(
                AdmissionEvidence(
                    str(row["delta_id"]),
                    str(row["restart_evidence"]),
                    str(row["ablation_evidence"]),
                )
                for row in payload["admission_evidence"]
            ),
            replay_digest=str(payload["replay_digest"]),
        )
        if cert.text() != text:
            raise ValueError("non-canonical closure certificate")
        return cert


def audit_closure(
    boundary: FrozenBoundary,
    terminal_records: tuple[TerminalRecord, ...],
    *,
    grammar_deltas: tuple[GrammarDelta, ...],
    capability_graph: CapabilityGraph,
    admission_evidence: tuple[AdmissionEvidence, ...],
    replay_digest: str,
) -> ClosureCertificate:
    if not replay_digest:
        raise ValueError("closure audit requires exact replay digest")
    expected = tuple(boundary.obligation_ids)
    observed = tuple(record.obligation_id for record in terminal_records)
    if len(observed) != len(set(observed)) or set(observed) != set(expected):
        raise ValueError("terminal records do not exactly cover frozen manifest")
    if any(not record.replayable for record in terminal_records):
        raise ValueError("non-replayable terminal record blocks closure")
    if any(record.kind is ResultKind.UNKNOWN_EXPRESSIVITY for record in terminal_records):
        raise ValueError("unresolved expressivity cannot terminate CLOSED_BOUNDED")

    allowed = {
        ResultKind.AUTHORIZED,
        ResultKind.COMPILED,
        ResultKind.REFUTED,
        ResultKind.NAMED_OBSTRUCTION,
        ResultKind.UNKNOWN_IDENTITY,
        ResultKind.UNKNOWN_CHOICE,
        ResultKind.UNKNOWN_SEARCH,
    }
    if any(record.kind not in allowed for record in terminal_records):
        raise ValueError("untyped or unsupported terminal record")

    delta_ids = tuple(delta.delta_id for delta in grammar_deltas)
    if len(delta_ids) != len(set(delta_ids)):
        raise ValueError("duplicate grammar delta in closure audit")
    evidence_map = {item.delta_id: item for item in admission_evidence}
    if len(evidence_map) != len(admission_evidence):
        raise ValueError("duplicate admission evidence")
    missing_evidence = set(delta_ids) - set(evidence_map)
    if missing_evidence:
        raise ValueError(f"structural admission lacks restart/ablation evidence: {sorted(missing_evidence)}")

    # Accessing active_ids revalidates the dependency closure represented by the graph.
    active = capability_graph.active_ids()
    return ClosureCertificate(
        status="CLOSED_BOUNDED",
        boundary=boundary,
        terminal_records=tuple(sorted(terminal_records, key=lambda row: row.obligation_id)),
        grammar_delta_ids=tuple(sorted(delta_ids)),
        active_capability_ids=tuple(active),
        admission_evidence=tuple(sorted(admission_evidence, key=lambda row: row.delta_id)),
        replay_digest=replay_digest,
    )
