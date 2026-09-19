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
            "lean-substitution-argument-provenance-diagnostic","lean-kernel",12.0,lp,
            1.0,0.20,6.0,60.0,2.0,2.0,1.5,0.2,1.0,1.0,
            provenance=(
                "run:35433560425",
                "classification:distributed-arguments",
                "argument-identity-dominant:episode9",
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
    p=argparse.ArgumentParser();p.add_argument("--precommit",required=True);p.add_argument("--target",required=True);p.add_argument("--episode9",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    pre,target,ep9=load(a.precommit),load(a.target),load(a.episode9)
    if pre.get("schema")!="qckn-live-real-episode-v10-precommit": raise AssertionError("bad precommit")
    if target.get("schema")!="substitution-argument-family-diagnostic-v1": raise AssertionError("bad target")
    if target["precommit"]["realitygraph_commit"]!="25cb163784828bb8fab9cde181282342b3c9bb00": raise AssertionError("target not frozen")
    if ep9.get("schema")!="qckn-live-real-episode-v9" or ep9.get("verdict")!="PASS": raise AssertionError("episode9 missing")
    if not all(target["gates"].values()): raise AssertionError("target gates failed")
    if target["classification"]!="distributed-arguments": raise AssertionError("unexpected classification")

    rows=target["rows"]
    if not all(r["argument_family_class_count"]>200 and r["argument_family_top8_coverage"]<0.70 for r in rows):
        raise AssertionError("distributed argument result changed")

    frontier=FrontierState("frontier:substitution-arguments","lean-kernel",3,3,
        route_ids={"route:lean-substitution-argument-family-diagnostic","route:lean-substitution-argument-provenance-diagnostic","route:lean-other-residual"},
        base_route_ids={"route:lean-substitution-argument-family-diagnostic","route:lean-substitution-argument-provenance-diagnostic","route:lean-other-residual"})
    rules=(
        DependencyRule("remove-argument-family-route","substitution_arguments_distributed","frontier:substitution-arguments","remove_route","route:lean-substitution-argument-family-diagnostic"),
        DependencyRule("record-argument-family-obstruction","substitution_arguments_distributed","frontier:substitution-arguments","add_obstruction","lean:substitution-arguments-no-compact-family:v1"),
    )
    rt=IncrementalFlashRuntime((frontier,),rules);before=rt.snapshot()
    ev=FlashEvent("episode10:argument-family-result",FlashEventKind.OBSTRUCTION,"lean-kernel","substitution_arguments_distributed","run:35433560425",(
        "precommit:25cb163784828bb8fab9cde181282342b3c9bb00","artifact:10581411360","digest:sha256:f2ad7207efcba45fba0e0d4328880dbefb16aa6d123dfe1776e74bfb2b9320fa"))
    delta=rt.admit(ev);after=rt.snapshot()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);state=out/"compiled-present.json";rt.save_compiled_present(state)
    restarted=IncrementalFlashRuntime.load_compiled_present(state,rules)
    profiles={p:rank(p) for p in ("conservative","neutral","aggressive")};battle={p:x["battle"][0] for p,x in profiles.items()};discovery={p:x["discovery"][0] for p,x in profiles.items()}
    eliminated=len(before["frontiers"]["frontier:substitution-arguments"]["route_ids"])-len(after["frontiers"]["frontier:substitution-arguments"]["route_ids"])
    cumulative=int(ep9["closure"]["cumulative_exact_routes_eliminated"])+eliminated
    gates={
      "precommit_bound_before_target":pre["frozen_before_target_experiment"] is True,
      "distributed_argument_outcome_verified":target["classification"]=="distributed-arguments",
      "both_cases_same_dominant_family":target["family_profiles"][0][0]["family"]==target["family_profiles"][1][0]["family"],
      "exact_argument_family_route_eliminated":eliminated==1,
      "obstruction_compiled":"lean:substitution-arguments-no-compact-family:v1" in after["frontiers"]["frontier:substitution-arguments"]["obstructions"],
      "restart_without_replay":restarted.replayed_events_on_restart==0 and restarted.snapshot()["frontiers"]==after["frontiers"],
      "battle_reselection_stable":len(set(battle.values()))==1,
      "discovery_reselection_stable":len(set(discovery.values()))==1,
      "ten_real_cycles_eliminated_ten_exact_routes":cumulative==10,
    }
    result={"schema":"qckn-live-real-episode-v10","verdict":"PASS" if all(gates.values()) else "FAIL","cycle":10,
      "source_episode9":{"run_id":35433372707,"artifact_id":10581401124,"artifact_digest":"sha256:782d8242750736893f4e00f714458b787702b84a35a8b389c53f53ee2f767383"},
      "target":{"run_id":35433560425,"artifact_id":10581411360,"artifact_digest":"sha256:f2ad7207efcba45fba0e0d4328880dbefb16aa6d123dfe1776e74bfb2b9320fa","classification":target["classification"],"sampled":[r["argument_family_sampled"] for r in rows],"class_counts":[r["argument_family_class_count"] for r in rows],"top8_coverages":[r["argument_family_top8_coverage"] for r in rows],"dominant_families":[r["argument_family_top"][0] for r in rows]},
      "closure":{"event_kind":ev.kind.value,"exact_routes_eliminated_this_cycle":eliminated,"cumulative_exact_routes_eliminated":cumulative,"after_routes":after["frontiers"]["frontier:substitution-arguments"]["route_ids"],"obstructions":after["frontiers"]["frontier:substitution-arguments"]["obstructions"]},
      "reselection":{"profiles":profiles,"battle_consensus":battle,"discovery_consensus":discovery,"next_battle_experiment":next(iter(battle.values())),"next_discovery_experiment":next(iter(discovery.values()))},
      "gates":gates,
      "claim_boundary":"Tenth prospectively frozen real cycle. New substitution arguments are distributed across roughly 230 shallow families and the top eight cover only about 64.7%, despite near-identical distributions across both cases. This refutes the frozen compact-family quotient only. The next diagnostic asks where those new argument identities are generated, before proposing any cross-argument equivalence."}
    (out/"episode10.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":result["verdict"],"target":result["target"],"closure":result["closure"],"battle_consensus":battle,"discovery_consensus":discovery,"gates":gates,"claim_boundary":result["claim_boundary"]},indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V10" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V10")
    return 0 if result["verdict"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
