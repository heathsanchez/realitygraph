from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from realitygraph.win_scheduler import (
    GlobalWinScheduler,
    VerifiedWinEvent,
    WinOpportunity,
)


SETTLED_PROTOCOL_OPPORTUNITIES = {
    "acquire-sair-state-compilation": (
        "res:sair:should-reuse-verified-state",
        "sair",
        100.0,
    ),
    "acquire-arc-state-compilation": (
        "res:arc:should-reuse-verified-state",
        "arc",
        80.0,
    ),
    "acquire-gpu-ir-state-compilation": (
        "res:gpu-ir:should-reuse-verified-state",
        "gpu-ir",
        120.0,
    ),
    "acquire-lean-restart-authority": (
        "res:lean-kernel:restartable-negative-reuse",
        "lean-kernel",
        200.0,
    ),
}

GPU_HARDWARE_RESIDUAL = "res:gpu-hardware:promote-ir-capability"

PROFILES = {
    "conservative": {
        "lean-kernel": 0.55,
        "gpu-hardware-authority": 0.35,
        "sair-public-capability": 0.35,
        "arc": 0.35,
        "collatz": 0.45,
        "flash-platform-next": 0.80,
    },
    "neutral": {
        "lean-kernel": 0.70,
        "gpu-hardware-authority": 0.50,
        "sair-public-capability": 0.50,
        "arc": 0.50,
        "collatz": 0.60,
        "flash-platform-next": 0.90,
    },
    "aggressive": {
        "lean-kernel": 0.85,
        "gpu-hardware-authority": 0.65,
        "sair-public-capability": 0.65,
        "arc": 0.65,
        "collatz": 0.75,
        "flash-platform-next": 1.00,
    },
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TypeError(f"expected object in {path}")
    return value


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _profile_probability(profile: str, key: str) -> float:
    return float(PROFILES[profile][key])


def portfolio(profile: str) -> tuple[WinOpportunity, ...]:
    p = PROFILES[profile]

    rows: list[WinOpportunity] = [
        # The event source. It is resolved by the verified real Flash event.
        WinOpportunity(
            "flash-meta-qualification",
            "realitygraph",
            direct_win=0.0,
            verification_probability=1.0,
            authority_readiness=1.0,
            destination_bridge_probability=1.0,
            flash_radius=4.0,
            future_search_removed=500.0,
            composition_unlocks=1.0,
            cost=1.0,
            latency=0.5,
            maintenance_cost=0.0,
            deadline_relevance=0.5,
            external_visibility=0.4,
            provenance=("real-multidomain-v2:verified-state-compilation",),
        ),
        WinOpportunity(
            "gpu-hardware-authority",
            "gpu-hardware",
            direct_win=2.0,
            verification_probability=_profile_probability(
                profile, "gpu-hardware-authority"
            ),
            authority_readiness=1.0,
            destination_bridge_probability=1.0,
            flash_radius=1.0,
            future_search_removed=300.0,
            composition_unlocks=1.0,
            cost=300.0,
            latency=3.0,
            maintenance_cost=0.5,
            deadline_relevance=0.55,
            external_visibility=0.75,
            provenance=(
                "gpu-ir-v1:80pct-developmental-search-reduction",
                GPU_HARDWARE_RESIDUAL,
            ),
        ),
        WinOpportunity(
            "lean-kernel",
            "lean-kernel",
            direct_win=10.0,
            verification_probability=_profile_probability(profile, "lean-kernel"),
            authority_readiness=1.0,
            destination_bridge_probability=0.25,
            flash_radius=6.0,
            future_search_removed=20.0,
            composition_unlocks=2.0,
            cost=3.0,
            latency=2.0,
            maintenance_cost=0.2,
            deadline_relevance=1.0,
            external_visibility=1.0,
            provenance=(
                "arena-current:182-correct-7-unknown-0-wrong",
                "real-multidomain-v2:lean-restart-authority-settled",
            ),
        ),
        WinOpportunity(
            "sair-public-capability",
            "sair",
            direct_win=2.0,
            verification_probability=_profile_probability(
                profile, "sair-public-capability"
            ),
            authority_readiness=1.0,
            destination_bridge_probability=0.80,
            flash_radius=8.0,
            future_search_removed=100.0,
            composition_unlocks=3.0,
            cost=2.5,
            latency=2.0,
            maintenance_cost=0.2,
            deadline_relevance=0.40,
            external_visibility=0.60,
            provenance=("real-multidomain-v2:sair-supported",),
        ),
        WinOpportunity(
            "arc",
            "arc",
            direct_win=5.0,
            verification_probability=_profile_probability(profile, "arc"),
            authority_readiness=0.85,
            destination_bridge_probability=0.30,
            flash_radius=12.0,
            future_search_removed=50.0,
            composition_unlocks=4.0,
            cost=4.0,
            latency=3.0,
            maintenance_cost=0.3,
            deadline_relevance=0.70,
            external_visibility=0.80,
            provenance=("real-multidomain-v2:arc-supported",),
        ),
        WinOpportunity(
            "collatz",
            "collatz",
            direct_win=1.0,
            verification_probability=_profile_probability(profile, "collatz"),
            authority_readiness=0.95,
            destination_bridge_probability=0.40,
            flash_radius=8.0,
            future_search_removed=100.0,
            composition_unlocks=3.0,
            cost=4.0,
            latency=3.0,
            maintenance_cost=0.2,
            deadline_relevance=0.10,
            external_visibility=0.50,
            provenance=("bounded-propagation:no-termination-claim",),
        ),
        WinOpportunity(
            "flash-platform-next",
            "realitygraph",
            direct_win=0.5,
            verification_probability=_profile_probability(
                profile, "flash-platform-next"
            ),
            authority_readiness=1.0,
            destination_bridge_probability=1.0,
            flash_radius=12.0,
            future_search_removed=96.0,
            composition_unlocks=5.0,
            cost=2.0,
            latency=1.0,
            maintenance_cost=0.4,
            deadline_relevance=0.50,
            external_visibility=0.40,
            provenance=("next-platform-capability:not-yet-authority",),
        ),
    ]

    # These opportunities are real protocol work *before* the V2 meta-capability
    # is admitted. Their costs are the exact residual estimates from the real
    # multidomain experiment, allowing cancellation accounting to stay typed.
    for opportunity_id, (residual_id, domain, estimated_cost) in (
        SETTLED_PROTOCOL_OPPORTUNITIES.items()
    ):
        rows.append(
            WinOpportunity(
                opportunity_id,
                domain,
                direct_win=0.0,
                verification_probability=0.8,
                authority_readiness=1.0,
                destination_bridge_probability=1.0,
                flash_radius=1.0,
                future_search_removed=estimated_cost,
                composition_unlocks=1.0,
                cost=estimated_cost,
                latency=2.0,
                maintenance_cost=0.0,
                deadline_relevance=0.30,
                external_visibility=0.20,
                provenance=(residual_id, "pre-flash-open-protocol-work"),
            )
        )

    return tuple(rows)


def _rank(
    scheduler: GlobalWinScheduler,
    *,
    mode: str,
    deadline_pressure: float,
) -> list[dict[str, Any]]:
    return [
        {
            "opportunity_id": row.opportunity_id,
            "score": row.score,
            "expected_direct_value": row.expected_direct_value,
            "expected_global_value": row.expected_global_value,
            "denominator": row.denominator,
        }
        for row in scheduler.rank(
            mode=mode,
            deadline_pressure=deadline_pressure,
        )
    ]


def _real_flash_event(
    real: dict[str, Any],
    *,
    result_digest: str,
) -> VerifiedWinEvent:
    cross = real["cross_domain_result"]
    genuine = cross["genuine_meta_flash"]
    settled = set(genuine["settled_protocol_residuals"])
    required = {
        residual_id
        for residual_id, _domain, _cost in SETTLED_PROTOCOL_OPPORTUNITIES.values()
    }
    if settled != required:
        raise AssertionError(
            f"unexpected settled residuals: {sorted(settled)}"
        )
    if float(genuine["estimated_protocol_search_cancelled"]) != 500.0:
        raise AssertionError("real Flash cancellation total changed")
    if cross["still_unresolved"] != [GPU_HARDWARE_RESIDUAL]:
        raise AssertionError("GPU hardware is no longer the sole authority residual")

    return VerifiedWinEvent(
        event_id=f"real-flash-v2:{result_digest[:20]}",
        source_opportunity_id="flash-meta-qualification",
        verified=True,
        direct_win_realized=0.0,
        flash_radius_realized=len(genuine["supporting_domains"]),
        future_search_removed_realized=float(
            genuine["estimated_protocol_search_cancelled"]
        ),
        composition_unlocks_realized=1.0,
        cancel_opportunities=tuple(sorted(SETTLED_PROTOCOL_OPPORTUNITIES)),
        provenance=(
            "real-multidomain-flash-v2",
            result_digest,
            *tuple(sorted(genuine["supporting_evidence_ids"])),
        ),
    )


def _unverified_mutation_rejected(profile: str) -> bool:
    scheduler = GlobalWinScheduler(portfolio(profile))
    bad = VerifiedWinEvent(
        event_id="negative-control:unverified-global-mutation",
        source_opportunity_id="flash-meta-qualification",
        verified=False,
        cancel_opportunities=("gpu-hardware-authority",),
    )
    before = scheduler.metrics()
    try:
        scheduler.admit_event(bad)
    except ValueError:
        return scheduler.metrics() == before
    return False


def run(profile: str, real_path: Path) -> dict[str, Any]:
    real = _load_json(real_path)
    result_digest = _digest(real_path)

    if real.get("verdict") != "PASS":
        raise AssertionError("real multidomain Flash prerequisite is not green")
    if not all(real.get("gates", {}).values()):
        raise AssertionError("real multidomain Flash prerequisite gates are not all green")

    scheduler = GlobalWinScheduler(portfolio(profile))
    before_battle = _rank(
        scheduler,
        mode="BATTLE",
        deadline_pressure=0.80,
    )
    before_discovery = _rank(
        scheduler,
        mode="DISCOVERY",
        deadline_pressure=0.0,
    )

    event = _real_flash_event(real, result_digest=result_digest)
    delta = scheduler.admit_event(event)

    after_battle = _rank(
        scheduler,
        mode="BATTLE",
        deadline_pressure=0.80,
    )
    after_discovery = _rank(
        scheduler,
        mode="DISCOVERY",
        deadline_pressure=0.0,
    )

    metrics = scheduler.metrics()
    open_ids = set(metrics["open"])
    cancelled = set(metrics["cancelled"])
    authority_ids = {
        *SETTLED_PROTOCOL_OPPORTUNITIES.keys(),
        "gpu-hardware-authority",
    }
    open_authority = sorted(open_ids & authority_ids)

    return {
        "profile": profile,
        "before": {
            "battle": before_battle,
            "discovery": before_discovery,
        },
        "after": {
            "battle": after_battle,
            "discovery": after_discovery,
        },
        "delta": {
            "event_id": delta.event_id,
            "verified": delta.verified,
            "cancelled": list(delta.cancelled),
            "repriced": list(delta.repriced),
            "changed_opportunities": list(delta.changed_opportunities),
            "flash_radius": delta.flash_radius,
        },
        "scheduler_metrics": metrics,
        "open_authority_opportunities": open_authority,
        "gates": {
            "verified_event_cancelled_exactly_settled_protocol_work": (
                cancelled == set(SETTLED_PROTOCOL_OPPORTUNITIES)
            ),
            "cancelled_work_cost_matches_real_flash_500": (
                abs(float(metrics["cancelled_work_cost"]) - 500.0) < 1e-9
            ),
            "future_search_removed_matches_real_flash_500": (
                abs(float(metrics["total_future_search_removed"]) - 500.0) < 1e-9
            ),
            "gpu_hardware_is_only_open_authority_acquisition": (
                open_authority == ["gpu-hardware-authority"]
            ),
            "lean_direct_is_battle_first": (
                after_battle[0]["opportunity_id"] == "lean-kernel"
            ),
            "portfolio_reclosed_after_verified_event": (
                [row["opportunity_id"] for row in before_battle]
                != [row["opportunity_id"] for row in after_battle]
                and not (
                    set(SETTLED_PROTOCOL_OPPORTUNITIES)
                    & {row["opportunity_id"] for row in after_battle}
                )
            ),
            "unverified_event_cannot_mutate_global_portfolio": (
                _unverified_mutation_rejected(profile)
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-result", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    real_path = Path(args.real_result)
    results = {
        profile: run(profile, real_path)
        for profile in PROFILES
    }
    all_gates = {
        f"{profile}:{gate}": passed
        for profile, result in results.items()
        for gate, passed in result["gates"].items()
    }
    real = _load_json(real_path)

    output = {
        "schema": "qckn-live-win-portfolio-v4",
        "passed": all(all_gates.values()),
        "real_flash_result_sha256": _digest(real_path),
        "real_flash_supporting_domains": (
            real["cross_domain_result"]["genuine_meta_flash"]["supporting_domains"]
        ),
        "real_flash_open_residuals": real["cross_domain_result"]["still_unresolved"],
        "profiles": PROFILES,
        "results": results,
        "gates": all_gates,
        "claim_boundary": (
            "The portfolio mutation is driven by the reconstructed, green real "
            "multidomain Flash V2 result. Its 500-unit cancellation is measured "
            "protocol-search option value. Direct-win magnitudes and verification "
            "probabilities remain explicit operator priors, not objective win "
            "probabilities. No unverified event may mutate shared portfolio state."
        ),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")

    print(
        json.dumps(
            {
                "passed": output["passed"],
                "real_flash_supporting_domains": output[
                    "real_flash_supporting_domains"
                ],
                "real_flash_open_residuals": output["real_flash_open_residuals"],
                "profiles": {
                    profile: {
                        "battle_before": [
                            row["opportunity_id"]
                            for row in result["before"]["battle"]
                        ],
                        "battle_after": [
                            row["opportunity_id"]
                            for row in result["after"]["battle"]
                        ],
                        "discovery_after": [
                            row["opportunity_id"]
                            for row in result["after"]["discovery"]
                        ],
                        "cancelled_work_cost": result[
                            "scheduler_metrics"
                        ]["cancelled_work_cost"],
                        "open_authority": result["open_authority_opportunities"],
                        "gates": result["gates"],
                    }
                    for profile, result in results.items()
                },
                "claim_boundary": output["claim_boundary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(
        "PASS_QCKN_LIVE_WIN_PORTFOLIO_V4"
        if output["passed"]
        else "FAIL_QCKN_LIVE_WIN_PORTFOLIO_V4"
    )
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
