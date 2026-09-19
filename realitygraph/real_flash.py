from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Callable


def _digest(payload: object, prefix: str) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(prefix.encode() + raw).hexdigest()


@dataclass(frozen=True)
class AuthorityEvidence:
    evidence_id: str
    domain: str
    kind: str
    contract: str
    scope: tuple[tuple[str, str], ...]
    consequence_signature: tuple[str, ...]
    source_ref: str
    source_sha256: str
    metrics: tuple[tuple[str, Any], ...] = ()
    pattern_ids: tuple[str, ...] = ()

    @property
    def scope_map(self) -> dict[str, str]:
        return dict(self.scope)

    @property
    def metric_map(self) -> dict[str, Any]:
        return dict(self.metrics)


@dataclass(frozen=True)
class TransferDecision:
    fingerprint: str
    source_evidence_id: str
    destination_domain: str
    claim: str
    status: str
    verifier_calls: int
    reason: str
    destination_evidence_id: str | None = None


@dataclass
class ProtocolResidual:
    residual_id: str
    domain: str
    required_pattern: str
    estimated_cost: int
    status: str = "OPEN"
    settled_by: str | None = None


@dataclass(frozen=True)
class MetaCapability:
    capability_id: str
    pattern_id: str
    supporting_domains: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]


class RealFlashGraph:
    """Authority-gated cross-domain evidence graph.

    Content transfer is never inferred from similarity. Every transfer must be
    independently checked by destination authority. Exact destination
    refutations become cached obstruction fingerprints; independently confirmed
    developmental patterns may compile into a meta-capability without widening
    the scope of source-domain mathematical content.
    """

    def __init__(self, domains: tuple[str, ...]) -> None:
        self.domains = tuple(domains)
        self.evidence: dict[str, AuthorityEvidence] = {}
        self.transfer_decisions: list[TransferDecision] = []
        self.transfer_obstructions: dict[str, TransferDecision] = {}
        self.meta_capabilities: dict[str, MetaCapability] = {}
        self.residuals: dict[str, ProtocolResidual] = {}
        self.events: list[dict[str, Any]] = []
        self.total_destination_verifier_calls = 0
        self.total_cached_transfer_blocks = 0
        self.total_residual_cost_cancelled = 0

    def add_evidence(self, evidence: AuthorityEvidence) -> None:
        if evidence.domain not in self.domains:
            raise ValueError(f"unknown domain {evidence.domain}")
        old = self.evidence.get(evidence.evidence_id)
        if old is not None and old != evidence:
            raise ValueError(f"evidence identity conflict {evidence.evidence_id}")
        if old is None:
            self.evidence[evidence.evidence_id] = evidence
            self.events.append({
                "kind": "authority_evidence",
                "event_id": evidence.evidence_id,
                "domain": evidence.domain,
            })

    def add_residual(self, residual: ProtocolResidual) -> None:
        if residual.domain not in self.domains:
            raise ValueError(f"unknown domain {residual.domain}")
        if residual.residual_id in self.residuals:
            raise ValueError(f"duplicate residual {residual.residual_id}")
        self.residuals[residual.residual_id] = residual

    def transfer_fingerprint(
        self,
        *,
        source_evidence_id: str,
        destination_domain: str,
        claim: str,
        exact_scope: dict[str, str],
    ) -> str:
        source = self.evidence[source_evidence_id]
        payload = {
            "source_evidence_id": source_evidence_id,
            "source_contract": source.contract,
            "source_signature": source.consequence_signature,
            "destination_domain": destination_domain,
            "claim": claim,
            "exact_scope": exact_scope,
        }
        return "real-transfer:" + _digest(payload, "real-flash-transfer-v1:")

    def propose_transfer(
        self,
        *,
        source_evidence_id: str,
        destination_domain: str,
        claim: str,
        exact_scope: dict[str, str],
        verifier: Callable[[AuthorityEvidence, str, str, dict[str, str]], tuple[str, str, str | None]],
    ) -> TransferDecision:
        if destination_domain not in self.domains:
            raise ValueError(f"unknown destination domain {destination_domain}")
        source = self.evidence[source_evidence_id]
        fp = self.transfer_fingerprint(
            source_evidence_id=source_evidence_id,
            destination_domain=destination_domain,
            claim=claim,
            exact_scope=exact_scope,
        )
        cached = self.transfer_obstructions.get(fp)
        if cached is not None:
            blocked = TransferDecision(
                fingerprint=fp,
                source_evidence_id=source_evidence_id,
                destination_domain=destination_domain,
                claim=claim,
                status="BLOCKED_BY_EXACT_REFUTATION",
                verifier_calls=0,
                reason=f"cached exact refutation: {cached.reason}",
                destination_evidence_id=cached.destination_evidence_id,
            )
            self.transfer_decisions.append(blocked)
            self.total_cached_transfer_blocks += 1
            self.events.append({
                "kind": "cached_transfer_block",
                "event_id": fp,
                "destination": destination_domain,
            })
            return blocked

        status, reason, destination_evidence_id = verifier(
            source, destination_domain, claim, exact_scope
        )
        verifier_calls = 1 if status in {"VERIFIED", "REFUTED", "UNKNOWN_AUTHORITY"} else 0
        self.total_destination_verifier_calls += verifier_calls
        decision = TransferDecision(
            fingerprint=fp,
            source_evidence_id=source_evidence_id,
            destination_domain=destination_domain,
            claim=claim,
            status=status,
            verifier_calls=verifier_calls,
            reason=reason,
            destination_evidence_id=destination_evidence_id,
        )
        self.transfer_decisions.append(decision)
        if status in {"REFUTED", "TYPE_MISMATCH"}:
            self.transfer_obstructions[fp] = decision
        self.events.append({
            "kind": "transfer_decision",
            "event_id": fp,
            "status": status,
            "source": source.domain,
            "destination": destination_domain,
        })
        return decision

    def compile_meta_pattern(self, pattern_id: str, *, min_domains: int = 2) -> MetaCapability | None:
        rows = [
            evidence
            for evidence in self.evidence.values()
            if pattern_id in evidence.pattern_ids
        ]
        domains = tuple(sorted({row.domain for row in rows}))
        if len(domains) < min_domains:
            return None
        cap = MetaCapability(
            capability_id="meta:" + _digest(
                {"pattern_id": pattern_id, "domains": domains},
                "real-flash-meta-v1:",
            )[:24],
            pattern_id=pattern_id,
            supporting_domains=domains,
            supporting_evidence_ids=tuple(sorted(row.evidence_id for row in rows)),
        )
        self.meta_capabilities[pattern_id] = cap
        self.events.append({
            "kind": "meta_capability",
            "event_id": cap.capability_id,
            "pattern_id": pattern_id,
            "supporting_domains": list(domains),
        })
        self.close_residuals()
        return cap

    def settle_residual_with_evidence(
        self,
        residual_id: str,
        *,
        evidence_id: str,
    ) -> ProtocolResidual:
        if residual_id not in self.residuals:
            raise KeyError(f"unknown residual {residual_id}")
        if evidence_id not in self.evidence:
            raise KeyError(f"unknown evidence {evidence_id}")
        residual = self.residuals[residual_id]
        evidence = self.evidence[evidence_id]
        if residual.status != "OPEN":
            return residual
        if evidence.domain != residual.domain:
            raise ValueError(
                "destination-local residual requires same-domain authority"
            )
        if residual.required_pattern not in evidence.pattern_ids:
            raise ValueError(
                "evidence does not license the residual's required pattern"
            )
        residual.status = "SETTLED"
        residual.settled_by = evidence.evidence_id
        self.total_residual_cost_cancelled += max(
            0, int(residual.estimated_cost)
        )
        self.events.append({
            "kind": "residual_settled_by_local_evidence",
            "event_id": residual.residual_id,
            "domain": residual.domain,
            "settled_by": evidence.evidence_id,
            "required_pattern": residual.required_pattern,
            "estimated_cost_cancelled": residual.estimated_cost,
        })
        return residual

    def close_residuals(self) -> None:
        for residual in self.residuals.values():
            if residual.status != "OPEN":
                continue
            cap = self.meta_capabilities.get(residual.required_pattern)
            if cap is None:
                continue
            if residual.domain not in cap.supporting_domains:
                continue
            residual.status = "SETTLED"
            residual.settled_by = cap.capability_id
            self.total_residual_cost_cancelled += max(0, int(residual.estimated_cost))
            self.events.append({
                "kind": "residual_settled",
                "event_id": residual.residual_id,
                "domain": residual.domain,
                "settled_by": cap.capability_id,
                "estimated_cost_cancelled": residual.estimated_cost,
            })

    def snapshot(self) -> dict[str, Any]:
        payload = {
            "schema": "qckn-real-multidomain-flash-v1",
            "domains": list(self.domains),
            "evidence": {
                key: asdict(value) for key, value in sorted(self.evidence.items())
            },
            "transfers": [asdict(row) for row in self.transfer_decisions],
            "transfer_obstruction_count": len(self.transfer_obstructions),
            "meta_capabilities": {
                key: asdict(value)
                for key, value in sorted(self.meta_capabilities.items())
            },
            "residuals": {
                key: asdict(value)
                for key, value in sorted(self.residuals.items())
            },
            "total_destination_verifier_calls": self.total_destination_verifier_calls,
            "total_cached_transfer_blocks": self.total_cached_transfer_blocks,
            "total_residual_cost_cancelled": self.total_residual_cost_cancelled,
            "events": list(self.events),
        }
        payload["digest"] = _digest(payload, "qckn-real-multidomain-flash-v1:")
        return payload
