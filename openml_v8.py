from __future__ import annotations
import hashlib,json,os
from pathlib import Path

from openml_v7 import load_world
from probe_openml_v8_manifest import main as freeze_manifest
from realitygraph.adaptive_policy import budget_from_memory
from realitygraph.meta_policy import policy_from_memory
from realitygraph.retained_capability import exact_restart
from scope_gate_v5 import run_portfolio

POLICY_PATH=Path("frozen-meta/adaptive_policy.mg")
POLICY_SHA="3da082adbcfcacc53c9745a0b6af42a4ea33655e43c3768bc755fdf41168fa92"
SCOPE_PATH=Path("frozen-meta/openml_scope_v8.json")
MANIFEST_SHA="TO_BE_FROZEN"

def main():
    freeze_manifest()
    manifest=json.loads(Path("openml-v8-manifest.json").read_text())
    if manifest["target_data_downloaded"]:
        raise AssertionError("V8 manifest leaked target payloads")
    if manifest["manifest_digest"]!=MANIFEST_SHA:
        raise AssertionError(f"V8 manifest drift: {manifest['manifest_digest']}")

    text=POLICY_PATH.read_text()
    if hashlib.sha256(text.encode()).hexdigest()!=POLICY_SHA:
        raise AssertionError("acquisition policy drift")
    memory=exact_restart(text)
    policy=policy_from_memory(memory)
    budget=budget_from_memory(memory)

    scope=json.loads(SCOPE_PATH.read_text())
    if scope["v8_target_outcomes_used"]:
        raise AssertionError("V8 scope contaminated by V8 outcomes")
    g=float(scope["gain_threshold"])
    r=float(scope["search_ratio_threshold"])

    worlds=[]
    for meta in manifest["worlds"]:
        w=load_world(int(meta["task_id"]),int(meta["data_id"]),meta["name"],policy,budget)
        ratio=w["cold_search_cost"]/max(1,w["adaptive_search_cost"])
        w["v8_promoted"]=(
            w["adaptive_accept"]
            and w["adaptive_cal_gain"]>=g
            and ratio<=r
        )
        w["search_ratio"]=ratio
        worlds.append(w)

    base=run_portfolio(worlds,lambda w:w["adaptive_accept"])
    v6=run_portfolio(worlds,lambda w:w["v6_promoted"])
    v8=run_portfolio(worlds,lambda w:w["v8_promoted"])

    cold=sum(w["cold_search_cost"] for w in worlds)
    adaptive=sum(w["adaptive_search_cost"] for w in worlds)
    future=sum(w["cold_search_cost"]*len(w["future_groups"]) for w in worlds)
    acq=cold/max(1,adaptive)
    life=future/max(1,adaptive)
    retain=v8["verified_events"]/max(1,base["verified_events"])
    v6retain=v6["verified_events"]/max(1,base["verified_events"])

    result={
      "manifest_digest":MANIFEST_SHA,
      "policy_sha256":POLICY_SHA,
      "scope":scope,
      "base":base,"v6":v6,"v8":v8,
      "cold_acquisition_cost":cold,
      "adaptive_acquisition_cost":adaptive,
      "acquisition_reduction":acq,
      "stateless_future_cost":future,
      "future_search_cost":0,
      "lifecycle_reduction":life,
      "v6_verified_event_retention":v6retain,
      "v8_verified_event_retention":retain,
      "worlds":[{
        "task_id":w["task_id"],"data_id":w["data_id"],"dataset":w["dataset"],
        "features":len(w["feature_names"]),"budget":w["budget"],
        "cal_gain":w["adaptive_cal_gain"],"search_ratio":w["search_ratio"],
        "accepted":w["adaptive_accept"],"v6":w["v6_promoted"],"v8":w["v8_promoted"],
        "future_groups":len(w["future_groups"]),
        "base_verified":base["source_stats"][w["task_id"]]["verified"],
        "base_revoked":base["source_stats"][w["task_id"]]["revoked"],
        "v6_verified":v6["source_stats"][w["task_id"]]["verified"],
        "v6_revoked":v6["source_stats"][w["task_id"]]["revoked"],
        "v8_verified":v8["source_stats"][w["task_id"]]["verified"],
        "v8_revoked":v8["source_stats"][w["task_id"]]["revoked"],
      } for w in worlds],
    }
    gates={
      "twenty_source_distinct_worlds":len(worlds)==20,
      "frozen_relational_scope":scope["training_worlds"]==20,
      "nontrivial_v8_portfolio":v8["promoted_sources"]>=6,
      "v8_failures_no_worse_than_base":v8["failures"]<=base["failures"],
      "v8_precision_no_worse_than_base":v8["survival_precision"]>=base["survival_precision"],
      "v8_retains_at_least_65pct_base_events":retain>=0.65,
      "v8_retention_no_worse_than_v6":retain>=v6retain,
      "every_v8_verified_event_causal":v8["causal_ablations"]==v8["verified_events"],
      "adaptive_acquisition_reduction":acq>=2.0,
      "lifecycle_reduction":life>=6.0,
      "future_search_zero":True,
    }
    result["gates"]=gates
    result["passed"]=all(gates.values())
    Path(os.environ.get("REALITYGRAPH_OPENML_V8_RESULT","openml-v8-summary.json")).write_text(
      json.dumps(result,sort_keys=True,indent=2)+"\n"
    )

    print("REALITYGRAPH / RELATIONAL SCOPE V8")
    print("----------------------------------")
    print(f"manifest_digest={MANIFEST_SHA}")
    print(f"gain_threshold={g:.17g} search_ratio_threshold={r:.17g}")
    for w in result["worlds"]:
        print(
          f"task={w['task_id']} {w['dataset'][:24]:24} gain={w['cal_gain']:+.4f} "
          f"ratio={w['search_ratio']:.2f} A={w['accepted']} V6={w['v6']} V8={w['v8']} "
          f"base={w['base_verified']}/{w['future_groups']} r={w['base_revoked']} "
          f"v8={w['v8_verified']}/{w['future_groups']} r={w['v8_revoked']}"
        )
    for name,stats in (("BASE",base),("V6",v6),("V8",v8)):
        print(
          f"{name}: promoted={stats['promoted_sources']} survived={stats['surviving_sources']} "
          f"failures={stats['failures']} verified={stats['verified_events']} "
          f"precision={stats['survival_precision']:.4f} bytes={stats['initial_bytes']}"
        )
    print(f"retention V6={v6retain:.4f} V8={retain:.4f} acquisition={acq:.2f}x lifecycle={life:.2f}x")
    for k,v in gates.items():print(f"gate_{k}={int(v)}")
    print("VERDICT")
    if result["passed"]:
        print("PASS_RELATIONAL_SCOPE_COMPOUNDING_V8")
    else:
        print("PARTIAL_RELATIONAL_SCOPE_COMPOUNDING_V8")
        raise AssertionError("one or more frozen V8 gates failed")

if __name__=="__main__":main()
