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
    lp={"conservative":0.74,"neutral":0.87,"aggressive":0.95}[profile]
    return (
        WinOpportunity(
            "lean-substitute-generated-argument-fanout-diagnostic","lean-kernel",12.5,lp,
            1.0,0.20,6.0,65.0,2.0,2.0,1.5,0.2,1.0,1.0,
            provenance=(
                "run:35433772321",
                "classification:stable-small-generator-basis",
                "largest-generator:substitute",
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
    p=argparse.ArgumentParser();p.add_argument("--precommit",required=True);p.add_argument("--target",required=True);p.add_argument("--episode10",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    pre,target,ep10=load(a.precommit),load(a.target),load(a.episode10)
    if pre.get("schema")!="qckn-live-real-episode-v11-precommit": raise AssertionError("bad precommit")
    if target.get("schema")!="substitution-argument-provenance-v1": raise AssertionError("bad target")
    if target["precommit"]["realitygraph_commit"]!="71fa248c183950e0757bc0bef76fd0129eecbd8e": raise AssertionError("target not frozen")
    if ep10.get("schema")!="qckn-live-real-episode-v10" or ep10.get("verdict")!="PASS": raise AssertionError("episode10 missing")
    if not all(target["gates"].values()): raise AssertionError("target gates failed")
    if target["classification"]!="stable-small-generator-basis": raise AssertionError("unexpected classification")

    rows=target["rows"]
    profiles_t=[r["argument_provenance"] for r in rows]
    if not all(x[0]["origin"]=="substitute" for x in profiles_t): raise AssertionError("largest generator changed")
    top3=[r["argument_provenance_top3_coverage"] for r in rows]
    if not all(x>=0.90 for x in top3): raise AssertionError("generator basis no longer concentrated")

    frontier=FrontierState("frontier:argument-provenance","lean-kernel",3,3,
        route_ids={"route:lean-substitution-argument-provenance-diagnostic","route:lean-substitute-generated-argument-fanout-diagnostic","route:lean-other-residual"},
        base_route_ids={"route:lean-substitution-argument-provenance-diagnostic","route:lean-substitute-generated-argument-fanout-diagnostic","route:lean-other-residual"})
    rules=(
        DependencyRule("remove-provenance-route","substitution_argument_generator_basis","frontier:argument-provenance","remove_route","route:lean-substitution-argument-provenance-diagnostic"),
        DependencyRule("record-generator-separator","substitution_argument_generator_basis","frontier:argument-provenance","add_separator","lean:substitution-argument-generator-basis:v1"),
    )
    rt=IncrementalFlashRuntime((frontier,),rules);before=rt.snapshot()
    ev=FlashEvent("episode11:argument-provenance-result",FlashEventKind.VERIFIED_SEPARATOR,"lean-kernel","substitution_argument_generator_basis","run:35433772321",(
        "precommit:71fa248c183950e0757bc0bef76fd0129eecbd8e","artifact:10582231225","digest:sha256:7384acd09fc29fb701a4179b24825de36739fc485f243dcbc15f3b7eccaf1bbe"))
    delta=rt.admit(ev);after=rt.snapshot()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);state=out/"compiled-present.json";rt.save_compiled_present(state)
    restarted=IncrementalFlashRuntime.load_compiled_present(state,rules)
    profiles={p:rank(p) for p in ("conservative","neutral","aggressive")};battle={p:x["battle"][0] for p,x in profiles.items()};discovery={p:x["discovery"][0] for p,x in profiles.items()}
    eliminated=len(before["frontiers"]["frontier:argument-provenance"]["route_ids"])-len(after["frontiers"]["frontier:argument-provenance"]["route_ids"])
    cumulative=int(ep10["closure"]["cumulative_exact_routes_eliminated"])+eliminated
    gates={
      "precommit_bound_before_target":pre["frozen_before_target_experiment"] is True,
      "stable_small_generator_basis_verified":target["classification"]=="stable-small-generator-basis",
      "substitute_largest_generator_both":all(x[0]["origin"]=="substitute" for x in profiles_t),
      "top3_generator_coverage_high":all(x>=0.90 for x in top3),
      "exact_provenance_route_eliminated":eliminated==1,
      "separator_compiled":"lean:substitution-argument-generator-basis:v1" in after["frontiers"]["frontier:argument-provenance"]["separators"],
      "restart_without_replay":restarted.replayed_events_on_restart==0 and restarted.snapshot()["frontiers"]==after["frontiers"],
      "battle_reselection_stable":len(set(battle.values()))==1,
      "discovery_reselection_stable":len(set(discovery.values()))==1,
      "eleven_real_cycles_eliminated_eleven_exact_routes":cumulative==11,
    }
    result={"schema":"qckn-live-real-episode-v11","verdict":"PASS" if all(gates.values()) else "FAIL","cycle":11,
      "source_episode10":{"run_id":35433654472,"artifact_id":10581074870,"artifact_digest":"sha256:27f5a6d0ac9587351f67ea28923486db0e3b2eb0b8e19e7e4c28c7fc440c4a73"},
      "target":{"run_id":35433772321,"artifact_id":10582231225,"artifact_digest":"sha256:7384acd09fc29fb701a4179b24825de36739fc485f243dcbc15f3b7eccaf1bbe","classification":target["classification"],"profiles":profiles_t,"top3_coverages":top3},
      "closure":{"event_kind":ev.kind.value,"exact_routes_eliminated_this_cycle":eliminated,"cumulative_exact_routes_eliminated":cumulative,"after_routes":after["frontiers"]["frontier:argument-provenance"]["route_ids"],"separators":after["frontiers"]["frontier:argument-provenance"]["separators"]},
      "reselection":{"profiles":profiles,"battle_consensus":battle,"discovery_consensus":discovery,"next_battle_experiment":next(iter(battle.values())),"next_discovery_experiment":next(iter(discovery.values()))},
      "gates":gates,
      "claim_boundary":"Eleventh prospectively frozen real cycle. New substitution-argument identities have a stable three-source generator basis: substitute, source-or-untracked, and shift cover about 92.89% in both cases, with substitute the largest single source (~39.6% of sampled new arguments). This licenses a prospective fanout diagnostic on substitute-generated arguments only; no cross-argument reuse or generator quotient is authorized."}
    (out/"episode11.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":result["verdict"],"target":result["target"],"closure":result["closure"],"battle_consensus":battle,"discovery_consensus":discovery,"gates":gates,"claim_boundary":result["claim_boundary"]},indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V11" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V11")
    return 0 if result["verdict"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
