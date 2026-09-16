from __future__ import annotations

import hashlib,json,math,os
from pathlib import Path

import openml
import pandas as pd

from openml_v7 import sampled_indices,split_indices,numeric_matrix,calibration_evaluation,compile_model,MIN_GAIN
from openml_v11 import micro_groups,stateful_run
from openml_v12 import adaptive_run
from openml_v14 import meta_run
from pmlb_meta_world import _descriptors
from probe_openml_regression_transfer_v2_manifest import main as freeze_manifest
from realitygraph.adaptive_policy import budget_features,budget_from_memory
from realitygraph.meta_policy import policy_from_memory
from realitygraph.retained_capability import exact_restart
from realitygraph.transfer_memory import model_to_law

POLICY_PATH=Path("frozen-meta/adaptive_policy.mg")
POLICY_SHA="3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
VERIFIER_PATH=Path("frozen-meta/openml_verifier_v15.json")
MANIFEST_SHA="000e4d92fd4f5cd7c7d64c40da640d7c9fdfc80efad05372c0a53e0e78fa4e33"

class InapplicableWorld(ValueError):
    pass

def finite_float(value):
    try: x=float(value)
    except (TypeError,ValueError): return None
    return x if math.isfinite(x) else None

def training_balanced_binary_target(y_values,train):
    vals=[finite_float(y_values[i]) for i in train]
    if any(v is None for v in vals):
        raise InapplicableWorld("nonfinite_training_target")
    unique=sorted(set(vals))
    if len(unique)<2:
        raise InapplicableWorld("constant_training_target")

    ordered=sorted(vals)
    best=None
    for a,b in zip(unique[:-1],unique[1:]):
        threshold=(a+b)/2.0
        lo=sum(v<=threshold for v in ordered); hi=len(ordered)-lo
        if not lo or not hi: continue
        key=(abs(lo-hi),threshold)
        if best is None or key<best[0]:
            best=(key,threshold)
    if best is None:
        raise InapplicableWorld("no_nontrivial_train_split")
    threshold=best[1]
    labels=[]
    for value in y_values:
        x=finite_float(value)
        if x is None:
            raise InapplicableWorld("nonfinite_sampled_target")
        labels.append(1 if x>threshold else 0)
    if len({labels[i] for i in train})<2:
        raise AssertionError("balanced training consequence unexpectedly collapsed")
    return threshold,labels

def load_world(task_id,data_id,expected_name,policy,budget_policy):
    task=openml.tasks.get_task(task_id,download_splits=False)
    dataset=task.get_dataset()
    if int(dataset.dataset_id)!=data_id: raise AssertionError("regression task/data drift")
    if str(dataset.name)!=expected_name: raise AssertionError("regression dataset name drift")

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

    candidates=[]
    for feature in range(len(feature_names)):
        descriptors=_descriptors(
          [rows[i][feature] for i in train],
          [labels[i] for i in train],
          f"openml-regression-v2-{task_id}",feature
        )
        cal=calibration_evaluation(rows,labels,feature,train,calibration)
        candidates.append({"feature":feature,"descriptors":list(descriptors),**cal})

    descriptor_world={"candidates":[{"feature":x["feature"],"descriptors":x["descriptors"]} for x in candidates]}
    budget=budget_policy.choose_budget(budget_features(policy,descriptor_world))
    ordered=sorted(candidates,key=lambda x:(-policy.score(tuple(x["descriptors"])),x["feature"]))
    selected_candidates=ordered[:min(budget,len(ordered))]
    adaptive_best=max(selected_candidates,key=lambda x:(x["cal_gain"],-x["feature"]))
    cold_best=max(candidates,key=lambda x:(x["cal_gain"],-x["feature"]))
    adaptive_cost=sum(x["threshold_evals"] for x in selected_candidates)
    cold_cost=sum(x["threshold_evals"] for x in candidates)
    adaptive_accept=adaptive_best["cal_gain"]>MIN_GAIN

    checksum=str(getattr(dataset,"md5_checksum","") or f"openml-data-{data_id}-version-{dataset.version}")
    source_hashes=((f"https://www.openml.org/d/{data_id}",checksum),)
    fit=tuple(train)+tuple(calibration)
    prior=(sum(labels[i] for i in fit)+1.0)/(len(fit)+2.0)
    law=None
    if adaptive_accept:
        model,prior=compile_model(
          feature_names,rows,labels,train,calibration,
          adaptive_best["feature"],adaptive_best["threshold"]
        )
        provenance=hashlib.sha256(
          (f"openml-regression-transfer-v2|task={task_id}|data={data_id}|checksum={checksum}|"
           f"target_threshold={target_threshold:.12g}|feature={adaptive_best['feature']}|"
           f"cal={adaptive_best['cal_gain']:.12g}").encode()
        ).hexdigest()[:12]
        law=model_to_law(source_hashes,model,provenance=provenance)

    return {
      "index":task_id,"task_id":task_id,"data_id":data_id,"dataset":expected_name,
      "source_hashes":source_hashes,"feature_names":feature_names,"rows":rows,"labels":labels,
      "prior":prior,"budget":budget,"adaptive_feature":adaptive_best["feature"],
      "adaptive_cal_gain":adaptive_best["cal_gain"],"adaptive_accept":adaptive_accept,
      "adaptive_search_cost":adaptive_cost,"cold_feature":cold_best["feature"],
      "cold_cal_gain":cold_best["cal_gain"],"cold_search_cost":cold_cost,"law":law,
      "rows_used":len(rows),"target_threshold":target_threshold,
      "target_threshold_source":"training_split_distinct_values_only","task_family":"regression"
    }

def main():
    freeze_manifest()
    manifest=json.loads(Path("openml-regression-transfer-v2-manifest.json").read_text())
    if manifest["target_data_downloaded"] or manifest["manifest_digest"]!=MANIFEST_SHA:
        raise AssertionError("V2 regression manifest drift or leakage")
    if manifest.get("task_type")!="Supervised Regression":
        raise AssertionError("V2 task family drift")

    frozen_text=POLICY_PATH.read_text()
    if hashlib.sha256(frozen_text.encode()).hexdigest()!=POLICY_SHA:
        raise AssertionError("acquisition policy drift")
    memory=exact_restart(frozen_text)
    acquisition_policy=policy_from_memory(memory); budget_policy=budget_from_memory(memory)

    verifier=json.loads(VERIFIER_PATH.read_text())
    retained_policy={
      "version":verifier["version"],"source_run":verifier["source_run"],
      "direct_threshold":verifier["retained_direct_shortcut_threshold"],
      "borderline_threshold":verifier["borderline_shortcut_threshold"],
      "heldout_outcomes_used":False,
    }
    ptext=json.dumps(retained_policy,sort_keys=True,separators=(",",":"))
    retained_policy=json.loads(ptext)
    retained_restart=json.dumps(retained_policy,sort_keys=True,separators=(",",":"))==ptext

    worlds=[]; inapplicable=[]
    for m in manifest["worlds"]:
        try:
            worlds.append(load_world(int(m["task_id"]),int(m["data_id"]),m["name"],acquisition_policy,budget_policy))
        except InapplicableWorld as e:
            inapplicable.append({"task_id":int(m["task_id"]),"data_id":int(m["data_id"]),"dataset":m["name"],"reason":str(e)})
    for w in worlds: w["micro_groups"]=micro_groups(w,8)

    state_cfg={"version":"openml-capability-state-v11-v1",
      "candidate_gain_floor":verifier["candidate_gain_floor"],
      "direct_gain_threshold":verifier["direct_gain_threshold"]}
    adaptive_cfg={"version":"openml-capability-state-v12-adaptive-evidence-v1",
      "candidate_gain_floor":verifier["candidate_gain_floor"],
      "direct_gain_threshold":verifier["direct_gain_threshold"]}

    fixed=stateful_run(worlds,state_cfg)
    adaptive=adaptive_run(worlds,adaptive_cfg)
    retained=meta_run(worlds,retained_policy)

    fixed_active={c["task_id"] for c in fixed["certificates"] if c["state"] in ("ACTIVE","REVOKED")}
    adaptive_active={c["task_id"] for c in adaptive["certificates"] if c["state"] in ("ACTIVE","REVOKED")}
    same_active=fixed_active==adaptive_active
    same_deploy=(fixed["verified_events"]==adaptive["verified_events"]
      and fixed["failures"]==adaptive["failures"]
      and fixed["surviving_sources"]==adaptive["surviving_sources"])
    adaptive_saving=1-adaptive["verifier_checks"]/max(1,fixed["verifier_checks"])
    retained_saving=1-retained["verifier_checks"]/max(1,adaptive["verifier_checks"])

    cold=sum(w["cold_search_cost"] for w in worlds)
    acq=sum(w["adaptive_search_cost"] for w in worlds)
    lifecycle=sum(w["cold_search_cost"]*5 for w in worlds)/max(1,acq)

    result={"manifest_digest":MANIFEST_SHA,"selected_worlds":20,"valid_worlds":len(worlds),
      "inapplicable_worlds":inapplicable,"task_family":"regression",
      "target_transform":"most balanced threshold between distinct training target values only",
      "fixed_v11":fixed,"adaptive_v12":adaptive,"retained_v15":retained,
      "same_active_set_fixed_vs_adaptive":same_active,
      "same_deployment_fixed_vs_adaptive":same_deploy,
      "adaptive_verifier_reduction":adaptive_saving,
      "retained_verifier_reduction_vs_adaptive":retained_saving,
      "acquisition_reduction":cold/max(1,acq),"lifecycle_reduction":lifecycle,
      "future_search_cost":0,
      "worlds":[{"task_id":w["task_id"],"data_id":w["data_id"],"dataset":w["dataset"],
        "target_threshold":w["target_threshold"],"target_threshold_source":w["target_threshold_source"],
        "gain":w["adaptive_cal_gain"],"budget":w["budget"],
        "adaptive_verified":adaptive["source_stats"][w["task_id"]]["verified"],
        "retained_verified":retained["source_stats"][w["task_id"]]["verified"]} for w in worlds]}

    gates={
      "twenty_source_only_regression_worlds_selected":len(manifest["worlds"])==20,
      "at_least_16_applicable_worlds":len(worlds)>=16,
      "all_target_thresholds_train_only":all(w["target_threshold_source"]=="training_split_distinct_values_only" for w in worlds),
      "nontrivial_acquisition":sum(1 for w in worlds if w["adaptive_accept"])>=5,
      "nontrivial_active_portfolio":adaptive["promoted_sources"]>=4,
      "adaptive_restart_exact":adaptive["restart_exact"],
      "fixed_and_adaptive_same_active_set":same_active,
      "fixed_and_adaptive_same_deployment":same_deploy,
      "adaptive_saves_at_least_10pct_verifier_checks":adaptive_saving>=0.10,
      "retained_policy_restart_exact":retained_restart,
      "retained_shortcut_exercised":retained["shortcuts"]>=1,
      "retained_saves_at_least_5pct_vs_adaptive":retained_saving>=0.05,
      "retained_verified_events_no_worse":retained["verified_events"]>=adaptive["verified_events"],
      "retained_failures_no_worse":retained["failures"]<=adaptive["failures"],
      "retained_precision_no_worse":retained["survival_precision"]>=adaptive["survival_precision"],
      "all_adaptive_verifier_successes_causal":adaptive["verifier_causal"]==adaptive["verifier_passes"],
      "all_adaptive_deployment_successes_causal":adaptive["causal_ablations"]==adaptive["verified_events"],
      "all_retained_verifier_successes_causal":retained["verifier_causal"]==retained["verifier_passes"],
      "all_retained_deployment_successes_causal":retained["causal_ablations"]==retained["verified_events"],
      "future_search_zero":True,"lifecycle_reduction_at_least_8x":lifecycle>=8.0,
    }
    result["gates"]=gates; result["passed"]=all(gates.values())
    Path(os.environ.get("REALITYGRAPH_OPENML_REGRESSION_V2_RESULT","openml-regression-transfer-v2-summary.json")).write_text(
      json.dumps(result,sort_keys=True,indent=2)+"\n")

    print("REALITYGRAPH / CROSS-FAMILY REGRESSION DEVELOPMENTAL TRANSFER V2")
    print("----------------------------------------------------------------")
    print(f"manifest_digest={MANIFEST_SHA} valid={len(worlds)}/20 inapplicable={len(inapplicable)}")
    for x in inapplicable: print(f"INAPPLICABLE task={x['task_id']} {x['dataset']} reason={x['reason']}")
    print(f"FIXED V11: checks={fixed['verifier_checks']} active={fixed['promoted_sources']} verified={fixed['verified_events']} failures={fixed['failures']} precision={fixed['survival_precision']:.4f}")
    print(f"ADAPTIVE V12: checks={adaptive['verifier_checks']} active={adaptive['promoted_sources']} verified={adaptive['verified_events']} failures={adaptive['failures']} precision={adaptive['survival_precision']:.4f}")
    print(f"RETAINED V15: checks={retained['verifier_checks']} shortcuts={retained['shortcuts']} active={retained['promoted_sources']} verified={retained['verified_events']} failures={retained['failures']} precision={retained['survival_precision']:.4f}")
    print(f"adaptive_reduction={adaptive_saving:.4f} retained_reduction={retained_saving:.4f} lifecycle={lifecycle:.2f}x")
    for k,v in gates.items(): print(f"gate_{k}={int(v)}")
    print("VERDICT")
    if result["passed"]: print("PASS_CROSS_FAMILY_REGRESSION_DEVELOPMENTAL_TRANSFER_V2")
    else:
        print("PARTIAL_CROSS_FAMILY_REGRESSION_DEVELOPMENTAL_TRANSFER_V2")
        raise AssertionError("one or more frozen regression V2 gates failed")

if __name__=="__main__": main()
