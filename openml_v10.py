from __future__ import annotations
import hashlib,json,os
from pathlib import Path

from openml_v7 import load_world
from probe_openml_v10_manifest import main as freeze_manifest
from realitygraph.adaptive_policy import budget_from_memory
from realitygraph.meta_policy import policy_from_memory
from realitygraph.mg import MG
from realitygraph.retained_capability import ablate_capability,applicable_transfer_capabilities,exact_restart
from scope_gate_v5 import eval_group

POLICY_PATH=Path("frozen-meta/adaptive_policy.mg")
POLICY_SHA="3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
CFG_PATH=Path("frozen-meta/openml_scope_v10.json")
MANIFEST_SHA="TO_BE_FROZEN"

def sh(value):
    return hashlib.sha256(f"openml-v10-deploy|{value}".encode()).digest()

def run_static(worlds,selector):
    laws=[w["law"] for w in worlds if w["law"] is not None and selector(w)]
    active=exact_restart(MG("openml-v10-static",laws).text())
    stats={w["task_id"]:{"promoted":selector(w) and w["law"] is not None,"verified":0,"events":max(0,len(w["future_groups"])-2),"revoked":False} for w in worlds}
    events=[]
    for w in worlds:
        for j,g in enumerate(w["future_groups"][2:],start=2):
            events.append((sh(f"{w['task_id']}|{j}"),w,j,g))
    events.sort(key=lambda x:(x[0],x[1]["task_id"],x[2]))
    verified=causal=failures=unknown=0
    for _,w,j,g in events:
        matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
        if not matches: unknown+=1; continue
        r=eval_group(w,g,active)
        if r["verified"]:
            verified+=1; causal+=int(r["causal"]); stats[w["task_id"]]["verified"]+=1
        else:
            failures+=1; stats[w["task_id"]]["revoked"]=True
            active=ablate_capability(active,matches[0].law_id)
    promoted=[x for x in stats.values() if x["promoted"]]
    survivors=[x for x in promoted if x["verified"]==x["events"] and not x["revoked"]]
    return {"verified_events":verified,"causal_ablations":causal,"failures":failures,"unknown_events":unknown,
      "promoted_sources":len(promoted),"surviving_sources":len(survivors),
      "survival_precision":len(survivors)/max(1,len(promoted)),"final_laws":len(active.laws),
      "initial_bytes":len(MG("openml-v10-static",laws).text().encode()),"source_stats":stats}

def run_selective(worlds,low,high):
    candidate=lambda w:w["adaptive_accept"] and w["adaptive_cal_gain"]>=low
    direct=lambda w:w["adaptive_accept"] and w["adaptive_cal_gain"]>=high
    laws=[w["law"] for w in worlds if w["law"] is not None and candidate(w)]
    active=exact_restart(MG("openml-v10-selective",laws).text())
    probation={"tested":0,"passed":0,"failed":0,"verified_checks":0,"causal_checks":0}
    for w in sorted(worlds,key=lambda x:x["task_id"]):
        if direct(w) or not candidate(w) or w["law"] is None: continue
        probation["tested"]+=1
        ok=True
        for g in w["future_groups"][:2]:
            matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
            if not matches: ok=False; break
            r=eval_group(w,g,active)
            probation["verified_checks"]+=int(r["verified"])
            probation["causal_checks"]+=int(r["causal"])
            if not r["verified"]:
                ok=False
                active=ablate_capability(active,matches[0].law_id)
                break
        if ok: probation["passed"]+=1
        else: probation["failed"]+=1
    text=active.text(); active=exact_restart(text); restart_exact=active.text()==text
    stats={w["task_id"]:{"promoted":bool(applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))),"verified":0,"events":max(0,len(w["future_groups"])-2),"revoked":False} for w in worlds}
    events=[]
    for w in worlds:
        for j,g in enumerate(w["future_groups"][2:],start=2):
            events.append((sh(f"{w['task_id']}|{j}"),w,j,g))
    events.sort(key=lambda x:(x[0],x[1]["task_id"],x[2]))
    verified=causal=failures=unknown=0
    for _,w,j,g in events:
        matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
        if not matches: unknown+=1; continue
        r=eval_group(w,g,active)
        if r["verified"]:
            verified+=1; causal+=int(r["causal"]); stats[w["task_id"]]["verified"]+=1
        else:
            failures+=1; stats[w["task_id"]]["revoked"]=True
            active=ablate_capability(active,matches[0].law_id)
    promoted=[x for x in stats.values() if x["promoted"]]
    survivors=[x for x in promoted if x["verified"]==x["events"] and not x["revoked"]]
    return {"probation":probation,"restart_exact":restart_exact,"verified_events":verified,
      "causal_ablations":causal,"failures":failures,"unknown_events":unknown,
      "promoted_sources":len(promoted),"surviving_sources":len(survivors),
      "survival_precision":len(survivors)/max(1,len(promoted)),"final_laws":len(active.laws),
      "initial_bytes_after_probation":len(text.encode()),"source_stats":stats}

def main():
    freeze_manifest()
    manifest=json.loads(Path("openml-v10-manifest.json").read_text())
    if manifest["target_data_downloaded"] or manifest["manifest_digest"]!=MANIFEST_SHA:
        raise AssertionError("V10 manifest drift or leakage")
    text=POLICY_PATH.read_text()
    if hashlib.sha256(text.encode()).hexdigest()!=POLICY_SHA: raise AssertionError("policy drift")
    mem=exact_restart(text); policy=policy_from_memory(mem); budget=budget_from_memory(mem)
    cfg=json.loads(CFG_PATH.read_text())
    if cfg["v10_target_outcomes_used"]: raise AssertionError("V10 contamination")
    low=float(cfg["borderline_gain_floor"]); high=float(cfg["direct_promotion_gain"])
    worlds=[load_world(int(m["task_id"]),int(m["data_id"]),m["name"],policy,budget) for m in manifest["worlds"]]

    base=run_static(worlds,lambda w:w["adaptive_accept"])
    v6=run_static(worlds,lambda w:w["adaptive_accept"] and w["adaptive_cal_gain"]>=high)
    v10=run_selective(worlds,low,high)
    retention=v10["verified_events"]/max(1,base["verified_events"])
    v6ret=v6["verified_events"]/max(1,base["verified_events"])
    cold=sum(w["cold_search_cost"] for w in worlds); adaptive=sum(w["adaptive_search_cost"] for w in worlds)
    future=sum(w["cold_search_cost"]*max(0,len(w["future_groups"])-2) for w in worlds)
    acq=cold/max(1,adaptive); life=future/max(1,adaptive)

    result={"manifest_digest":MANIFEST_SHA,"config":cfg,"base":base,"v6":v6,"v10":v10,
      "v6_retention":v6ret,"v10_retention":retention,"acquisition_reduction":acq,
      "lifecycle_reduction":life,"future_search_cost":0}
    gates={
      "twenty_source_only_worlds":len(worlds)==20,
      "borderline_probation_exercised":v10["probation"]["tested"]>=2,
      "restart_exact":v10["restart_exact"],
      "v10_precision_no_worse_than_v6":v10["survival_precision"]>=v6["survival_precision"],
      "v10_failures_no_worse_than_v6":v10["failures"]<=v6["failures"],
      "v10_retention_no_worse_than_v6":retention>=v6ret,
      "v10_retains_at_least_80pct_base":retention>=0.80,
      "every_v10_verified_event_causal":v10["causal_ablations"]==v10["verified_events"],
      "acquisition_reduction":acq>=2.0,"lifecycle_reduction":life>=4.0,"future_search_zero":True,
    }
    result["gates"]=gates; result["passed"]=all(gates.values())
    Path(os.environ.get("REALITYGRAPH_OPENML_V10_RESULT","openml-v10-summary.json")).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("REALITYGRAPH / SELECTIVE ESCALATION V10")
    print("---------------------------------------")
    print(f"manifest_digest={MANIFEST_SHA} low={low:.17g} high={high:.17g}")
    print(f"borderline tested={v10['probation']['tested']} passed={v10['probation']['passed']} failed={v10['probation']['failed']}")
    for name,x in (("BASE",base),("V6",v6),("V10",v10)):
        print(f"{name}: promoted={x['promoted_sources']} survived={x['surviving_sources']} failures={x['failures']} verified={x['verified_events']} precision={x['survival_precision']:.4f}")
    print(f"retention V6={v6ret:.4f} V10={retention:.4f} acquisition={acq:.2f}x lifecycle={life:.2f}x")
    for k,v in gates.items(): print(f"gate_{k}={int(v)}")
    print("VERDICT")
    if result["passed"]: print("PASS_SELECTIVE_ESCALATION_V10")
    else:
        print("PARTIAL_SELECTIVE_ESCALATION_V10")
        raise AssertionError("one or more frozen V10 gates failed")

if __name__=="__main__":main()
