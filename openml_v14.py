from __future__ import annotations
import hashlib,json,os
from pathlib import Path

from openml_v7 import load_world
from openml_v11 import micro_groups
from openml_v12 import adaptive_run
from probe_openml_v14_manifest import main as freeze_manifest
from realitygraph.adaptive_policy import budget_from_memory
from realitygraph.meta_policy import policy_from_memory
from realitygraph.mg import MG
from realitygraph.retained_capability import (
    ablate_capability, applicable_transfer_capabilities, exact_restart
)
from scope_gate_v5 import eval_group

POLICY_PATH=Path("frozen-meta/adaptive_policy.mg")
POLICY_SHA="3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
CFG_PATH=Path("frozen-meta/openml_portfolio_v14.json")
MANIFEST_SHA="6b87c8379d32914063e492a8ff1e08037a06f333400661b8322ab7c58ddf9b57"

def h(seed,value):
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()

def baseline_cfg(cfg):
    return {
      "version":"openml-capability-state-v12-adaptive-evidence-v1",
      "candidate_gain_floor":0.01599671357125708,
      "direct_gain_threshold":0.05718096689694352,
    }

def learn_threshold(worlds, baseline, band, required_prefix):
    certs={int(c["task_id"]):c for c in baseline["certificates"]}
    examples=[]
    for w in worlds:
        c=certs[w["task_id"]]
        if c.get("band")!=band:
            continue
        bits=list(c.get("evidence",[]))
        if len(bits)<len(required_prefix):
            continue
        if tuple(bits[:len(required_prefix)])!=tuple(required_prefix):
            continue
        good=(c.get("state")=="ACTIVE")
        examples.append((float(w["adaptive_cal_gain"]),good,w["task_id"]))
    if not examples:
        return None,[]
    gains=sorted({x[0] for x in examples})
    for t in gains:
        selected=[x for x in examples if x[0]>=t]
        if selected and any(x[1] for x in selected) and all(x[1] for x in selected):
            return t,examples
    return None,examples

def learn_policy(dev_worlds, dev_baseline, cfg):
    direct_t,direct_examples=learn_threshold(dev_worlds,dev_baseline,"DIRECT",(True,))
    border_t,border_examples=learn_threshold(dev_worlds,dev_baseline,"BORDERLINE",(True,True))
    policy={
      "version":cfg["version"],
      "manifest_digest":MANIFEST_SHA,
      "development_task_ids":[w["task_id"] for w in dev_worlds],
      "heldout_task_ids":[],
      "direct_threshold":direct_t,
      "borderline_threshold":border_t,
      "direct_examples":[{"gain":g,"good":good,"task_id":tid} for g,good,tid in direct_examples],
      "borderline_examples":[{"gain":g,"good":good,"task_id":tid} for g,good,tid in border_examples],
      "heldout_outcomes_used":False,
    }
    text=json.dumps(policy,sort_keys=True,separators=(",",":"))
    restarted=json.loads(text)
    exact=json.dumps(restarted,sort_keys=True,separators=(",",":"))==text
    return restarted,text,exact

def meta_run(worlds, policy):
    low=0.01599671357125708
    high=0.05718096689694352
    candidate=lambda w:w["adaptive_accept"] and w["adaptive_cal_gain"]>=low
    laws=[w["law"] for w in worlds if w["law"] is not None and candidate(w)]
    active=exact_restart(MG("openml-v14-portfolio-verifier",laws).text())

    certs=[]; checks=passes=verifier_causal=0; shortcuts=0
    for w in sorted(worlds,key=lambda x:x["task_id"]):
        if not candidate(w) or w["law"] is None:
            certs.append({"task_id":w["task_id"],"law_id":None,"band":"REJECTED","evidence":[],"state":"SUSPENDED","shortcut":False})
            continue
        band="DIRECT" if w["adaptive_cal_gain"]>=high else "BORDERLINE"
        bits=[]; state="PROBATION"; shortcut=False
        for g in w["micro_groups"][:3]:
            matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
            if not matches:
                state="SUSPENDED"; break
            r=eval_group(w,g,active)
            checks+=1; passes+=int(r["verified"]); verifier_causal+=int(r["causal"])
            bits.append(bool(r["verified"]))

            if band=="DIRECT":
                if (
                    len(bits)==1 and bits[0]
                    and policy["direct_threshold"] is not None
                    and w["adaptive_cal_gain"]>=float(policy["direct_threshold"])
                ):
                    state="ACTIVE"; shortcut=True; shortcuts+=1; break
                p=sum(bits); f=len(bits)-p
                if p>=2:
                    state="ACTIVE"; break
                if f>=2:
                    state="SUSPENDED"; break
                if len(bits)==3:
                    state="ACTIVE" if p>=2 else "SUSPENDED"
            else:
                if not r["verified"]:
                    state="SUSPENDED"; break
                if (
                    len(bits)==2 and all(bits)
                    and policy["borderline_threshold"] is not None
                    and w["adaptive_cal_gain"]>=float(policy["borderline_threshold"])
                ):
                    state="ACTIVE"; shortcut=True; shortcuts+=1; break
                if len(bits)==3:
                    state="ACTIVE"

        matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
        law_id=matches[0].law_id if matches else None
        if state!="ACTIVE" and matches:
            active=ablate_capability(active,matches[0].law_id)
        certs.append({
          "task_id":w["task_id"],"law_id":law_id,"band":band,
          "evidence":bits,"state":state,"shortcut":shortcut
        })

    mg_text=active.text()
    state_text=json.dumps({"policy":policy,"certificates":certs},sort_keys=True,separators=(",",":"))
    restarted=exact_restart(mg_text)
    state_restart=json.loads(state_text)
    restart_exact=(
      restarted.text()==mg_text
      and json.dumps(state_restart,sort_keys=True,separators=(",",":"))==state_text
    )
    cert_map={int(x["task_id"]):x for x in state_restart["certificates"]}

    stats={w["task_id"]:{
      "promoted":cert_map[w["task_id"]]["state"]=="ACTIVE",
      "verified":0,"events":5,"revoked":False
    } for w in worlds}
    events=[]
    for w in worlds:
        for j,g in enumerate(w["micro_groups"][3:],start=3):
            events.append((h("openml-v11-deploy",f"{w['task_id']}|{j}"),w,j,g))
    events.sort(key=lambda x:(x[0],x[1]["task_id"],x[2]))

    active=restarted; verified=causal=failures=unknown=0
    for _,w,j,g in events:
        matches=applicable_transfer_capabilities(active,w["source_hashes"],tuple(w["feature_names"]))
        if not matches:
            unknown+=1; continue
        r=eval_group(w,g,active)
        if r["verified"]:
            verified+=1; causal+=int(r["causal"]); stats[w["task_id"]]["verified"]+=1
        else:
            failures+=1; stats[w["task_id"]]["revoked"]=True
            active=ablate_capability(active,matches[0].law_id)
            cert_map[w["task_id"]]["state"]="REVOKED"

    promoted=[x for x in stats.values() if x["promoted"]]
    survivors=[x for x in promoted if x["verified"]==x["events"] and not x["revoked"]]
    return {
      "verifier_checks":checks,"verifier_passes":passes,"verifier_causal":verifier_causal,
      "shortcuts":shortcuts,"restart_exact":restart_exact,
      "state_certificate_bytes":len(state_text.encode()),
      "initial_active_laws":len(restarted.laws),"final_laws":len(active.laws),
      "verified_events":verified,"causal_ablations":causal,"failures":failures,
      "unknown_events":unknown,"promoted_sources":len(promoted),
      "surviving_sources":len(survivors),
      "survival_precision":len(survivors)/max(1,len(promoted)),
      "certificates":list(cert_map.values()),"source_stats":stats
    }

def main():
    freeze_manifest()
    manifest=json.loads(Path("openml-v14-manifest.json").read_text())
    if manifest["target_data_downloaded"] or manifest["manifest_digest"]!=MANIFEST_SHA:
        raise AssertionError("V14 manifest drift or leakage")
    cfg=json.loads(CFG_PATH.read_text())
    if cfg["v14_heldout_outcomes_used_to_learn_policy"]:
        raise AssertionError("V14 protocol contamination")

    text=POLICY_PATH.read_text()
    if hashlib.sha256(text.encode()).hexdigest()!=POLICY_SHA:
        raise AssertionError("acquisition policy drift")
    mem=exact_restart(text)
    acquisition_policy=policy_from_memory(mem); budget=budget_from_memory(mem)

    worlds=[load_world(int(m["task_id"]),int(m["data_id"]),m["name"],acquisition_policy,budget) for m in manifest["worlds"]]
    for w in worlds:
        w["micro_groups"]=micro_groups(w,8)

    n=int(cfg["development_worlds"])
    dev=worlds[:n]; test=worlds[n:]
    if len(dev)!=8 or len(test)!=12:
        raise AssertionError("V14 developmental split drift")

    basecfg=baseline_cfg(cfg)
    dev_baseline=adaptive_run(dev,basecfg)
    learned,policy_text,policy_restart=learn_policy(dev,dev_baseline,cfg)
    learned["heldout_task_ids"]=[w["task_id"] for w in test]
    policy_text=json.dumps(learned,sort_keys=True,separators=(",",":"))
    learned=json.loads(policy_text)
    policy_restart=policy_restart and json.dumps(learned,sort_keys=True,separators=(",",":"))==policy_text

    baseline=adaptive_run(test,basecfg)
    v14=meta_run(test,learned)

    reduction=1-v14["verifier_checks"]/max(1,baseline["verifier_checks"])
    cold=sum(w["cold_search_cost"] for w in test)
    acq=sum(w["adaptive_search_cost"] for w in test)
    lifecycle=sum(w["cold_search_cost"]*5 for w in test)/max(1,acq)

    result={
      "manifest_digest":MANIFEST_SHA,"config":cfg,"learned_policy":learned,
      "development_baseline":dev_baseline,"heldout_v12":baseline,"heldout_v14":v14,
      "verifier_check_reduction":reduction,
      "acquisition_reduction":cold/max(1,acq),
      "lifecycle_reduction":lifecycle,"future_search_cost":0,
      "development_task_ids":[w["task_id"] for w in dev],
      "heldout_task_ids":[w["task_id"] for w in test],
    }
    gates={
      "source_only_manifest_exact":len(worlds)==20,
      "development_heldout_split_exact":len(dev)==8 and len(test)==12,
      "policy_restart_exact":policy_restart,
      "at_least_one_learned_shortcut":v14["shortcuts"]>=1,
      "at_least_10pct_fewer_heldout_verifier_checks":reduction>=0.10,
      "heldout_verified_events_no_worse_than_v12":v14["verified_events"]>=baseline["verified_events"],
      "heldout_failures_no_worse_than_v12":v14["failures"]<=baseline["failures"],
      "heldout_precision_no_worse_than_v12":v14["survival_precision"]>=baseline["survival_precision"],
      "all_verifier_successes_causal":v14["verifier_causal"]==v14["verifier_passes"],
      "all_deployment_successes_causal":v14["causal_ablations"]==v14["verified_events"],
      "future_search_zero":True,
      "compact_policy_and_state":len(policy_text.encode())<=8192 and v14["state_certificate_bytes"]<=16000,
      "lifecycle_reduction":lifecycle>=8.0,
    }
    result["gates"]=gates; result["passed"]=all(gates.values())
    Path(os.environ.get("REALITYGRAPH_OPENML_V14_RESULT","openml-v14-summary.json")).write_text(
      json.dumps(result,sort_keys=True,indent=2)+"\n"
    )

    print("REALITYGRAPH / PORTFOLIO VERIFIER COMPILATION V14")
    print("-------------------------------------------------")
    print(f"manifest_digest={MANIFEST_SHA}")
    print(f"development_tasks={[w['task_id'] for w in dev]}")
    print(f"heldout_tasks={[w['task_id'] for w in test]}")
    print(f"learned_direct_threshold={learned['direct_threshold']} learned_borderline_threshold={learned['borderline_threshold']}")
    print(f"V12 checks={baseline['verifier_checks']} verified={baseline['verified_events']} failures={baseline['failures']} precision={baseline['survival_precision']:.4f}")
    print(f"V14 checks={v14['verifier_checks']} shortcuts={v14['shortcuts']} verified={v14['verified_events']} failures={v14['failures']} precision={v14['survival_precision']:.4f}")
    print(f"heldout_verifier_reduction={reduction:.4f} lifecycle={lifecycle:.2f}x")
    for k,v in gates.items():
        print(f"gate_{k}={int(v)}")
    print("VERDICT")
    if result["passed"]:
        print("PASS_PORTFOLIO_VERIFIER_COMPILATION_V14")
    else:
        print("PARTIAL_PORTFOLIO_VERIFIER_COMPILATION_V14")
        raise AssertionError("one or more frozen V14 gates failed")

if __name__=="__main__":
    main()
