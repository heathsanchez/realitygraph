from __future__ import annotations

import argparse
import json
from pathlib import Path

from realitygraph.flash_contract import (
    CapabilityState,
    DependencyRule,
    FlashEvent,
    FlashEventKind,
    FrontierState,
    IncrementalFlashRuntime,
)
from realitygraph.win_scheduler import GlobalWinScheduler, WinOpportunity


def load(path: Path):
    value=json.loads(path.read_text())
    if not isinstance(value,dict):
        raise TypeError(path)
    return value


def next_market(profile: str):
    # Same qualitative priors as the earlier live substrate, but the exact
    # scoped-cache promotion route has been removed by the new outcome.
    probs={
        "conservative":0.55,
        "neutral":0.70,
        "aggressive":0.85,
    }
    p=probs[profile]
    return (
        WinOpportunity(
            "lean-cache-overhead-decomposition",
            "lean-kernel",
            direct_win=9.0,
            verification_probability=p,
            authority_readiness=1.0,
            destination_bridge_probability=0.20,
            flash_radius=4.0,
            future_search_removed=12.0,
            composition_unlocks=1.0,
            cost=2.0,
            latency=1.5,
            maintenance_cost=0.1,
            deadline_relevance=1.0,
            external_visibility=1.0,
            provenance=(
                "run:35421936419",
                "economic-obstruction:scoped-cache-reserve",
            ),
        ),
        WinOpportunity(
            "sair-true-proof-compounding",
            "sair",
            direct_win=8.0,
            verification_probability={"conservative":0.40,"neutral":0.55,"aggressive":0.70}[profile],
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
            provenance=("sair-v6:false-side-compounding-qualified",),
        ),
        WinOpportunity(
            "arc-next-capability",
            "arc",
            direct_win=6.0,
            verification_probability={"conservative":0.45,"neutral":0.60,"aggressive":0.75}[profile],
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
            provenance=("arc-v3:restart-refutation-qualified",),
        ),
        WinOpportunity(
            "collatz-obstruction-closure",
            "collatz",
            direct_win=4.0,
            verification_probability={"conservative":0.35,"neutral":0.50,"aggressive":0.65}[profile],
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
            provenance=("collatz:bank-order-redundancy:v1",),
        ),
        WinOpportunity(
            "flash-platform-next",
            "realitygraph",
            direct_win=2.0,
            verification_probability={"conservative":0.80,"neutral":0.90,"aggressive":1.00}[profile],
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
            provenance=("real-flash-v3:authority-closed",),
        ),
    )


def rank(profile: str):
    scheduler=GlobalWinScheduler(next_market(profile))
    battle=scheduler.rank(mode="BATTLE",deadline_pressure=0.80)
    discovery=scheduler.rank(mode="DISCOVERY",deadline_pressure=0.0)
    def rows(xs):
        return [
            {
                "opportunity_id":x.opportunity_id,
                "score":x.score,
                "expected_direct_value":x.expected_direct_value,
                "expected_global_value":x.expected_global_value,
                "denominator":x.denominator,
            }
            for x in xs
        ]
    return {"battle":rows(battle),"discovery":rows(discovery)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--precommit",required=True)
    p.add_argument("--target",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()

    pre=load(Path(args.precommit))
    target=load(Path(args.target))
    if pre.get("schema")!="qckn-live-real-episode-v1-precommit":
        raise AssertionError("unexpected precommit schema")
    if target.get("schema")!="succ-le-succ-scoped-localdef-whnf-cache-v1":
        raise AssertionError("unexpected target schema")
    if target["precommit"]["realitygraph_precommit_commit"]!="7a2806d8efa5b1b018c1adeb53bffbab6f2dbe54":
        raise AssertionError("target did not bind to frozen precommit")
    if not all(target.get("gates",{}).values()):
        raise AssertionError("target qualification failed")

    status=target["economic_status"]
    if status not in {"ACTIVE","RESERVE"}:
        raise AssertionError("unexpected economic status")

    cap=CapabilityState(
        "lean:succ-le-succ-scoped-localdef-whnf-cache:v1",
        "VERIFIED",
        status,
        "run:35421936419/artifact:10576959191",
        (
            "prospectively measured scoped realization; "
            f"economic_status={status}"
        ),
    )
    frontier=FrontierState(
        "frontier:lean-cache",
        "lean-kernel",
        base_search_cost=3,
        search_cost=3,
        route_ids={
            "route:lean-scoped-cache-promotion",
            "route:lean-cache-overhead-decomposition",
            "route:lean-other-residual",
        },
        base_route_ids={
            "route:lean-scoped-cache-promotion",
            "route:lean-cache-overhead-decomposition",
            "route:lean-other-residual",
        },
    )

    rules=[
        DependencyRule(
            "resolve-scoped-route-active",
            "scoped_cache_active",
            "frontier:lean-cache",
            "remove_route",
            "route:lean-scoped-cache-promotion",
        ),
        DependencyRule(
            "activate-scoped-cache",
            "scoped_cache_active",
            "frontier:lean-cache",
            "activate_capability",
            cap.capability_id,
        ),
        DependencyRule(
            "resolve-scoped-route-reserve",
            "scoped_cache_reserve",
            "frontier:lean-cache",
            "remove_route",
            "route:lean-scoped-cache-promotion",
        ),
        DependencyRule(
            "reserve-scoped-cache",
            "scoped_cache_reserve",
            "frontier:lean-cache",
            "reserve_capability",
            cap.capability_id,
        ),
        DependencyRule(
            "compile-economic-obstruction",
            "scoped_cache_reserve",
            "frontier:lean-cache",
            "add_obstruction",
            "lean:succ-le-succ-scoped-cache-not-profitable:v1",
        ),
    ]
    runtime=IncrementalFlashRuntime((frontier,),rules,(cap,))
    before=runtime.snapshot()
    key="scoped_cache_active" if status=="ACTIVE" else "scoped_cache_reserve"
    kind=(
        FlashEventKind.PROMOTED_CAPABILITY
        if status=="ACTIVE"
        else FlashEventKind.PREFERENCE_CHANGE
    )
    event=FlashEvent(
        "episode1:scoped-cache-result",
        kind,
        "lean-kernel",
        key,
        "run:35421936419",
        (
            "precommit:7a2806d8efa5b1b018c1adeb53bffbab6f2dbe54",
            "artifact:10576959191",
            "digest:sha256:38d389a8fa8e452f8cf872d5db2cbe2d152995600459730f278eb063c38aada1",
        ),
    )
    delta=runtime.admit(event)
    after=runtime.snapshot()

    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    state_path=out/"compiled-present.json"
    runtime.save_compiled_present(state_path)
    restarted=IncrementalFlashRuntime.load_compiled_present(state_path,rules)
    restarted_snapshot=restarted.snapshot()

    profiles={name:rank(name) for name in ("conservative","neutral","aggressive")}
    battle={name:data["battle"][0]["opportunity_id"] for name,data in profiles.items()}
    discovery={name:data["discovery"][0]["opportunity_id"] for name,data in profiles.items()}

    comp=target["comparison"]
    resolved_before=len(before["frontiers"]["frontier:lean-cache"]["route_ids"])
    resolved_after=len(after["frontiers"]["frontier:lean-cache"]["route_ids"])
    exact_routes_eliminated=resolved_before-resolved_after

    gates={
        "precommit_bound_before_result":pre["frozen_before_target_experiment"] is True,
        "qualification_green":all(target["gates"].values()),
        "promotion_rule_obeyed":(
            (status=="ACTIVE" and comp["scoped_elapsed_ms"]<comp["cold_elapsed_ms"])
            or
            (status=="RESERVE" and comp["scoped_elapsed_ms"]>=comp["cold_elapsed_ms"])
        ),
        "exact_selected_route_compiled_away":(
            "route:lean-scoped-cache-promotion"
            not in after["frontiers"]["frontier:lean-cache"]["route_ids"]
            and exact_routes_eliminated==1
        ),
        "economic_failure_becomes_obstruction_if_reserve":(
            status!="RESERVE"
            or "lean:succ-le-succ-scoped-cache-not-profitable:v1"
            in after["frontiers"]["frontier:lean-cache"]["obstructions"]
        ),
        "semantic_capability_retained":(
            cap.capability_id
            in (
                after["frontiers"]["frontier:lean-cache"]["active_capabilities"]
                if status=="ACTIVE"
                else after["frontiers"]["frontier:lean-cache"]["reserve_capabilities"]
            )
        ),
        "restart_no_replay":(
            restarted.replayed_events_on_restart==0
            and restarted_snapshot["frontiers"]==after["frontiers"]
        ),
        "battle_reselection_stable":len(set(battle.values()))==1,
        "discovery_reselection_stable":len(set(discovery.values()))==1,
    }

    result={
        "schema":"qckn-live-real-episode-v1",
        "verdict":"PASS" if all(gates.values()) else "FAIL",
        "cycle":1,
        "precommit":pre,
        "target_result":{
            "run_id":35421936419,
            "artifact_id":10576959191,
            "artifact_digest":"sha256:38d389a8fa8e452f8cf872d5db2cbe2d152995600459730f278eb063c38aada1",
            "economic_status":status,
            "comparison":comp,
        },
        "closure":{
            "event_kind":kind.value,
            "touched_frontiers":list(delta.touched_frontiers),
            "changed_frontiers":list(delta.changed_frontiers),
            "exact_future_acquisition_routes_eliminated":exact_routes_eliminated,
            "before_routes":before["frontiers"]["frontier:lean-cache"]["route_ids"],
            "after_routes":after["frontiers"]["frontier:lean-cache"]["route_ids"],
            "active_capabilities":after["frontiers"]["frontier:lean-cache"]["active_capabilities"],
            "reserve_capabilities":after["frontiers"]["frontier:lean-cache"]["reserve_capabilities"],
            "obstructions":after["frontiers"]["frontier:lean-cache"]["obstructions"],
        },
        "reselection":{
            "profiles":profiles,
            "battle_consensus":battle,
            "discovery_consensus":discovery,
            "next_battle_experiment":next(iter(battle.values())),
            "next_discovery_experiment":next(iter(discovery.values())),
        },
        "gates":gates,
        "claim_boundary":(
            "This is the first prospectively frozen target episode after the six-invariant "
            "Flash gate. The selected Lean realization and promotion rule were committed "
            "before the target run. One exact future acquisition route is counted as "
            "eliminated because that precise realization now has a verified economic "
            "classification. Wall-time milliseconds remain Lean-local and are not "
            "scalarized with SAIR, ARC, Collatz or GPU costs."
        ),
    }
    (out/"episode.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "verdict":result["verdict"],
        "target_result":result["target_result"],
        "closure":result["closure"],
        "battle_consensus":battle,
        "discovery_consensus":discovery,
        "gates":gates,
        "claim_boundary":result["claim_boundary"],
    },indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V1" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V1")
    return 0 if result["verdict"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
