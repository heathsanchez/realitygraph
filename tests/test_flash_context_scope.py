#!/usr/bin/env python3
import importlib.util,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("scope",ROOT/"qckn_flash_context_scope.py")
scope=importlib.util.module_from_spec(spec); spec.loader.exec_module(scope)

def event(eid,cid,support=()):
    return {
        "event_id":eid,
        "event_kind":"capability_admission",
        "repository":"metalogiclabs/mathgraph-lean-kernel",
        "payload":{"capability":{"capability_id":cid},"support_ids":list(support)},
    }

state={
  "schema":"qckn-flash-state-bundle-v1",
  "events":[
    event("var","lean:direct-var:v1"),
    event("framed","lean:direct-framed-prune:v1",("lean:direct-var:v1",)),
    event("unfold","lean:ordinary-unfold-neutral:v1",("lean:direct-var:v1",)),
  ],
  "event_manifest":{},
}
ref=json.loads((ROOT/"context/lean_ordinary_unfold_refinement_v1.json").read_text())
view=scope.build_view(state,[ref])
assert "lean:ordinary-unfold-neutral:v1" not in view["contextual_active_capability_ids"]
assert view["contextual_reserve_capability_ids"]==["lean:ordinary-unfold-neutral:v1"]
assert view["invariant_history_retained"]

# If the Framed capability is later revoked, the old lawful capability becomes
# eligible again without rediscovery.
state2=json.loads(json.dumps(state))
state2["events"].append({
    "event_id":"framed-revoke",
    "event_kind":"capability_revocation",
    "repository":"metalogiclabs/mathgraph-lean-kernel",
    "payload":{"capability_id":"lean:direct-framed-prune:v1","reason":"test"},
})
view2=scope.build_view(state2,[ref])
assert "lean:ordinary-unfold-neutral:v1" in view2["contextual_active_capability_ids"]
assert not view2["contextual_reserve_capability_ids"]

print("QCKN_FLASH_CONTEXT_SCOPE_TESTS_PASS")
