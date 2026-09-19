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
            "lean-substitute-node-reuse-accounting-diagnostic","lean-kernel",12.0,lp,
            1.0,0.20,6.0,60.0,2.0,2.0,1.5,0.2,1.0,1.0,
            provenance=(
                "episode12:diffuse-cross-product",
                "historical:deferred-v2-no-resolution",
                "historical:prefix-plan-not-protected-clean",
                "current:compiled-node-reuse-active",
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
    p=argparse.ArgumentParser();p.add_argument("--precommit",required=True);p.add_argument("--episode12",required=True);p.add_argument("--deferred",required=True);p.add_argument("--prefix-plan",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    pre,ep12,deferred,prefix=load(a.precommit),load(a.episode12),load(a.deferred),load(a.prefix_plan)
    if pre.get("schema")!="qckn-live-real-episode-v13-precommit": raise AssertionError("bad precommit")
    if ep12.get("schema")!="qckn-live-real-episode-v12" or ep12.get("verdict")!="PASS": raise AssertionError("episode12 missing")

    conclusion=deferred.get("conclusion",{})
    deferred_ok=(
        conclusion.get("lawful_candidates")==[] and
        conclusion.get("provisional_winner") is None and
        all(v.get("wrong")==0 and v.get("protectedChanged")==0 and v.get("resolved")==0 for v in conclusion.get("candidates",[]))
    )
    prefix_wrong=any(
        r.get("name")=="undecidability/alg-conv-trans-acc-left" and
        r.get("want")=="ACCEPT" and r.get("status")=="REJECT"
        for r in prefix.get("rows",[])
    )
    prefix_ok=(prefix.get("promotable") is False and prefix.get("protectedClean") is False and prefix_wrong)
    if not deferred_ok: raise AssertionError("deferred historical evidence changed")
    if not prefix_ok: raise AssertionError("prefix-plan historical evidence changed")

    frontier=FrontierState("frontier:substitution-lineage","lean-kernel",4,4,
        route_ids={
            "route:lean-substitution-lineage-reclosure",
            "route:retest-deferred-substitution-v2-unchanged",
            "route:retest-prefix-substitution-plan-unchanged",
            "route:lean-substitute-node-reuse-accounting-diagnostic",
            "route:lean-other-residual",
        },
        base_route_ids={
            "route:lean-substitution-lineage-reclosure",
            "route:retest-deferred-substitution-v2-unchanged",
            "route:retest-prefix-substitution-plan-unchanged",
            "route:lean-substitute-node-reuse-accounting-diagnostic",
            "route:lean-other-residual",
        })
    rules=(
        DependencyRule("remove-lineage-route","substitution_lineage_imported","frontier:substitution-lineage","remove_route","route:lean-substitution-lineage-reclosure"),
        DependencyRule("remove-deferred-retest","substitution_lineage_imported","frontier:substitution-lineage","remove_route","route:retest-deferred-substitution-v2-unchanged"),
        DependencyRule("remove-prefix-plan-retest","substitution_lineage_imported","frontier:substitution-lineage","remove_route","route:retest-prefix-substitution-plan-unchanged"),
        DependencyRule("record-deferred-obstruction","substitution_lineage_imported","frontier:substitution-lineage","add_obstruction","lean:historical-deferred-substitution-v2-no-resolution:v1"),
        DependencyRule("record-plan-obstruction","substitution_lineage_imported","frontier:substitution-lineage","add_obstruction","lean:historical-prefix-substitution-plan-not-protected-clean:v1"),
    )
    rt=IncrementalFlashRuntime((frontier,),rules);before=rt.snapshot()
    ev=FlashEvent("episode13:historical-substitution-lineage-import",FlashEventKind.OBSTRUCTION,"lean-kernel","substitution_lineage_imported","historical-artifacts",(
        "run:34923444179/artifact:10378473440/digest:7d97a2741df5ef00efbcf87c4982c2d4fda6a89d0d9bb4f8ae86e521218597a5",
        "run:35010257884/artifact:10413695411/digest:a65588ce0488f9139bbc89a3f6b248dab02544e97fb88654967d682d81775fd2",
    ))
    delta=rt.admit(ev);after=rt.snapshot()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);state=out/"compiled-present.json";rt.save_compiled_present(state)
    restarted=IncrementalFlashRuntime.load_compiled_present(state,rules)

    profiles={p:rank(p) for p in ("conservative","neutral","aggressive")};battle={p:x["battle"][0] for p,x in profiles.items()};discovery={p:x["discovery"][0] for p,x in profiles.items()}
    before_routes=set(before["frontiers"]["frontier:substitution-lineage"]["route_ids"]);after_routes=set(after["frontiers"]["frontier:substitution-lineage"]["route_ids"])
    removed=before_routes-after_routes
    historical_removed={
        "route:retest-deferred-substitution-v2-unchanged",
        "route:retest-prefix-substitution-plan-unchanged",
    }
    exact_historical_eliminated=len(removed&historical_removed)
    cumulative=int(ep12["closure"]["cumulative_exact_routes_eliminated"])+exact_historical_eliminated

    gates={
      "precommit_frozen_before_import":pre["frozen_before_import"] is True,
      "deferred_v2_evidence_verified":deferred_ok,
      "prefix_plan_evidence_verified":prefix_ok,
      "both_historical_reacquisition_routes_removed":exact_historical_eliminated==2,
      "scoped_obstructions_compiled":{
          "lean:historical-deferred-substitution-v2-no-resolution:v1",
          "lean:historical-prefix-substitution-plan-not-protected-clean:v1",
      }<=set(after["frontiers"]["frontier:substitution-lineage"]["obstructions"]),
      "restart_without_replay":restarted.replayed_events_on_restart==0 and restarted.snapshot()["frontiers"]==after["frontiers"],
      "battle_reselection_stable":len(set(battle.values()))==1,
      "discovery_reselection_stable":len(set(discovery.values()))==1,
      "cumulative_exact_reacquisition_routes_eliminated_14":cumulative==14,
    }
    result={"schema":"qckn-live-real-episode-v13","verdict":"PASS" if all(gates.values()) else "FAIL","cycle":13,
      "source_episode12":{"run_id":35434746406,"artifact_id":10581753164,"artifact_digest":"sha256:bc95772567922300dc5877c2da99d0889e0ae8e7e9f47490bb5a2a06a9191461"},
      "historical_imports":{
        "deferred_v2":{"run_id":34923444179,"artifact_id":10378473440,"artifact_digest":"sha256:7d97a2741df5ef00efbcf87c4982c2d4fda6a89d0d9bb4f8ae86e521218597a5","lawful_candidates":conclusion.get("lawful_candidates"),"provisional_winner":conclusion.get("provisional_winner")},
        "prefix_plan":{"run_id":35010257884,"artifact_id":10413695411,"artifact_digest":"sha256:a65588ce0488f9139bbc89a3f6b248dab02544e97fb88654967d682d81775fd2","promotable":prefix.get("promotable"),"protectedClean":prefix.get("protectedClean"),"counterexample_present":prefix_wrong},
      },
      "closure":{"event_kind":ev.kind.value,"historical_exact_routes_eliminated_this_cycle":exact_historical_eliminated,"removed_routes":sorted(removed),"cumulative_exact_routes_eliminated":cumulative,"after_routes":sorted(after_routes),"obstructions":after["frontiers"]["frontier:substitution-lineage"]["obstructions"]},
      "reselection":{"profiles":profiles,"battle_consensus":battle,"discovery_consensus":discovery,"next_battle_experiment":next(iter(battle.values())),"next_discovery_experiment":next(iter(discovery.values()))},
      "gates":gates,
      "claim_boundary":"Cycle 13 is a lineage reclosure rather than a new Lean target experiment. It imports two artifact-backed historical consequences at their original scope and removes only exact unchanged-candidate reacquisition routes. The old results do not rule out all deferred substitution or all compiled plans under the current kernel. Their value here is that Flash does not pay to rediscover those exact failures."}
    (out/"episode13.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"verdict":result["verdict"],"historical_imports":result["historical_imports"],"closure":result["closure"],"battle_consensus":battle,"discovery_consensus":discovery,"gates":gates,"claim_boundary":result["claim_boundary"]},indent=2,sort_keys=True))
    print("PASS_QCKN_LIVE_REAL_EPISODE_V13" if result["verdict"]=="PASS" else "FAIL_QCKN_LIVE_REAL_EPISODE_V13")
    return 0 if result["verdict"]=="PASS" else 1
if __name__=="__main__": raise SystemExit(main())
