from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ZeroFailureEvidence:
    observations: int
    confidence: float
    upper_error: float
    max_error: float

    @property
    def accepted(self) -> bool:
        return self.observations > 0 and self.upper_error <= self.max_error


def zero_failure_upper_bound(
    observations: int,
    confidence: float = 0.95,
) -> float:
    """Exact one-sided binomial upper bound after observing zero failures.

    Solves (1-p)^n = 1-confidence. This is an empirical Bernoulli-risk
    certificate over the audited prediction process, not a logical guarantee.
    """
    if observations <= 0:
        return 1.0
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between 0 and 1")
    alpha = 1.0 - confidence
    return 1.0 - math.exp(math.log(alpha) / observations)


def certify_zero_failures(
    observations: int,
    *,
    confidence: float = 0.95,
    max_error: float = 0.05,
) -> ZeroFailureEvidence:
    if not 0.0 < max_error < 1.0:
        raise ValueError("max_error must lie strictly between 0 and 1")
    return ZeroFailureEvidence(
        observations,
        confidence,
        zero_failure_upper_bound(observations, confidence),
        max_error,
    )
