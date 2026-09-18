from __future__ import annotations

import json
import os
from pathlib import Path

from realitygraph.win_scheduler import GlobalWinScheduler, WinOpportunity


PROFILES = {
    "conservative": {
        "lean-kernel": 0.55,
        "sair": 0.50,
        "arc": 0.35,
        "collatz": 0.45,
        "flash-platform": 0.90,
    },
    "neutral": {
        "lean-kernel": 0.70,
        "sair": 0.65,
        "arc": 0.50,
        "collatz": 0.60,
        "flash-platform": 1.00,
    },
    "aggressive": {
        "lean-kernel": 0.85,
        "sair": 0.80,
        "arc": 0.65,
        "collatz": 0.75,
        "flash-platform": 1.00,
    },
}


PROVENANCE = {
    "lean-kernel": {
        "repository": "heathsanchez/lean-kernel-arena",
        "branch": "mda-kernel-genesis-v1",
        "commit": "d965b8b790f69ae388b41feb08df59e3c7ce8648",
        "note": "exact-kernel work; direct external benchmark surface",
    },
    "sair": {
        "repository": "heathsanchez/test",
        "branch": "v30-sair-epistemic-compounding",
        "run": 32543510571,
        "note": "formal checked reasoning competition surface; current next-step probability remains an operator prior",
    },
    "arc": {
        "repository": "heathsanchez/Minimal-Sufficient-Interface",
        "branch": "arc3-global-flash-closure-v4",
        "run": 35405132123,
        "note": "public development diagnostics; V4 matched market-local protected performance, produced no structural prunes, and is not a hidden competition score",
    },
    "collatz": {
        "repository": "heathsanchez/test",
        "branch": "collatz-flash-propagation-v1",
        "run": 35403074591,
        "note": "bounded propagation qualified; no advantage over upfront guard and no termination claim",
    },
    "flash-platform": {
        "repository": "heathsanchez/realitygraph",
        "branch": "qckn-flash-closure-v1-frozen",
        "run": 35403569863,
        "note": "qualified developmental infrastructure; indirect external-win surface",
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
            provenance=(
                "commit:d965b8b790f69ae388b41feb08df59e3c7ce8648",
            ),
        ),
        WinOpportunity(
            "sair",
            "formal-reasoning",
            direct_win=8.0,
            verification_probability=p["sair"],
            authority_readiness=1.0,
            destination_bridge_probability=0.50,
            flash_radius=8.0,
            future_search_removed=40.0,
            composition_unlocks=3.0,
            cost=3.0,
            latency=2.5,
            maintenance_cost=0.2,
            deadline_relevance=0.90,
            external_visibility=1.0,
            provenance=("run:32543510571",),
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


def ranking(profile: str, mode: str, deadline_pressure: float) -> list[dict[str, object]]:
    scheduler = GlobalWinScheduler(portfolio(profile))
    rows = scheduler.rank(
        mode=mode,
        deadline_pressure=deadline_pressure,
    )
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
    results = {}
    for profile in PROFILES:
        results[profile] = {
            "battle": ranking(profile, "BATTLE", 0.80),
            "discovery": ranking(profile, "DISCOVERY", 0.0),
        }

    battle_orders = [
        tuple(row["opportunity_id"] for row in results[p]["battle"])
        for p in PROFILES
    ]
    discovery_orders = [
        tuple(row["opportunity_id"] for row in results[p]["discovery"])
        for p in PROFILES
    ]

    robust_battle = battle_orders[0] if len(set(battle_orders)) == 1 else ()
    robust_discovery = (
        discovery_orders[0] if len(set(discovery_orders)) == 1 else ()
    )

    return {
        "schema": "qckn-live-win-portfolio-v1",
        "claim_boundary": (
            "Ranking over explicit operator priors, not objective probabilities. "
            "Measured provenance fixes the current authority/status evidence; "
            "verification probabilities are stress-tested at conservative, "
            "neutral, and aggressive values. Domains without a current exact "
            "adapter are intentionally unranked."
        ),
        "profiles": PROFILES,
        "provenance": PROVENANCE,
        "rankings": results,
        "robust_battle_order": list(robust_battle),
        "robust_discovery_order": list(robust_discovery),
        "robust_battle_top_two": list(robust_battle[:2]),
        "robust_discovery_top": (
            robust_discovery[0] if robust_discovery else None
        ),
        "unranked_until_current_adapter": [
            "gpu-kernel-optimization",
            "robotics",
            "parkinsons",
            "other empirical competitions",
        ],
        "gates": {
            "battle_order_robust_across_priors": bool(robust_battle),
            "discovery_order_robust_across_priors": bool(robust_discovery),
            "battle_lean_first": bool(
                robust_battle and robust_battle[0] == "lean-kernel"
            ),
            "battle_sair_second": bool(
                len(robust_battle) > 1 and robust_battle[1] == "sair"
            ),
            "discovery_flash_first": bool(
                robust_discovery
                and robust_discovery[0] == "flash-platform"
            ),
        },
    }


def main() -> int:
    result = run_snapshot()
    result["passed"] = all(result["gates"].values())
    serialized = json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    output = os.environ.get("QCKN_LIVE_WIN_PORTFOLIO_RESULT_PATH")
    if output:
        Path(output).write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
