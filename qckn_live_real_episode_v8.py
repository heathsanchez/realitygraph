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
    lp={"conservative":0.70,"neutral":0.84,"aggressive":0.93}[profile]
    return (
        WinOpportunity(
            "lean-substitution-key-diversity-diagnostic","lean-kernel",11.5,lp,
            1.0,0.20,6.0,50.0,2.0,2.0,1.5,0.2,1.0,1.0,
            provenance=(
                "run:35433027905",
                "classification:mixed-substitution-reuse",
                "subst-reuse-ratio:~0.4326",
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
    p=argparse.ArgumentParser();p.add_argument("--precommit",required=True);p.add_argument("--target",required=True);p.add_argument("--episode7",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    pre,target,ep7=load(a.precommit),load(a.target),load(a.episode7)
    if pre.get("schema")!="qckn-live-real-episode-v8-precommit": raise AssertionError("bad precommit")
    if target.get("schema")!="substitute-consequence-accounting-v1": raise AssertionError("bad target")
    if target["precommit"]["realitygraph_commit"]!="2a147eb014986b07d53b6d70b012837235fa514e": raise AssertionError("target not frozen")
    if ep7.get("schema")!="qckn-live-real-episode-v7" or ep7.get("verdict")!="PASS": raise AssertionError("episode7 missing")
    if not all(target["gates"].values()): raise AssertionError("target gates failed")
    if target["classification"]!="mixed": raise AssertionError("unexpected accounting classification")

    ratios=[r["substitution_reuse_ratio"] for r in target["rows"]]
    if not all(0.20<r<0.80 for r in ratios): raise AssertionError("mixed reuse regime not observed")

    frontier=FrontierState("frontier:substitute-accounting","lean-kernel",3,3,
        route_ids={"route:lean-substitute-consequence-accounting-diagnostic","route:lean-substitution-key-diversity-diagnostic","route:lean-other-residual"},
        base_route_ids={"route:lean-substitute-consequence-accounting-diagnostic","route:lean-substitution-key-diversity-diagnostic","route:lean-other-residual"})
    rules=(
        DependencyRule("remove-accounting-route","substitution_reuse_mixed","frontier:substitute-accounting","remove_route","route:lean-substitute-consequence-accounting-diagnostic"),
        DependencyRule("record-mixed-separator","substitution_reuse_mixed","frontier:substitute-accounting","add_separator","lean:substitution-reuse-mixed-regime:v1"),
    )
    rt=IncrementalFlashRuntime((frontier,),rules);before=rt.snapshot()
    ev=FlashEvent("episode8:substitute-accounting-result",FlashEventKind.VERIFIED_SEPARATOR,"lean-kernel","substitution_reuse_mixed","run:35433027905",(
        "precommit:2a147eb014986b07d53b6d70b012837235fa514e","artifact:10581855617","digest:sha256:649b841ea3f581eb98e9d9cf84c304872fa7b5b42dafa01dd3f5d674893063cd"))
    delta=rt.admit(ev);after=rt.snapshot()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);state=out/"compiled-present.json";rt.save_compiled_present(state)
    restarted=IncrementalFlashRuntime.load_compiled_present(state,rules)
    profiles={p:rank(p) for p in ("conservative","neutral","aggressive")};battle={p:x["battle"][0] for p,x in profiles.items()};discovery={p:x["discovery"][0] for p,x in profiles.items()}
    eliminated=len(before["frontiers"]["frontier:substitute-accounting"]["route_ids"])-len(after["frontiers"]["frontier:substitute-accounting"]["route_ids"])
    cumulative=int(ep7["closure"]["cumulative_exact_routes_eliminated"])+eliminated
    gates={
      "precommit_bound_before_target":pre["frozen_before_target_experiment"] is True,
      "mixed_reuse_regime_verified":target["classification"]=="mixed",
      "two_cases_nearly_identical_ratio":abs(ratios[0]-ratios[1])<0.001,
      "exact_accounting_route_eliminated":eliminated==1,
      "separator_compiled":"lean:substitution-reuse-mixed-regime:v1" in after["frontiers"]["frontier:substitute-accounting"]["separators"],
      "restart_without_replay":restarted.replayed_events_on_restart==0 and restarted.snapshot()["frontiers"]==after["frontiers"],
      "battle_reselection_stable":len(set(battle.values()))==1,
      "discovery_reselection_stable":len(set(discovery.values()))==1,
      "eight_real_cycles_eliminated_eight_exact_routes":cumulative==8,
    }
    result={"schema":"qckn-live-real-episode-v8","verdict":"PASS" if all(gates.values()) else "FAIL","cycle":8,
      "source_episode7":{"run_id":35432871957,"artifact_id":10581205893,"artifact_digest":"sha256:f04a37a60bf265463b3dec96e10dc466fbc9bc6ec1ba4aeb1f6db9faa91469c0"},
      "target":{"run_id":35433027905,"artifact_id":10581855617,"artifact_digest":"sha256:649b841ea3f581eb98e9d9cf84c304872fa7b5b42dafa01dd3f5d674893063cd","classification":target["classification"],"substitution_reuse_ratios":ratios,"rows":target["rows"]},
      "closure":{"event_kind":ev.kind.value,"exact_routes_eliminated_this_cycle":eliminated,"cumulative_exact_routes_eliminated":cumulative,"after_routes":after["frontiers"]["frontier:substitute-accounting"]["route_ids"],"separators":after["frontiers"]["frontier:substitute-accounting"]["separators"]},
      "reselection":{"profiles":profiles,"battle_consensus":battle,"discovery_consensus":discovery,"next_battle_experiment":next(iter(battle.values())),"next_discovery_experiment":next(iter(discovery.values()))},
      "gates":gates,
      "claim_boundary":"Eighth prospectively frozen real cycle. Existing exact substitution memoization is neither saturated nor sparse on the measured deep-list contract: reuse is about 43.26% in both cases. Aggregate binder range skips and compiled node/spine reuse are also substantial. This licenses a diagnostic of exact cache-key diversity to learn which key dimension prevents reuse; it does not license a stronger cache yet."}
    (out/"episode8.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":result["verdict"],"target":{"classification":target["classification"],"ratios":ratios},"closure":result["closure"],"battle_consensus":battle,"discovery_consensus":discovery,"gates":gates,"claim_boundary":result["claim_boundary"]},indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V8" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V8")
    return 0 if result["verdict"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
