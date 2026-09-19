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
    lp={"conservative":0.98,"neutral":0.99,"aggressive":1.0}[profile]
    return (
        WinOpportunity(
            "lean-substitution-lineage-reclosure","lean-kernel",10.0,lp,
            1.0,1.0,8.0,120.0,4.0,0.5,0.5,0.1,1.0,1.0,
            provenance=(
                "run:35434288923",
                "classification:diffuse-cross-product",
                "repo-history:deferred-substitution+argument-independent+compiled-plan",
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
    p=argparse.ArgumentParser();p.add_argument("--precommit",required=True);p.add_argument("--target",required=True);p.add_argument("--episode11",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    pre,target,ep11=load(a.precommit),load(a.target),load(a.episode11)
    if pre.get("schema")!="qckn-live-real-episode-v12-precommit": raise AssertionError("bad precommit")
    if target.get("schema")!="substitute-generated-argument-fanout-v1": raise AssertionError("bad target")
    if target["precommit"]["realitygraph_commit"]!="6842cb48501c6ee40825b70adcf424c68d5a1c4f": raise AssertionError("target not frozen")
    if ep11.get("schema")!="qckn-live-real-episode-v11" or ep11.get("verdict")!="PASS": raise AssertionError("episode11 missing")
    if not all(target["gates"].values()): raise AssertionError("target gates failed")
    if target["classification"]!="diffuse-cross-product": raise AssertionError("unexpected classification")

    rows=target["rows"]
    if not all(r["substitute_top32_expression_coverage"]<0.20 and r["substitute_top32_argument_coverage"]<0.50 for r in rows):
        raise AssertionError("diffuse concentration changed")

    frontier=FrontierState("frontier:substitute-fanout","lean-kernel",3,3,
        route_ids={"route:lean-substitute-generated-argument-fanout-diagnostic","route:lean-substitution-lineage-reclosure","route:lean-other-residual"},
        base_route_ids={"route:lean-substitute-generated-argument-fanout-diagnostic","route:lean-substitution-lineage-reclosure","route:lean-other-residual"})
    rules=(
        DependencyRule("remove-fanout-route","substitute_cross_product_diffuse","frontier:substitute-fanout","remove_route","route:lean-substitute-generated-argument-fanout-diagnostic"),
        DependencyRule("record-cross-product-obstruction","substitute_cross_product_diffuse","frontier:substitute-fanout","add_obstruction","lean:substitute-generated-cross-product-diffuse:v1"),
    )
    rt=IncrementalFlashRuntime((frontier,),rules);before=rt.snapshot()
    ev=FlashEvent("episode12:substitute-fanout-result",FlashEventKind.OBSTRUCTION,"lean-kernel","substitute_cross_product_diffuse","run:35434288923",(
        "precommit:6842cb48501c6ee40825b70adcf424c68d5a1c4f","artifact:10581547095","digest:sha256:7157f1c2f21dce8f94be944229857a4ed7b2e1af80854ed3b4fe7e6ed463911d"))
    delta=rt.admit(ev);after=rt.snapshot()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);state=out/"compiled-present.json";rt.save_compiled_present(state)
    restarted=IncrementalFlashRuntime.load_compiled_present(state,rules)
    profiles={p:rank(p) for p in ("conservative","neutral","aggressive")};battle={p:x["battle"][0] for p,x in profiles.items()};discovery={p:x["discovery"][0] for p,x in profiles.items()}
    eliminated=len(before["frontiers"]["frontier:substitute-fanout"]["route_ids"])-len(after["frontiers"]["frontier:substitute-fanout"]["route_ids"])
    cumulative=int(ep11["closure"]["cumulative_exact_routes_eliminated"])+eliminated
    gates={
      "precommit_bound_before_target":pre["frozen_before_target_experiment"] is True,
      "diffuse_cross_product_verified":target["classification"]=="diffuse-cross-product",
      "both_sides_diffuse_both_cases":all(r["substitute_top32_expression_coverage"]<0.20 and r["substitute_top32_argument_coverage"]<0.50 for r in rows),
      "exact_fanout_route_eliminated":eliminated==1,
      "obstruction_compiled":"lean:substitute-generated-cross-product-diffuse:v1" in after["frontiers"]["frontier:substitute-fanout"]["obstructions"],
      "restart_without_replay":restarted.replayed_events_on_restart==0 and restarted.snapshot()["frontiers"]==after["frontiers"],
      "battle_reselection_stable":len(set(battle.values()))==1,
      "discovery_reselection_stable":len(set(discovery.values()))==1,
      "twelve_real_cycles_eliminated_twelve_exact_routes":cumulative==12,
    }
    result={"schema":"qckn-live-real-episode-v12","verdict":"PASS" if all(gates.values()) else "FAIL","cycle":12,
      "source_episode11":{"run_id":35434165106,"artifact_id":10581302233,"artifact_digest":"sha256:094d665aefdd209b0265d06a590e3e239aa9007c91abb706c566cb8b9b0bfe36"},
      "target":{"run_id":35434288923,"artifact_id":10581547095,"artifact_digest":"sha256:7157f1c2f21dce8f94be944229857a4ed7b2e1af80854ed3b4fe7e6ed463911d","classification":target["classification"],"sampled":[r["substitute_fanout_sampled"] for r in rows],"expression_identity_counts":[r["substitute_expression_identity_count"] for r in rows],"argument_identity_counts":[r["substitute_argument_identity_count"] for r in rows],"top32_expression_coverages":[r["substitute_top32_expression_coverage"] for r in rows],"top32_argument_coverages":[r["substitute_top32_argument_coverage"] for r in rows]},
      "closure":{"event_kind":ev.kind.value,"exact_routes_eliminated_this_cycle":eliminated,"cumulative_exact_routes_eliminated":cumulative,"after_routes":after["frontiers"]["frontier:substitute-fanout"]["route_ids"],"obstructions":after["frontiers"]["frontier:substitute-fanout"]["obstructions"]},
      "reselection":{"profiles":profiles,"battle_consensus":battle,"discovery_consensus":discovery,"next_battle_experiment":next(iter(battle.values())),"next_discovery_experiment":next(iter(discovery.values()))},
      "gates":gates,
      "claim_boundary":"Twelfth prospectively frozen real cycle. Substitute-generated new-argument events form a diffuse identity cross-product: 8,801 expression identities and 920 argument identities per case, with top-32 coverage only ~14.2% and ~39.0% respectively. This rules out the frozen hot-identity-basis route. Before inventing a higher-level representation, the graph now selects a zero/low-cost reclosure over prior substitution experiments already present in repository history."}
    (out/"episode12.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":result["verdict"],"target":result["target"],"closure":result["closure"],"battle_consensus":battle,"discovery_consensus":discovery,"gates":gates,"claim_boundary":result["claim_boundary"]},indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V12" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V12")
    return 0 if result["verdict"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
