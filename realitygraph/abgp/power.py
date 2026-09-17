from __future__ import annotations

from fractions import Fraction
from math import comb
from typing import Any, Mapping

from .manifest import ABGPAnalysisPlan


def _binomial_probability(n: int, k: int, p: float) -> float:
    if k < 0 or k > n:
        return 0.0
    if p <= 0.0:
        return 1.0 if k == 0 else 0.0
    if p >= 1.0:
        return 1.0 if k == n else 0.0
    return comb(n, k) * (p**k) * ((1.0 - p) ** (n - k))


def _null_critical_wins(discordant: int, alpha: float) -> int | None:
    if discordant <= 0:
        return None
    denominator = 2**discordant
    tail_numerator = 0
    critical: int | None = None
    for wins in range(discordant, -1, -1):
        tail_numerator += comb(discordant, wins)
        if tail_numerator / denominator <= alpha:
            critical = wins
        else:
            break
    return critical


def _binomial_upper_tail(n: int, minimum: int, p: float) -> float:
    if minimum <= 0:
        return 1.0
    if minimum > n:
        return 0.0
    return sum(_binomial_probability(n, k, p) for k in range(minimum, n + 1))


def paired_exact_power(
    n: int,
    p10: Fraction,
    p01: Fraction,
    alpha: Fraction,
) -> float:
    """Exact unconditional power of the one-sided paired McNemar/binomial test.

    `p10` is P(control=0,treatment=1); `p01` is the reverse discordance.
    The test conditions on the realized discordant count, while power averages over
    its exact Binomial(n, p10+p01) distribution.
    """

    if n <= 0:
        raise ValueError("n must be positive")
    if p10 < 0 or p01 < 0 or p10 + p01 > 1:
        raise ValueError("discordance probabilities must be non-negative and sum to <= 1")
    if alpha <= 0 or alpha >= 1:
        raise ValueError("alpha must lie strictly between zero and one")

    q = float(p10 + p01)
    if q == 0.0:
        return 0.0
    win_given_discordant = float(p10 / (p10 + p01))
    alpha_f = float(alpha)
    power = 0.0
    for discordant in range(n + 1):
        probability_discordant = _binomial_probability(n, discordant, q)
        if probability_discordant == 0.0:
            continue
        critical = _null_critical_wins(discordant, alpha_f)
        if critical is None:
            continue
        conditional_rejection = _binomial_upper_tail(
            discordant,
            critical,
            win_given_discordant,
        )
        power += probability_discordant * conditional_rejection
    return min(1.0, max(0.0, power))


def _signed_null_distribution(counts: Mapping[int, int]) -> dict[int, int]:
    distribution: dict[int, int] = {0: 1}
    for weight in sorted(counts):
        count = int(counts[weight])
        if weight <= 0 or count < 0:
            raise ValueError("weights must be positive and counts non-negative")
        for _ in range(count):
            nxt: dict[int, int] = {}
            for statistic, ways in distribution.items():
                nxt[statistic + weight] = nxt.get(statistic + weight, 0) + ways
                nxt[statistic - weight] = nxt.get(statistic - weight, 0) + ways
            distribution = nxt
    return distribution


def _signed_alternative_distribution(
    counts: Mapping[int, int], plus_probability: float
) -> dict[int, float]:
    if not (0.0 <= plus_probability <= 1.0):
        raise ValueError("plus_probability must be in [0,1]")
    distribution: dict[int, float] = {0: 1.0}
    minus_probability = 1.0 - plus_probability
    for weight in sorted(counts):
        for _ in range(int(counts[weight])):
            nxt: dict[int, float] = {}
            for statistic, probability in distribution.items():
                nxt[statistic + weight] = (
                    nxt.get(statistic + weight, 0.0)
                    + probability * plus_probability
                )
                nxt[statistic - weight] = (
                    nxt.get(statistic - weight, 0.0)
                    + probability * minus_probability
                )
            distribution = nxt
    return distribution


def g_conditional_power(
    n_worlds: int,
    max_dose_discordance_rate: float,
    max_dose_effect: float,
    alpha: float,
) -> float:
    """Conditional exact power for G under a frozen discordance nuisance law.

    At dose d, exactly round(n*q*d) matched pairs are discordant. Conditional on
    discordance, the relevant-minus-irrelevant sign has probability theta chosen
    so that the expected dose-1 gap is `max_dose_effect`. This mirrors the exact
    sign-randomization test while varying the nuisance discordance rate explicitly.
    """

    if n_worlds <= 0:
        raise ValueError("n_worlds must be positive")
    q = float(max_dose_discordance_rate)
    delta = float(max_dose_effect)
    if not (0.0 < q <= 1.0) or not (0.0 < delta <= q):
        raise ValueError("require 0 < effect <= discordance rate <= 1")
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must lie strictly between zero and one")

    doses = (0.10, 0.25, 0.50, 1.00)
    weights = (2, 5, 10, 20)
    counts = {
        weight: max(1, int(round(n_worlds * q * dose)))
        for dose, weight in zip(doses, weights)
    }
    plus_probability = (1.0 + delta / q) / 2.0

    null = _signed_null_distribution(counts)
    total_null = 2 ** sum(counts.values())
    running = 0
    critical: int | None = None
    for statistic in sorted(null, reverse=True):
        running += null[statistic]
        if running / total_null <= alpha:
            critical = statistic
        else:
            break
    if critical is None:
        return 0.0

    alternative = _signed_alternative_distribution(counts, plus_probability)
    return min(
        1.0,
        max(
            0.0,
            sum(probability for statistic, probability in alternative.items() if statistic >= critical),
        ),
    )


def _paired_arm_audit(
    n: int,
    effect: float,
    discordance_rates: list[float],
    alpha: float,
    minimum_power: float,
) -> dict[str, Any]:
    points: list[dict[str, float]] = []
    for q in discordance_rates:
        if q < effect:
            raise ValueError("paired nuisance discordance must be >= effect floor")
        p10 = Fraction(str((q + effect) / 2.0))
        p01 = Fraction(str((q - effect) / 2.0))
        power = paired_exact_power(n, p10, p01, Fraction(str(alpha)))
        points.append(
            {
                "discordance_rate": q,
                "p10": float(p10),
                "p01": float(p01),
                "power": power,
            }
        )
    minimum = min(point["power"] for point in points)
    return {
        "n": n,
        "effect_floor": effect,
        "points": points,
        "minimum_observed_power": minimum,
        "qualified": minimum >= minimum_power,
    }


def qualification_power_audit(plan: ABGPAnalysisPlan) -> dict[str, Any]:
    qualification = plan.raw.get("qualification")
    if not isinstance(qualification, Mapping):
        raise ValueError("analysis plan lacks qualification power specification")
    minimum_power = float(qualification["minimum_power"])
    alpha = float(qualification["holm_component_alpha_floor"])
    paired = qualification["paired_nuisance_envelope"]
    g_spec = qualification["g_nuisance_envelope"]

    a = _paired_arm_audit(
        int(plan.arms["A"]["n"]),
        float(plan.arms["A"]["effect_floor"]),
        [float(x) for x in paired["A"]["discordance_rates"]],
        alpha,
        minimum_power,
    )
    b = _paired_arm_audit(
        int(plan.arms["B"]["n_units"]),
        float(plan.arms["B"]["effect_floor_each_control"]),
        [float(x) for x in paired["B"]["discordance_rates"]],
        alpha,
        minimum_power,
    )
    p = _paired_arm_audit(
        int(plan.arms["P"]["n"]),
        float(plan.arms["P"]["effect_floor"]),
        [float(x) for x in paired["P"]["discordance_rates"]],
        alpha,
        minimum_power,
    )

    g_points: list[dict[str, float]] = []
    for q in g_spec["max_dose_discordance_rates"]:
        power = g_conditional_power(
            int(plan.arms["G"]["n_worlds"]),
            float(q),
            float(g_spec["max_dose_effect_floor"]),
            alpha,
        )
        g_points.append({"max_dose_discordance_rate": float(q), "power": power})
    g_min = min(point["power"] for point in g_points)
    g = {
        "n": int(plan.arms["G"]["n_worlds"]),
        "effect_floor": float(g_spec["max_dose_effect_floor"]),
        "points": g_points,
        "minimum_observed_power": g_min,
        "qualified": g_min >= minimum_power,
    }

    arms = {"A": a, "B": b, "G": g, "P": p}
    return {
        "minimum_required_power": minimum_power,
        "component_alpha": alpha,
        "arms": arms,
        "qualified": all(value["qualified"] for value in arms.values()),
    }
