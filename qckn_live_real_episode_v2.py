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


def market(profile: str):
    p={"conservative":0.55,"neutral":0.70,"aggressive":0.85}[profile]
    return (
        WinOpportunity(
            "lean-nat-le-transition-quotient-diagnostic",
            "lean-kernel",
            direct_win=9.0,
            verification_probability=p,
            authority_readiness=1.0,
            destination_bridge_probability=0.25,
            flash_radius=5.0,
            future_search_removed=20.0,
            composition_unlocks=2.0,
            cost=2.5,
            latency=2.0,
            maintenance_cost=0.2,
            deadline_relevance=1.0,
            external_visibility=1.0,
            provenance=(
                "run:35422152175",
                "obstruction:whnf-memoization-no-net-win",
                "observation:Nat.succ_le_succ-common-hotspot",
            ),
        ),
        WinOpportunity(
            "sair-true-proof-compounding","sair",8.0,
            {"conservative":0.40,"neutral":0.55,"aggressive":0.70}[profile],
            0.90,0.60,5.0,100.0,2.0,5.0,4.0,0.3,0.90,0.90,
            provenance=("sair-v6:false-side-compounding-qualified",),
        ),
        WinOpportunity(
            "arc-next-capability","arc",6.0,
            {"conservative":0.45,"neutral":0.60,"aggressive":0.75}[profile],
            0.95,0.75,5.0,80.0,2.0,4.0,3.0,0.3,0.80,0.90,
            provenance=("arc-v3:restart-refutation-qualified",),
        ),
        WinOpportunity(
            "collatz-obstruction-closure","collatz",4.0,
            {"conservative":0.35,"neutral":0.50,"aggressive":0.65}[profile],
            0.95,0.25,3.0,200.0,1.0,6.0,4.0,0.2,0.70,0.80,
            provenance=("collatz:bank-order-redundancy:v1",),
        ),
        WinOpportunity(
            "flash-platform-next","realitygraph",2.0,
            {"conservative":0.80,"neutral":0.90,"aggressive":1.00}[profile],
            1.0,1.0,8.0,300.0,4.0,2.0,1.0,0.5,0.60,0.60,
            provenance=("qckn-live-developmental-substrate-v2:green",),
        ),
    )


def rank(profile: str):
    s=GlobalWinScheduler(market(profile))
    b=s.rank(mode="BATTLE",deadline_pressure=0.80)
    d=s.rank(mode="DISCOVERY",deadline_pressure=0.0)
    return {
        "battle":[x.opportunity_id for x in b],
        "discovery":[x.opportunity_id for x in d],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--precommit",required=True)
    p.add_argument("--target",required=True)
    p.add_argument("--episode1",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()

    pre=load(Path(args.precommit))
    target=load(Path(args.target))
    ep1=load(Path(args.episode1))

    if pre.get("schema")!="qckn-live-real-episode-v2-precommit":
        raise AssertionError("unexpected episode2 precommit")
    if target.get("schema")!="localdef-whnf-cache-overhead-decomposition-v1":
        raise AssertionError("unexpected target schema")
    if target["precommit"]["realitygraph_commit"]!="596038b0d96fcda4780056be10bc69766bbcdaf7":
        raise AssertionError("target not bound to frozen episode2 precommit")
    if not all(target["gates"].values()):
        raise AssertionError("target gates failed")
    if ep1.get("schema")!="qckn-live-real-episode-v1" or ep1.get("verdict")!="PASS":
        raise AssertionError("episode1 chain missing")
    if target["next_route"]!="pivot-away-from-whnf-memoization":
        raise AssertionError("unexpected frozen classification")

    cap=CapabilityState(
        "lean:succ-le-succ-whnf-memoization:v1",
        "VERIFIED",
        "RESERVE",
        "run:35422152175/artifact:10576714731",
        "semantically valid exact reuse, but no net wall-time win under frozen 2M-step contract",
    )
    frontier=FrontierState(
        "frontier:lean-cache",
        "lean-kernel",
        base_search_cost=3,
        search_cost=3,
        route_ids={
            "route:lean-cache-overhead-decomposition",
            "route:lean-nat-le-transition-quotient-diagnostic",
            "route:lean-other-residual",
        },
        base_route_ids={
            "route:lean-cache-overhead-decomposition",
            "route:lean-nat-le-transition-quotient-diagnostic",
            "route:lean-other-residual",
        },
    )
    rules=(
        DependencyRule(
            "remove-overhead-route",
            "whnf_memoization_no_net_win",
            "frontier:lean-cache",
            "remove_route",
            "route:lean-cache-overhead-decomposition",
        ),
        DependencyRule(
            "reserve-memoization",
            "whnf_memoization_no_net_win",
            "frontier:lean-cache",
            "reserve_capability",
            cap.capability_id,
        ),
        DependencyRule(
            "compile-memo-obstruction",
            "whnf_memoization_no_net_win",
            "frontier:lean-cache",
            "add_obstruction",
            "lean:whnf-memoization-no-net-win-at-2m:v1",
        ),
    )
    rt=IncrementalFlashRuntime((frontier,),rules,(cap,))
    before=rt.snapshot()
    event=FlashEvent(
        "episode2:overhead-decomposition-result",
        FlashEventKind.OBSTRUCTION,
        "lean-kernel",
        "whnf_memoization_no_net_win",
        "run:35422152175",
        (
            "precommit:596038b0d96fcda4780056be10bc69766bbcdaf7",
            "artifact:10576714731",
            "digest:sha256:eb405f9383ad5a2b765ea466e8a0fe58637ea9747747b9d4107b7a77f478d6b6",
        ),
    )
    delta=rt.admit(event)
    after=rt.snapshot()

    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    state=out/"compiled-present.json"
    rt.save_compiled_present(state)
    restarted=IncrementalFlashRuntime.load_compiled_present(state,rules)

    profiles={p:rank(p) for p in ("conservative","neutral","aggressive")}
    battle={p:x["battle"][0] for p,x in profiles.items()}
    discovery={p:x["discovery"][0] for p,x in profiles.items()}

    routes_before=len(before["frontiers"]["frontier:lean-cache"]["route_ids"])
    routes_after=len(after["frontiers"]["frontier:lean-cache"]["route_ids"])
    eliminated=routes_before-routes_after
    cumulative=int(ep1["closure"]["exact_future_acquisition_routes_eliminated"])+eliminated

    gates={
        "precommit_bound_before_target":pre["frozen_before_target_experiment"] is True,
        "classification_obeyed":target["next_route"]=="pivot-away-from-whnf-memoization",
        "exact_route_eliminated":eliminated==1 and "route:lean-cache-overhead-decomposition" not in after["frontiers"]["frontier:lean-cache"]["route_ids"],
        "memoization_obstruction_compiled":"lean:whnf-memoization-no-net-win-at-2m:v1" in after["frontiers"]["frontier:lean-cache"]["obstructions"],
        "semantic_capability_retained_in_reserve":cap.capability_id in after["frontiers"]["frontier:lean-cache"]["reserve_capabilities"],
        "restart_without_replay":restarted.replayed_events_on_restart==0 and restarted.snapshot()["frontiers"]==after["frontiers"],
        "battle_reselection_stable":len(set(battle.values()))==1,
        "discovery_reselection_stable":len(set(discovery.values()))==1,
        "two_real_cycles_eliminated_two_exact_routes":cumulative==2,
    }

    result={
        "schema":"qckn-live-real-episode-v2",
        "verdict":"PASS" if all(gates.values()) else "FAIL",
        "cycle":2,
        "source_episode1":{
            "run_id":35422069761,
            "artifact_id":10577249725,
            "artifact_digest":"sha256:4d2b1bb252c0865738c4ceaefac82c0b3708a5d523c07081c0edf2e4b6dccf1f",
        },
        "target":{
            "run_id":35422152175,
            "artifact_id":10576714731,
            "artifact_digest":"sha256:eb405f9383ad5a2b765ea466e8a0fe58637ea9747747b9d4107b7a77f478d6b6",
            "totals_ms":target["totals_ms"],
            "deltas_ms":target["deltas_ms"],
            "classification":target["classification"],
            "next_route":target["next_route"],
        },
        "closure":{
            "event_kind":event.kind.value,
            "touched_frontiers":list(delta.touched_frontiers),
            "changed_frontiers":list(delta.changed_frontiers),
            "exact_routes_eliminated_this_cycle":eliminated,
            "cumulative_exact_routes_eliminated":cumulative,
            "after_routes":after["frontiers"]["frontier:lean-cache"]["route_ids"],
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
            "Second prospectively frozen real developmental cycle. The measured negative result "
            "is scoped to the current Nat.succ_le_succ deep-list frontier, 2M semantic-step "
            "budget, GitHub runner and exact memoization realizations tested. It does not prove "
            "memoization is universally harmful. The durable consequence is narrower: these "
            "specific verified cache realizations need not be reacquired under the same contract."
        ),
    }
    (out/"episode2.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "verdict":result["verdict"],
        "target":result["target"],
        "closure":result["closure"],
        "battle_consensus":battle,
        "discovery_consensus":discovery,
        "gates":gates,
        "claim_boundary":result["claim_boundary"],
    },indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V2" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V2")
    return 0 if result["verdict"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
