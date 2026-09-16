from __future__ import annotations
import json
from pathlib import Path

from capability_generator_transfer_v2 import load_base_world,representation_world,evaluate,GRAMMARS
from openml_regression_transfer_v2 import InapplicableWorld
from probe_capability_generator_controller_v3_manifest import main as freeze_manifest

MANIFEST_SHA="991cd0f3f83f1b3961a81ceaf8c04625f3ad874f7f37378b19f85758d9576a54"

def certmap(stats): return {int(c["task_id"]):c for c in stats["certificates"]}
def mixed(c):
    e=list(c.get("evidence") or [])
    return bool(e) and any(e) and not all(e)

def main():
    freeze_manifest()
    manifest=json.loads(Path("capability-generator-controller-transfer-v3-manifest.json").read_text())
    if manifest["manifest_digest"]!=MANIFEST_SHA or manifest["target_data_downloaded"]:
        raise AssertionError("V3 pilot manifest drift")

    bases=[]; invalid=[]
    for m in manifest["worlds"]:
        try: bases.append(load_base_world(int(m["task_id"]),int(m["data_id"]),m["name"]))
        except InapplicableWorld as e: invalid.append({"task_id":int(m["task_id"]),"dataset":m["name"],"reason":str(e)})

    raw=[representation_world(b,(),"raw") for b in bases]
    allg=[representation_world(b,GRAMMARS,"raw+all") for b in bases]
    rs=evaluate(raw); es=evaluate(allg)
    rc=certmap(rs); rw={w["task_id"]:w for w in raw}; ew={w["task_id"]:w for w in allg}

    attempts=[w["task_id"] for w in raw if (not rs["source_stats"][w["task_id"]]["promoted"]) and mixed(rc[w["task_id"]])]
    effective=[tid for tid in attempts if ew[tid]["selected_origin"]!="raw"]
    controlled=[ew[w["task_id"]] if w["task_id"] in effective else w for w in raw]
    cs=evaluate(controlled)

    rescues=[]; harms=[]
    for tid in effective:
        r=rs["source_stats"][tid]; c=cs["source_stats"][tid]
        if ((not r["promoted"]) or r["revoked"] or r["verified"]<r["events"]) and c["promoted"] and not c["revoked"] and c["verified"]==c["events"] and c["verified"]>r["verified"]:
            rescues.append(tid)
        if c["revoked"] and not r["revoked"]: harms.append(tid)

    raw_search=sum(w["search_cost"] for w in raw)
    exhaustive_search=sum(w["search_cost"] for w in allg)
    incremental={w["task_id"]:max(0,ew[w["task_id"]]["search_cost"]-w["search_cost"]) for w in raw}
    controlled_search=raw_search+sum(incremental[t] for t in attempts)

    rows=[]
    for tid in attempts:
        rows.append({
          "task_id":tid,"dataset":rw[tid]["dataset"],
          "raw_gain":rw[tid]["adaptive_cal_gain"],
          "portfolio_gain":ew[tid]["adaptive_cal_gain"],
          "portfolio_origin":ew[tid]["selected_origin"],
          "raw_evidence":rc[tid]["evidence"],"raw_state":rc[tid]["state"],
          "raw_verified":rs["source_stats"][tid]["verified"],"raw_revoked":rs["source_stats"][tid]["revoked"],
          "portfolio_verified":es["source_stats"][tid]["verified"],"portfolio_revoked":es["source_stats"][tid]["revoked"],
          "controlled_verified":cs["source_stats"][tid]["verified"],"controlled_revoked":cs["source_stats"][tid]["revoked"],
        })

    result={
      "status":"EXPLORATORY_PILOT_ONLY","source_run":35052946216,
      "controller":"open grammar portfolio only when raw is not promoted and verifier evidence is mixed",
      "portfolio":list(GRAMMARS),
      "invalid":invalid,"attempts":attempts,"effective":effective,"rescues":rescues,"harms":harms,
      "raw":{"verified":rs["verified_events"],"failures":rs["failures"],"precision":rs["survival_precision"]},
      "controlled":{"verified":cs["verified_events"],"failures":cs["failures"],"precision":cs["survival_precision"]},
      "exhaustive":{"verified":es["verified_events"],"failures":es["failures"],"precision":es["survival_precision"]},
      "search":{"raw":raw_search,"controlled":controlled_search,"exhaustive":exhaustive_search,
                "exhaustive_over_controlled":exhaustive_search/max(1,controlled_search)},
      "rows":rows,
    }
    Path("capability-generator-portfolio-pilot.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("REPAIR-ONLY GENERATOR PORTFOLIO / V3 EXPLORATORY PILOT")
    print("------------------------------------------------------")
    print(f"attempts={attempts} effective={effective} rescues={rescues} harms={harms}")
    print(f"raw verified={rs['verified_events']} failures={rs['failures']} precision={rs['survival_precision']:.4f}")
    print(f"controlled verified={cs['verified_events']} failures={cs['failures']} precision={cs['survival_precision']:.4f}")
    print(f"exhaustive verified={es['verified_events']} failures={es['failures']} precision={es['survival_precision']:.4f}")
    print(f"search raw={raw_search} controlled={controlled_search} exhaustive={exhaustive_search} ratio={exhaustive_search/max(1,controlled_search):.2f}x")
    for x in rows: print(json.dumps(x,sort_keys=True))

if __name__=="__main__": main()
