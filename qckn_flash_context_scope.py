#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

SCHEMA="qckn-flash-context-view-v1"

def _event_id(row):
    return str(row.get("event_id",""))

def build_view(state:dict, refinements:list[dict]) -> dict:
    if state.get("schema")!="qckn-flash-state-bundle-v1":
        raise ValueError("unsupported state bundle")
    events=state.get("events")
    if not isinstance(events,list):
        raise ValueError("state bundle requires events")

    admissions={}
    revocations=set()
    for row in events:
        if not isinstance(row,dict):
            continue
        kind=row.get("event_kind")
        payload=row.get("payload",{})
        if kind=="capability_admission":
            cap=payload.get("capability",{})
            cid=str(cap.get("capability_id",""))
            if cid:
                admissions[cid]={
                    "event_id":_event_id(row),
                    "support_ids":tuple(str(x) for x in payload.get("support_ids",())),
                    "repository":str(row.get("repository","")),
                }
        elif kind=="capability_revocation":
            cid=str(payload.get("capability_id",""))
            if cid:
                revocations.add(cid)

    def base_valid(cid,seen=None):
        if cid in revocations or cid not in admissions:
            return False
        seen=set() if seen is None else set(seen)
        if cid in seen:
            raise ValueError("support cycle")
        seen.add(cid)
        return all(base_valid(s,seen) for s in admissions[cid]["support_ids"])

    base=sorted(cid for cid in admissions if base_valid(cid))
    base_set=set(base)

    normalized={}
    for r in refinements:
        if r.get("schema")!="qckn-flash-capability-context-refinement-v1":
            raise ValueError("unsupported refinement schema")
        cid=str(r.get("capability_id",""))
        if cid not in admissions:
            raise ValueError(f"refinement targets unknown capability: {cid}")
        old=normalized.get(cid)
        canon=json.dumps(r,sort_keys=True,separators=(",",":"))
        if old is not None and old[0]!=canon:
            raise ValueError(f"conflicting context refinement: {cid}")
        normalized[cid]=(canon,r)

    suppressed={}
    for cid,(_canon,r) in normalized.items():
        blockers=sorted(set(str(x) for x in r.get("suppress_if_present",())))
        present=[x for x in blockers if x in base_set]
        if cid in base_set and present:
            suppressed[cid]={
                "by":present,
                "reason":str(r.get("reason","")),
                "evidence":r.get("evidence",{}),
            }

    active=sorted(base_set-set(suppressed))
    reserve=sorted(suppressed)
    return {
        "schema":SCHEMA,
        "base_active_capability_ids":base,
        "contextual_active_capability_ids":active,
        "contextual_reserve_capability_ids":reserve,
        "suppressed":suppressed,
        "revoked_capability_ids":sorted(revocations),
        "invariant_history_retained":all(cid in admissions for cid in reserve),
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--state",type=Path,required=True)
    p.add_argument("--refinement",type=Path,action="append",default=[])
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    state=json.loads(a.state.read_text())
    refs=[json.loads(x.read_text()) for x in a.refinement]
    view=build_view(state,refs)
    a.out.write_text(json.dumps(view,indent=2,sort_keys=True)+"\n")
    print("QCKN_FLASH_CONTEXT_VIEW_PASS")
    print("ACTIVE="+",".join(view["contextual_active_capability_ids"]))
    print("RESERVE="+",".join(view["contextual_reserve_capability_ids"]))

if __name__=="__main__":
    main()
