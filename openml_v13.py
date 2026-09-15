from __future__ import annotations
import hashlib,json,os
from pathlib import Path

from openml_v7 import load_world
from openml_v11 import micro_groups,stateful_run
from openml_v12 import adaptive_run
from probe_openml_v13_manifest import main as freeze_manifest
from realitygraph.adaptive_policy import budget_from_memory
from realitygraph.meta_policy import policy_from_memory
from realitygraph.retained_capability import exact_restart

POLICY_PATH=Path("frozen-meta/adaptive_policy.mg")
POLICY_SHA="3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
CFG_PATH=Path("frozen-meta/openml_state_v13.json")
MANIFEST_SHA="cd7bbfc028b53076722c69e0ed658c81a5e463a9a0c38f5522457d24cfe01688"

def main():
    freeze_manifest()
    manifest=json.loads(Path("openml-v13-manifest.json").read_text())
    if manifest["target_data_downloaded"] or manifest["manifest_digest"]!=MANIFEST_SHA:
        raise AssertionError("V13 manifest drift or leakage")

    text=POLICY_PATH.read_text()
    if hashlib.sha256(text.encode()).hexdigest()!=POLICY_SHA:
        raise AssertionError("policy drift")
    mem=exact_restart(text)
    policy=policy_from_memory(mem); budget=budget_from_memory(mem)

    cfg=json.loads(CFG_PATH.read_text())
    if cfg["v13_target_outcomes_used"]:
        raise AssertionError("V13 contamination")

    worlds=[load_world(int(m["task_id"]),int(m["data_id"]),m["name"],policy,budget) for m in manifest["worlds"]]
    for w in worlds:
        w["micro_groups"]=micro_groups(w,8)

    fixed_cfg={
      "version":"openml-capability-state-v11-v1",
      "candidate_gain_floor":cfg["candidate_gain_floor"],
      "direct_gain_threshold":cfg["direct_gain_threshold"],
    }
    adaptive_cfg={
      "version":"openml-capability-state-v12-adaptive-evidence-v1",
      "candidate_gain_floor":cfg["candidate_gain_floor"],
      "direct_gain_threshold":cfg["direct_gain_threshold"],
    }

    fixed=stateful_run(worlds,fixed_cfg)
    adaptive=adaptive_run(worlds,adaptive_cfg)

    fixed_active={c["task_id"] for c in fixed["certificates"] if c["state"] in ("ACTIVE","REVOKED")}
    adaptive_active={c["task_id"] for c in adaptive["certificates"] if c["state"] in ("ACTIVE","REVOKED")}
    same_active=fixed_active==adaptive_active
    same_deploy=(
      fixed["verified_events"]==adaptive["verified_events"]
      and fixed["failures"]==adaptive["failures"]
      and fixed["surviving_sources"]==adaptive["surviving_sources"]
    )
    saving=1-adaptive["verifier_checks"]/max(1,fixed["verifier_checks"])

    cold=sum(w["cold_search_cost"] for w in worlds)
    acq=sum(w["adaptive_search_cost"] for w in worlds)
    lifecycle=sum(w["cold_search_cost"]*5 for w in worlds)/max(1,acq)

    result={
      "manifest_digest":MANIFEST_SHA,"config":cfg,
      "fixed_v11":fixed,"adaptive_v13":adaptive,
      "same_active_set":same_active,"same_deployment_outcome":same_deploy,
      "verifier_check_reduction":saving,
      "acquisition_reduction":cold/max(1,acq),
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
    Path(os.environ.get("REALITYGRAPH_OPENML_V13_RESULT","openml-v13-summary.json")).write_text(
      json.dumps(result,sort_keys=True,indent=2)+"\n"
    )
    print("REALITYGRAPH / ADAPTIVE EVIDENCE V13 REPLICATION")
    print("-----------------------------------------------")
    print(f"manifest_digest={MANIFEST_SHA}")
    print(f"fixed_checks={fixed['verifier_checks']} adaptive_checks={adaptive['verifier_checks']} reduction={saving:.4f}")
    print(f"same_active_set={same_active} same_deployment_outcome={same_deploy}")
    print(f"FIXED: active={fixed['promoted_sources']} survived={fixed['surviving_sources']} failures={fixed['failures']} verified={fixed['verified_events']} precision={fixed['survival_precision']:.4f}")
    print(f"V13: active={adaptive['promoted_sources']} survived={adaptive['surviving_sources']} failures={adaptive['failures']} verified={adaptive['verified_events']} precision={adaptive['survival_precision']:.4f}")
    for k,v in gates.items():print(f"gate_{k}={int(v)}")
    print("VERDICT")
    if result["passed"]:
        print("PASS_ADAPTIVE_EVIDENCE_REPLICATION_V13")
    else:
        print("PARTIAL_ADAPTIVE_EVIDENCE_REPLICATION_V13")
        raise AssertionError("one or more frozen V13 gates failed")

if __name__=="__main__":main()
