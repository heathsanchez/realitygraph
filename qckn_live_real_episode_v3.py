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
    direct_p={"conservative":0.70,"neutral":0.85,"aggressive":0.95}[profile]
    return (
        WinOpportunity(
            "lean-direct-nat-le-transition-rule",
            "lean-kernel",
            direct_win=12.0,
            verification_probability=direct_p,
            authority_readiness=1.0,
            destination_bridge_probability=0.25,
            flash_radius=6.0,
            future_search_removed=40.0,
            composition_unlocks=2.0,
            cost=2.5,
            latency=2.0,
            maintenance_cost=0.2,
            deadline_relevance=1.0,
            external_visibility=1.0,
            provenance=(
                "run:35425078446",
                "classification:quotient-and-direct-transition-candidate",
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
    p.add_argument("--episode2",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()

    pre=load(Path(args.precommit))
    target=load(Path(args.target))
    ep2=load(Path(args.episode2))

    if pre.get("schema")!="qckn-live-real-episode-v3-precommit":
        raise AssertionError("unexpected episode3 precommit")
    if target.get("schema")!="nat-le-transition-quotient-diagnostic-v1":
        raise AssertionError("unexpected target schema")
    if target["precommit"]["realitygraph_commit"]!="2c01cb013734253ade4129fa4728b64f6f33d164":
        raise AssertionError("target not bound to episode3 precommit")
    if not all(target["gates"].values()):
        raise AssertionError("target diagnostic gates failed")
    if ep2.get("schema")!="qckn-live-real-episode-v2" or ep2.get("verdict")!="PASS":
        raise AssertionError("episode2 chain missing")

    classification=target["classification"]
    if classification!="quotient-and-direct-transition-candidate":
        raise AssertionError("direct-transition path not licensed")

    frontier=FrontierState(
        "frontier:lean-transition",
        "lean-kernel",
        base_search_cost=3,
        search_cost=3,
        route_ids={
            "route:lean-nat-le-transition-quotient-diagnostic",
            "route:lean-direct-nat-le-transition-rule",
            "route:lean-other-residual",
        },
        base_route_ids={
            "route:lean-nat-le-transition-quotient-diagnostic",
            "route:lean-direct-nat-le-transition-rule",
            "route:lean-other-residual",
        },
    )
    rules=(
        DependencyRule(
            "remove-transition-diagnostic",
            "nat_le_transition_quotient_verified",
            "frontier:lean-transition",
            "remove_route",
            "route:lean-nat-le-transition-quotient-diagnostic",
        ),
        DependencyRule(
            "record-transition-separator",
            "nat_le_transition_quotient_verified",
            "frontier:lean-transition",
            "add_separator",
            "lean:le-le-nat-instlenat-to-nat-le:v1",
        ),
    )
    rt=IncrementalFlashRuntime((frontier,),rules)
    before=rt.snapshot()
    ev=FlashEvent(
        "episode3:nat-le-transition-diagnostic-result",
        FlashEventKind.VERIFIED_SEPARATOR,
        "lean-kernel",
        "nat_le_transition_quotient_verified",
        "run:35425078446",
        (
            "precommit:2c01cb013734253ade4129fa4728b64f6f33d164",
            "artifact:10578288835",
            "digest:sha256:55af8ffd71d8ee527b6169192a2bd18b6d0a344f9a7f4c70a8a85c00d059ffeb",
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
    cumulative=int(ep2["closure"]["cumulative_exact_routes_eliminated"])+eliminated

    rows=target["rows"]
    gates={
        "precommit_bound_before_target":pre["frozen_before_target_experiment"] is True,
        "diagnostic_classifies_direct_candidate":classification=="quotient-and-direct-transition-candidate",
        "dominant_output_head_stable":len({r["dominant_output_head"] for r in rows})==1,
        "transition_space_small":all(r["transition_class_count"]<=8 and r["top8_coverage"]>=0.99 for r in rows),
        "exact_diagnostic_route_eliminated":eliminated==1,
        "separator_compiled":"lean:le-le-nat-instlenat-to-nat-le:v1" in after["frontiers"]["frontier:lean-transition"]["separators"],
        "restart_without_replay":restarted.replayed_events_on_restart==0 and restarted.snapshot()["frontiers"]==after["frontiers"],
        "battle_reselection_stable":len(set(battle.values()))==1,
        "discovery_reselection_stable":len(set(discovery.values()))==1,
        "three_real_cycles_eliminated_three_exact_routes":cumulative==3,
    }

    result={
        "schema":"qckn-live-real-episode-v3",
        "verdict":"PASS" if all(gates.values()) else "FAIL",
        "cycle":3,
        "source_episode2":{
            "run_id":35422326680,
            "artifact_id":10578065010,
            "artifact_digest":"sha256:12dd7f614f93dfe79883bad21c862172039acbf0d291b7c619f033a31e2b508e",
        },
        "target":{
            "run_id":35425078446,
            "artifact_id":10578288835,
            "artifact_digest":"sha256:55af8ffd71d8ee527b6169192a2bd18b6d0a344f9a7f4c70a8a85c00d059ffeb",
            "classification":classification,
            "rows":[
                {
                    "name":r["name"],
                    "target_calls":r["target_calls"],
                    "sampled":r["sampled"],
                    "transition_class_count":r["transition_class_count"],
                    "top8_coverage":r["top8_coverage"],
                    "dominant_transition_count":r["dominant_transition_count"],
                    "dominant_output_head":r["dominant_output_head"],
                }
                for r in rows
            ],
        },
        "closure":{
            "event_kind":ev.kind.value,
            "exact_routes_eliminated_this_cycle":eliminated,
            "cumulative_exact_routes_eliminated":cumulative,
            "after_routes":after["frontiers"]["frontier:lean-transition"]["route_ids"],
            "separators":after["frontiers"]["frontier:lean-transition"]["separators"],
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
            "Third prospectively frozen real developmental cycle. The diagnostic shows a small, "
            "stable transition family from LE.le Nat instLENat toward Nat.le inside the measured "
            "Nat.succ_le_succ hotspot. This licenses a prospective direct-transition candidate, "
            "not the semantic rule itself. The rewrite remains untrusted until an independent "
            "cold/restart/ablation qualification and corpus regression pass."
        ),
    }
    (out/"episode3.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "verdict":result["verdict"],
        "target":result["target"],
        "closure":result["closure"],
        "battle_consensus":battle,
        "discovery_consensus":discovery,
        "gates":gates,
        "claim_boundary":result["claim_boundary"],
    },indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V3" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V3")
    return 0 if result["verdict"]=="PASS" else 1


if __name__=="__main__":
    raise SystemExit(main())
