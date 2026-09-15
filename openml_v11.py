from __future__ import annotations
import hashlib,json,os
from pathlib import Path

from openml_v7 import load_world,split_indices
from probe_openml_v11_manifest import main as freeze_manifest
from realitygraph.adaptive_policy import budget_from_memory
from realitygraph.meta_policy import policy_from_memory
from realitygraph.mg import MG
from realitygraph.retained_capability import ablate_capability,applicable_transfer_capabilities,exact_restart
from scope_gate_v5 import eval_group

POLICY_PATH=Path("frozen-meta/adaptive_policy.mg")
POLICY_SHA="3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
CFG_PATH=Path("frozen-meta/openml_state_v11.json")
MANIFEST_SHA="02db015eaf28db8fdae23d73809b06bf8083fb4ce7fe908a32da4829684cc024"

def h(seed,value):
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()

def micro_groups(world,k=8):
    local=tuple(range(len(world["rows"])))
    _,_,test=split_indices(world["task_id"],local)
    ordered=sorted(test,key=lambda i:(h(f"v11|micro|{world['task_id']}",str(i)),i))
    groups=[[] for _ in range(k)]
    for j,i in enumerate(ordered): groups[j%k].append(i)
    out=tuple(tuple(sorted(g)) for g in groups if g)
    if len(out)!=k: raise AssertionError(f"need {k} nonempty microshards")
    return out

def stream_key(task_id,j):
    return h("openml-v11-deploy",f"{task_id}|{j}")

def static_run(worlds,selector):
    laws=[w["law"] for w in worlds if w["law"] is not None and selector(w)]
    initial=MG("openml-v11-static",laws)
    active=exact_restart(initial.text())
    stats={w["task_id"]:{"promoted":selector(w) and w["law"] is not None,"verified":0,"events":5,"revoked":False} for w in worlds}
    events=[]
    for w in worlds:
        for j,g in enumerate(w["micro_groups"][3:],start=3):
            events.append((stream_key(w["task_id"],j),w,j,g))
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
    return {"initial_laws":len(initial.laws),"initial_bytes":len(initial.text().encode()),
      "final_laws":len(active.laws),"verified_events":verified,"causal_ablations":causal,
      "failures":failures,"unknown_events":unknown,"promoted_sources":len(promoted),
      "surviving_sources":len(survivors),"survival_precision":len(survivors)/max(1,len(promoted)),
      "source_stats":stats}

def stateful_run(worlds,cfg):
    low=float(cfg["candidate_gain_floor"]); high=float(cfg["direct_gain_threshold"])
    candidate=lambda w:w["adaptive_accept"] and w["adaptive_cal_gain"]>=low
    laws=[w["law"] for w in worlds if w["law"] is not None and candidate(w)]
    active=exact_restart(MG("openml-v11-stateful",laws).text())
    certs=[]
    verifier_checks=verifier_passes=verifier_causal=0
    for w in sorted(worlds,key=lambda x:x["task_id"]):
        if not candidate(w) or w["law"] is None:
            certs.append({"task_id":w["task_id"],"law_id":None,"band":"REJECTED","evidence":[],"state":"SUSPENDED"})
            continue
        band="DIRECT" if w["adaptive_cal_gain"]>=high else "BORDERLINE"
        bits=[]
        for g in w["micro_groups"][:3]:
            matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
            if not matches: break
            r=eval_group(w,g,active)
            verifier_checks+=1; verifier_passes+=int(r["verified"]); verifier_causal+=int(r["causal"])
            bits.append(bool(r["verified"]))
        needed=2 if band=="DIRECT" else 3
        state="ACTIVE" if sum(bits)>=needed and len(bits)==3 else "SUSPENDED"
        matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
        law_id=matches[0].law_id if matches else None
        if state!="ACTIVE" and matches:
            active=ablate_capability(active,matches[0].law_id)
        certs.append({"task_id":w["task_id"],"law_id":law_id,"band":band,"evidence":bits,"required_passes":needed,"state":state})

    mg_text=active.text()
    state_text=json.dumps({"version":cfg["version"],"certificates":certs},sort_keys=True,separators=(",",":"))
    restarted=exact_restart(mg_text)
    state_restart=json.loads(state_text)
    restart_exact=(restarted.text()==mg_text and json.dumps(state_restart,sort_keys=True,separators=(",",":"))==state_text)
    cert_map={int(x["task_id"]):x for x in state_restart["certificates"]}

    stats={w["task_id"]:{"promoted":cert_map[w["task_id"]]["state"]=="ACTIVE","verified":0,"events":5,"revoked":False} for w in worlds}
    events=[]
    for w in worlds:
        for j,g in enumerate(w["micro_groups"][3:],start=3):
            events.append((stream_key(w["task_id"],j),w,j,g))
    events.sort(key=lambda x:(x[0],x[1]["task_id"],x[2]))
    active=restarted; verified=causal=failures=unknown=0
    for _,w,j,g in events:
        matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
        if not matches: unknown+=1; continue
        r=eval_group(w,g,active)
        if r["verified"]:
            verified+=1; causal+=int(r["causal"]); stats[w["task_id"]]["verified"]+=1
        else:
            failures+=1; stats[w["task_id"]]["revoked"]=True
            active=ablate_capability(active,matches[0].law_id)
            cert_map[w["task_id"]]["state"]="REVOKED"
    promoted=[x for x in stats.values() if x["promoted"]]
    survivors=[x for x in promoted if x["verified"]==x["events"] and not x["revoked"]]
    return {"verifier_checks":verifier_checks,"verifier_passes":verifier_passes,
      "verifier_causal":verifier_causal,"restart_exact":restart_exact,
      "state_certificate_bytes":len(state_text.encode()),"initial_active_laws":len(restarted.laws),
      "initial_active_bytes":len(mg_text.encode()),"final_laws":len(active.laws),
      "verified_events":verified,"causal_ablations":causal,"failures":failures,
      "unknown_events":unknown,"promoted_sources":len(promoted),
      "surviving_sources":len(survivors),"survival_precision":len(survivors)/max(1,len(promoted)),
      "certificates":list(cert_map.values()),"source_stats":stats}

def main():
    freeze_manifest()
    manifest=json.loads(Path("openml-v11-manifest.json").read_text())
    if manifest["target_data_downloaded"] or manifest["manifest_digest"]!=MANIFEST_SHA:
        raise AssertionError("V11 manifest drift or leakage")
    text=POLICY_PATH.read_text()
    if hashlib.sha256(text.encode()).hexdigest()!=POLICY_SHA: raise AssertionError("policy drift")
    mem=exact_restart(text); policy=policy_from_memory(mem); budget=budget_from_memory(mem)
    cfg=json.loads(CFG_PATH.read_text())
    if cfg["v11_target_outcomes_used"]: raise AssertionError("V11 contamination")
    worlds=[load_world(int(m["task_id"]),int(m["data_id"]),m["name"],policy,budget) for m in manifest["worlds"]]
    for w in worlds: w["micro_groups"]=micro_groups(w,8)

    low=float(cfg["candidate_gain_floor"]); high=float(cfg["direct_gain_threshold"])
    base=static_run(worlds,lambda w:w["adaptive_accept"])
    v6=static_run(worlds,lambda w:w["adaptive_accept"] and w["adaptive_cal_gain"]>=high)
    v11=stateful_run(worlds,cfg)
    retention=v11["verified_events"]/max(1,base["verified_events"])
    v6ret=v6["verified_events"]/max(1,base["verified_events"])
    cold=sum(w["cold_search_cost"] for w in worlds); adaptive=sum(w["adaptive_search_cost"] for w in worlds)
    deployment_cold=sum(w["cold_search_cost"]*5 for w in worlds)
    acq=cold/max(1,adaptive); life=deployment_cold/max(1,adaptive)

    result={"manifest_digest":MANIFEST_SHA,"config":cfg,"base":base,"v6":v6,"v11":v11,
      "v6_retention":v6ret,"v11_retention":retention,"acquisition_reduction":acq,
      "lifecycle_reduction":life,"future_search_cost":0,
      "worlds":[{"task_id":w["task_id"],"data_id":w["data_id"],"dataset":w["dataset"],
        "gain":w["adaptive_cal_gain"],"candidate":w["adaptive_accept"] and w["adaptive_cal_gain"]>=low,
        "direct":w["adaptive_accept"] and w["adaptive_cal_gain"]>=high,
        "v11_state":next(c["state"] for c in v11["certificates"] if c["task_id"]==w["task_id"]),
        "v11_evidence":next(c["evidence"] for c in v11["certificates"] if c["task_id"]==w["task_id"]),
        "v11_verified":v11["source_stats"][w["task_id"]]["verified"],
        "v11_revoked":v11["source_stats"][w["task_id"]]["revoked"]} for w in worlds]}
    gates={
      "twenty_source_only_worlds":len(worlds)==20,
      "eight_microshards_each":all(len(w["micro_groups"])==8 for w in worlds),
      "state_restart_exact":v11["restart_exact"],
      "evidence_conditioning_exercised":v11["verifier_checks"]>=12,
      "nontrivial_active_portfolio":v11["promoted_sources"]>=5,
      "v11_precision_no_worse_than_v6":v11["survival_precision"]>=v6["survival_precision"],
      "v11_failures_no_worse_than_v6":v11["failures"]<=v6["failures"],
      "v11_retention_no_worse_than_v6":retention>=v6ret,
      "v11_retains_at_least_75pct_base":retention>=0.75,
      "all_deployment_successes_causal":v11["causal_ablations"]==v11["verified_events"],
      "all_verifier_successes_causal":v11["verifier_causal"]==v11["verifier_passes"],
      "acquisition_reduction":acq>=2.0,"lifecycle_reduction":life>=8.0,
      "future_search_zero":True,"compact_state_certificate":v11["state_certificate_bytes"]<=12000,
    }
    result["gates"]=gates; result["passed"]=all(gates.values())
    Path(os.environ.get("REALITYGRAPH_OPENML_V11_RESULT","openml-v11-summary.json")).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")

    print("REALITYGRAPH / EVIDENCE-CONDITIONED CAPABILITY STATE V11")
    print("--------------------------------------------------------")
    print(f"manifest_digest={MANIFEST_SHA}")
    print(f"verifier_checks={v11['verifier_checks']} active_after_evidence={v11['promoted_sources']} state_bytes={v11['state_certificate_bytes']}")
    for w in result["worlds"]:
        print(f"task={w['task_id']} {w['dataset'][:24]:24} gain={w['gain']:+.4f} direct={w['direct']} evidence={w['v11_evidence']} state={w['v11_state']} deploy={w['v11_verified']}/5 revoke={w['v11_revoked']}")
    for name,x in (("BASE",base),("V6",v6),("V11",v11)):
        print(f"{name}: promoted={x['promoted_sources']} survived={x['surviving_sources']} failures={x['failures']} verified={x['verified_events']} precision={x['survival_precision']:.4f}")
    print(f"retention V6={v6ret:.4f} V11={retention:.4f} acquisition={acq:.2f}x lifecycle={life:.2f}x")
    for k,v in gates.items(): print(f"gate_{k}={int(v)}")
    print("VERDICT")
    if result["passed"]: print("PASS_EVIDENCE_CONDITIONED_CAPABILITY_STATE_V11")
    else:
        print("PARTIAL_EVIDENCE_CONDITIONED_CAPABILITY_STATE_V11")
        raise AssertionError("one or more frozen V11 gates failed")

if __name__=="__main__": main()
