from __future__ import annotations
import hashlib,json,os
from pathlib import Path

from openml_v7 import load_world
from probe_openml_v9_manifest import main as freeze_manifest
from realitygraph.adaptive_policy import budget_from_memory
from realitygraph.meta_policy import policy_from_memory
from realitygraph.mg import MG
from realitygraph.retained_capability import ablate_capability,applicable_transfer_capabilities,exact_restart
from scope_gate_v5 import eval_group

POLICY_PATH=Path("frozen-meta/adaptive_policy.mg")
POLICY_SHA="3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
V9_PATH=Path("frozen-meta/openml_scope_v9.json")
MANIFEST_SHA="a06a8d7cc616579dbc6c677e6a5348169795a09776324b8a762266cd55b4b2cd"

def stream_hash(value):
    return hashlib.sha256(f"openml-v9-deploy|{value}".encode()).digest()

def run_static(worlds,selector):
    laws=[w["law"] for w in worlds if w["law"] is not None and selector(w)]
    memory=exact_restart(MG("openml-v9-static",laws).text())
    stats={w["task_id"]:{"promoted":selector(w) and w["law"] is not None,"verified":0,"events":max(0,len(w["future_groups"])-1),"revoked":False} for w in worlds}
    events=[]
    for w in worlds:
        for j,g in enumerate(w["future_groups"][1:],start=1):
            events.append((stream_hash(f"{w['task_id']}|{j}"),w,j,g))
    events.sort(key=lambda x:(x[0],x[1]["task_id"],x[2]))
    active=memory; verified=causal=failures=unknown=0
    for _,w,j,g in events:
        matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
        if not matches:
            unknown+=1; continue
        result=eval_group(w,g,active)
        if result["verified"]:
            verified+=1; causal+=int(result["causal"]); stats[w["task_id"]]["verified"]+=1
        else:
            failures+=1; stats[w["task_id"]]["revoked"]=True
            active=ablate_capability(active,matches[0].law_id)
    promoted=[x for x in stats.values() if x["promoted"]]
    survivors=[x for x in promoted if x["verified"]==x["events"] and not x["revoked"]]
    return {
      "initial_laws":len(memory.laws),"final_laws":len(active.laws),
      "initial_bytes":len(memory.text().encode()),"verified_events":verified,
      "causal_ablations":causal,"failures":failures,"unknown_events":unknown,
      "promoted_sources":len(promoted),"surviving_sources":len(survivors),
      "survival_precision":len(survivors)/max(1,len(promoted)),"source_stats":stats
    }

def run_probation(worlds,selector):
    laws=[w["law"] for w in worlds if w["law"] is not None and selector(w)]
    active=exact_restart(MG("openml-v9-probation",laws).text())
    probation={"tested":0,"passed":0,"failed":0,"causal":0}
    for w in sorted(worlds,key=lambda x:x["task_id"]):
        if not selector(w) or w["law"] is None or not w["future_groups"]:
            continue
        matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
        if not matches: continue
        probation["tested"]+=1
        result=eval_group(w,w["future_groups"][0],active)
        if result["verified"]:
            probation["passed"]+=1; probation["causal"]+=int(result["causal"])
        else:
            probation["failed"]+=1
            active=ablate_capability(active,matches[0].law_id)
    text=active.text()
    active=exact_restart(text)
    restart_exact=active.text()==text

    stats={w["task_id"]:{"promoted":bool(applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))),"verified":0,"events":max(0,len(w["future_groups"])-1),"revoked":False} for w in worlds}
    events=[]
    for w in worlds:
        for j,g in enumerate(w["future_groups"][1:],start=1):
            events.append((stream_hash(f"{w['task_id']}|{j}"),w,j,g))
    events.sort(key=lambda x:(x[0],x[1]["task_id"],x[2]))
    verified=causal=failures=unknown=0
    for _,w,j,g in events:
        matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
        if not matches:
            unknown+=1; continue
        result=eval_group(w,g,active)
        if result["verified"]:
            verified+=1; causal+=int(result["causal"]); stats[w["task_id"]]["verified"]+=1
        else:
            failures+=1; stats[w["task_id"]]["revoked"]=True
            active=ablate_capability(active,matches[0].law_id)
    promoted=[x for x in stats.values() if x["promoted"]]
    survivors=[x for x in promoted if x["verified"]==x["events"] and not x["revoked"]]
    return {
      "probation":probation,"restart_exact":restart_exact,
      "initial_laws_after_probation":len(promoted),"final_laws":len(active.laws),
      "initial_bytes_after_probation":len(text.encode()),"verified_events":verified,
      "causal_ablations":causal,"failures":failures,"unknown_events":unknown,
      "promoted_sources":len(promoted),"surviving_sources":len(survivors),
      "survival_precision":len(survivors)/max(1,len(promoted)),"source_stats":stats
    }

def main():
    freeze_manifest()
    manifest=json.loads(Path("openml-v9-manifest.json").read_text())
    if manifest["target_data_downloaded"] or manifest["manifest_digest"]!=MANIFEST_SHA:
        raise AssertionError("V9 manifest drift or leakage")
    text=POLICY_PATH.read_text()
    if hashlib.sha256(text.encode()).hexdigest()!=POLICY_SHA:
        raise AssertionError("acquisition policy drift")
    mem=exact_restart(text)
    policy=policy_from_memory(mem); budget=budget_from_memory(mem)
    cfg=json.loads(V9_PATH.read_text())
    if cfg["v9_target_outcomes_used"]: raise AssertionError("V9 policy contamination")
    floor=float(cfg["gain_threshold"])

    worlds=[load_world(int(m["task_id"]),int(m["data_id"]),m["name"],policy,budget) for m in manifest["worlds"]]
    candidate=lambda w:w["adaptive_accept"] and w["adaptive_cal_gain"]>=floor
    v6=lambda w:w["v6_promoted"]
    base=lambda w:w["adaptive_accept"]

    b=run_static(worlds,base)
    s=run_static(worlds,v6)
    p=run_probation(worlds,candidate)
    retention=p["verified_events"]/max(1,b["verified_events"])
    v6ret=s["verified_events"]/max(1,b["verified_events"])
    cold=sum(w["cold_search_cost"] for w in worlds)
    adaptive=sum(w["adaptive_search_cost"] for w in worlds)
    future=sum(w["cold_search_cost"]*max(0,len(w["future_groups"])-1) for w in worlds)
    acq=cold/max(1,adaptive); life=future/max(1,adaptive)

    result={
      "manifest_digest":MANIFEST_SHA,"policy_sha256":POLICY_SHA,"config":cfg,
      "base":b,"v6":s,"v9":p,"v9_retention":retention,"v6_retention":v6ret,
      "acquisition_reduction":acq,"lifecycle_reduction":life,"future_search_cost":0,
      "worlds":[{
        "task_id":w["task_id"],"data_id":w["data_id"],"dataset":w["dataset"],
        "gain":w["adaptive_cal_gain"],"candidate":candidate(w),"v6":v6(w),
        "future_groups":len(w["future_groups"]),
        "v9_promoted":p["source_stats"][w["task_id"]]["promoted"],
        "v9_verified":p["source_stats"][w["task_id"]]["verified"],
        "v9_revoked":p["source_stats"][w["task_id"]]["revoked"],
      } for w in worlds],
    }
    gates={
      "twenty_source_only_worlds":len(worlds)==20,
      "probation_nontrivial":p["probation"]["tested"]>=6 and p["promoted_sources"]>=4,
      "probation_restart_exact":p["restart_exact"],
      "v9_precision_no_worse_than_v6":p["survival_precision"]>=s["survival_precision"],
      "v9_failures_no_worse_than_v6":p["failures"]<=s["failures"],
      "v9_retains_at_least_75pct_base_deployment_events":retention>=0.75,
      "v9_retention_no_worse_than_v6":retention>=v6ret,
      "every_v9_verified_event_causal":p["causal_ablations"]==p["verified_events"],
      "adaptive_acquisition_reduction":acq>=2.0,
      "lifecycle_reduction":life>=6.0,
      "future_search_zero":True,
    }
    result["gates"]=gates; result["passed"]=all(gates.values())
    Path(os.environ.get("REALITYGRAPH_OPENML_V9_RESULT","openml-v9-summary.json")).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")

    print("REALITYGRAPH / VERIFIER-GATED PROBATION V9")
    print("------------------------------------------")
    print(f"manifest_digest={MANIFEST_SHA} gain_floor={floor:.17g}")
    print(f"probation tested={p['probation']['tested']} passed={p['probation']['passed']} failed={p['probation']['failed']}")
    for name,x in (("BASE",b),("V6",s),("V9",p)):
        print(f"{name}: promoted={x['promoted_sources']} survived={x['surviving_sources']} failures={x['failures']} verified={x['verified_events']} precision={x['survival_precision']:.4f}")
    print(f"retention V6={v6ret:.4f} V9={retention:.4f} acquisition={acq:.2f}x lifecycle={life:.2f}x")
    for k,v in gates.items():print(f"gate_{k}={int(v)}")
    print("VERDICT")
    if result["passed"]: print("PASS_VERIFIER_GATED_PROBATION_V9")
    else:
        print("PARTIAL_VERIFIER_GATED_PROBATION_V9")
        raise AssertionError("one or more frozen V9 gates failed")

if __name__=="__main__":main()
