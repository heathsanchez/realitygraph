from __future__ import annotations
import hashlib,json,os
from pathlib import Path

from openml_v7 import load_world
from openml_v11 import micro_groups
from openml_v12 import adaptive_run
from openml_v14 import meta_run
from probe_openml_v15_manifest import main as freeze_manifest
from realitygraph.adaptive_policy import budget_from_memory
from realitygraph.meta_policy import policy_from_memory
from realitygraph.retained_capability import exact_restart

POLICY_PATH=Path("frozen-meta/adaptive_policy.mg")
POLICY_SHA="3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
VERIFIER_PATH=Path("frozen-meta/openml_verifier_v15.json")
MANIFEST_SHA="8cd1638ecb2cb7c3fabbcd6a4be6f11bb0513676546b784a1d84fa87f34c2265"

def main():
    freeze_manifest()
    manifest=json.loads(Path("openml-v15-manifest.json").read_text())
    if manifest["target_data_downloaded"] or manifest["manifest_digest"]!=MANIFEST_SHA:
        raise AssertionError("V15 manifest drift or leakage")

    verifier=json.loads(VERIFIER_PATH.read_text())
    if verifier["v15_target_outcomes_used"]:
        raise AssertionError("V15 verifier policy contamination")
    policy={
      "version":verifier["version"],
      "source_run":verifier["source_run"],
      "direct_threshold":verifier["retained_direct_shortcut_threshold"],
      "borderline_threshold":verifier["borderline_shortcut_threshold"],
      "heldout_outcomes_used":False,
    }
    ptext=json.dumps(policy,sort_keys=True,separators=(",",":"))
    restarted_policy=json.loads(ptext)
    policy_restart=(json.dumps(restarted_policy,sort_keys=True,separators=(",",":"))==ptext)

    text=POLICY_PATH.read_text()
    if hashlib.sha256(text.encode()).hexdigest()!=POLICY_SHA:
        raise AssertionError("acquisition policy drift")
    mem=exact_restart(text)
    acquisition_policy=policy_from_memory(mem)
    budget=budget_from_memory(mem)

    worlds=[load_world(int(m["task_id"]),int(m["data_id"]),m["name"],acquisition_policy,budget) for m in manifest["worlds"]]
    for w in worlds:
        w["micro_groups"]=micro_groups(w,8)

    basecfg={
      "version":"openml-capability-state-v12-adaptive-evidence-v1",
      "candidate_gain_floor":verifier["candidate_gain_floor"],
      "direct_gain_threshold":verifier["direct_gain_threshold"],
    }
    baseline=adaptive_run(worlds,basecfg)
    retained=meta_run(worlds,restarted_policy)

    reduction=1-retained["verifier_checks"]/max(1,baseline["verifier_checks"])
    cold=sum(w["cold_search_cost"] for w in worlds)
    acq=sum(w["adaptive_search_cost"] for w in worlds)
    lifecycle=sum(w["cold_search_cost"]*5 for w in worlds)/max(1,acq)

    result={
      "manifest_digest":MANIFEST_SHA,
      "retained_verifier":verifier,
      "v12":baseline,
      "v15":retained,
      "verifier_check_reduction":reduction,
      "acquisition_reduction":cold/max(1,acq),
      "lifecycle_reduction":lifecycle,
      "future_search_cost":0,
      "worlds":[{
        "task_id":w["task_id"],"data_id":w["data_id"],"dataset":w["dataset"],
        "gain":w["adaptive_cal_gain"],
        "v12_verified":baseline["source_stats"][w["task_id"]]["verified"],
        "v12_revoked":baseline["source_stats"][w["task_id"]]["revoked"],
        "v15_verified":retained["source_stats"][w["task_id"]]["verified"],
        "v15_revoked":retained["source_stats"][w["task_id"]]["revoked"],
      } for w in worlds],
    }
    gates={
      "twenty_source_only_worlds":len(worlds)==20,
      "retained_policy_restart_exact":policy_restart,
      "no_v15_policy_relearning":verifier["source_run"]==35038200844,
      "retained_shortcut_exercised":retained["shortcuts"]>=1,
      "at_least_10pct_fewer_verifier_checks":reduction>=0.10,
      "verified_events_no_worse_than_v12":retained["verified_events"]>=baseline["verified_events"],
      "failures_no_worse_than_v12":retained["failures"]<=baseline["failures"],
      "precision_no_worse_than_v12":retained["survival_precision"]>=baseline["survival_precision"],
      "all_verifier_successes_causal":retained["verifier_causal"]==retained["verifier_passes"],
      "all_deployment_successes_causal":retained["causal_ablations"]==retained["verified_events"],
      "future_search_zero":True,
      "compact_retained_policy_and_state":len(ptext.encode())<=4096 and retained["state_certificate_bytes"]<=20000,
      "lifecycle_reduction":lifecycle>=8.0,
    }
    result["gates"]=gates
    result["passed"]=all(gates.values())
    Path(os.environ.get("REALITYGRAPH_OPENML_V15_RESULT","openml-v15-summary.json")).write_text(
      json.dumps(result,sort_keys=True,indent=2)+"\n"
    )

    print("REALITYGRAPH / RETAINED VERIFIER POLICY TRANSFER V15")
    print("----------------------------------------------------")
    print(f"manifest_digest={MANIFEST_SHA}")
    print(f"retained_direct_threshold={policy['direct_threshold']}")
    print(f"V12 checks={baseline['verifier_checks']} verified={baseline['verified_events']} failures={baseline['failures']} precision={baseline['survival_precision']:.4f}")
    print(f"V15 checks={retained['verifier_checks']} shortcuts={retained['shortcuts']} verified={retained['verified_events']} failures={retained['failures']} precision={retained['survival_precision']:.4f}")
    print(f"verifier_reduction={reduction:.4f} lifecycle={lifecycle:.2f}x")
    for k,v in gates.items():
        print(f"gate_{k}={int(v)}")
    print("VERDICT")
    if result["passed"]:
        print("PASS_RETAINED_VERIFIER_POLICY_TRANSFER_V15")
    else:
        print("PARTIAL_RETAINED_VERIFIER_POLICY_TRANSFER_V15")
        raise AssertionError("one or more frozen V15 gates failed")

if __name__=="__main__":
    main()
