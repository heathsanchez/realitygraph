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
    lp={"conservative":0.76,"neutral":0.88,"aggressive":0.96}[profile]
    return (
        WinOpportunity(
            "lean-substitute-app-allocation-diagnostic","lean-kernel",13.0,lp,
            1.0,0.20,6.0,70.0,2.0,2.0,1.5,0.2,1.0,1.0,
            provenance=(
                "run:35435040357",
                "classification:allocation-dominant",
                "fresh-app-allocations:745842",
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
    p=argparse.ArgumentParser();p.add_argument("--precommit",required=True);p.add_argument("--target",required=True);p.add_argument("--episode13",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    pre,target,ep13=load(a.precommit),load(a.target),load(a.episode13)
    if pre.get("schema")!="qckn-live-real-episode-v14-precommit": raise AssertionError("bad precommit")
    if target.get("schema")!="substitute-node-reuse-accounting-v1": raise AssertionError("bad target")
    if target["precommit"]["realitygraph_commit"]!="328d597b2836846e67ff527acd1434311792cc11": raise AssertionError("target not frozen")
    if ep13.get("schema")!="qckn-live-real-episode-v13" or ep13.get("verdict")!="PASS": raise AssertionError("episode13 missing")
    if not all(target["gates"].values()): raise AssertionError("target gates failed")
    if target["classification"]!="allocation-dominant": raise AssertionError("unexpected classification")

    rows=target["rows"]
    if not all(r["substitute_make_fresh_fraction"]>0.70 for r in rows): raise AssertionError("fresh-allocation dominance changed")
    app_rows=[]
    for r in rows:
        app=next(x for x in r["substitute_make_by_tag"] if x["tag"]=="app")
        if app["freshAllocation"]<700000: raise AssertionError("app allocation hotspot changed")
        app_rows.append(app)

    frontier=FrontierState("frontier:substitute-output","lean-kernel",3,3,
        route_ids={"route:lean-substitute-node-reuse-accounting-diagnostic","route:lean-substitute-app-allocation-diagnostic","route:lean-other-residual"},
        base_route_ids={"route:lean-substitute-node-reuse-accounting-diagnostic","route:lean-substitute-app-allocation-diagnostic","route:lean-other-residual"})
    rules=(
        DependencyRule("remove-node-accounting-route","substitution_output_allocation_dominant","frontier:substitute-output","remove_route","route:lean-substitute-node-reuse-accounting-diagnostic"),
        DependencyRule("record-allocation-separator","substitution_output_allocation_dominant","frontier:substitute-output","add_separator","lean:substitution-output-allocation-dominant:v1"),
        DependencyRule("record-app-hotspot","substitution_output_allocation_dominant","frontier:substitute-output","add_separator","lean:substitution-fresh-app-allocation-hotspot:v1"),
    )
    rt=IncrementalFlashRuntime((frontier,),rules);before=rt.snapshot()
    ev=FlashEvent("episode14:node-reuse-accounting-result",FlashEventKind.VERIFIED_SEPARATOR,"lean-kernel","substitution_output_allocation_dominant","run:35435040357",(
        "precommit:328d597b2836846e67ff527acd1434311792cc11",
        "artifact:10582183120",
        "digest:sha256:238012eaeae5ca66ee72ecd7ff9bac32eb995ff048c3ceb95d1836fbbea4a94b"))
    delta=rt.admit(ev);after=rt.snapshot()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);state=out/"compiled-present.json";rt.save_compiled_present(state)
    restarted=IncrementalFlashRuntime.load_compiled_present(state,rules)
    profiles={p:rank(p) for p in ("conservative","neutral","aggressive")};battle={p:x["battle"][0] for p,x in profiles.items()};discovery={p:x["discovery"][0] for p,x in profiles.items()}
    eliminated=len(before["frontiers"]["frontier:substitute-output"]["route_ids"])-len(after["frontiers"]["frontier:substitute-output"]["route_ids"])
    cumulative=int(ep13["closure"]["cumulative_exact_routes_eliminated"])+eliminated

    gates={
      "precommit_bound_before_target":pre["frozen_before_target_experiment"] is True,
      "allocation_dominant_verified":target["classification"]=="allocation-dominant",
      "fresh_fraction_over_70_percent":all(r["substitute_make_fresh_fraction"]>0.70 for r in rows),
      "app_largest_fresh_allocation_tag":all(r["substitute_make_by_tag"][0]["tag"]=="app" for r in rows),
      "app_fresh_allocations_over_700k":all(x["freshAllocation"]>700000 for x in app_rows),
      "exact_accounting_route_eliminated":eliminated==1,
      "separators_compiled":{
        "lean:substitution-output-allocation-dominant:v1",
        "lean:substitution-fresh-app-allocation-hotspot:v1",
      }<=set(after["frontiers"]["frontier:substitute-output"]["separators"]),
      "restart_without_replay":restarted.replayed_events_on_restart==0 and restarted.snapshot()["frontiers"]==after["frontiers"],
      "battle_reselection_stable":len(set(battle.values()))==1,
      "discovery_reselection_stable":len(set(discovery.values()))==1,
      "cumulative_exact_routes_eliminated_15":cumulative==15,
    }

    result={"schema":"qckn-live-real-episode-v14","verdict":"PASS" if all(gates.values()) else "FAIL","cycle":14,
      "source_episode13":{"run_id":35434872033,"artifact_id":10582093003,"artifact_digest":"sha256:841e41d66e4628e33060503398b27039bc3d2d6845aa93a471a8830454632419"},
      "target":{"run_id":35435040357,"artifact_id":10582183120,"artifact_digest":"sha256:238012eaeae5ca66ee72ecd7ff9bac32eb995ff048c3ceb95d1836fbbea4a94b","classification":target["classification"],"reuse_fractions":[r["substitute_make_reuse_fraction"] for r in rows],"fresh_fractions":[r["substitute_make_fresh_fraction"] for r in rows],"app_rows":app_rows},
      "closure":{"event_kind":ev.kind.value,"exact_routes_eliminated_this_cycle":eliminated,"cumulative_exact_routes_eliminated":cumulative,"after_routes":after["frontiers"]["frontier:substitute-output"]["route_ids"],"separators":after["frontiers"]["frontier:substitute-output"]["separators"]},
      "reselection":{"profiles":profiles,"battle_consensus":battle,"discovery_consensus":discovery,"next_battle_experiment":next(iter(battle.values())),"next_discovery_experiment":next(iter(discovery.values()))},
      "gates":gates,
      "claim_boundary":"Cycle 14 establishes that output node construction, not missing exact node reuse alone, is the dominant measured substitution residual: about 74.53% of make calls allocate fresh nodes, with app responsible for about 745,842 fresh allocations per case. This licenses a prospective app-child identity diagnostic. It does not license app-node reuse across distinct children."}
    (out/"episode14.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":result["verdict"],"target":result["target"],"closure":result["closure"],"battle_consensus":battle,"discovery_consensus":discovery,"gates":gates,"claim_boundary":result["claim_boundary"]},indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V14" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V14")
    return 0 if result["verdict"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
