from __future__ import annotations

from enum import Enum

from .developmental_types import DevelopmentalResult, ResultKind
from .residual_certificate import ResidualCertificate


class DevelopmentalRoute(str, Enum):
    TERMINAL = "TERMINAL"
    SPLIT = "SPLIT"
    EVIDENCE = "EVIDENCE"
    SEARCH = "SEARCH"
    EXPAND = "EXPAND"


def route_residual(
    result: DevelopmentalResult,
    *,
    residual_certificate: ResidualCertificate | None = None,
) -> DevelopmentalRoute:
    if result.kind in {
        ResultKind.AUTHORIZED,
        ResultKind.COMPILED,
        ResultKind.REFUTED,
        ResultKind.NAMED_OBSTRUCTION,
    }:
        return DevelopmentalRoute.TERMINAL
    if result.kind is ResultKind.UNKNOWN_IDENTITY:
        return DevelopmentalRoute.SPLIT
    if result.kind is ResultKind.UNKNOWN_CHOICE:
        return DevelopmentalRoute.EVIDENCE
    if result.kind is ResultKind.UNKNOWN_SEARCH:
        return DevelopmentalRoute.SEARCH
    if result.kind is ResultKind.UNKNOWN_EXPRESSIVITY:
        if residual_certificate is None:
            raise ValueError("EXPAND requires the exact ResidualCertificate")
        if residual_certificate.digest != result.certificate_digest:
            raise ValueError("expressivity result/certificate digest mismatch")
        if residual_certificate.obligation_id != result.obligation_id:
            raise ValueError("expressivity result/certificate obligation mismatch")
        return DevelopmentalRoute.EXPAND
    raise ValueError(f"unsupported developmental result kind: {result.kind}")
