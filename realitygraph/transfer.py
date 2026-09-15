from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


class _Metrics(Protocol):
    log_loss: float
    max_group_harm: float


class _Plan(Protocol):
    rules: Sequence[object]


class _Certificate(Protocol):
    accepted: bool
    sealed_baseline_metrics: _Metrics
    sealed_metrics: _Metrics
    plan: _Plan


@dataclass(frozen=True)
class TransferAssessment:
    status: str
    row_gain: float
    group_gain: float
    grouping_penalty: float
    row_accepted: bool
    group_accepted: bool
    group_harm: float
    row_probes: tuple[str, ...]
    group_probes: tuple[str, ...]

    @property
    def transferable(self) -> bool:
        return self.status == "TRANSFERABLE"

    @property
    def leakage_dependent(self) -> bool:
        return self.status == "LEAKAGE_DEPENDENT"


def _probe_names(certificate: _Certificate) -> tuple[str, ...]:
    names = []
    for rule in certificate.plan.rules:
        name = getattr(rule, "probe_name", None)
        if name is not None:
            names.append(str(name))
    return tuple(names)


def assess_transfer(
    row_certificate: _Certificate,
    group_certificate: _Certificate,
    *,
    harm_tolerance: float = 1e-12,
) -> TransferAssessment:
    """Classify whether a learned consequence survives natural grouping.

    TRANSFERABLE:
        the natural-group sealed certificate is accepted and harms no held-out
        group.

    LEAKAGE_DEPENDENT:
        the naive row-wise certificate is accepted, but the natural-group
        certificate is not.

    UNRESOLVED:
        neither test earns a transferable claim.

    GROUP_ONLY:
        natural grouping succeeds even though the row-wise control did not.
        This is retained separately rather than forced into the leakage binary.
    """
    row_gain = (
        row_certificate.sealed_baseline_metrics.log_loss
        - row_certificate.sealed_metrics.log_loss
    )
    group_gain = (
        group_certificate.sealed_baseline_metrics.log_loss
        - group_certificate.sealed_metrics.log_loss
    )
    group_harm = group_certificate.sealed_metrics.max_group_harm

    group_safe = group_certificate.accepted and group_harm <= harm_tolerance
    if group_safe and row_certificate.accepted:
        status = "TRANSFERABLE"
    elif group_safe:
        status = "GROUP_ONLY"
    elif row_certificate.accepted:
        status = "LEAKAGE_DEPENDENT"
    else:
        status = "UNRESOLVED"

    return TransferAssessment(
        status=status,
        row_gain=row_gain,
        group_gain=group_gain,
        grouping_penalty=(
            group_certificate.sealed_metrics.log_loss
            - row_certificate.sealed_metrics.log_loss
        ),
        row_accepted=row_certificate.accepted,
        group_accepted=group_certificate.accepted,
        group_harm=group_harm,
        row_probes=_probe_names(row_certificate),
        group_probes=_probe_names(group_certificate),
    )
