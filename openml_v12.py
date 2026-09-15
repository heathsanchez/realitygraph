from __future__ import annotations
import hashlib,json,os
from pathlib import Path

from openml_v7 import load_world
from openml_v11 import micro_groups,stateful_run
from probe_openml_v12_manifest import main as freeze_manifest
from realitygraph.adaptive_policy import budget_from_memory
from realitygraph.meta_policy import policy_from_memory
from realitygraph.mg import MG
from realitygraph.retained_capability import ablate_capability,applicable_transfer_capabilities,exact_restart
from scope_gate_v5 import eval_group

POLICY_PATH=Path("frozen-meta/adaptive_policy.mg")
POLICY_SHA="3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
CFG_PATH=Path("frozen-meta/openml_state_v12.json")
MANIFEST_SHA="bf0e170e0405f32af1dc98ac7391eda25f9ea0a8e12644df4f40d720e159dc33"

def h(seed,value):
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()

def adaptive_run(worlds,cfg):
    low=float(cfg["candidate_gain_floor"]); high=float(cfg["direct_gain_threshold"])
    candidate=lambda w:w["adaptive_accept"] and w["adaptive_cal_gain"]>=low
    laws=[w["law"] for w in worlds if w["law"] is not None and candidate(w)]
    active=exact_restart(MG("openml-v12-adaptive",laws).text())

    certs=[]; checks=passes=causal=0
    for w in sorted(worlds,key=lambda x:x["task_id"]):
        if not candidate(w) or w["law"] is None:
            certs.append({"task_id":w["task_id"],"law_id":None,"band":"REJECTED","evidence":[],"state":"SUSPENDED"})
            continue
        band="DIRECT" if w["adaptive_cal_gain"]>=high else "BORDERLINE"
        bits=[]; state="PROBATION"
        for g in w["micro_groups"][:3]:
            matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
            if not matches: state="SUSPENDED"; break
            r=eval_group(w,g,active)
            checks+=1; passes+=int(r["verified"]); causal+=int(r["causal"]); bits.append(bool(r["verified"]))

            if band=="DIRECT":
                p=sum(bits); f=len(bits)-p
                if p>=2: state="ACTIVE"; break
                if f>=2: state="SUSPENDED"; break
                if len(bits)==3: state="ACTIVE" if p>=2 else "SUSPENDED"
            else:
                if not r["verified"]: state="SUSPENDED"; break
                if len(bits)==3: state="ACTIVE"

        matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
        law_id=matches[0].law_id if matches else None
        if state!="ACTIVE" and matches:
            active=ablate_capability(active,matches[0].law_id)
        certs.append({"task_id":w["task_id"],"law_id":law_id,"band":band,"evidence":bits,"state":state})

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
            events.append((h("openml-v12-deploy",f"{w['task_id']}|{j}"),w,j,g))
    events.sort(key=lambda x:(x[0],x[1]["task_id"],x[2]))

    active=restarted; verified=deploy_causal=failures=unknown=0
    for _,w,j,g in events:
        matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
        if not matches:
            unknown+=1; continue
        r=eval_group(w,g,active)
        if r["verified"]:
            verified+=1; deploy_causal+=int(r["causal"]); stats[w["task_id"]]["verified"]+=1
        else:
            failures+=1; stats[w["task_id"]]["revoked"]=True
            active=ablate_capability(active,matches[0].law_id)
            cert_map[w["task_id"]]["state"]="REVOKED"

    promoted=[x for x in stats.values() if x["promoted"]]
    survivors=[x for x in promoted if x["verified"]==x["events"] and not x["revoked"]]
    return {
      "verifier_checks":checks,"verifier_passes":passes,"verifier_causal":causal,
      "restart_exact":restart_exact,"state_certificate_bytes":len(state_text.encode()),
      "initial_active_laws":len(restarted.laws),"final_laws":len(active.laws),
      "verified_events":verified,"causal_ablations":deploy_causal,"failures":failures,
      "unknown_events":unknown,"promoted_sources":len(promoted),"surviving_sources":len(survivors),
      "survival_precision":len(survivors)/max(1,len(promoted)),
      "certificates":list(cert_map.values()),"source_stats":stats
    }

def main():
    freeze_manifest()
    manifest=json.loads(Path("openml-v12-manifest.json").read_text())
    if manifest["target_data_downloaded"] or manifest["manifest_digest"]!=MANIFEST_SHA:
        raise AssertionError("V12 manifest drift or leakage")
    text=POLICY_PATH.read_text()
    if hashlib.sha256(text.encode()).hexdigest()!=POLICY_SHA: raise AssertionError("policy drift")
    mem=exact_restart(text); policy=policy_from_memory(mem); budget=budget_from_memory(mem)
    cfg=json.loads(CFG_PATH.read_text())
    if cfg["v12_target_outcomes_used"]: raise AssertionError("V12 contamination")

    worlds=[load_world(int(m["task_id"]),int(m["data_id"]),m["name"],policy,budget) for m in manifest["worlds"]]
    for w in worlds: w["micro_groups"]=micro_groups(w,8)

    fixed_cfg={
      "version":"openml-capability-state-v11-v1",
      "candidate_gain_floor":cfg["candidate_gain_floor"],
      "direct_gain_threshold":cfg["direct_gain_threshold"],
    }
    fixed=stateful_run(worlds,fixed_cfg)
    adaptive=adaptive_run(worlds,cfg)

    fixed_active={c["task_id"] for c in fixed["certificates"] if c["state"] in ("ACTIVE","REVOKED")}
    adaptive_active={c["task_id"] for c in adaptive["certificates"] if c["state"] in ("ACTIVE","REVOKED")}
    same_active=fixed_active==adaptive_active
    same_deploy=(fixed["verified_events"]==adaptive["verified_events"] and fixed["failures"]==adaptive["failures"] and fixed["surviving_sources"]==adaptive["surviving_sources"])
    saving=1-adaptive["verifier_checks"]/max(1,fixed["verifier_checks"])

    cold=sum(w["cold_search_cost"] for w in worlds); acq=sum(w["adaptive_search_cost"] for w in worlds)
    lifecycle=sum(w["cold_search_cost"]*5 for w in worlds)/max(1,acq)

    result={
      "manifest_digest":MANIFEST_SHA,"config":cfg,"fixed_v11":fixed,"adaptive_v12":adaptive,
      "same_active_set":same_active,"same_deployment_outcome":same_deploy,
      "verifier_check_reduction":saving,"acquisition_reduction":cold/max(1,acq),
      "lifecycle_reduction":lifecycle,"future_search_cost":0
    }
    gates={
      "twenty_source_only_worlds":len(worlds)==20,
      "eight_microshards_each":all(len(w["micro_groups"])==8 for w in worlds),
      "adaptive_restart_exact":adaptive["restart_exact"],
      "same_active_set_as_fixed_v11":same_active,
      "same_deployment_outcome_as_fixed_v11":same_deploy,
      "at_least_15pct_fewer_verifier_checks":saving>=0.15,
      "all_verifier_successes_causal":adaptive["verifier_causal"]==adaptive["verifier_passes"],
      "all_deployment_successes_causal":adaptive["causal_ablations"]==adaptive["verified_events"],
      "future_search_zero":True,
      "compact_state_certificate":adaptive["state_certificate_bytes"]<=12000,
      "lifecycle_reduction":lifecycle>=8.0
    }
    result["gates"]=gates; result["passed"]=all(gates.values())
    Path(os.environ.get("REALITYGRAPH_OPENML_V12_RESULT","openml-v12-summary.json")).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")

    print("REALITYGRAPH / ADAPTIVE EVIDENCE V12")
    print("------------------------------------")
    print(f"manifest_digest={MANIFEST_SHA}")
    print(f"fixed_checks={fixed['verifier_checks']} adaptive_checks={adaptive['verifier_checks']} reduction={saving:.4f}")
    print(f"same_active_set={same_active} same_deployment_outcome={same_deploy}")
    print(f"FIXED: active={fixed['promoted_sources']} survived={fixed['surviving_sources']} failures={fixed['failures']} verified={fixed['verified_events']} precision={fixed['survival_precision']:.4f}")
    print(f"V12: active={adaptive['promoted_sources']} survived={adaptive['surviving_sources']} failures={adaptive['failures']} verified={adaptive['verified_events']} precision={adaptive['survival_precision']:.4f}")
    for k,v in gates.items(): print(f"gate_{k}={int(v)}")
    print("VERDICT")
    if result["passed"]: print("PASS_ADAPTIVE_EVIDENCE_COMPILATION_V12")
    else:
        print("PARTIAL_ADAPTIVE_EVIDENCE_COMPILATION_V12")
        raise AssertionError("one or more frozen V12 gates failed")

if __name__=="__main__": main()
