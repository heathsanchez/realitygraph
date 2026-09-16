from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def canonical_digest(payload: Any, *, prefix: str = "") -> str:
    body = prefix + canonical_json(payload)
    return hashlib.sha256(body.encode()).hexdigest()


class ResultKind(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    COMPILED = "COMPILED"
    REFUTED = "REFUTED"
    UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"
    UNKNOWN_CHOICE = "UNKNOWN_CHOICE"
    UNKNOWN_SEARCH = "UNKNOWN_SEARCH"
    UNKNOWN_EXPRESSIVITY = "UNKNOWN_EXPRESSIVITY"
    NAMED_OBSTRUCTION = "NAMED_OBSTRUCTION"


@dataclass(frozen=True)
class CertificateRef:
    kind: str
    digest: str

    def __post_init__(self) -> None:
        if not self.kind or not self.digest:
            raise ValueError("certificate reference requires kind and digest")


@dataclass(frozen=True)
class BoundarySnapshot:
    state_digest: str
    authority_snapshot: str
    language_id: str
    substrate_id: str
    protected_consequences: tuple[str, ...] = ()

    @property
    def digest(self) -> str:
        return canonical_digest(asdict(self), prefix="boundary-snapshot-v1:")


@dataclass(frozen=True)
class DevelopmentalResult:
    kind: ResultKind
    obligation_id: str
    detail: str = ""
    certificate_digest: str = ""

    def __post_init__(self) -> None:
        if not self.obligation_id:
            raise ValueError("developmental result requires obligation_id")
        if self.kind is ResultKind.UNKNOWN_EXPRESSIVITY and not self.certificate_digest:
            raise ValueError("UnknownExpressivity requires a residual certificate")


@dataclass(frozen=True)
class CompletenessCertificate:
    language_id: str
    substrate_scope: str
    state_digest: str
    authority_snapshot: str
    enumerated_signatures: tuple[str, ...]
    verifier_id: str
    replay_evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.language_id or not self.substrate_scope:
            raise ValueError("completeness certificate requires language and scope")
        if not self.state_digest or not self.authority_snapshot:
            raise ValueError("completeness certificate requires state and authority")
        if not self.enumerated_signatures:
            raise ValueError("completeness certificate requires an exhausted class")
        if not self.verifier_id:
            raise ValueError("completeness certificate requires verifier_id")

    def payload(self) -> dict[str, Any]:
        return {
            "language_id": self.language_id,
            "substrate_scope": self.substrate_scope,
            "state_digest": self.state_digest,
            "authority_snapshot": self.authority_snapshot,
            "enumerated_signatures": list(self.enumerated_signatures),
            "verifier_id": self.verifier_id,
            "replay_evidence": list(self.replay_evidence),
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="complete-v1:")

    def text(self) -> str:
        return canonical_json({"version": "complete-v1", **self.payload()}) + "\n"

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "CompletenessCertificate":
        return cls(
            language_id=str(payload["language_id"]),
            substrate_scope=str(payload["substrate_scope"]),
            state_digest=str(payload["state_digest"]),
            authority_snapshot=str(payload["authority_snapshot"]),
            enumerated_signatures=tuple(str(x) for x in payload["enumerated_signatures"]),
            verifier_id=str(payload["verifier_id"]),
            replay_evidence=tuple(str(x) for x in payload.get("replay_evidence", ())),
        )

    @classmethod
    def from_text(cls, text: str) -> "CompletenessCertificate":
        payload = json.loads(text)
        if payload.pop("version", None) != "complete-v1":
            raise ValueError("unsupported completeness certificate version")
        cert = cls.from_payload(payload)
        if cert.text() != text:
            raise ValueError("non-canonical completeness certificate")
        return cert


@dataclass(frozen=True)
class NoResolutionCertificate:
    language_id: str
    state_digest: str
    authority_snapshot: str
    unresolved: tuple[str, ...]
    checked_signatures: tuple[str, ...]
    verifier_id: str
    replay_evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.language_id or not self.state_digest or not self.authority_snapshot:
            raise ValueError("no-resolution certificate requires language/state/authority")
        if not self.unresolved:
            raise ValueError("no-resolution certificate requires an unresolved obligation")
        if not self.checked_signatures:
            raise ValueError("no-resolution certificate requires checked signatures")
        if not self.verifier_id:
            raise ValueError("no-resolution certificate requires verifier_id")

    def payload(self) -> dict[str, Any]:
        return {
            "language_id": self.language_id,
            "state_digest": self.state_digest,
            "authority_snapshot": self.authority_snapshot,
            "unresolved": list(self.unresolved),
            "checked_signatures": list(self.checked_signatures),
            "verifier_id": self.verifier_id,
            "replay_evidence": list(self.replay_evidence),
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="no-resolution-v1:")

    def text(self) -> str:
        return canonical_json({"version": "no-resolution-v1", **self.payload()}) + "\n"

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "NoResolutionCertificate":
        return cls(
            language_id=str(payload["language_id"]),
            state_digest=str(payload["state_digest"]),
            authority_snapshot=str(payload["authority_snapshot"]),
            unresolved=tuple(str(x) for x in payload["unresolved"]),
            checked_signatures=tuple(str(x) for x in payload["checked_signatures"]),
            verifier_id=str(payload["verifier_id"]),
            replay_evidence=tuple(str(x) for x in payload.get("replay_evidence", ())),
        )

    @classmethod
    def from_text(cls, text: str) -> "NoResolutionCertificate":
        payload = json.loads(text)
        if payload.pop("version", None) != "no-resolution-v1":
            raise ValueError("unsupported no-resolution certificate version")
        cert = cls.from_payload(payload)
        if cert.text() != text:
            raise ValueError("non-canonical no-resolution certificate")
        return cert
