from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Iterable

from .attack import AttackStatus, exhaustive_attack
from .capability import FiniteCapability, compose_capabilities
from .capability_graph import CapabilityGraph
from .compiled_present import CompiledPresent
from .ledger import Ledger
from .meta_memory import MetaMemory


def _digest(payload: object, prefix: str) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(prefix.encode() + raw).hexdigest()


@dataclass(frozen=True)
class PresentState:
    state_id: str
    provenance_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.state_id:
            raise ValueError("present state requires identity")
        if len(self.provenance_ids) != len(set(self.provenance_ids)):
            raise ValueError("present state provenance IDs must be unique")


@dataclass(frozen=True)
class ProtectedContinuation:
    continuation_id: str
    outcomes: tuple[tuple[str, str], ...]
    authority_snapshot: str
    verifier_id: str

    def __post_init__(self) -> None:
        if not self.continuation_id:
            raise ValueError("protected continuation requires identity")
        if not self.authority_snapshot or not self.verifier_id:
            raise ValueError("protected continuation requires authority and verifier")
        state_ids = [str(state_id) for state_id, _ in self.outcomes]
        if not state_ids or len(state_ids) != len(set(state_ids)):
            raise ValueError("protected continuation requires unique state outcomes")

    @property
    def outcome_map(self) -> dict[str, str]:
        return {str(state_id): str(outcome) for state_id, outcome in self.outcomes}


@dataclass(frozen=True)
class QuotientDelta:
    previous_classes: tuple[tuple[str, ...], ...]
    current_classes: tuple[tuple[str, ...], ...]
    split_classes: tuple[tuple[str, ...], ...]
    merged_classes: tuple[tuple[str, ...], ...]
    changed_state_ids: tuple[str, ...]


class FutureQuotient:
    """Present identity induced only by currently protected future consequences."""

    def __init__(
        self,
        states: Iterable[PresentState],
        *,
        authority_snapshot: str,
        verifier_id: str,
    ) -> None:
        rows = tuple(states)
        state_ids = [row.state_id for row in rows]
        if not state_ids or len(state_ids) != len(set(state_ids)):
            raise ValueError("future quotient requires unique present states")
        if not authority_snapshot or not verifier_id:
            raise ValueError("future quotient requires authority and verifier")
        self.states = {row.state_id: row for row in rows}
        self.authority_snapshot = str(authority_snapshot)
        self.verifier_id = str(verifier_id)
        self.continuations: dict[str, ProtectedContinuation] = {}

    def _signature(self, state_id: str) -> tuple[str, ...]:
        if state_id not in self.states:
            raise ValueError(f"unknown present state: {state_id}")
        return tuple(
            self.continuations[continuation_id].outcome_map[state_id]
            for continuation_id in sorted(self.continuations)
        )

    def classes(self) -> tuple[tuple[str, ...], ...]:
        buckets: dict[tuple[str, ...], list[str]] = {}
        for state_id in sorted(self.states):
            buckets.setdefault(self._signature(state_id), []).append(state_id)
        classes = tuple(tuple(state_ids) for state_ids in buckets.values())
        return tuple(sorted(classes))

    def equivalent(self, left: str, right: str) -> bool:
        return self._signature(left) == self._signature(right)

    @staticmethod
    def _changed_states(
        previous: tuple[tuple[str, ...], ...],
        current: tuple[tuple[str, ...], ...],
    ) -> tuple[str, ...]:
        previous_class = {
            state_id: group
            for group in previous
            for state_id in group
        }
        current_class = {
            state_id: group
            for group in current
            for state_id in group
        }
        return tuple(
            sorted(
                state_id
                for state_id in previous_class
                if previous_class[state_id] != current_class[state_id]
            )
        )

    @staticmethod
    def _split_classes(
        previous: tuple[tuple[str, ...], ...],
        current: tuple[tuple[str, ...], ...],
    ) -> tuple[tuple[str, ...], ...]:
        current_sets = tuple(set(group) for group in current)
        split = [
            group
            for group in previous
            if sum(bool(set(group) & current_group) for current_group in current_sets) > 1
        ]
        return tuple(sorted(split))

    @staticmethod
    def _merged_classes(
        previous: tuple[tuple[str, ...], ...],
        current: tuple[tuple[str, ...], ...],
    ) -> tuple[tuple[str, ...], ...]:
        previous_sets = tuple(set(group) for group in previous)
        merged = [
            group
            for group in current
            if sum(bool(set(group) & previous_group) for previous_group in previous_sets) > 1
        ]
        return tuple(sorted(merged))

    def _delta(
        self,
        previous: tuple[tuple[str, ...], ...],
        *,
        suppress_structural_labels: bool = False,
    ) -> QuotientDelta:
        current = self.classes()
        return QuotientDelta(
            previous_classes=previous,
            current_classes=current,
            split_classes=() if suppress_structural_labels else self._split_classes(previous, current),
            merged_classes=() if suppress_structural_labels else self._merged_classes(previous, current),
            changed_state_ids=self._changed_states(previous, current),
        )

    def admit_continuation(
        self,
        continuation: ProtectedContinuation,
    ) -> QuotientDelta:
        if (
            continuation.authority_snapshot != self.authority_snapshot
            or continuation.verifier_id != self.verifier_id
        ):
            raise ValueError("protected continuation authority/verifier mismatch")
        if set(continuation.outcome_map) != set(self.states):
            raise ValueError("protected continuation must cover exact present-state carrier")

        previous = self.classes()
        had_continuations = bool(self.continuations)
        old = self.continuations.get(continuation.continuation_id)
        if old is not None and old != continuation:
            raise ValueError("protected continuation identity conflict")
        self.continuations[continuation.continuation_id] = continuation
        return self._delta(
            previous,
            suppress_structural_labels=not had_continuations,
        )

    def revoke_continuation(
        self,
        continuation_id: str,
        *,
        reason: str,
    ) -> QuotientDelta:
        if not reason:
            raise ValueError("continuation revocation requires reason")
        if continuation_id not in self.continuations:
            raise ValueError("cannot revoke unknown protected continuation")
        previous = self.classes()
        del self.continuations[continuation_id]
        return self._delta(previous)


@dataclass(frozen=True)
class FlashContract:
    authority_snapshot: str
    verifier_id: str

    def __post_init__(self) -> None:
        if not self.authority_snapshot or not self.verifier_id:
            raise ValueError("flash contract requires authority and verifier")

    @property
    def key(self) -> tuple[str, str]:
        return (self.authority_snapshot, self.verifier_id)


@dataclass(frozen=True)
class FlashObstruction:
    obstruction_id: str
    input_type: str
    output_type: str
    contract: FlashContract
    candidate_fingerprint: str
    separating_input: str
    expected_output: str
    actual_output: str
    provenance: str = ""

    def __post_init__(self) -> None:
        if not self.obstruction_id or not self.candidate_fingerprint:
            raise ValueError("obstruction requires identity and candidate fingerprint")
        if not self.input_type or not self.output_type:
            raise ValueError("obstruction requires interface types")
        if not self.separating_input:
            raise ValueError("obstruction requires separating input")
        if self.expected_output == self.actual_output:
            raise ValueError("obstruction must contain a real separation")

    @property
    def contract_key(self) -> tuple[str, str, str, str]:
        return (
            self.input_type,
            self.output_type,
            self.contract.authority_snapshot,
            self.contract.verifier_id,
        )


@dataclass(frozen=True)
class FlashCompositionRule:
    rule_id: str
    first_capability_id: str
    second_capability_id: str
    result_capability_id: str
    oracle: tuple[tuple[str, str], ...]
    certificate_id: str

    def __post_init__(self) -> None:
        if not all(
            (
                self.rule_id,
                self.first_capability_id,
                self.second_capability_id,
                self.result_capability_id,
                self.certificate_id,
            )
        ):
            raise ValueError("composition rule requires stable identities")
        keys = [key for key, _ in self.oracle]
        if not keys or len(keys) != len(set(keys)):
            raise ValueError("composition rule requires a unique finite oracle")


@dataclass
class LiveObligation:
    obligation_id: str
    input_type: str
    source_input_type: str
    output_type: str
    oracle: tuple[tuple[str, str], ...]
    transport_to_source: tuple[tuple[str, str], ...]
    contract: FlashContract
    candidate_fingerprints: tuple[str, ...] = ()
    domain: str = ""
    status: str = "OPEN"
    solved_by: str | None = None
    support_ids: tuple[str, ...] = ()
    searched_fingerprints: list[str] = field(default_factory=list)
    pruned_fingerprints: set[str] = field(default_factory=set)
    worker_cancelled: bool = False
    cancelled_remaining_search: int = 0
    reopen_count: int = 0

    def __post_init__(self) -> None:
        if not self.obligation_id:
            raise ValueError("obligation requires identity")
        if not self.input_type or not self.source_input_type or not self.output_type:
            raise ValueError("obligation requires interface types")
        oracle_keys = [str(key) for key, _ in self.oracle]
        if not oracle_keys or len(oracle_keys) != len(set(oracle_keys)):
            raise ValueError("obligation requires a unique finite oracle")
        transport = dict(self.transport_to_source)
        if set(oracle_keys) != set(transport):
            raise ValueError("transport must cover the exact target oracle carrier")
        if len(self.candidate_fingerprints) != len(set(self.candidate_fingerprints)):
            raise ValueError("candidate fingerprints must be unique")

    @property
    def oracle_map(self) -> dict[str, str]:
        return {str(key): str(value) for key, value in self.oracle}

    @property
    def transport_map(self) -> dict[str, str]:
        return {str(key): str(value) for key, value in self.transport_to_source}

    @property
    def contract_key(self) -> tuple[str, str, str, str]:
        return (
            self.source_input_type,
            self.output_type,
            self.contract.authority_snapshot,
            self.contract.verifier_id,
        )

    def remaining_search(self) -> int:
        if self.status == "DISCHARGED":
            return 0
        searched = set(self.searched_fingerprints)
        return sum(
            fingerprint not in searched and fingerprint not in self.pruned_fingerprints
            for fingerprint in self.candidate_fingerprints
        )


@dataclass(frozen=True)
class CapabilityRecord:
    capability: FiniteCapability
    support_ids: tuple[str, ...]
    origin: str


@dataclass(frozen=True)
class FlashDelta:
    iterations: int
    discharged: tuple[str, ...]
    reopened: tuple[str, ...]
    generated_capabilities: tuple[str, ...]
    pruned_candidate_occurrences: int
    changed_obligations: tuple[str, ...]
    flash_radius: int
    restored_candidate_occurrences: int = 0


@dataclass(frozen=True)
class CapabilityAdmissionEvent:
    event_id: str
    capability: FiniteCapability
    oracle: tuple[tuple[str, str], ...]
    support_ids: tuple[str, ...] = ()
    origin: str = "verified-external"


@dataclass(frozen=True)
class ObstructionAdmissionEvent:
    event_id: str
    obstruction: FlashObstruction


@dataclass(frozen=True)
class CapabilityRevocationEvent:
    event_id: str
    capability_id: str
    reason: str


@dataclass(frozen=True)
class ObstructionRevocationEvent:
    event_id: str
    obstruction_id: str
    reason: str


@dataclass(frozen=True)
class ExternalEventEnvelope:
    schema: str
    event_id: str
    event_kind: str
    repository: str
    commit: str
    authority_snapshot: str
    verifier_id: str
    source_evidence_sha256: str
    payload: dict[str, object]
    payload_sha256: str

    SCHEMA = "qckn-flash-external-event-v1"

    @staticmethod
    def _canonical_payload(payload: dict[str, object]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def _payload_digest(cls, payload: dict[str, object]) -> str:
        return hashlib.sha256(cls._canonical_payload(payload).encode()).hexdigest()

    @staticmethod
    def _source_digest(source_evidence: bytes) -> str:
        return hashlib.sha256(source_evidence).hexdigest()

    @staticmethod
    def _valid_commit(commit: str) -> bool:
        return len(commit) == 40 and all(ch in "0123456789abcdef" for ch in commit)

    @classmethod
    def _build(
        cls,
        *,
        event_id: str,
        event_kind: str,
        repository: str,
        commit: str,
        authority_snapshot: str,
        verifier_id: str,
        source_evidence: bytes,
        payload: dict[str, object],
    ) -> "ExternalEventEnvelope":
        if not event_id or not repository or "/" not in repository:
            raise ValueError("external event requires identity and repository")
        if not cls._valid_commit(commit):
            raise ValueError("external event requires full lowercase commit SHA")
        if not authority_snapshot or not verifier_id:
            raise ValueError("external event requires authority and verifier")
        return cls(
            schema=cls.SCHEMA,
            event_id=event_id,
            event_kind=event_kind,
            repository=repository,
            commit=commit,
            authority_snapshot=authority_snapshot,
            verifier_id=verifier_id,
            source_evidence_sha256=cls._source_digest(source_evidence),
            payload=payload,
            payload_sha256=cls._payload_digest(payload),
        )

    @classmethod
    def capability(
        cls,
        *,
        event_id: str,
        repository: str,
        commit: str,
        authority_snapshot: str,
        verifier_id: str,
        source_evidence: bytes,
        capability: dict[str, object],
        oracle: list[list[str]],
        support_ids: list[str] | None = None,
        origin: str = "verified-external",
    ) -> "ExternalEventEnvelope":
        payload: dict[str, object] = {
            "capability": capability,
            "oracle": oracle,
            "support_ids": list(support_ids or []),
            "origin": origin,
        }
        return cls._build(
            event_id=event_id,
            event_kind="capability_admission",
            repository=repository,
            commit=commit,
            authority_snapshot=authority_snapshot,
            verifier_id=verifier_id,
            source_evidence=source_evidence,
            payload=payload,
        )

    @classmethod
    def obstruction(
        cls,
        *,
        event_id: str,
        repository: str,
        commit: str,
        authority_snapshot: str,
        verifier_id: str,
        source_evidence: bytes,
        obstruction: dict[str, object],
    ) -> "ExternalEventEnvelope":
        payload: dict[str, object] = {"obstruction": obstruction}
        return cls._build(
            event_id=event_id,
            event_kind="obstruction_admission",
            repository=repository,
            commit=commit,
            authority_snapshot=authority_snapshot,
            verifier_id=verifier_id,
            source_evidence=source_evidence,
            payload=payload,
        )

    @classmethod
    def capability_revocation(
        cls,
        *,
        event_id: str,
        repository: str,
        commit: str,
        authority_snapshot: str,
        verifier_id: str,
        source_evidence: bytes,
        capability_id: str,
        reason: str,
    ) -> "ExternalEventEnvelope":
        if not capability_id or not reason:
            raise ValueError("capability revocation requires identity and reason")
        payload: dict[str, object] = {
            "capability_id": capability_id,
            "reason": reason,
        }
        return cls._build(
            event_id=event_id,
            event_kind="capability_revocation",
            repository=repository,
            commit=commit,
            authority_snapshot=authority_snapshot,
            verifier_id=verifier_id,
            source_evidence=source_evidence,
            payload=payload,
        )

    @classmethod
    def obstruction_revocation(
        cls,
        *,
        event_id: str,
        repository: str,
        commit: str,
        authority_snapshot: str,
        verifier_id: str,
        source_evidence: bytes,
        obstruction_id: str,
        reason: str,
    ) -> "ExternalEventEnvelope":
        if not obstruction_id or not reason:
            raise ValueError("obstruction revocation requires identity and reason")
        payload: dict[str, object] = {
            "obstruction_id": obstruction_id,
            "reason": reason,
        }
        return cls._build(
            event_id=event_id,
            event_kind="obstruction_revocation",
            repository=repository,
            commit=commit,
            authority_snapshot=authority_snapshot,
            verifier_id=verifier_id,
            source_evidence=source_evidence,
            payload=payload,
        )

    def _plain(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "event_id": self.event_id,
            "event_kind": self.event_kind,
            "repository": self.repository,
            "commit": self.commit,
            "authority_snapshot": self.authority_snapshot,
            "verifier_id": self.verifier_id,
            "source_evidence_sha256": self.source_evidence_sha256,
            "payload": self.payload,
            "payload_sha256": self.payload_sha256,
        }

    def to_text(self) -> str:
        return json.dumps(self._plain(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_text(cls, text: str) -> "ExternalEventEnvelope":
        try:
            row = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid external flash event") from exc
        if not isinstance(row, dict) or row.get("schema") != cls.SCHEMA:
            raise ValueError("unsupported external flash event schema")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("invalid external flash event payload")
        expected_payload_digest = cls._payload_digest(payload)
        if row.get("payload_sha256") != expected_payload_digest:
            raise ValueError("external flash event payload digest mismatch")
        envelope = cls(
            schema=str(row["schema"]),
            event_id=str(row.get("event_id", "")),
            event_kind=str(row.get("event_kind", "")),
            repository=str(row.get("repository", "")),
            commit=str(row.get("commit", "")),
            authority_snapshot=str(row.get("authority_snapshot", "")),
            verifier_id=str(row.get("verifier_id", "")),
            source_evidence_sha256=str(row.get("source_evidence_sha256", "")),
            payload=payload,
            payload_sha256=str(row.get("payload_sha256", "")),
        )
        if (
            not envelope.event_id
            or "/" not in envelope.repository
            or not cls._valid_commit(envelope.commit)
            or not envelope.authority_snapshot
            or not envelope.verifier_id
            or len(envelope.source_evidence_sha256) != 64
        ):
            raise ValueError("invalid external flash event metadata")
        if envelope.to_text() != text:
            raise ValueError("noncanonical external flash event")
        return envelope

    def verify_source_bytes(self, source_evidence: bytes) -> None:
        if self._source_digest(source_evidence) != self.source_evidence_sha256:
            raise ValueError("external flash event source evidence digest mismatch")

    def to_runtime_event(
        self,
    ) -> (
        CapabilityAdmissionEvent
        | ObstructionAdmissionEvent
        | CapabilityRevocationEvent
        | ObstructionRevocationEvent
    ):
        if self.event_kind == "capability_admission":
            raw = self.payload.get("capability")
            oracle = self.payload.get("oracle")
            if not isinstance(raw, dict) or not isinstance(oracle, list):
                raise ValueError("invalid capability event payload")
            if (
                raw.get("authority_snapshot") != self.authority_snapshot
                or raw.get("verifier_id") != self.verifier_id
            ):
                raise ValueError("capability contract does not match envelope")
            capability = FiniteCapability(
                capability_id=str(raw["capability_id"]),
                input_type=str(raw["input_type"]),
                output_type=str(raw["output_type"]),
                semantics=tuple((str(a), str(b)) for a, b in raw["semantics"]),
                guard_inputs=tuple(str(v) for v in raw.get("guard_inputs", ())),
                certificate_id=str(raw["certificate_id"]),
                dependencies=tuple(str(v) for v in raw.get("dependencies", ())),
                authority_snapshot=str(raw["authority_snapshot"]),
                verifier_id=str(raw["verifier_id"]),
                provenance_ids=tuple(str(v) for v in raw.get("provenance_ids", ())),
                cost=int(raw.get("cost", 0)),
            )
            return CapabilityAdmissionEvent(
                event_id=self.event_id,
                capability=capability,
                oracle=tuple((str(a), str(b)) for a, b in oracle),
                support_ids=tuple(str(v) for v in self.payload.get("support_ids", ())),
                origin=str(self.payload.get("origin", "verified-external")),
            )
        if self.event_kind == "obstruction_admission":
            raw = self.payload.get("obstruction")
            if not isinstance(raw, dict):
                raise ValueError("invalid obstruction event payload")
            contract_raw = raw.get("contract")
            if not isinstance(contract_raw, dict):
                raise ValueError("invalid obstruction contract")
            contract = FlashContract(
                str(contract_raw.get("authority_snapshot", "")),
                str(contract_raw.get("verifier_id", "")),
            )
            if contract.key != (self.authority_snapshot, self.verifier_id):
                raise ValueError("obstruction contract does not match envelope")
            obstruction = FlashObstruction(
                obstruction_id=str(raw["obstruction_id"]),
                input_type=str(raw["input_type"]),
                output_type=str(raw["output_type"]),
                contract=contract,
                candidate_fingerprint=str(raw["candidate_fingerprint"]),
                separating_input=str(raw["separating_input"]),
                expected_output=str(raw["expected_output"]),
                actual_output=str(raw["actual_output"]),
                provenance=str(raw.get("provenance", "")),
            )
            return ObstructionAdmissionEvent(self.event_id, obstruction)
        if self.event_kind == "capability_revocation":
            capability_id = str(self.payload.get("capability_id", ""))
            reason = str(self.payload.get("reason", ""))
            if not capability_id or not reason:
                raise ValueError("invalid capability revocation payload")
            return CapabilityRevocationEvent(
                event_id=self.event_id,
                capability_id=capability_id,
                reason=reason,
            )
        if self.event_kind == "obstruction_revocation":
            obstruction_id = str(self.payload.get("obstruction_id", ""))
            reason = str(self.payload.get("reason", ""))
            if not obstruction_id or not reason:
                raise ValueError("invalid obstruction revocation payload")
            return ObstructionRevocationEvent(
                event_id=self.event_id,
                obstruction_id=obstruction_id,
                reason=reason,
            )
        raise ValueError(f"unsupported external flash event kind: {self.event_kind}")


class FlashEventRuntime:
    """Idempotent typed admission boundary for domain-produced Flash events."""

    MANIFEST_SCHEMA = "qckn-flash-event-manifest-v1"

    def __init__(self, closure: "FlashClosure") -> None:
        self.closure = closure
        self._events: dict[str, object] = {}
        self._event_digests: dict[str, str] = {}
        self._results: dict[str, FlashDelta] = {}

    @staticmethod
    def _event_digest(event: object) -> str:
        raw = json.dumps(
            asdict(event),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(
            type(event).__name__.encode() + b":" + raw
        ).hexdigest()

    @classmethod
    def _manifest_text_from_digests(
        cls,
        digests: dict[str, str],
    ) -> str:
        payload = {
            "schema": cls.MANIFEST_SCHEMA,
            "events": [
                [event_id, digest]
                for event_id, digest in sorted(digests.items())
            ],
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

    def event_manifest_text(self) -> str:
        return self._manifest_text_from_digests(self._event_digests)

    @classmethod
    def from_event_manifest(
        cls,
        closure: "FlashClosure",
        text: str,
    ) -> "FlashEventRuntime":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid flash event manifest") from exc
        if payload.get("schema") != cls.MANIFEST_SCHEMA:
            raise ValueError("unsupported flash event manifest schema")
        rows = payload.get("events")
        if not isinstance(rows, list):
            raise ValueError("invalid flash event manifest events")
        digests: dict[str, str] = {}
        for row in rows:
            if (
                not isinstance(row, list)
                or len(row) != 2
                or not isinstance(row[0], str)
                or not row[0]
                or not isinstance(row[1], str)
                or not row[1]
            ):
                raise ValueError("invalid flash event manifest row")
            event_id, digest = row
            if event_id in digests:
                raise ValueError("duplicate flash event identity")
            digests[event_id] = digest
        canonical = cls._manifest_text_from_digests(digests)
        if text != canonical:
            raise ValueError("noncanonical flash event manifest")
        runtime = cls(closure)
        runtime._event_digests = digests
        return runtime

    def event_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._event_digests))

    @staticmethod
    def _replay_noop() -> FlashDelta:
        return FlashDelta(
            iterations=0,
            discharged=(),
            reopened=(),
            generated_capabilities=(),
            pruned_candidate_occurrences=0,
            changed_obligations=(),
            flash_radius=0,
            restored_candidate_occurrences=0,
        )

    def apply(
        self,
        event: (
            CapabilityAdmissionEvent
            | ObstructionAdmissionEvent
            | CapabilityRevocationEvent
            | ObstructionRevocationEvent
        ),
    ) -> FlashDelta:
        if not event.event_id:
            raise ValueError("flash event requires identity")
        digest = self._event_digest(event)
        old_digest = self._event_digests.get(event.event_id)
        if old_digest is not None:
            if old_digest != digest:
                raise ValueError("flash event identity conflict")
            return self._results.get(event.event_id, self._replay_noop())

        if isinstance(event, CapabilityAdmissionEvent):
            result = self.closure.admit_capability(
                event.capability,
                oracle=event.oracle,
                support_ids=event.support_ids,
                origin=event.origin,
            )
        elif isinstance(event, ObstructionAdmissionEvent):
            result = self.closure.admit_obstruction(event.obstruction)
        elif isinstance(event, CapabilityRevocationEvent):
            result = self.closure.revoke_capability(
                event.capability_id,
                reason=event.reason,
            )
        elif isinstance(event, ObstructionRevocationEvent):
            result = self.closure.revoke_obstruction(
                event.obstruction_id,
                reason=event.reason,
            )
        else:
            raise TypeError(f"unsupported flash event: {type(event).__name__}")

        self._events[event.event_id] = event
        self._event_digests[event.event_id] = digest
        self._results[event.event_id] = result
        return result


class FlashClosure:
    """Global consequence closure over verified capabilities and live obligations.

    Search may speculate outside this object. Only independently verified
    capability admissions and exact separating obstructions can mutate shared
    developmental state.
    """

    def __init__(
        self,
        obligations: Iterable[LiveObligation],
        *,
        composition_rules: Iterable[FlashCompositionRule] = (),
        kernel: str = "qckn-flash-closure-v1",
    ) -> None:
        rows = tuple(obligations)
        ids = [row.obligation_id for row in rows]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("flash closure requires unique live obligations")
        self.obligations = {row.obligation_id: row for row in rows}
        self.composition_rules = tuple(composition_rules)
        rule_ids = [row.rule_id for row in self.composition_rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("composition rule IDs must be unique")
        self.kernel = str(kernel)
        self.ledger = Ledger()
        self.capabilities: dict[str, CapabilityRecord] = {}
        self.revoked_ids: set[str] = set()
        self.obstructions: dict[str, FlashObstruction] = {}
        self.closure_count = 0
        self.event_count = 0
        self.total_pruned_occurrences = 0
        self.total_cancelled_future_search = 0
        self.flash_events: list[dict[str, object]] = []

    @staticmethod
    def candidate_fingerprint(
        source_rows: tuple[tuple[str, str], ...],
        *,
        input_type: str,
        output_type: str,
        contract: FlashContract,
    ) -> str:
        payload = {
            "input_type": input_type,
            "output_type": output_type,
            "authority_snapshot": contract.authority_snapshot,
            "verifier_id": contract.verifier_id,
            "semantics": [list(row) for row in source_rows],
        }
        return _digest(payload, "flash-candidate-v1:")

    def note_search_attempt(self, obligation_id: str, fingerprint: str) -> None:
        obligation = self.obligations[obligation_id]
        if obligation.status != "OPEN":
            raise ValueError("cannot search a discharged obligation")
        if fingerprint not in obligation.candidate_fingerprints:
            raise ValueError("search attempt outside frozen candidate portfolio")
        if fingerprint in obligation.pruned_fingerprints:
            raise ValueError("search attempted a globally refuted candidate")
        if fingerprint in obligation.searched_fingerprints:
            raise ValueError("duplicate search attempt")
        obligation.searched_fingerprints.append(fingerprint)

    @staticmethod
    def _verify_capability(
        capability: FiniteCapability,
        oracle: tuple[tuple[str, str], ...],
    ) -> bool:
        oracle_map = {str(key): str(value) for key, value in oracle}
        inputs = tuple(str(key) for key, _ in oracle)
        if set(inputs) != set(capability.guarded_inputs):
            return False
        attack = exhaustive_attack(
            capability,
            oracle_map,
            inputs,
            budget=len(inputs),
        )
        return attack.status is AttackStatus.SURVIVE

    def admit_capability(
        self,
        capability: FiniteCapability,
        *,
        oracle: tuple[tuple[str, str], ...],
        support_ids: Iterable[str] = (),
        origin: str = "verified-external",
    ) -> FlashDelta:
        if not self._verify_capability(capability, oracle):
            raise ValueError("capability failed declared independent authority")
        support = tuple(sorted(set(str(value) for value in support_ids)))
        if capability.capability_id in support:
            raise ValueError("capability cannot causally support itself")
        old = self.capabilities.get(capability.capability_id)
        record = CapabilityRecord(capability, support, str(origin))
        if old is not None and old != record:
            raise ValueError("capability identity conflict")
        if old is None:
            self.capabilities[capability.capability_id] = record
            self.ledger.append_promote_capability(capability, self.kernel)
        self.event_count += 1
        delta = self.close()
        self._record_flash_event(
            "capability",
            capability.capability_id,
            delta,
        )
        return delta

    def admit_obstruction(self, obstruction: FlashObstruction) -> FlashDelta:
        old = self.obstructions.get(obstruction.obstruction_id)
        if old is not None and old != obstruction:
            raise ValueError("obstruction identity conflict")
        if old is None:
            self.obstructions[obstruction.obstruction_id] = obstruction
        self.event_count += 1
        delta = self.close()
        self._record_flash_event(
            "obstruction",
            obstruction.obstruction_id,
            delta,
        )
        return delta

    def revoke_obstruction(
        self,
        obstruction_id: str,
        *,
        reason: str,
    ) -> FlashDelta:
        if obstruction_id not in self.obstructions:
            raise ValueError("cannot revoke unknown obstruction")
        if not reason:
            raise ValueError("obstruction revocation requires reason")
        del self.obstructions[obstruction_id]
        self.event_count += 1
        delta = self.close()
        self._record_flash_event(
            "obstruction-revocation",
            obstruction_id,
            delta,
        )
        return delta

    def revoke_capability(
        self,
        capability_id: str,
        *,
        reason: str,
    ) -> FlashDelta:
        if capability_id not in self.capabilities:
            raise ValueError("cannot revoke unknown capability")
        if not reason:
            raise ValueError("revocation requires reason")
        if capability_id not in self.revoked_ids:
            self.revoked_ids.add(capability_id)
            self.ledger.append_revoke_capability(
                capability_id,
                self.kernel,
                reason=reason,
            )
        self.event_count += 1
        delta = self.close()
        self._record_flash_event(
            "revocation",
            capability_id,
            delta,
        )
        return delta

    def _record_flash_event(
        self,
        event_kind: str,
        event_id: str,
        delta: FlashDelta,
    ) -> None:
        self.flash_events.append(
            {
                "event_kind": event_kind,
                "event_id": event_id,
                "iterations": delta.iterations,
                "changed_obligations": list(delta.changed_obligations),
                "flash_radius": delta.flash_radius,
                "generated_capabilities": list(delta.generated_capabilities),
                "pruned_candidate_occurrences": delta.pruned_candidate_occurrences,
                "restored_candidate_occurrences": delta.restored_candidate_occurrences,
                "discharged": list(delta.discharged),
                "reopened": list(delta.reopened),
            }
        )

    def _record_valid(
        self,
        capability_id: str,
        seen: set[str] | None = None,
    ) -> bool:
        if capability_id in self.revoked_ids:
            return False
        record = self.capabilities.get(capability_id)
        if record is None:
            return False
        seen = set() if seen is None else set(seen)
        if capability_id in seen:
            raise ValueError("causal support cycle")
        seen.add(capability_id)
        return all(self._record_valid(support, seen) for support in record.support_ids)

    def active_capability_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                capability_id
                for capability_id in self.capabilities
                if self._record_valid(capability_id)
            )
        )

    def _capability_solves(
        self,
        capability: FiniteCapability,
        obligation: LiveObligation,
    ) -> bool:
        if capability.input_type != obligation.source_input_type:
            return False
        if capability.output_type != obligation.output_type:
            return False
        if capability.authority_snapshot != obligation.contract.authority_snapshot:
            return False
        if capability.verifier_id != obligation.contract.verifier_id:
            return False
        transport = obligation.transport_map
        for target_input, expected in obligation.oracle:
            source_input = transport[str(target_input)]
            if not capability.applicable(source_input):
                return False
            if capability.execute(source_input) != str(expected):
                return False
        return True

    def _apply_obstructions(self) -> tuple[int, int, set[str]]:
        pruned = 0
        restored = 0
        changed: set[str] = set()
        by_contract: dict[tuple[str, str, str, str], set[str]] = {}
        for obstruction in self.obstructions.values():
            by_contract.setdefault(obstruction.contract_key, set()).add(
                obstruction.candidate_fingerprint
            )
        for obligation in self.obligations.values():
            forbidden = by_contract.get(obligation.contract_key, set())
            searched = set(obligation.searched_fingerprints)
            desired = {
                fingerprint
                for fingerprint in obligation.candidate_fingerprints
                if fingerprint in forbidden and fingerprint not in searched
            }
            current = set(obligation.pruned_fingerprints)
            newly_pruned = desired - current
            newly_restored = current - desired
            if newly_pruned or newly_restored:
                obligation.pruned_fingerprints = desired
                pruned += len(newly_pruned)
                restored += len(newly_restored)
                changed.add(obligation.obligation_id)
        return pruned, restored, changed

    def _derive_compositions(self) -> tuple[list[str], bool]:
        generated: list[str] = []
        changed = False
        for rule in self.composition_rules:
            if rule.result_capability_id in self.capabilities:
                continue
            if not self._record_valid(rule.first_capability_id):
                continue
            if not self._record_valid(rule.second_capability_id):
                continue
            first = self.capabilities[rule.first_capability_id].capability
            second = self.capabilities[rule.second_capability_id].capability
            dependent = compose_capabilities(
                f"{rule.result_capability_id}:dependent",
                first,
                second,
            )
            if not self._verify_capability(dependent, rule.oracle):
                raise ValueError("composition failed independent authority")
            standalone = FiniteCapability(
                capability_id=rule.result_capability_id,
                input_type=dependent.input_type,
                output_type=dependent.output_type,
                semantics=dependent.semantics,
                guard_inputs=dependent.guard_inputs,
                certificate_id=rule.certificate_id,
                dependencies=(),
                authority_snapshot=dependent.authority_snapshot,
                verifier_id=dependent.verifier_id,
                provenance_ids=tuple(
                    dict.fromkeys(
                        (
                            first.capability_id,
                            second.capability_id,
                            dependent.certificate_id,
                            *first.provenance_ids,
                            *second.provenance_ids,
                        )
                    )
                ),
                cost=dependent.cost,
            )
            if not self._verify_capability(standalone, rule.oracle):
                raise ValueError("standalone composition materialization failed authority")
            support = tuple(
                sorted(
                    set(
                        (
                            rule.first_capability_id,
                            rule.second_capability_id,
                        )
                    )
                )
            )
            self.capabilities[standalone.capability_id] = CapabilityRecord(
                standalone,
                support,
                f"composition:{rule.rule_id}",
            )
            self.ledger.append_promote_capability(standalone, self.kernel)
            generated.append(standalone.capability_id)
            changed = True
        return generated, changed

    def _refresh_obligations(
        self,
    ) -> tuple[set[str], set[str], set[str]]:
        discharged: set[str] = set()
        reopened: set[str] = set()
        changed: set[str] = set()
        active = self.active_capability_ids()

        for obligation in self.obligations.values():
            valid_current = (
                obligation.solved_by is not None
                and self._record_valid(obligation.solved_by)
                and self._capability_solves(
                    self.capabilities[obligation.solved_by].capability,
                    obligation,
                )
            )
            if obligation.status == "DISCHARGED" and not valid_current:
                obligation.status = "OPEN"
                obligation.solved_by = None
                obligation.support_ids = ()
                obligation.worker_cancelled = False
                obligation.cancelled_remaining_search = 0
                obligation.reopen_count += 1
                reopened.add(obligation.obligation_id)
                changed.add(obligation.obligation_id)

            if obligation.status != "OPEN":
                continue

            candidates = [
                capability_id
                for capability_id in active
                if self._capability_solves(
                    self.capabilities[capability_id].capability,
                    obligation,
                )
            ]
            if not candidates:
                continue
            candidates.sort(
                key=lambda capability_id: (
                    self.capabilities[capability_id].capability.cost,
                    capability_id,
                )
            )
            chosen = candidates[0]
            remaining = obligation.remaining_search()
            obligation.status = "DISCHARGED"
            obligation.solved_by = chosen
            obligation.support_ids = (
                chosen,
                *self.capabilities[chosen].support_ids,
            )
            obligation.worker_cancelled = True
            obligation.cancelled_remaining_search = remaining
            self.total_cancelled_future_search += remaining
            discharged.add(obligation.obligation_id)
            changed.add(obligation.obligation_id)
        return discharged, reopened, changed

    def close(self) -> FlashDelta:
        generated: set[str] = set()
        discharged: set[str] = set()
        reopened: set[str] = set()
        changed_obligations: set[str] = set()
        pruned_total = 0
        restored_total = 0
        iterations = 0

        while True:
            iterations += 1
            if iterations > 128:
                raise RuntimeError("flash closure failed to reach fixed point")
            changed = False

            pruned, restored, pruned_obligations = self._apply_obstructions()
            if pruned or restored:
                changed = True
                pruned_total += pruned
                restored_total += restored
                self.total_pruned_occurrences += pruned
                changed_obligations.update(pruned_obligations)

            derived, derived_changed = self._derive_compositions()
            if derived_changed:
                changed = True
                generated.update(derived)

            new_discharged, new_reopened, obligation_changes = (
                self._refresh_obligations()
            )
            if new_discharged or new_reopened:
                changed = True
            discharged.update(new_discharged)
            reopened.update(new_reopened)
            changed_obligations.update(obligation_changes)

            if not changed:
                break

        self.closure_count += 1
        return FlashDelta(
            iterations=iterations,
            discharged=tuple(sorted(discharged)),
            reopened=tuple(sorted(reopened)),
            generated_capabilities=tuple(sorted(generated)),
            pruned_candidate_occurrences=pruned_total,
            changed_obligations=tuple(sorted(changed_obligations)),
            flash_radius=len(changed_obligations),
            restored_candidate_occurrences=restored_total,
        )

    def compiled_present(self) -> CompiledPresent:
        capabilities = tuple(
            self.capabilities[capability_id].capability
            for capability_id in self.active_capability_ids()
        )
        return CompiledPresent.compile(
            CapabilityGraph(capabilities),
            MetaMemory.empty(),
        ).restart()

    def open_obligation_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                obligation.obligation_id
                for obligation in self.obligations.values()
                if obligation.status == "OPEN"
            )
        )

    def discharged_obligation_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                obligation.obligation_id
                for obligation in self.obligations.values()
                if obligation.status == "DISCHARGED"
            )
        )

    def rank_open_obligations(self) -> tuple[tuple[str, float], ...]:
        open_rows = [
            obligation
            for obligation in self.obligations.values()
            if obligation.status == "OPEN"
        ]
        scores: list[tuple[str, float]] = []
        for obligation in open_rows:
            compatible = sum(
                other.status == "OPEN"
                and other.contract_key == obligation.contract_key
                for other in open_rows
            )
            remaining = max(1, obligation.remaining_search())
            scores.append(
                (
                    obligation.obligation_id,
                    float(compatible) / float(remaining),
                )
            )
        return tuple(sorted(scores, key=lambda row: (-row[1], row[0])))

    def metrics(self) -> dict[str, object]:
        present = self.compiled_present()
        return {
            "schema": "qckn-flash-closure-v1",
            "open_obligations": list(self.open_obligation_ids()),
            "discharged_obligations": list(self.discharged_obligation_ids()),
            "active_capability_ids": list(self.active_capability_ids()),
            "obstruction_ids": sorted(self.obstructions),
            "ledger_event_count": len(self.ledger.events),
            "ledger_digest": self.ledger.digest(),
            "compiled_present_digest": present.digest,
            "compiled_present_bytes": len(present.text().encode("utf-8")),
            "closure_count": self.closure_count,
            "event_count": self.event_count,
            "total_pruned_candidate_occurrences": self.total_pruned_occurrences,
            "total_cancelled_future_search": self.total_cancelled_future_search,
            "priority_order": [
                [obligation_id, score]
                for obligation_id, score in self.rank_open_obligations()
            ],
            "obligations": {
                obligation_id: {
                    "domain": obligation.domain,
                    "status": obligation.status,
                    "solved_by": obligation.solved_by,
                    "support_ids": list(obligation.support_ids),
                    "searched": len(obligation.searched_fingerprints),
                    "pruned": len(obligation.pruned_fingerprints),
                    "remaining_search": obligation.remaining_search(),
                    "worker_cancelled": obligation.worker_cancelled,
                    "cancelled_remaining_search": (
                        obligation.cancelled_remaining_search
                    ),
                    "reopen_count": obligation.reopen_count,
                }
                for obligation_id, obligation in sorted(self.obligations.items())
            },
            "flash_events": list(self.flash_events),
        }
