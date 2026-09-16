from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .developmental_types import (
    CompletenessCertificate,
    NoResolutionCertificate,
    ResultKind,
    canonical_digest,
    canonical_json,
)


@dataclass(frozen=True)
class ResidualCertificate:
    obligation_id: str
    state_digest: str
    authority_snapshot: str
    language_id: str
    substrate_id: str
    protected_consequences: tuple[str, ...]
    residual_type: ResultKind
    observational_equivalence: tuple[str, ...]
    unresolved_pairs_or_obligations: tuple[str, ...]
    completeness_certificate: CompletenessCertificate
    no_resolution_certificate: NoResolutionCertificate
    necessary_constraints: tuple[str, ...]
    candidate_version_space_digest: str
    replay_evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.residual_type is not ResultKind.UNKNOWN_EXPRESSIVITY:
            raise ValueError("ResidualCertificate licenses only UnknownExpressivity")
        if not self.obligation_id or not self.state_digest or not self.authority_snapshot:
            raise ValueError("residual certificate requires obligation/state/authority")
        if not self.language_id or not self.substrate_id:
            raise ValueError("residual certificate requires language and lower substrate")
        if not self.unresolved_pairs_or_obligations:
            raise ValueError("residual certificate requires unresolved obligations")
        if not self.necessary_constraints:
            raise ValueError("residual certificate requires K(rho)")
        if not self.candidate_version_space_digest:
            raise ValueError("residual certificate requires version-space digest")

        complete = self.completeness_certificate
        no_resolution = self.no_resolution_certificate
        expected = (self.language_id, self.state_digest, self.authority_snapshot)
        if (complete.language_id, complete.state_digest, complete.authority_snapshot) != expected:
            raise ValueError("completeness certificate is stale or mismatched")
        if (no_resolution.language_id, no_resolution.state_digest, no_resolution.authority_snapshot) != expected:
            raise ValueError("no-resolution certificate is stale or mismatched")
        if not set(self.unresolved_pairs_or_obligations).issubset(set(no_resolution.unresolved)):
            raise ValueError("residual obligations were not certified unresolved")

    def payload(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "state_digest": self.state_digest,
            "authority_snapshot": self.authority_snapshot,
            "language_id": self.language_id,
            "substrate_id": self.substrate_id,
            "protected_consequences": list(self.protected_consequences),
            "residual_type": self.residual_type.value,
            "observational_equivalence": list(self.observational_equivalence),
            "unresolved_pairs_or_obligations": list(self.unresolved_pairs_or_obligations),
            "completeness_certificate": self.completeness_certificate.payload(),
            "no_resolution_certificate": self.no_resolution_certificate.payload(),
            "necessary_constraints": list(self.necessary_constraints),
            "candidate_version_space_digest": self.candidate_version_space_digest,
            "replay_evidence": list(self.replay_evidence),
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.payload(), prefix="residual-certificate-v1:")

    def text(self) -> str:
        return canonical_json({"version": "residual-certificate-v1", **self.payload()}) + "\n"

    @classmethod
    def from_text(cls, text: str) -> "ResidualCertificate":
        payload = json.loads(text)
        if payload.pop("version", None) != "residual-certificate-v1":
            raise ValueError("unsupported residual certificate version")
        cert = cls(
            obligation_id=str(payload["obligation_id"]),
            state_digest=str(payload["state_digest"]),
            authority_snapshot=str(payload["authority_snapshot"]),
            language_id=str(payload["language_id"]),
            substrate_id=str(payload["substrate_id"]),
            protected_consequences=tuple(str(x) for x in payload["protected_consequences"]),
            residual_type=ResultKind(str(payload["residual_type"])),
            observational_equivalence=tuple(str(x) for x in payload["observational_equivalence"]),
            unresolved_pairs_or_obligations=tuple(
                str(x) for x in payload["unresolved_pairs_or_obligations"]
            ),
            completeness_certificate=CompletenessCertificate.from_payload(
                payload["completeness_certificate"]
            ),
            no_resolution_certificate=NoResolutionCertificate.from_payload(
                payload["no_resolution_certificate"]
            ),
            necessary_constraints=tuple(str(x) for x in payload["necessary_constraints"]),
            candidate_version_space_digest=str(payload["candidate_version_space_digest"]),
            replay_evidence=tuple(str(x) for x in payload.get("replay_evidence", ())),
        )
        if cert.text() != text:
            raise ValueError("non-canonical residual certificate")
        return cert


def make_expressivity_residual(
    *,
    obligation_id: str,
    state_digest: str,
    authority_snapshot: str,
    language_id: str,
    substrate_id: str,
    protected_consequences: tuple[str, ...],
    observational_equivalence: tuple[str, ...],
    unresolved: tuple[str, ...],
    completeness: CompletenessCertificate | None,
    no_resolution: NoResolutionCertificate | None,
    necessary_constraints: tuple[str, ...],
    candidate_version_space_digest: str,
    replay_evidence: tuple[str, ...],
) -> ResidualCertificate:
    if completeness is None:
        raise ValueError("UnknownExpressivity requires completeness certificate")
    if no_resolution is None:
        raise ValueError("UnknownExpressivity requires no-resolution certificate")
    return ResidualCertificate(
        obligation_id=obligation_id,
        state_digest=state_digest,
        authority_snapshot=authority_snapshot,
        language_id=language_id,
        substrate_id=substrate_id,
        protected_consequences=protected_consequences,
        residual_type=ResultKind.UNKNOWN_EXPRESSIVITY,
        observational_equivalence=observational_equivalence,
        unresolved_pairs_or_obligations=unresolved,
        completeness_certificate=completeness,
        no_resolution_certificate=no_resolution,
        necessary_constraints=necessary_constraints,
        candidate_version_space_digest=candidate_version_space_digest,
        replay_evidence=replay_evidence,
    )
