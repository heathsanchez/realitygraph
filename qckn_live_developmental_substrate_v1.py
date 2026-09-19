from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from realitygraph.win_scheduler import (
    GlobalWinScheduler,
    VerifiedWinEvent,
    WinOpportunity,
)


PROFILES = {
    "conservative": {
        "lean-kernel": 0.55,
        "sair-true-proof-compounding": 0.40,
        "arc-next-capability": 0.45,
        "collatz-obstruction-closure": 0.35,
        "flash-platform-next": 0.80,
        "gpu-hardware-generalization": 0.35,
    },
    "neutral": {
        "lean-kernel": 0.70,
        "sair-true-proof-compounding": 0.55,
        "arc-next-capability": 0.60,
        "collatz-obstruction-closure": 0.50,
        "flash-platform-next": 0.90,
        "gpu-hardware-generalization": 0.50,
    },
    "aggressive": {
        "lean-kernel": 0.85,
        "sair-true-proof-compounding": 0.70,
        "arc-next-capability": 0.75,
        "collatz-obstruction-closure": 0.65,
        "flash-platform-next": 1.00,
        "gpu-hardware-generalization": 0.65,
    },
}

ROUTE_IDS = {
    "lean_unfold": "route:lean-ordinary-unfold",
    "arc_repeat": "route:arc-ft09-vc33-repeat",
    "collatz_repeat": "route:collatz-bank-order-repeat",
    "sair_reacquire": "route:sair-residual12-reacquire",
    "lean_resource_only": "route:lean-resource-only-scaling",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object in {path}")
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prob(profile: str, key: str) -> float:
    return float(PROFILES[profile][key])


def portfolio(profile: str) -> tuple[WinOpportunity, ...]:
    rows = [
        WinOpportunity(
            "lean-kernel",
            "lean-kernel",
            direct_win=10.0,
            verification_probability=_prob(profile, "lean-kernel"),
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
                "real-flash-v3:authority-closed",
                "lean:deep-list-post-semantic-frontier",
            ),
        ),
        WinOpportunity(
            "sair-true-proof-compounding",
            "sair",
            direct_win=8.0,
            verification_probability=_prob(profile, "sair-true-proof-compounding"),
            authority_readiness=0.90,
            destination_bridge_probability=0.60,
            flash_radius=5.0,
            future_search_removed=100.0,
            composition_unlocks=2.0,
            cost=5.0,
            latency=4.0,
            maintenance_cost=0.3,
            deadline_relevance=0.90,
            external_visibility=0.90,
            provenance=(
                "sair-v6:false-side-compounding-qualified",
                "next:proof-side-reuse",
            ),
        ),
        WinOpportunity(
            "arc-next-capability",
            "arc",
            direct_win=6.0,
            verification_probability=_prob(profile, "arc-next-capability"),
            authority_readiness=0.95,
            destination_bridge_probability=0.75,
            flash_radius=5.0,
            future_search_removed=80.0,
            composition_unlocks=2.0,
            cost=4.0,
            latency=3.0,
            maintenance_cost=0.3,
            deadline_relevance=0.80,
            external_visibility=0.90,
            provenance=(
                "arc-v3:restart-refutation-qualified",
                "live-router:arc-obstruction-active",
            ),
        ),
        WinOpportunity(
            "collatz-obstruction-closure",
            "collatz",
            direct_win=4.0,
            verification_probability=_prob(profile, "collatz-obstruction-closure"),
            authority_readiness=0.95,
            destination_bridge_probability=0.25,
            flash_radius=3.0,
            future_search_removed=200.0,
            composition_unlocks=1.0,
            cost=6.0,
            latency=4.0,
            maintenance_cost=0.2,
            deadline_relevance=0.70,
            external_visibility=0.80,
            provenance=(
                "live-router:collatz-bank-order-obstruction",
            ),
        ),
        WinOpportunity(
            "flash-platform-next",
            "realitygraph",
            direct_win=2.0,
            verification_probability=_prob(profile, "flash-platform-next"),
            authority_readiness=1.0,
            destination_bridge_probability=1.0,
            flash_radius=8.0,
            future_search_removed=300.0,
            composition_unlocks=4.0,
            cost=2.0,
            latency=1.0,
            maintenance_cost=0.5,
            deadline_relevance=0.60,
            external_visibility=0.60,
            provenance=(
                "real-flash-v3:no-declared-authority-residuals",
                "live-router-v3:persistent-event-state",
            ),
        ),
        WinOpportunity(
            "gpu-hardware-generalization",
            "gpu-hardware",
            direct_win=3.0,
            verification_probability=_prob(profile, "gpu-hardware-generalization"),
            authority_readiness=0.80,
            destination_bridge_probability=0.80,
            flash_radius=2.0,
            future_search_removed=30.0,
            composition_unlocks=1.0,
            cost=5.0,
            latency=3.0,
            maintenance_cost=0.5,
            deadline_relevance=0.50,
            external_visibility=0.80,
            provenance=(
                "rtx4090:v1-two-shapes-qualified",
                "generalization-not-yet-authorized",
            ),
        ),
    ]

    # Exact routes that live evidence is allowed to remove. Their cost is in
    # scheduler prioritization units only, not a measured cross-domain scalar.
    for oid, domain in (
        (ROUTE_IDS["lean_unfold"], "lean-kernel"),
        (ROUTE_IDS["arc_repeat"], "arc"),
        (ROUTE_IDS["collatz_repeat"], "collatz"),
        (ROUTE_IDS["sair_reacquire"], "sair"),
        (ROUTE_IDS["lean_resource_only"], "lean-kernel"),
    ):
        rows.append(
            WinOpportunity(
                oid,
                domain,
                direct_win=0.1,
                verification_probability=1.0,
                authority_readiness=1.0,
                destination_bridge_probability=0.0,
                flash_radius=0.0,
                future_search_removed=0.0,
                composition_unlocks=0.0,
                cost=1.0,
                latency=1.0,
                maintenance_cost=0.0,
                deadline_relevance=0.2,
                external_visibility=0.1,
                provenance=("exact-route-control",),
            )
        )
    return tuple(rows)


def _rank(scheduler: GlobalWinScheduler, mode: str, pressure: float) -> list[dict[str, Any]]:
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


def _resolve_route(
    scheduler: GlobalWinScheduler,
    route_id: str,
    *,
    event_id: str,
    provenance: tuple[str, ...],
) -> None:
    if scheduler.opportunities[route_id].status != "OPEN":
        return
    scheduler.admit_event(
        VerifiedWinEvent(
            event_id=event_id,
            source_opportunity_id=route_id,
            verified=True,
            provenance=provenance,
        )
    )


def _validate_v3(v3: dict[str, Any]) -> None:
    if v3.get("schema") != "qckn-real-multidomain-flash-v3":
        raise AssertionError("unexpected V3 schema")
    if v3.get("verdict") != "PASS" or not all(v3.get("gates", {}).values()):
        raise AssertionError("real multidomain V3 is not fully green")
    residuals = v3.get("residuals", {})
    if not residuals or any(row.get("status") != "SETTLED" for row in residuals.values()):
        raise AssertionError("V3 still has a declared authority residual")
    bus = v3.get("event_bus", {})
    if bus.get("edge_count") != 5 or bus.get("hardware_edge_count") != 1:
        raise AssertionError("V3 event-bus authority shape changed")


def _validate_live(cycle: dict[str, Any], context: dict[str, Any]) -> None:
    if cycle.get("schema") != "qckn-flash-live-router-cycle-v1":
        raise AssertionError("unexpected live-router schema")
    summary = cycle["summary"]
    if summary.get("external_events", 0) < 6:
        raise AssertionError("live router lost events")
    if summary.get("active_capabilities", 0) < 4:
        raise AssertionError("live router lost active capabilities")
    if summary.get("obstructions", 0) < 2:
        raise AssertionError("live router lost obstructions")
    if context.get("schema") != "qckn-flash-context-view-v1":
        raise AssertionError("unexpected context view")
    if "lean:ordinary-unfold-neutral:v1" not in set(
        context.get("contextual_reserve_capability_ids", [])
    ):
        raise AssertionError("ordinary-unfold reserve state changed")
    required_active = {
        "lean:direct-framed-prune:v1",
        "lean:direct-var:v1",
        "sair:residual12-portfolio:v1",
    }
    if not required_active <= set(context.get("contextual_active_capability_ids", [])):
        raise AssertionError("contextual active capability set changed")


def _validate_deep_list(row: dict[str, Any]) -> None:
    if row.get("schema") != "deep-list-semantic-repair-v1":
        raise AssertionError("unexpected deep-list evidence schema")
    if not all(row.get("gates", {}).values()):
        raise AssertionError("deep-list semantic repair gate is not green")
    cases = row.get("rows", [])
    if len(cases) != 2:
        raise AssertionError("expected two deep-list cases")
    for case in cases:
        attempts = case.get("attempts", [])
        if not attempts or attempts[-1].get("budget") != 8_000_000:
            raise AssertionError("deep-list budget horizon changed")
        if attempts[-1].get("status") != "UNKNOWN":
            raise AssertionError("deep-list terminal status changed")
        if any(a.get("status") == "REJECT" for a in attempts):
            raise AssertionError("deep-list candidate reintroduced wrong reject")


def _apply_live_effects(
    scheduler: GlobalWinScheduler,
    cycle: dict[str, Any],
    context: dict[str, Any],
    deep: dict[str, Any],
) -> list[dict[str, str]]:
    applied: list[dict[str, str]] = []
    summary = cycle["summary"]
    obstructions = set(summary.get("obstruction_ids", []))
    active = set(context.get("contextual_active_capability_ids", []))
    reserve = set(context.get("contextual_reserve_capability_ids", []))

    if "lean:ordinary-unfold-neutral:v1" in reserve:
        _resolve_route(
            scheduler,
            ROUTE_IDS["lean_unfold"],
            event_id="substrate:lean-unfold-reserve",
            provenance=("live-context:ordinary-unfold-reserve",),
        )
        applied.append({"route": ROUTE_IDS["lean_unfold"], "reason": "contextual-reserve"})

    if "arc3:ft09-vc33-transfer-refutation:v2" in obstructions:
        _resolve_route(
            scheduler,
            ROUTE_IDS["arc_repeat"],
            event_id="substrate:arc-repeat-refuted",
            provenance=("live-obstruction:arc3-ft09-vc33",),
        )
        applied.append({"route": ROUTE_IDS["arc_repeat"], "reason": "exact-refutation"})

    if "collatz:bank-order-redundancy:v1" in obstructions:
        _resolve_route(
            scheduler,
            ROUTE_IDS["collatz_repeat"],
            event_id="substrate:collatz-bank-order-refuted",
            provenance=("live-obstruction:collatz-bank-order",),
        )
        applied.append({"route": ROUTE_IDS["collatz_repeat"], "reason": "exact-obstruction"})

    if "sair:residual12-portfolio:v1" in active:
        _resolve_route(
            scheduler,
            ROUTE_IDS["sair_reacquire"],
            event_id="substrate:sair-residual12-reuse",
            provenance=("live-capability:sair-residual12-portfolio",),
        )
        applied.append({"route": ROUTE_IDS["sair_reacquire"], "reason": "compiled-capability"})

    # The post-resource Lean experiment established that simply increasing the
    # resource envelope does not close the two deep-list cases; the semantic
    # candidate remains UNKNOWN even at 8M without a wrong reject.
    _validate_deep_list(deep)
    _resolve_route(
        scheduler,
        ROUTE_IDS["lean_resource_only"],
        event_id="substrate:lean-resource-only-refuted",
        provenance=("run:35412538505", "PASS_DEEP_LIST_SEMANTIC_REPAIR_V1"),
    )
    applied.append(
        {
            "route": ROUTE_IDS["lean_resource_only"],
            "reason": "resource-only-route-refuted",
        }
    )
    return applied


def run_profile(
    profile: str,
    v3: dict[str, Any],
    cycle: dict[str, Any],
    context: dict[str, Any],
    deep: dict[str, Any],
) -> dict[str, Any]:
    scheduler = GlobalWinScheduler(portfolio(profile))
    before_battle = _rank(scheduler, "BATTLE", 0.80)
    before_discovery = _rank(scheduler, "DISCOVERY", 0.0)

    applied = _apply_live_effects(scheduler, cycle, context, deep)

    after_battle = _rank(scheduler, "BATTLE", 0.80)
    after_discovery = _rank(scheduler, "DISCOVERY", 0.0)
    metrics = scheduler.metrics()

    resolved_routes = {
        row["route"] for row in applied
    }
    expected_routes = set(ROUTE_IDS.values())

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
        "applied_live_effects": applied,
        "scheduler_metrics": metrics,
        "gates": {
            "all_exact_routes_removed": resolved_routes == expected_routes,
            "all_declared_authority_residuals_already_settled": all(
                row["status"] == "SETTLED" for row in v3["residuals"].values()
            ),
            "lean_is_battle_first": after_battle[0]["opportunity_id"] == "lean-kernel",
            "flash_is_discovery_first": (
                after_discovery[0]["opportunity_id"] == "flash-platform-next"
            ),
            "resolved_routes_absent_from_rankings": not (
                expected_routes
                & {
                    row["opportunity_id"]
                    for row in (*after_battle, *after_discovery)
                }
            ),
        },
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--v3-result", required=True)
    p.add_argument("--live-cycle", required=True)
    p.add_argument("--context-view", required=True)
    p.add_argument("--deep-list-evidence", required=True)
    p.add_argument("--live-meta", required=True)
    p.add_argument("--deep-meta", required=True)
    p.add_argument("--previous-state")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    v3_path = Path(args.v3_result)
    live_cycle_path = Path(args.live_cycle)
    context_path = Path(args.context_view)
    deep_path = Path(args.deep_list_evidence)
    live_meta_path = Path(args.live_meta)
    deep_meta_path = Path(args.deep_meta)

    v3 = _load(v3_path)
    cycle = _load(live_cycle_path)
    context = _load(context_path)
    deep = _load(deep_path)
    live_meta = _load(live_meta_path)
    deep_meta = _load(deep_meta_path)

    _validate_v3(v3)
    _validate_live(cycle, context)
    _validate_deep_list(deep)

    profiles = {
        profile: run_profile(profile, v3, cycle, context, deep)
        for profile in PROFILES
    }
    all_gates = {
        f"{profile}:{gate}": value
        for profile, row in profiles.items()
        for gate, value in row["gates"].items()
    }

    battle_tops = {
        profile: row["after"]["battle"][0]["opportunity_id"]
        for profile, row in profiles.items()
    }
    discovery_tops = {
        profile: row["after"]["discovery"][0]["opportunity_id"]
        for profile, row in profiles.items()
    }
    if len(set(battle_tops.values())) != 1:
        raise AssertionError(f"no battle consensus: {battle_tops}")
    if len(set(discovery_tops.values())) != 1:
        raise AssertionError(f"no discovery consensus: {discovery_tops}")

    previous = (
        _load(Path(args.previous_state))
        if args.previous_state and Path(args.previous_state).exists()
        else None
    )
    cycle_number = int(previous.get("cycle_number", 0)) + 1 if previous else 1
    history = list(previous.get("selection_history", [])) if previous else []

    selected = next(iter(battle_tops.values()))
    selected_experiment = {
        "opportunity_id": selected,
        "experiment_class": "deep-list-post-semantic-frontier",
        "repository": "heathsanchez/lean-kernel-arena",
        "ref": "mda-deep-list-semantic-repair-v1",
        "ref_sha": "a2450817fd57b6299f227f6e1e05f703c4292151",
        "source_evidence_run": 35412538505,
        "source_evidence_artifact": 10574609822,
        "next_question": (
            "after eliminating the latent rigid false reject and adding exact Nat "
            "reductions, what repeated consequence dominates the two 8M-step UNKNOWN frontiers?"
        ),
        "claim_boundary": (
            "diagnostic next-step selection only; no claim that additional budget "
            "or any unverified conversion rule will close the Arena cases"
        ),
    }
    history.append(
        {
            "cycle": cycle_number,
            "battle_selected": selected,
            "discovery_selected": next(iter(discovery_tops.values())),
            "live_event_count": cycle["summary"]["external_events"],
            "live_event_ids": cycle["summary"]["event_ids"],
            "deep_list_status": [
                {
                    "name": row["name"],
                    "terminal_budget": row["attempts"][-1]["budget"],
                    "terminal_status": row["attempts"][-1]["status"],
                    "terminal_steps": row["attempts"][-1]["steps"],
                }
                for row in deep["rows"]
            ],
        }
    )

    result = {
        "schema": "qckn-live-developmental-substrate-v1",
        "passed": all(all_gates.values()),
        "cycle_number": cycle_number,
        "inputs": {
            "v3_sha256": _sha(v3_path),
            "live_cycle_sha256": _sha(live_cycle_path),
            "context_view_sha256": _sha(context_path),
            "deep_list_evidence_sha256": _sha(deep_path),
            "live_artifact": live_meta,
            "deep_list_artifact": deep_meta,
        },
        "authority_state": {
            "declared_residuals_open": [],
            "declared_residuals_settled": sorted(v3["residuals"]),
            "real_flash_v3_graph_digest": v3["graph_snapshot"]["digest"],
            "hardware_authority": v3["hardware_authority"],
        },
        "live_state": {
            "external_events": cycle["summary"]["external_events"],
            "new_event_ids": cycle["new_event_ids"],
            "unchanged_event_ids": cycle["unchanged_event_ids"],
            "retained_past_event_ids": cycle["retained_past_event_ids"],
            "active_capability_ids": context["contextual_active_capability_ids"],
            "reserve_capability_ids": context["contextual_reserve_capability_ids"],
            "obstruction_ids": cycle["summary"]["obstruction_ids"],
            "producer_repositories": cycle["summary"]["repositories"],
        },
        "profiles": profiles,
        "battle_consensus": battle_tops,
        "discovery_consensus": discovery_tops,
        "selected_experiment": selected_experiment,
        "selection_history": history[-20:],
        "gates": all_gates,
        "claim_boundary": (
            "This is an authority-gated live developmental scheduling qualification. "
            "V3 supplies the closed declared authority graph; the persistent live router "
            "supplies current cross-repository capabilities and obstructions; the deep-list "
            "experiment supplies a current Lean local separator. Exact live evidence may "
            "remove only matching routes. Remaining opportunity probabilities, direct-win "
            "magnitudes, cost and latency values are explicit operator priors used for "
            "ranking, not objective probabilities or commensurate measured costs."
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "substrate.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    (out / "state.json").write_text(
        json.dumps(
            {
                "schema": "qckn-live-developmental-substrate-state-v1",
                "cycle_number": cycle_number,
                "selection_history": result["selection_history"],
                "last_battle_selection": selected,
                "last_discovery_selection": next(iter(discovery_tops.values())),
                "last_live_event_ids": cycle["summary"]["event_ids"],
                "last_graph_digest": v3["graph_snapshot"]["digest"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print(
        json.dumps(
            {
                "passed": result["passed"],
                "cycle_number": cycle_number,
                "live_state": result["live_state"],
                "battle_consensus": battle_tops,
                "discovery_consensus": discovery_tops,
                "selected_experiment": selected_experiment,
                "gates": all_gates,
                "claim_boundary": result["claim_boundary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(
        "PASS_QCKN_LIVE_DEVELOPMENTAL_SUBSTRATE_V1"
        if result["passed"]
        else "FAIL_QCKN_LIVE_DEVELOPMENTAL_SUBSTRATE_V1"
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
