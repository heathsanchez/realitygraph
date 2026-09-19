from __future__ import annotations

import argparse,json
from pathlib import Path

from realitygraph.flash_contract import DependencyRule,FlashEvent,FlashEventKind,FrontierState,IncrementalFlashRuntime
from realitygraph.win_scheduler import GlobalWinScheduler,WinOpportunity


def load(p):
    v=json.loads(Path(p).read_text())
    if not isinstance(v,dict): raise TypeError(p)
    return v


def market(profile):
    lp={"conservative":0.60,"neutral":0.75,"aggressive":0.88}[profile]
    return (
        WinOpportunity(
            "lean-isvalidchar-operation-chain-diagnostic","lean-kernel",10.0,lp,
            1.0,0.20,5.0,30.0,2.0,2.5,2.0,0.2,1.0,1.0,
            provenance=("isvalidchar:no-single-method-majority","substitute-make-whnf-cluster"),
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


def rank(profile):
    s=GlobalWinScheduler(market(profile))
    return {
        "battle":[x.opportunity_id for x in s.rank(mode="BATTLE",deadline_pressure=0.80)],
        "discovery":[x.opportunity_id for x in s.rank(mode="DISCOVERY",deadline_pressure=0.0)],
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--precommit",required=True)
    p.add_argument("--target",required=True)
    p.add_argument("--episode4",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()

    pre,target,ep4=load(a.precommit),load(a.target),load(a.episode4)
    if pre.get("schema")!="qckn-live-real-episode-v5-precommit": raise AssertionError("bad precommit")
    if target.get("schema")!="isvalidchar-method-profile-v1": raise AssertionError("bad target")
    if target["precommit"]["realitygraph_commit"]!="6bb224e72e2183e79b40298a5033349159a7e59e": raise AssertionError("target not frozen")
    if ep4.get("schema")!="qckn-live-real-episode-v4" or ep4.get("verdict")!="PASS": raise AssertionError("episode4 missing")

    g=target["gates"]
    expected_negative=(
        g["no_wrong_reject"] and
        g["both_remain_unknown_at_4m"] and
        g["profile_nonempty"] and
        g["same_dominant_method"] and
        (not g["dominant_method_majority"]) and
        g["common_terminal_frontier"]
    )
    if not expected_negative: raise AssertionError("unexpected method-profile outcome")

    frontier=FrontierState(
        "frontier:isvalidchar","lean-kernel",3,3,
        route_ids={"route:lean-isvalidchar-frontier-diagnostic","route:lean-isvalidchar-operation-chain-diagnostic","route:lean-other-residual"},
        base_route_ids={"route:lean-isvalidchar-frontier-diagnostic","route:lean-isvalidchar-operation-chain-diagnostic","route:lean-other-residual"},
    )
    rules=(
        DependencyRule("remove-method-route","isvalidchar_no_single_method_majority","frontier:isvalidchar","remove_route","route:lean-isvalidchar-frontier-diagnostic"),
        DependencyRule("record-method-obstruction","isvalidchar_no_single_method_majority","frontier:isvalidchar","add_obstruction","lean:isvalidchar-no-single-method-majority:v1"),
    )
    rt=IncrementalFlashRuntime((frontier,),rules)
    before=rt.snapshot()
    ev=FlashEvent(
        "episode5:isvalidchar-method-profile-result",
        FlashEventKind.OBSTRUCTION,
        "lean-kernel",
        "isvalidchar_no_single_method_majority",
        "run:35425587870",
        (
            "precommit:6bb224e72e2183e79b40298a5033349159a7e59e",
            "artifact:10578654535",
            "digest:sha256:89673729c6c226a83e8706ad62da53d3443cfffd491b8d8eb8202a5f13710dbe",
        ),
    )
    delta=rt.admit(ev)
    after=rt.snapshot()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    state=out/"compiled-present.json";rt.save_compiled_present(state)
    restarted=IncrementalFlashRuntime.load_compiled_present(state,rules)

    profiles={p:rank(p) for p in ("conservative","neutral","aggressive")}
    battle={p:x["battle"][0] for p,x in profiles.items()}
    discovery={p:x["discovery"][0] for p,x in profiles.items()}
    eliminated=len(before["frontiers"]["frontier:isvalidchar"]["route_ids"])-len(after["frontiers"]["frontier:isvalidchar"]["route_ids"])
    cumulative=int(ep4["closure"]["cumulative_exact_routes_eliminated"])+eliminated

    method_profiles=target["method_profiles"]
    top3=[
        [{"method":x["method"],"ticks":x["ticks"]} for x in row[:3]]
        for row in method_profiles
    ]
    gates={
        "precommit_bound_before_target":pre["frozen_before_target_experiment"] is True,
        "expected_no_single_method_outcome":expected_negative,
        "same_top_three_methods": [x["method"] for x in top3[0]]==[x["method"] for x in top3[1]],
        "exact_method_route_eliminated":eliminated==1,
        "obstruction_compiled":"lean:isvalidchar-no-single-method-majority:v1" in after["frontiers"]["frontier:isvalidchar"]["obstructions"],
        "restart_without_replay":restarted.replayed_events_on_restart==0 and restarted.snapshot()["frontiers"]==after["frontiers"],
        "battle_reselection_stable":len(set(battle.values()))==1,
        "discovery_reselection_stable":len(set(discovery.values()))==1,
        "five_real_cycles_eliminated_five_exact_routes":cumulative==5,
    }

    result={
        "schema":"qckn-live-real-episode-v5",
        "verdict":"PASS" if all(gates.values()) else "FAIL",
        "cycle":5,
        "source_episode4":{"run_id":35425477279,"artifact_id":10578499369,"artifact_digest":"sha256:dc4049fff8c38f924e804250770df80fde88726c1d4fc726ac783b9bfe24abcc"},
        "target":{
            "run_id":35425587870,
            "artifact_id":10578654535,
            "artifact_digest":"sha256:89673729c6c226a83e8706ad62da53d3443cfffd491b8d8eb8202a5f13710dbe",
            "workflow_conclusion":"failure_expected_from_frozen_majority_gate",
            "same_dominant_method":True,
            "dominant_method_majority":False,
            "top3_methods":top3,
        },
        "closure":{
            "event_kind":ev.kind.value,
            "exact_routes_eliminated_this_cycle":eliminated,
            "cumulative_exact_routes_eliminated":cumulative,
            "after_routes":after["frontiers"]["frontier:isvalidchar"]["route_ids"],
            "obstructions":after["frontiers"]["frontier:isvalidchar"]["obstructions"],
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
            "Fifth prospectively frozen real developmental cycle. Both deep-list cases share "
            "the same isValidChar_UInt32 method ordering, but no single method accounts for "
            "a majority of attributed ticks. The durable consequence is therefore an obstruction "
            "against a single-method explanation and a narrower next diagnostic over the common "
            "substitute/make/whnf operation chain, not an optimization claim."
        ),
    }
    (out/"episode5.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({
        "verdict":result["verdict"],"target":result["target"],"closure":result["closure"],
        "battle_consensus":battle,"discovery_consensus":discovery,"gates":gates,
        "claim_boundary":result["claim_boundary"],
    },indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V5" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V5")
    return 0 if result["verdict"]=="PASS" else 1


if __name__=="__main__": raise SystemExit(main())
