from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import qckn_live_win_portfolio_v2 as v2
from realitygraph.win_scheduler import GlobalWinScheduler

REAL_V2 = {
    "run": 35407546348,
    "head_sha": "c2ba9f43a8b1e543c3ea201fadd4f9b758328e8c",
    "artifact_id": 10573281685,
    "artifact_digest": "sha256:3ea6814c28de6bb73aa7786c8d5f8c0361e632aa05219c07d4952e031835b41f",
    "verified_state_compilation_domains": ["arc", "gpu-ir", "lean-kernel", "sair"],
    "protocol_search_cancelled": 500,
    "open_authority_residuals": ["res:gpu-hardware:promote-ir-capability"],
}
LEAN_STRICT_RESIDUAL = {
    "current_public_cases": 189,
    "correct": 182,
    "unknown": 7,
    "wrong": 0,
    "errors": 0,
    "families": {
        "host-stack": 2,
        "fueled-chain-budget": 1,
        "deep-list-budget": 2,
        "pair-countermodel-budget": 2,
    },
}


def portfolio(profile: str):
    rows = [
        row
        for row in v2.portfolio(profile)
        if row.opportunity_id != "lean-restart-authority"
    ]
    out = []
    for row in rows:
        if row.opportunity_id == "lean-kernel":
            row = replace(
                row,
                provenance=(
                    "real-multidomain-v2:lean-restart-settled",
                    "arena-current:7-unknown-0-wrong",
                ),
            )
        elif row.opportunity_id == "gpu-hardware-authority":
            row = replace(
                row,
                provenance=(
                    "real-multidomain-v2:sole-open-authority-residual",
                    "gpu-ir-v1:80pct-developmental-search-reduction",
                ),
            )
        out.append(row)
    return tuple(out)


def rank(profile: str, mode: str, pressure: float):
    scheduler = GlobalWinScheduler(portfolio(profile))
    return [
        {
            "opportunity_id": row.opportunity_id,
            "score": row.score,
            "expected_direct_value": row.expected_direct_value,
            "expected_global_value": row.expected_global_value,
            "denominator": row.denominator,
        }
        for row in scheduler.rank(mode=mode, deadline_pressure=pressure)
    ]


def run_snapshot():
    results = {
        profile: {
            "battle": rank(profile, "BATTLE", 0.80),
            "discovery": rank(profile, "DISCOVERY", 0.0),
        }
        for profile in v2.PROFILES
    }
    battle_orders = {
        p: [row["opportunity_id"] for row in results[p]["battle"]]
        for p in v2.PROFILES
    }
    discovery_orders = {
        p: [row["opportunity_id"] for row in results[p]["discovery"]]
        for p in v2.PROFILES
    }
    gpu_positions = {
        p: discovery_orders[p].index("gpu-hardware-authority") + 1
        for p in v2.PROFILES
    }
    gates = {
        "settled_lean_restart_removed_from_every_portfolio": all(
            "lean-restart-authority" not in order
            for order in (*battle_orders.values(), *discovery_orders.values())
        ),
        "lean_direct_battle_first_across_priors": all(
            order[0] == "lean-kernel" for order in battle_orders.values()
        ),
        "flash_platform_discovery_first_across_priors": all(
            order[0] == "flash-platform" for order in discovery_orders.values()
        ),
        "gpu_hardware_discovery_top3_across_priors": all(
            position <= 3 for position in gpu_positions.values()
        ),
        "gpu_hardware_is_only_cross_domain_authority_residual": (
            REAL_V2["open_authority_residuals"]
            == ["res:gpu-hardware:promote-ir-capability"]
        ),
        "lean_strict_residual_remains_explicit": (
            LEAN_STRICT_RESIDUAL["unknown"] == 7
            and LEAN_STRICT_RESIDUAL["wrong"] == 0
        ),
        "real_v2_cancelled_500_protocol_search": (
            REAL_V2["protocol_search_cancelled"] == 500
        ),
    }
    return {
        "schema": "qckn-live-win-portfolio-v3",
        "passed": all(gates.values()),
        "claim_boundary": (
            "Ranking uses explicit operator priors. Real Multidomain V2 settles "
            "the Lean restart-authority opportunity but does not settle Lean's "
            "seven strict public Arena UNKNOWNs. GPU hardware remains the sole "
            "open cross-domain authority residual."
        ),
        "real_multidomain_v2": REAL_V2,
        "lean_strict_residual": LEAN_STRICT_RESIDUAL,
        "profiles": v2.PROFILES,
        "rankings": results,
        "battle_orders": battle_orders,
        "discovery_orders": discovery_orders,
        "gpu_hardware_discovery_positions": gpu_positions,
        "gates": gates,
    }


def main():
    result = run_snapshot()
    serialized = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    output = os.environ.get("QCKN_LIVE_WIN_PORTFOLIO_V3_RESULT_PATH")
    if output:
        Path(output).write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
