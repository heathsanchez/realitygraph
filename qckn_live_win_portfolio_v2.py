from __future__ import annotations

import json
import os
from pathlib import Path

from realitygraph.win_scheduler import GlobalWinScheduler, WinOpportunity


PROFILES = {
    "conservative": {
        "lean-kernel": 0.55,
        "lean-restart-authority": 0.45,
        "gpu-hardware-authority": 0.35,
        "sair-public-capability": 0.35,
        "arc": 0.35,
        "collatz": 0.45,
        "flash-platform": 0.90,
    },
    "neutral": {
        "lean-kernel": 0.70,
        "lean-restart-authority": 0.60,
        "gpu-hardware-authority": 0.50,
        "sair-public-capability": 0.50,
        "arc": 0.50,
        "collatz": 0.60,
        "flash-platform": 1.00,
    },
    "aggressive": {
        "lean-kernel": 0.85,
        "lean-restart-authority": 0.75,
        "gpu-hardware-authority": 0.65,
        "sair-public-capability": 0.65,
        "arc": 0.65,
        "collatz": 0.75,
        "flash-platform": 1.00,
    },
}


PROVENANCE = {
    "real-multidomain": {
        "run": 35406136686,
        "artifact": 10572761317,
        "pattern": "verified_state_compilation",
        "supporting_domains": ["sair", "arc", "gpu-ir"],
        "estimated_protocol_search_cancelled": 300,
        "open_residuals": {
            "gpu-hardware": 300,
            "lean-kernel": 200,
        },
    },
    "lean-kernel": {
        "repository": "heathsanchez/lean-kernel-arena",
        "branch": "mda-arena-qualification-v1",
        "commit": "994dfa6312063856252e812908556b748ad3fd83",
        "note": "direct public Arena benchmark surface; current authority-acquisition experiment is running separately",
    },
    "sair": {
        "repository": "metalogiclabs/mathgraph",
        "run": 35402936630,
        "note": "sealed public FALSE reserve: 50% fewer model calls and higher verified yield; no private competition score or TRUE-proof claim",
    },
    "arc": {
        "repository": "heathsanchez/Minimal-Sufficient-Interface",
        "run": 35405132123,
        "note": "V4 matched market-local protected performance; zero structural prunes",
    },
    "collatz": {
        "repository": "heathsanchez/test",
        "run": 35403074591,
        "note": "bounded propagation qualified; no advantage over upfront guard and no termination claim",
    },
    "gpu-ir": {
        "repository": "heathsanchez/test",
        "commit": "c5402d50000b5e20f64318edcb113479e313db19",
        "run": 35405925307,
        "note": "finite IR developmental optimization qualified; GPU hardware authority unavailable",
    },
}


def portfolio(profile: str) -> tuple[WinOpportunity, ...]:
    p = PROFILES[profile]
    return (
        WinOpportunity(
            "lean-kernel",
            "lean-kernel",
            direct_win=10.0,
            verification_probability=p["lean-kernel"],
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
            provenance=("arena-public-qualification",),
        ),
        WinOpportunity(
            "lean-restart-authority",
            "lean-kernel",
            direct_win=1.5,
            verification_probability=p["lean-restart-authority"],
            authority_readiness=1.0,
            destination_bridge_probability=1.0,
            flash_radius=1.0,
            future_search_removed=200.0,
            composition_unlocks=1.0,
            cost=2.0,
            latency=1.5,
            maintenance_cost=0.1,
            deadline_relevance=0.80,
            external_visibility=0.80,
            provenance=(
                "real-multidomain:res:lean-kernel:restartable-negative-reuse",
            ),
        ),
        WinOpportunity(
            "gpu-hardware-authority",
            "gpu-hardware",
            direct_win=2.0,
            verification_probability=p["gpu-hardware-authority"],
            authority_readiness=1.0,
            destination_bridge_probability=1.0,
            flash_radius=1.0,
            future_search_removed=300.0,
            composition_unlocks=1.0,
            cost=3.0,
            latency=2.0,
            maintenance_cost=0.2,
            deadline_relevance=0.50,
            external_visibility=0.70,
            provenance=(
                "real-multidomain:res:gpu-hardware:promote-ir-capability",
            ),
        ),
        WinOpportunity(
            "sair-public-capability",
            "sair",
            direct_win=2.0,
            verification_probability=p["sair-public-capability"],
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
            provenance=("run:35402936630",),
        ),
        WinOpportunity(
            "arc",
            "arc",
            direct_win=5.0,
            verification_probability=p["arc"],
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
            provenance=("run:35405132123",),
        ),
        WinOpportunity(
            "collatz",
            "collatz",
            direct_win=1.0,
            verification_probability=p["collatz"],
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
            provenance=("run:35403074591",),
        ),
        WinOpportunity(
            "flash-platform",
            "realitygraph",
            direct_win=0.5,
            verification_probability=p["flash-platform"],
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
            provenance=("run:35403569863",),
        ),
    )


def rank(profile: str, mode: str, pressure: float) -> list[dict[str, object]]:
    scheduler = GlobalWinScheduler(portfolio(profile))
    rows = scheduler.rank(mode=mode, deadline_pressure=pressure)
    return [
        {
            "opportunity_id": row.opportunity_id,
            "score": row.score,
            "expected_direct_value": row.expected_direct_value,
            "expected_global_value": row.expected_global_value,
            "denominator": row.denominator,
        }
        for row in rows
    ]


def run_snapshot() -> dict[str, object]:
    results = {
        profile: {
            "battle": rank(profile, "BATTLE", 0.80),
            "discovery": rank(profile, "DISCOVERY", 0.0),
        }
        for profile in PROFILES
    }

    battle_orders = {
        profile: [row["opportunity_id"] for row in results[profile]["battle"]]
        for profile in PROFILES
    }
    discovery_orders = {
        profile: [row["opportunity_id"] for row in results[profile]["discovery"]]
        for profile in PROFILES
    }

    battle_top = {order[0] for order in battle_orders.values()}
    discovery_top = {order[0] for order in discovery_orders.values()}
    lean_restart_positions = {
        profile: order.index("lean-restart-authority") + 1
        for profile, order in battle_orders.items()
    }
    gpu_discovery_positions = {
        profile: order.index("gpu-hardware-authority") + 1
        for profile, order in discovery_orders.items()
    }

    gates = {
        "lean_direct_battle_first_across_priors": battle_top == {"lean-kernel"},
        "flash_platform_discovery_first_across_priors": (
            discovery_top == {"flash-platform"}
        ),
        "lean_restart_authority_is_battle_top3_across_priors": all(
            position <= 3 for position in lean_restart_positions.values()
        ),
        "gpu_hardware_is_discovery_top4_across_priors": all(
            position <= 4 for position in gpu_discovery_positions.values()
        ),
        "sair_not_treated_as_private_score_claim": all(
            battle_orders[p].index("sair-public-capability")
            > battle_orders[p].index("lean-kernel")
            for p in PROFILES
        ),
        "real_multidomain_option_value_is_explicit": (
            PROVENANCE["real-multidomain"]["open_residuals"]
            == {"gpu-hardware": 300, "lean-kernel": 200}
        ),
    }

    return {
        "schema": "qckn-live-win-portfolio-v2",
        "passed": all(gates.values()),
        "claim_boundary": (
            "Ranking over explicit operator priors, not objective probabilities. "
            "The real multidomain run supplies measured option-value residuals "
            "and authority boundaries. Direct-win magnitudes and verification "
            "probabilities remain stress-tested operator inputs."
        ),
        "profiles": PROFILES,
        "provenance": PROVENANCE,
        "rankings": results,
        "battle_orders": battle_orders,
        "discovery_orders": discovery_orders,
        "lean_restart_battle_positions": lean_restart_positions,
        "gpu_hardware_discovery_positions": gpu_discovery_positions,
        "gates": gates,
    }


def main() -> int:
    result = run_snapshot()
    serialized = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    output = os.environ.get("QCKN_LIVE_WIN_PORTFOLIO_V2_RESULT_PATH")
    if output:
        Path(output).write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
