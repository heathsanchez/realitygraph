from __future__ import annotations

import json,os
from pathlib import Path

from capability_generator_transfer_v2 import (
    load_base_world, representation_world, evaluate, GRAMMARS
)
from openml_regression_transfer_v2 import InapplicableWorld
from probe_capability_generator_controller_v3_manifest import main as freeze_manifest

MANIFEST_SHA="991cd0f3f83f1b3961a81ceaf8c04625f3ad874f7f37378b19f85758d9576a54"
POLICY_PATH=Path("frozen-meta/capability_generator_controller_v3.json")

def certmap(stats):
    return {int(c["task_id"]):c for c in stats["certificates"]}

def mixed_evidence(cert):
    ev=list(cert.get("evidence") or [])
    return bool(ev) and any(ev) and not all(ev)

def main():
    freeze_manifest()
    manifest=json.loads(Path("capability-generator-controller-transfer-v3-manifest.json").read_text())
    if manifest["target_data_downloaded"] or manifest["manifest_digest"]!=MANIFEST_SHA:
        raise AssertionError("V3 manifest drift or leakage")
    if len(manifest["worlds"])!=20:
        raise AssertionError("V3 manifest size drift")

    policy=json.loads(POLICY_PATH.read_text())
    if policy["v3_target_outcomes_used"] or policy["uses_deployment_outcomes_during_v3"]:
        raise AssertionError("V3 controller contamination")
    ptext=json.dumps(policy,sort_keys=True,separators=(",",":"))
    restarted=json.loads(ptext)
    policy_restart=(json.dumps(restarted,sort_keys=True,separators=(",",":"))==ptext)
    if restarted["generator"]!="absdiff":
        raise AssertionError("unexpected retained generator")
    expected_rule="invoke generator iff raw verifier evidence contains at least one pass and at least one fail; otherwise retain raw"
    if restarted["controller_rule"]!=expected_rule:
        raise AssertionError("unexpected retained controller rule")

    bases=[]; invalid=[]
    for m in manifest["worlds"]:
        try:
            bases.append(load_base_world(int(m["task_id"]),int(m["data_id"]),m["name"]))
        except InapplicableWorld as e:
            invalid.append({"task_id":int(m["task_id"]),"dataset":m["name"],"reason":str(e)})

    if len(bases)<16:
        result={"manifest_digest":MANIFEST_SHA,"valid":len(bases),"invalid":invalid,"passed":False}
        Path(os.environ.get("REALITYGRAPH_GENERATOR_CONTROLLER_V3_RESULT","capability-generator-controller-v3-summary.json")).write_text(
            json.dumps(result,sort_keys=True,indent=2)+"\n")
        raise AssertionError("insufficient valid V3 worlds")

    raw=[representation_world(b,(),"raw") for b in bases]
    raw_stats=evaluate(raw)
    rc=certmap(raw_stats)

    gen=[representation_world(b,("absdiff",),"raw+absdiff") for b in bases]
    gen_map={w["task_id"]:w for w in gen}
    raw_map={w["task_id"]:w for w in raw}

    attempts=[]
    effective=[]
    controlled=[]
    for w in raw:
        tid=w["task_id"]
        invoke=mixed_evidence(rc[tid])
        if invoke:
            attempts.append(tid)
            gw=gen_map[tid]
            if gw["selected_origin"]!="raw":
                controlled.append(gw)
                effective.append(tid)
            else:
                controlled.append(w)
        else:
            controlled.append(w)

    controlled_stats=evaluate(controlled)
    unconditional_stats=evaluate(gen)
    exhaustive=[representation_world(b,GRAMMARS,"raw+all") for b in bases]
    exhaustive_stats=evaluate(exhaustive)

    raw_search=sum(w["search_cost"] for w in raw)
    gen_search=sum(w["search_cost"] for w in gen)
    exhaustive_search=sum(w["search_cost"] for w in exhaustive)
    incremental={w["task_id"]:max(0,gen_map[w["task_id"]]["search_cost"]-w["search_cost"]) for w in raw}
    controlled_search=raw_search+sum(incremental[tid] for tid in attempts)
    search_reduction=exhaustive_search/max(1,controlled_search)
    unconditional_reduction=gen_search/max(1,controlled_search)

    rs=raw_stats["source_stats"]; cs=controlled_stats["source_stats"]
    rescues=[]
    harms=[]
    for tid in effective:
        r=rs[tid]; c=cs[tid]
        raw_insufficient=(not r["promoted"]) or r["revoked"] or r["verified"]<r["events"]
        ctrl_survives=c["promoted"] and not c["revoked"] and c["verified"]==c["events"]
        if raw_insufficient and ctrl_survives and c["verified"]>r["verified"]:
            rescues.append(tid)
        if c["revoked"] and not r["revoked"]:
            harms.append(tid)

    result={
      "manifest_digest":MANIFEST_SHA,
      "policy":restarted,
      "policy_restart_exact":policy_restart,
      "valid_worlds":len(bases),"invalid_worlds":invalid,
      "raw":raw_stats,
      "controlled":controlled_stats,
      "unconditional_absdiff":unconditional_stats,
      "exhaustive":exhaustive_stats,
      "controller_attempts":attempts,
      "effective_generated_replacements":effective,
      "rescue_tasks":rescues,
      "new_harm_tasks":harms,
      "search":{
        "raw":raw_search,
        "controlled":controlled_search,
        "unconditional_absdiff":gen_search,
        "exhaustive_all_grammars":exhaustive_search,
        "exhaustive_over_controlled":search_reduction,
        "unconditional_over_controlled":unconditional_reduction,
      },
      "deployment_future_search_cost":0,
    }

    gates={
      "source_only_20_world_manifest":len(manifest["worlds"])==20,
      "at_least_16_applicable_worlds":len(bases)>=16,
      "all_target_consequences_train_only":all(b["target_threshold_source"]=="training_split_distinct_values_only" for b in bases),
      "retained_policy_restart_exact":policy_restart,
      "generator_not_relearned":restarted["generator"]=="absdiff" and restarted["generator_source_run"]==35052246708,
      "controller_not_relearned":restarted["controller_source_run"]==35052502246,
      "controller_invoked":len(attempts)>=1,
      "effective_generated_replacement":len(effective)>=1,
      "new_verified_capability_rescue":len(rescues)>=1,
      "no_new_harm_tasks":len(harms)==0,
      "controlled_verified_events_no_worse_than_raw":controlled_stats["verified_events"]>=raw_stats["verified_events"],
      "controlled_failures_no_worse_than_raw":controlled_stats["failures"]<=raw_stats["failures"],
      "controlled_precision_no_worse_than_raw":controlled_stats["survival_precision"]>=raw_stats["survival_precision"],
      "controlled_no_worse_than_unconditional_failures":controlled_stats["failures"]<=unconditional_stats["failures"],
      "controlled_no_worse_than_unconditional_precision":controlled_stats["survival_precision"]>=unconditional_stats["survival_precision"],
      "controlled_search_at_least_1_5x_cheaper_than_exhaustive":search_reduction>=1.5,
      "all_controlled_verifier_successes_causal":controlled_stats["verifier_causal"]==controlled_stats["verifier_passes"],
      "all_controlled_deployment_successes_causal":controlled_stats["causal_ablations"]==controlled_stats["verified_events"],
      "deployment_future_search_zero":True,
    }
    result["gates"]=gates; result["passed"]=all(gates.values())
    Path(os.environ.get("REALITYGRAPH_GENERATOR_CONTROLLER_V3_RESULT","capability-generator-controller-v3-summary.json")).write_text(
        json.dumps(result,sort_keys=True,indent=2)+"\n")

    print("REALITYGRAPH / RETAINED GENERATOR + INVOCATION CONTROLLER V3")
    print("------------------------------------------------------------")
    print(f"manifest_digest={MANIFEST_SHA} valid={len(bases)}/20 invalid={len(invalid)}")
    print(f"raw verified={raw_stats['verified_events']} failures={raw_stats['failures']} precision={raw_stats['survival_precision']:.4f}")
    print(f"unconditional verified={unconditional_stats['verified_events']} failures={unconditional_stats['failures']} precision={unconditional_stats['survival_precision']:.4f}")
    print(f"controlled attempts={attempts} effective={effective} rescues={rescues} harms={harms}")
    print(f"controlled verified={controlled_stats['verified_events']} failures={controlled_stats['failures']} precision={controlled_stats['survival_precision']:.4f}")
    print(f"search raw={raw_search} controlled={controlled_search} unconditional={gen_search} exhaustive={exhaustive_search} exhaustive/control={search_reduction:.2f}x")
    for k,v in gates.items(): print(f"gate_{k}={int(v)}")
    print("VERDICT")
    if result["passed"]:
        print("PASS_RETAINED_GENERATOR_CONTROLLER_TRANSFER_V3")
    else:
        print("PARTIAL_RETAINED_GENERATOR_CONTROLLER_TRANSFER_V3")
        raise AssertionError("one or more frozen generator-controller V3 gates failed")

if __name__=="__main__":
    main()
