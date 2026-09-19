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
    lp={"conservative":0.72,"neutral":0.86,"aggressive":0.94}[profile]
    return (
        WinOpportunity(
            "lean-substitution-argument-family-diagnostic","lean-kernel",12.0,lp,
            1.0,0.20,6.0,55.0,2.0,2.0,1.5,0.2,1.0,1.0,
            provenance=(
                "run:35433300505",
                "classification:argument-identity-dominant",
                "new-argument-fraction:~0.38974",
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
    p=argparse.ArgumentParser();p.add_argument("--precommit",required=True);p.add_argument("--target",required=True);p.add_argument("--episode8",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    pre,target,ep8=load(a.precommit),load(a.target),load(a.episode8)
    if pre.get("schema")!="qckn-live-real-episode-v9-precommit": raise AssertionError("bad precommit")
    if target.get("schema")!="substitution-key-diversity-v1": raise AssertionError("bad target")
    if target["precommit"]["realitygraph_commit"]!="6606524bb42dca43c45e376c356624680836d9f8": raise AssertionError("target not frozen")
    if ep8.get("schema")!="qckn-live-real-episode-v8" or ep8.get("verdict")!="PASS": raise AssertionError("episode8 missing")
    if not all(target["gates"].values()): raise AssertionError("target gates failed")
    if target["classification"]!="argument-identity-dominant": raise AssertionError("unexpected classification")

    fractions=[r["substitution_key_partition_fractions"] for r in target["rows"]]
    if not all(f["new_argument"]>f["new_expression"] and f["new_argument"]>f["new_depth"] for f in fractions):
        raise AssertionError("argument identity not dominant in both cases")

    frontier=FrontierState("frontier:substitution-key","lean-kernel",3,3,
        route_ids={"route:lean-substitution-key-diversity-diagnostic","route:lean-substitution-argument-family-diagnostic","route:lean-other-residual"},
        base_route_ids={"route:lean-substitution-key-diversity-diagnostic","route:lean-substitution-argument-family-diagnostic","route:lean-other-residual"})
    rules=(
        DependencyRule("remove-key-route","substitution_argument_identity_dominant","frontier:substitution-key","remove_route","route:lean-substitution-key-diversity-diagnostic"),
        DependencyRule("record-argument-separator","substitution_argument_identity_dominant","frontier:substitution-key","add_separator","lean:substitution-argument-identity-dominant:v1"),
    )
    rt=IncrementalFlashRuntime((frontier,),rules);before=rt.snapshot()
    ev=FlashEvent("episode9:key-diversity-result",FlashEventKind.VERIFIED_SEPARATOR,"lean-kernel","substitution_argument_identity_dominant","run:35433300505",(
        "precommit:6606524bb42dca43c45e376c356624680836d9f8","artifact:10581241360","digest:sha256:8b1a064ef2570c48f8c967420b11e6ed2ab3b34b501a1739de27514979010293"))
    delta=rt.admit(ev);after=rt.snapshot()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);state=out/"compiled-present.json";rt.save_compiled_present(state)
    restarted=IncrementalFlashRuntime.load_compiled_present(state,rules)
    profiles={p:rank(p) for p in ("conservative","neutral","aggressive")};battle={p:x["battle"][0] for p,x in profiles.items()};discovery={p:x["discovery"][0] for p,x in profiles.items()}
    eliminated=len(before["frontiers"]["frontier:substitution-key"]["route_ids"])-len(after["frontiers"]["frontier:substitution-key"]["route_ids"])
    cumulative=int(ep8["closure"]["cumulative_exact_routes_eliminated"])+eliminated
    gates={
      "precommit_bound_before_target":pre["frozen_before_target_experiment"] is True,
      "argument_identity_dominant":target["classification"]=="argument-identity-dominant",
      "both_cases_same_partition":all(abs(fractions[0][k]-fractions[1][k])<0.001 for k in fractions[0]),
      "exact_key_route_eliminated":eliminated==1,
      "separator_compiled":"lean:substitution-argument-identity-dominant:v1" in after["frontiers"]["frontier:substitution-key"]["separators"],
      "restart_without_replay":restarted.replayed_events_on_restart==0 and restarted.snapshot()["frontiers"]==after["frontiers"],
      "battle_reselection_stable":len(set(battle.values()))==1,
      "discovery_reselection_stable":len(set(discovery.values()))==1,
      "nine_real_cycles_eliminated_nine_exact_routes":cumulative==9,
    }
    result={"schema":"qckn-live-real-episode-v9","verdict":"PASS" if all(gates.values()) else "FAIL","cycle":9,
      "source_episode8":{"run_id":35433119341,"artifact_id":10582075523,"artifact_digest":"sha256:c4ee54f80947f157e6934b60137bd7879e056f41c2d5078123bb7c2711ac4be7"},
      "target":{"run_id":35433300505,"artifact_id":10581241360,"artifact_digest":"sha256:8b1a064ef2570c48f8c967420b11e6ed2ab3b34b501a1739de27514979010293","classification":target["classification"],"fractions":fractions,"partitions":[r["substitution_key_partition"] for r in target["rows"]]},
      "closure":{"event_kind":ev.kind.value,"exact_routes_eliminated_this_cycle":eliminated,"cumulative_exact_routes_eliminated":cumulative,"after_routes":after["frontiers"]["frontier:substitution-key"]["route_ids"],"separators":after["frontiers"]["frontier:substitution-key"]["separators"]},
      "reselection":{"profiles":profiles,"battle_consensus":battle,"discovery_consensus":discovery,"next_battle_experiment":next(iter(battle.values())),"next_discovery_experiment":next(iter(discovery.values()))},
      "gates":gates,
      "claim_boundary":"Ninth prospectively frozen real cycle. New substitution-argument identity is the largest exact cache-key miss component in both deep-list cases (~38.97% of all observed substitution-key visits), ahead of new expression identity (~22.11%) and new binder depth (~5.78%). This licenses a prospective diagnostic of argument families; it does not permit argument quotienting or cross-argument cache reuse."}
    (out/"episode9.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":result["verdict"],"target":result["target"],"closure":result["closure"],"battle_consensus":battle,"discovery_consensus":discovery,"gates":gates,"claim_boundary":result["claim_boundary"]},indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V9" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V9")
    return 0 if result["verdict"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
