from __future__ import annotations
import json
from pathlib import Path

from capability_generator_transfer_v2 import (
    MANIFEST_SHA, load_base_world, representation_world, evaluate
)
from probe_capability_generator_transfer_v2_manifest import main as freeze_manifest

def certs(stats):
    return {int(c["task_id"]):c for c in stats["certificates"]}

def main():
    freeze_manifest()
    manifest=json.loads(Path("capability-generator-transfer-v2-manifest.json").read_text())
    if manifest["manifest_digest"]!=MANIFEST_SHA or manifest["target_data_downloaded"]:
        raise AssertionError("V2 pilot manifest drift")

    held=manifest["worlds"][8:]
    bases=[]
    invalid=[]
    for m in held:
        try:
            bases.append(load_base_world(int(m["task_id"]),int(m["data_id"]),m["name"]))
        except Exception as e:
            invalid.append({"task_id":int(m["task_id"]),"dataset":m["name"],"reason":str(e)})

    raw=[representation_world(b,(),"raw") for b in bases]
    gen=[representation_world(b,("absdiff",),"raw+absdiff") for b in bases]
    rs=evaluate(raw); gs=evaluate(gen)
    rc=certs(rs); gc=certs(gs)
    rw={w["task_id"]:w for w in raw}; gw={w["task_id"]:w for w in gen}

    rows=[]
    for tid in sorted(rw):
        rcert=rc[tid]; gcert=gc[tid]
        mixed=(any(rcert["evidence"]) and not all(rcert["evidence"])) if rcert["evidence"] else False
        generated=gw[tid]["selected_origin"]!="raw"
        invoke=mixed
        rawstat=rs["source_stats"][tid]; genstat=gs["source_stats"][tid]
        chosen=genstat if invoke and generated else rawstat
        rows.append({
          "task_id":tid,
          "dataset":rw[tid]["dataset"],
          "raw_gain":rw[tid]["adaptive_cal_gain"],
          "generated_gain":gw[tid]["adaptive_cal_gain"],
          "gain_delta":gw[tid]["adaptive_cal_gain"]-rw[tid]["adaptive_cal_gain"],
          "generated_origin":gw[tid]["selected_origin"],
          "raw_band":rcert["band"],"raw_evidence":rcert["evidence"],"raw_state":rcert["state"],
          "generated_band":gcert["band"],"generated_evidence":gcert["evidence"],"generated_state":gcert["state"],
          "controller_mixed_raw_evidence":mixed,
          "controller_invokes_generated":bool(invoke and generated),
          "raw_verified":rawstat["verified"],"raw_revoked":rawstat["revoked"],
          "generated_verified":genstat["verified"],"generated_revoked":genstat["revoked"],
          "chosen_verified":chosen["verified"],"chosen_revoked":chosen["revoked"],
        })

    invoked=[x for x in rows if x["controller_invokes_generated"]]
    chosen_verified=sum(x["chosen_verified"] for x in rows)
    chosen_failures=sum(1 for x in rows if x["chosen_revoked"])
    chosen_promoted=sum(1 for x in rows if (
        (gc[x["task_id"]]["state"] in ("ACTIVE","REVOKED") if x["controller_invokes_generated"]
         else rc[x["task_id"]]["state"] in ("ACTIVE","REVOKED"))
    ))
    chosen_survivors=sum(1 for x in rows if x["chosen_verified"]==5 and not x["chosen_revoked"])
    precision=chosen_survivors/max(1,chosen_promoted)
    result={
      "status":"EXPLORATORY_PILOT_ONLY",
      "source_run":35052246708,
      "controller":{
        "rule":"invoke absdiff iff raw verifier evidence contains at least one pass and at least one fail; otherwise retain raw",
        "uses_deployment_outcomes_for_invocation":False
      },
      "invalid":invalid,
      "raw":{"verified":rs["verified_events"],"failures":rs["failures"],"precision":rs["survival_precision"]},
      "unconditional_absdiff":{"verified":gs["verified_events"],"failures":gs["failures"],"precision":gs["survival_precision"]},
      "controlled":{"invocations":len(invoked),"tasks":[x["task_id"] for x in invoked],
                    "verified":chosen_verified,"failures":chosen_failures,"precision":precision,
                    "promoted":chosen_promoted,"survivors":chosen_survivors},
      "rows":rows
    }
    Path("capability-generator-controller-pilot.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("GENERATOR INVOCATION CONTROLLER / V2 EXPLORATORY PILOT")
    print("------------------------------------------------------")
    print("controller=mixed_raw_verifier_evidence")
    print(f"raw verified={rs['verified_events']} failures={rs['failures']} precision={rs['survival_precision']:.4f}")
    print(f"unconditional verified={gs['verified_events']} failures={gs['failures']} precision={gs['survival_precision']:.4f}")
    print(f"controlled invocations={len(invoked)} tasks={[x['task_id'] for x in invoked]} verified={chosen_verified} failures={chosen_failures} precision={precision:.4f}")
    for x in rows:
        print(json.dumps(x,sort_keys=True))

if __name__=="__main__":
    main()
