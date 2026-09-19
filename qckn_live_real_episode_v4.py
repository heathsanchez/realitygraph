from __future__ import annotations

import argparse
import json
from pathlib import Path

from realitygraph.flash_contract import (
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
    lean_p={"conservative":0.65,"neutral":0.80,"aggressive":0.90}[profile]
    return (
        WinOpportunity(
            "lean-isvalidchar-frontier-diagnostic",
            "lean-kernel",
            direct_win=10.0,
            verification_probability=lean_p,
            authority_readiness=1.0,
            destination_bridge_probability=0.20,
            flash_radius=5.0,
            future_search_removed=25.0,
            composition_unlocks=1.0,
            cost=2.5,
            latency=2.0,
            maintenance_cost=0.2,
            deadline_relevance=1.0,
            external_visibility=1.0,
            provenance=(
                "frontier-profile:isValidChar_UInt32-second-largest",
                "obstruction:direct-nat-le-no-performance-win",
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
    p.add_argument("--episode3",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()

    pre=load(Path(args.precommit))
    target=load(Path(args.target))
    ep3=load(Path(args.episode3))

    if pre.get("schema")!="qckn-live-real-episode-v4-precommit":
        raise AssertionError("unexpected episode4 precommit")
    if target.get("schema")!="direct-nat-le-transition-v1":
        raise AssertionError("unexpected target schema")
    if target["precommit"]["realitygraph_commit"]!="c8837b46f507dfc556c37ada5c5af3550784ac25":
        raise AssertionError("target not bound to episode4 precommit")
    if ep3.get("schema")!="qckn-live-real-episode-v3" or ep3.get("verdict")!="PASS":
        raise AssertionError("episode3 chain missing")

    gates=target["gates"]
    semantic_green=all(
        gates[k]
        for k in (
            "semantic_statuses_match_cold",
            "no_wrong_reject",
            "candidate_exercised",
            "restart_reproduces_candidate",
            "ablation_restores_cold",
        )
    )
    economic_green=bool(gates["candidate_improves_steps_or_wall_time"])
    if not semantic_green or economic_green:
        raise AssertionError("unexpected direct-transition outcome classification")

    frontier=FrontierState(
        "frontier:lean-transition",
        "lean-kernel",
        base_search_cost=3,
        search_cost=3,
        route_ids={
            "route:lean-direct-nat-le-transition-rule",
            "route:lean-isvalidchar-frontier-diagnostic",
            "route:lean-other-residual",
        },
        base_route_ids={
            "route:lean-direct-nat-le-transition-rule",
            "route:lean-isvalidchar-frontier-diagnostic",
            "route:lean-other-residual",
        },
    )
    rules=(
        DependencyRule(
            "remove-direct-transition-route",
            "direct_nat_le_no_performance_win",
            "frontier:lean-transition",
            "remove_route",
            "route:lean-direct-nat-le-transition-rule",
        ),
        DependencyRule(
            "record-direct-transition-economic-obstruction",
            "direct_nat_le_no_performance_win",
            "frontier:lean-transition",
            "add_obstruction",
            "lean:direct-nat-le-transition-no-performance-win:v1",
        ),
    )
    rt=IncrementalFlashRuntime((frontier,),rules)
    before=rt.snapshot()
    ev=FlashEvent(
        "episode4:direct-nat-le-candidate-result",
        FlashEventKind.OBSTRUCTION,
        "lean-kernel",
        "direct_nat_le_no_performance_win",
        "run:35425309044",
        (
            "precommit:c8837b46f507dfc556c37ada5c5af3550784ac25",
            "artifact:10578129606",
            "digest:sha256:9506f7027530df998d33641cff7c6c95d98f2c8a55670820fb7f7b29d80436f5",
        ),
    )
    delta=rt.admit(ev)
    after=rt.snapshot()

    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=True)
    state=out/"compiled-present.json"
    rt.save_compiled_present(state)
    restarted=IncrementalFlashRuntime.load_compiled_present(state,rules)

    profiles={p:rank(p) for p in ("conservative","neutral","aggressive")}
    battle={p:x["battle"][0] for p,x in profiles.items()}
    discovery={p:x["discovery"][0] for p,x in profiles.items()}

    eliminated=len(before["frontiers"]["frontier:lean-transition"]["route_ids"])-len(after["frontiers"]["frontier:lean-transition"]["route_ids"])
    cumulative=int(ep3["closure"]["cumulative_exact_routes_eliminated"])+eliminated

    comparison=target["comparison"]
    gates_out={
        "precommit_bound_before_target":pre["frozen_before_target_experiment"] is True,
        "semantic_target_controls_green":semantic_green,
        "economic_gate_failed":economic_green is False,
        "candidate_slower_than_cold":comparison["candidate_elapsed_ms"]>comparison["cold_elapsed_ms"],
        "exact_direct_rule_route_eliminated":eliminated==1,
        "economic_obstruction_compiled":"lean:direct-nat-le-transition-no-performance-win:v1" in after["frontiers"]["frontier:lean-transition"]["obstructions"],
        "restart_without_replay":restarted.replayed_events_on_restart==0 and restarted.snapshot()["frontiers"]==after["frontiers"],
        "battle_reselection_stable":len(set(battle.values()))==1,
        "discovery_reselection_stable":len(set(discovery.values()))==1,
        "four_real_cycles_eliminated_four_exact_routes":cumulative==4,
    }

    result={
        "schema":"qckn-live-real-episode-v4",
        "verdict":"PASS" if all(gates_out.values()) else "FAIL",
        "cycle":4,
        "source_episode3":{
            "run_id":35425168709,
            "artifact_id":10578117716,
            "artifact_digest":"sha256:3bd1bc23e71c242b40cb05c7c9b93fc4de56ca7a95588fefacd2fcc44af4f682",
        },
        "target":{
            "run_id":35425309044,
            "artifact_id":10578129606,
            "artifact_digest":"sha256:9506f7027530df998d33641cff7c6c95d98f2c8a55670820fb7f7b29d80436f5",
            "workflow_conclusion":"failure_expected_from_frozen_economic_gate",
            "semantic_green":semantic_green,
            "economic_green":economic_green,
            "comparison":comparison,
        },
        "closure":{
            "event_kind":ev.kind.value,
            "exact_routes_eliminated_this_cycle":eliminated,
            "cumulative_exact_routes_eliminated":cumulative,
            "after_routes":after["frontiers"]["frontier:lean-transition"]["route_ids"],
            "obstructions":after["frontiers"]["frontier:lean-transition"]["obstructions"],
        },
        "reselection":{
            "profiles":profiles,
            "battle_consensus":battle,
            "discovery_consensus":discovery,
            "next_battle_experiment":next(iter(battle.values())),
            "next_discovery_experiment":next(iter(discovery.values())),
        },
        "gates":gates_out,
        "claim_boundary":(
            "Fourth prospectively frozen real developmental cycle. The direct LE.le Nat "
            "transition candidate matched cold semantics on the two target cases and replay/"
            "ablation controls, but did not improve steps and was materially slower on this "
            "contract. Because the frozen economic gate failed, public-corpus promotion was "
            "not attempted. The durable consequence is an economic obstruction for this exact "
            "guarded realization on the current deep-list contract, not a semantic refutation "
            "of the definitional transition."
        ),
    }
    (out/"episode4.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "verdict":result["verdict"],
        "target":result["target"],
        "closure":result["closure"],
        "battle_consensus":battle,
        "discovery_consensus":discovery,
        "gates":gates_out,
        "claim_boundary":result["claim_boundary"],
    },indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V4" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V4")
    return 0 if result["verdict"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
