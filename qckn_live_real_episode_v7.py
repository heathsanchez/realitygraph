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
    lp={"conservative":0.68,"neutral":0.82,"aggressive":0.92}[profile]
    return (
        WinOpportunity(
            "lean-substitute-consequence-accounting-diagnostic","lean-kernel",11.0,lp,
            1.0,0.20,6.0,45.0,2.0,2.0,1.5,0.2,1.0,1.0,
            provenance=(
                "run:35432756619",
                "obstruction:substitute-make-shapes-distributed",
                "existing:binder-cache+structural-sharing+compiled-node-reuse",
            ),
        ),
        WinOpportunity("sair-true-proof-compounding","sair",8.0,{"conservative":0.40,"neutral":0.55,"aggressive":0.70}[profile],0.90,0.60,5.0,100.0,2.0,5.0,4.0,0.3,0.90,0.90,provenance=("sair-v6:false-side-compounding-qualified",)),
        WinOpportunity("arc-next-capability","arc",6.0,{"conservative":0.45,"neutral":0.60,"aggressive":0.75}[profile],0.95,0.75,5.0,80.0,2.0,4.0,3.0,0.3,0.80,0.90,provenance=("arc-v3:restart-refutation-qualified",)),
        WinOpportunity("collatz-obstruction-closure","collatz",4.0,{"conservative":0.35,"neutral":0.50,"aggressive":0.65}[profile],0.95,0.25,3.0,200.0,1.0,6.0,4.0,0.2,0.70,0.80,provenance=("collatz:bank-order-redundancy:v1",)),
        WinOpportunity("flash-platform-next","realitygraph",2.0,{"conservative":0.80,"neutral":0.90,"aggressive":1.00}[profile],1.0,1.0,8.0,300.0,4.0,2.0,1.0,0.5,0.60,0.60,provenance=("qckn-live-developmental-substrate-v2:green",)),
    )

def rank(profile):
    s=GlobalWinScheduler(market(profile))
    return {"battle":[x.opportunity_id for x in s.rank(mode="BATTLE",deadline_pressure=0.80)],"discovery":[x.opportunity_id for x in s.rank(mode="DISCOVERY",deadline_pressure=0.0)]}

def main():
    p=argparse.ArgumentParser();p.add_argument("--precommit",required=True);p.add_argument("--target",required=True);p.add_argument("--episode6",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    pre,target,ep6=load(a.precommit),load(a.target),load(a.episode6)
    if pre.get("schema")!="qckn-live-real-episode-v7-precommit": raise AssertionError("bad precommit")
    if target.get("schema")!="substitute-make-shape-quotient-diagnostic-v1": raise AssertionError("bad target")
    if target["precommit"]["realitygraph_commit"]!="37de6528971f8664b622aa64aac6044013e2203f": raise AssertionError("target not frozen")
    if ep6.get("schema")!="qckn-live-real-episode-v6" or ep6.get("verdict")!="PASS": raise AssertionError("episode6 missing")
    if not all(target["gates"].values()): raise AssertionError("target gates failed")
    if target["classification"]!="distributed-shapes": raise AssertionError("unexpected classification")

    rows=target["rows"]
    for row in rows:
        x=row["attempts"][-1]
        if x["substitute_make_shape_class_count"]<=16 or x["substitute_make_top8_shape_coverage"]>=0.99:
            raise AssertionError("shape distribution no longer matches outcome")

    frontier=FrontierState("frontier:substitute-make","lean-kernel",3,3,
        route_ids={"route:lean-substitute-make-shape-quotient-diagnostic","route:lean-substitute-consequence-accounting-diagnostic","route:lean-other-residual"},
        base_route_ids={"route:lean-substitute-make-shape-quotient-diagnostic","route:lean-substitute-consequence-accounting-diagnostic","route:lean-other-residual"})
    rules=(
        DependencyRule("remove-shape-route","substitute_make_shapes_distributed","frontier:substitute-make","remove_route","route:lean-substitute-make-shape-quotient-diagnostic"),
        DependencyRule("record-shape-obstruction","substitute_make_shapes_distributed","frontier:substitute-make","add_obstruction","lean:substitute-make-no-small-shape-basis:v1"),
    )
    rt=IncrementalFlashRuntime((frontier,),rules);before=rt.snapshot()
    ev=FlashEvent("episode7:substitute-make-shape-result",FlashEventKind.OBSTRUCTION,"lean-kernel","substitute_make_shapes_distributed","run:35432756619",(
        "precommit:37de6528971f8664b622aa64aac6044013e2203f","artifact:10581495447","digest:sha256:62f636ef62bcf001ec92892a513a9e4f5b9ae774a78a1752687f7430027c8261"))
    delta=rt.admit(ev);after=rt.snapshot()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);state=out/"compiled-present.json";rt.save_compiled_present(state)
    restarted=IncrementalFlashRuntime.load_compiled_present(state,rules)
    profiles={p:rank(p) for p in ("conservative","neutral","aggressive")};battle={p:x["battle"][0] for p,x in profiles.items()};discovery={p:x["discovery"][0] for p,x in profiles.items()}
    eliminated=len(before["frontiers"]["frontier:substitute-make"]["route_ids"])-len(after["frontiers"]["frontier:substitute-make"]["route_ids"])
    cumulative=int(ep6["closure"]["cumulative_exact_routes_eliminated"])+eliminated
    gates={
      "precommit_bound_before_target":pre["frozen_before_target_experiment"] is True,
      "distributed_shape_outcome_verified":target["classification"]=="distributed-shapes",
      "both_cases_identical_top_shapes":target["shape_profiles"][0]==target["shape_profiles"][1],
      "exact_shape_route_eliminated":eliminated==1,
      "obstruction_compiled":"lean:substitute-make-no-small-shape-basis:v1" in after["frontiers"]["frontier:substitute-make"]["obstructions"],
      "restart_without_replay":restarted.replayed_events_on_restart==0 and restarted.snapshot()["frontiers"]==after["frontiers"],
      "battle_reselection_stable":len(set(battle.values()))==1,
      "discovery_reselection_stable":len(set(discovery.values()))==1,
      "seven_real_cycles_eliminated_seven_exact_routes":cumulative==7,
    }
    result={"schema":"qckn-live-real-episode-v7","verdict":"PASS" if all(gates.values()) else "FAIL","cycle":7,
      "source_episode6":{"run_id":35425959951,"artifact_id":10579535046,"artifact_digest":"sha256:990769532bbffb81625a145703c8333506bd399f58951b53082033548cb38022"},
      "target":{"run_id":35432756619,"artifact_id":10581495447,"artifact_digest":"sha256:62f636ef62bcf001ec92892a513a9e4f5b9ae774a78a1752687f7430027c8261","classification":target["classification"],"shape_class_counts":[r["attempts"][-1]["substitute_make_shape_class_count"] for r in rows],"top8_coverages":[r["attempts"][-1]["substitute_make_top8_shape_coverage"] for r in rows]},
      "closure":{"event_kind":ev.kind.value,"exact_routes_eliminated_this_cycle":eliminated,"cumulative_exact_routes_eliminated":cumulative,"after_routes":after["frontiers"]["frontier:substitute-make"]["route_ids"],"obstructions":after["frontiers"]["frontier:substitute-make"]["obstructions"]},
      "reselection":{"profiles":profiles,"battle_consensus":battle,"discovery_consensus":discovery,"next_battle_experiment":next(iter(battle.values())),"next_discovery_experiment":next(iter(discovery.values()))},
      "gates":gates,
      "claim_boundary":"Seventh prospectively frozen real cycle. The shallow substitute->make shape basis is distributed (38 classes, top-8 coverage about 70.1%) despite identical distributions across both cases. This refutes the frozen small-shape-basis hypothesis only. The next diagnostic measures where existing exact binder caches, closed-subtree skips and structural node reuse succeed or fail before inventing another representation."}
    (out/"episode7.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":result["verdict"],"target":result["target"],"closure":result["closure"],"battle_consensus":battle,"discovery_consensus":discovery,"gates":gates,"claim_boundary":result["claim_boundary"]},indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V7" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V7")
    return 0 if result["verdict"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
