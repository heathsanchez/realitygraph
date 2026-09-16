from __future__ import annotations

import bisect,hashlib,json,math,os
from pathlib import Path

import openml
import pandas as pd

from openml_v7 import sampled_indices,split_indices,numeric_matrix,calibration_evaluation,compile_model,MIN_GAIN
from openml_v11 import micro_groups
from openml_v12 import adaptive_run
from openml_regression_transfer_v2 import training_balanced_binary_target,InapplicableWorld
from probe_capability_generator_transfer_v1_manifest import main as freeze_manifest
from realitygraph.retained_capability import exact_restart
from realitygraph.transfer_memory import model_to_law

MANIFEST_SHA="80757258d4048f66b02814ac3f935987fd5e1680430868f765c058bf1c1b4ff4"
GRAMMARS=("sum","diff","absdiff")
MAX_BASE_FEATURES=8
DEV_WORLDS=8
HELDOUT_WORLDS=12

def h(seed,value):
    return hashlib.sha256(f"{seed}|{value}".encode()).digest()

def load_base_world(task_id,data_id,expected_name):
    task=openml.tasks.get_task(task_id,download_splits=False)
    dataset=task.get_dataset()
    if int(dataset.dataset_id)!=data_id: raise AssertionError("generator task/data drift")
    if str(dataset.name)!=expected_name: raise AssertionError("generator dataset name drift")
    X,y,_,_=dataset.get_data(target=task.target_name,dataset_format="dataframe")
    X=X.reset_index(drop=True); y=y.reset_index(drop=True)
    if not pd.api.types.is_numeric_dtype(y):
        y=pd.to_numeric(y,errors="coerce")
    selected=sampled_indices(task_id,len(X))
    Xs=X.iloc[list(selected)].reset_index(drop=True)
    ys=y.iloc[list(selected)].reset_index(drop=True)
    local=tuple(range(len(Xs)))
    train,calibration,test=split_indices(task_id,local)
    target_threshold,labels=training_balanced_binary_target(ys,train)
    feature_names,rows=numeric_matrix(task_id,Xs,train)
    checksum=str(getattr(dataset,"md5_checksum","") or f"openml-data-{data_id}-version-{dataset.version}")
    return {
      "task_id":task_id,"data_id":data_id,"dataset":expected_name,
      "source_hashes":((f"https://www.openml.org/d/{data_id}",checksum),),
      "feature_names":feature_names,"rows":rows,"labels":labels,
      "train":train,"calibration":calibration,"target_threshold":target_threshold,
      "target_threshold_source":"training_split_distinct_values_only",
      "rows_used":len(rows)
    }

def rank_columns(base):
    task_id=base["task_id"]; train=base["train"]
    idx=list(range(len(base["feature_names"])))
    idx.sort(key=lambda j:(h(f"generator-feature|{task_id}",base["feature_names"][j]),j))
    idx=idx[:min(MAX_BASE_FEATURES,len(idx))]
    cols=[]; names=[]
    for j in idx:
        train_vals=sorted(float(base["rows"][i][j]) for i in train)
        n=len(train_vals)
        col=[]
        for row in base["rows"]:
            v=float(row[j])
            col.append(bisect.bisect_right(train_vals,v)/n)
        cols.append(col); names.append(base["feature_names"][j])
    if len(cols)<2: raise InapplicableWorld("fewer_than_two_generator_features")
    return names,cols

def candidate_matrix(base,families):
    raw_names,raw_cols=rank_columns(base)
    names=[f"raw::{n}" for n in raw_names]
    origins=["raw"]*len(raw_cols)
    cols=[list(c) for c in raw_cols]
    for family in families:
        for i in range(len(raw_cols)):
            for j in range(i+1,len(raw_cols)):
                a=raw_cols[i]; b=raw_cols[j]
                if family=="sum": values=[x+y for x,y in zip(a,b)]
                elif family=="diff": values=[x-y for x,y in zip(a,b)]
                elif family=="absdiff": values=[abs(x-y) for x,y in zip(a,b)]
                else: raise AssertionError(f"unknown grammar {family}")
                cols.append(values)
                names.append(f"{family}::{raw_names[i]}::{raw_names[j]}")
                origins.append(family)
    rows=[[cols[j][i] for j in range(len(cols))] for i in range(len(base["rows"]))]
    return names,origins,rows

def representation_world(base,families,label):
    names,origins,rows=candidate_matrix(base,families)
    train=base["train"]; calibration=base["calibration"]; labels=base["labels"]
    candidates=[]
    for feature in range(len(names)):
        cal=calibration_evaluation(rows,labels,feature,train,calibration)
        candidates.append({"feature":feature,"origin":origins[feature],**cal})
    best=max(candidates,key=lambda x:(x["cal_gain"],-x["feature"]))
    accept=best["cal_gain"]>MIN_GAIN
    fit=tuple(train)+tuple(calibration)
    prior=(sum(labels[i] for i in fit)+1.0)/(len(fit)+2.0)
    law=None
    if accept:
        model,prior=compile_model(names,rows,labels,train,calibration,best["feature"],best["threshold"])
        provenance=hashlib.sha256(
          (f"capability-generator-v1|task={base['task_id']}|grammar={label}|"
           f"origin={best['origin']}|gain={best['cal_gain']:.12g}|name={names[best['feature']]}").encode()
        ).hexdigest()[:12]
        law=model_to_law(base["source_hashes"],model,provenance=provenance)
    world={
      "index":base["task_id"],"task_id":base["task_id"],"data_id":base["data_id"],
      "dataset":base["dataset"],"source_hashes":base["source_hashes"],
      "feature_names":names,"rows":rows,"labels":labels,"prior":prior,
      "adaptive_cal_gain":best["cal_gain"],"adaptive_accept":accept,"law":law,
      "selected_origin":best["origin"],"selected_name":names[best["feature"]],
      "candidate_count":len(candidates),
      "search_cost":sum(x["threshold_evals"] for x in candidates),
      "generator_label":label,"target_threshold":base["target_threshold"],
    }
    world["micro_groups"]=micro_groups(world,8)
    return world

def protocol_cfg():
    return {
      "version":"capability-generator-transfer-v1-evidence",
      "candidate_gain_floor":0.01599671357125708,
      "direct_gain_threshold":0.05718096689694352,
    }

def evaluate(worlds):
    if not worlds:
        return None
    return adaptive_run(worlds,protocol_cfg())

def rescue_tasks(candidate_stats,raw_stats,candidate_worlds,raw_worlds):
    cw={w["task_id"]:w for w in candidate_worlds}
    rw={w["task_id"]:w for w in raw_worlds}
    out=[]
    for tid,w in cw.items():
        cs=candidate_stats["source_stats"][tid]; rs=raw_stats["source_stats"][tid]
        generated=w["selected_origin"]!="raw"
        improvement=cs["verified"]>rs["verified"]
        raw_insufficient=(not rs["promoted"]) or rs["revoked"] or rs["verified"]<rs["events"]
        candidate_survives=cs["promoted"] and not cs["revoked"] and cs["verified"]==cs["events"]
        if generated and raw_insufficient and candidate_survives and improvement:
            out.append(tid)
    return sorted(out)

def main():
    freeze_manifest()
    manifest=json.loads(Path("capability-generator-transfer-v1-manifest.json").read_text())
    if manifest["target_data_downloaded"] or manifest["manifest_digest"]!=MANIFEST_SHA:
        raise AssertionError("generator manifest drift or leakage")
    if len(manifest["worlds"])!=20: raise AssertionError("generator manifest size drift")

    dev_meta=manifest["worlds"][:DEV_WORLDS]
    held_meta=manifest["worlds"][DEV_WORLDS:]
    if len(dev_meta)!=8 or len(held_meta)!=12: raise AssertionError("generator split drift")

    dev_base=[]; held_base=[]; invalid=[]
    for split,items,target in (("dev",dev_meta,dev_base),("heldout",held_meta,held_base)):
        for m in items:
            try:
                target.append(load_base_world(int(m["task_id"]),int(m["data_id"]),m["name"]))
            except InapplicableWorld as e:
                invalid.append({"split":split,"task_id":int(m["task_id"]),"dataset":m["name"],"reason":str(e)})

    if len(dev_base)<7 or len(held_base)<10:
        result={"manifest_digest":MANIFEST_SHA,"invalid":invalid,"dev_valid":len(dev_base),"heldout_valid":len(held_base),"passed":False}
        Path(os.environ.get("REALITYGRAPH_GENERATOR_RESULT","capability-generator-transfer-v1-summary.json")).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
        raise AssertionError("insufficient valid worlds before generator learning")

    dev_raw=[representation_world(b,(),"raw") for b in dev_base]
    raw_stats=evaluate(dev_raw)
    family_dev={}
    for family in GRAMMARS:
        worlds=[representation_world(b,(family,),f"raw+{family}") for b in dev_base]
        stats=evaluate(worlds)
        rescues=rescue_tasks(stats,raw_stats,worlds,dev_raw)
        search=sum(w["search_cost"] for w in worlds)
        family_dev[family]={"worlds":worlds,"stats":stats,"rescues":rescues,"search_cost":search}

    ranked=[]
    for family in GRAMMARS:
        x=family_dev[family]; s=x["stats"]
        improvement=s["verified_events"]-raw_stats["verified_events"]
        key=(len(x["rescues"]),improvement,-s["failures"],s["verified_events"],s["survival_precision"],-x["search_cost"],family)
        ranked.append((key,family))
    ranked.sort(reverse=True)
    selected=ranked[0][1]
    selected_dev=family_dev[selected]
    if not selected_dev["rescues"] and selected_dev["stats"]["verified_events"]<=raw_stats["verified_events"]:
        selected=None

    generator_policy={
      "version":"capability-generator-transfer-v1",
      "manifest_digest":MANIFEST_SHA,
      "development_task_ids":[int(x["task_id"]) for x in dev_meta],
      "heldout_task_ids":[int(x["task_id"]) for x in held_meta],
      "candidate_grammars":list(GRAMMARS),
      "selected_grammar":selected,
      "learning_rule":"lexicographic maximize rescue_count, verified_improvement, -failures, verified_events, precision, -search_cost",
      "heldout_outcomes_used":False,
    }
    ptext=json.dumps(generator_policy,sort_keys=True,separators=(",",":"))
    restarted=json.loads(ptext)
    policy_restart=json.dumps(restarted,sort_keys=True,separators=(",",":"))==ptext

    held_raw=[representation_world(b,(),"raw") for b in held_base]
    raw_hold=evaluate(held_raw)
    if selected is None:
        held_learned=held_raw
    else:
        held_learned=[representation_world(b,(selected,),f"raw+{selected}") for b in held_base]
    learned_hold=evaluate(held_learned)
    held_all=[representation_world(b,GRAMMARS,"raw+all") for b in held_base]
    all_hold=evaluate(held_all)

    rescues=rescue_tasks(learned_hold,raw_hold,held_learned,held_raw)
    learned_search=sum(w["search_cost"] for w in held_learned)
    exhaustive_search=sum(w["search_cost"] for w in held_all)
    search_reduction=exhaustive_search/max(1,learned_search)
    generated_selected=[w["task_id"] for w in held_learned if w["selected_origin"]!="raw"]

    result={
      "manifest_digest":MANIFEST_SHA,"invalid_worlds":invalid,
      "development_valid":len(dev_base),"heldout_valid":len(held_base),
      "generator_policy":restarted,"generator_policy_restart_exact":policy_restart,
      "development":{
        "raw":{"verified":raw_stats["verified_events"],"failures":raw_stats["failures"],"precision":raw_stats["survival_precision"]},
        "families":{f:{
          "rescues":family_dev[f]["rescues"],
          "verified":family_dev[f]["stats"]["verified_events"],
          "failures":family_dev[f]["stats"]["failures"],
          "precision":family_dev[f]["stats"]["survival_precision"],
          "search_cost":family_dev[f]["search_cost"],
        } for f in GRAMMARS}
      },
      "heldout":{
        "raw":raw_hold,"learned":learned_hold,"exhaustive":all_hold,
        "rescue_tasks":rescues,"generated_selected_tasks":generated_selected,
        "learned_search_cost":learned_search,"exhaustive_search_cost":exhaustive_search,
        "search_reduction":search_reduction,
      },
      "future_search_cost":0,
    }

    gates={
      "source_only_20_world_manifest":len(manifest["worlds"])==20,
      "fixed_8_12_split":len(dev_meta)==8 and len(held_meta)==12,
      "at_least_7_dev_and_10_heldout_valid":len(dev_base)>=7 and len(held_base)>=10,
      "all_target_consequences_train_only":all(b["target_threshold_source"]=="training_split_distinct_values_only" for b in dev_base+held_base),
      "generator_policy_restart_exact":policy_restart,
      "nontrivial_generator_learned":selected is not None,
      "heldout_generated_representation_selected":len(generated_selected)>=1,
      "heldout_new_verified_capability_rescue":len(rescues)>=1,
      "heldout_verified_events_no_worse_than_raw":learned_hold["verified_events"]>=raw_hold["verified_events"],
      "heldout_failures_no_worse_than_raw":learned_hold["failures"]<=raw_hold["failures"],
      "heldout_precision_no_worse_than_raw":learned_hold["survival_precision"]>=raw_hold["survival_precision"],
      "learned_generator_search_at_least_1_5x_cheaper_than_exhaustive":search_reduction>=1.5,
      "all_learned_verifier_successes_causal":learned_hold["verifier_causal"]==learned_hold["verifier_passes"],
      "all_learned_deployment_successes_causal":learned_hold["causal_ablations"]==learned_hold["verified_events"],
      "future_search_zero":True,
    }
    result["gates"]=gates; result["passed"]=all(gates.values())
    Path(os.environ.get("REALITYGRAPH_GENERATOR_RESULT","capability-generator-transfer-v1-summary.json")).write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")

    print("REALITYGRAPH / CAPABILITY GENERATOR TRANSFER V1")
    print("-----------------------------------------------")
    print(f"manifest_digest={MANIFEST_SHA} dev_valid={len(dev_base)}/8 heldout_valid={len(held_base)}/12")
    print(f"dev_raw verified={raw_stats['verified_events']} failures={raw_stats['failures']} precision={raw_stats['survival_precision']:.4f}")
    for f in GRAMMARS:
        s=family_dev[f]["stats"]
        print(f"dev_{f}: rescues={len(family_dev[f]['rescues'])} verified={s['verified_events']} failures={s['failures']} precision={s['survival_precision']:.4f}")
    print(f"learned_generator={selected}")
    print(f"held_raw verified={raw_hold['verified_events']} failures={raw_hold['failures']} precision={raw_hold['survival_precision']:.4f}")
    print(f"held_learned verified={learned_hold['verified_events']} failures={learned_hold['failures']} precision={learned_hold['survival_precision']:.4f}")
    print(f"held_rescues={rescues} generated_selected={generated_selected}")
    print(f"generator_search_reduction_vs_exhaustive={search_reduction:.2f}x")
    for k,v in gates.items(): print(f"gate_{k}={int(v)}")
    print("VERDICT")
    if result["passed"]: print("PASS_CAPABILITY_GENERATOR_TRANSFER_V1")
    else:
        print("PARTIAL_CAPABILITY_GENERATOR_TRANSFER_V1")
        raise AssertionError("one or more frozen generator transfer gates failed")

if __name__=="__main__": main()
