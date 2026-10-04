#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path("/tmp/current-authority")
sys.path.insert(0, "frozen-runtime")
from qckn_flash_cross_repo_ingest import restore_state_bundle  # noqa: E402


def context():
    manifest=json.loads((ROOT/"manifest.json").read_text())
    audit=json.loads((ROOT/"bundles/manifest-audit.json").read_text())
    view=json.loads((ROOT/"bundles/current-authority-view.json").read_text())
    cycle=json.loads((ROOT/"live/cycle.json").read_text())
    previous_text=(ROOT/"previous-state-bundle.json").read_text()
    current_text=(ROOT/"live/state-bundle.json").read_text()
    previous_summary,_=restore_state_bundle(previous_text)
    current_summary,_=restore_state_bundle(current_text)
    expected=set(audit["expected_new_event_ids"])
    preserved=set(audit["preserve_historical_event_ids"])
    previous_ids=set(previous_summary["event_ids"])
    current_ids=set(current_summary["event_ids"])
    return {
        "manifest":manifest,"audit":audit,"view":view,"cycle":cycle,
        "previous_text":previous_text,"current_text":current_text,
        "previous_summary":previous_summary,"current_summary":current_summary,
        "expected":expected,"preserved":preserved,
        "previous_ids":previous_ids,"current_ids":current_ids,
    }


def check_events(c):
    assert len(c["expected"])==3, c["expected"]
    assert set(c["cycle"]["new_event_ids"])==c["expected"], c["cycle"]
    assert not set(c["cycle"]["unchanged_event_ids"]), c["cycle"]
    print("PASS_CURRENT_AUTHORITY_EVENT_DELTA_V1")


def check_history(c):
    assert c["previous_ids"] <= c["current_ids"], {
        "missing":sorted(c["previous_ids"]-c["current_ids"])
    }
    assert c["preserved"] <= c["previous_ids"], {
        "declared_preserve_not_in_baseline":sorted(c["preserved"]-c["previous_ids"])
    }
    assert c["preserved"] <= c["current_ids"], {
        "declared_preserve_missing_after_reclose":sorted(c["preserved"]-c["current_ids"])
    }
    assert c["current_ids"] == c["previous_ids"] | c["expected"], {
        "unexpected":sorted(c["current_ids"]-(c["previous_ids"]|c["expected"])),
        "missing":sorted((c["previous_ids"]|c["expected"])-c["current_ids"]),
    }
    print("PASS_IMMUTABLE_HISTORY_RETENTION_V1")


def check_deltas(c):
    p=c["previous_summary"]; q=c["current_summary"]
    assert q["external_events"] == p["external_events"] + 3, (p["external_events"],q["external_events"])
    assert q["active_capabilities"] == p["active_capabilities"] + 2, (p["active_capabilities"],q["active_capabilities"])
    assert q["obstructions"] == p["obstructions"] + 1, (p["obstructions"],q["obstructions"])
    print("PASS_CURRENT_AUTHORITY_CLOSURE_DELTAS_V1")


def check_views(c):
    p=c["previous_summary"]; q=c["current_summary"]
    assert q["revoked_capability_ids"] == p["revoked_capability_ids"], {
        "previous":p["revoked_capability_ids"],"current":q["revoked_capability_ids"]
    }
    assert c["manifest"]["policy"]["truth_revocations"] == []
    assert c["audit"]["truth_revocations"] == []
    assert c["view"]["supersession_semantics"].startswith("view-only")
    assert {v["current_event_id"] for v in c["view"]["views"]} == c["expected"]
    print("PASS_VIEW_ONLY_SUPERSESSION_V1")


def check_reload(c):
    first,_=restore_state_bundle(c["current_text"])
    second,_=restore_state_bundle(c["current_text"])
    assert second["event_ids"] == first["event_ids"]
    assert second["active_capability_ids"] == first["active_capability_ids"]
    assert second["obstruction_ids"] == first["obstruction_ids"]
    print("PASS_EXACT_FLASH_RELOAD_V1")


def write_qualification(c):
    p=c["previous_summary"]; q=c["current_summary"]
    qualification={
        "schema":"current-authority-event-manifest-qualification-v1",
        "baseline_run":c["manifest"]["baseline"]["run"],
        "baseline_artifact":c["manifest"]["baseline"]["artifact"],
        "previous_external_events":p["external_events"],
        "current_external_events":q["external_events"],
        "new_event_ids":sorted(c["expected"]),
        "preserved_historical_event_ids":sorted(c["preserved"]),
        "active_capability_delta":q["active_capabilities"]-p["active_capabilities"],
        "obstruction_delta":q["obstructions"]-p["obstructions"],
        "prior_revoked_capability_ids":p["revoked_capability_ids"],
        "current_revoked_capability_ids":q["revoked_capability_ids"],
        "truth_revocations":[],
        "reload_exact":True,
        "result":"PASS_CURRENT_AUTHORITY_EVENT_MANIFEST_V1",
    }
    (ROOT/"qualification.json").write_text(json.dumps(qualification,indent=2,sort_keys=True)+"\n")
    print("PASS_CURRENT_AUTHORITY_EVENT_MANIFEST_V1")
    print(json.dumps(qualification,sort_keys=True))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("check",choices=["events","history","deltas","views","reload","write"])
    args=parser.parse_args()
    c=context()
    {
        "events":check_events,
        "history":check_history,
        "deltas":check_deltas,
        "views":check_views,
        "reload":check_reload,
        "write":write_qualification,
    }[args.check](c)


if __name__=="__main__":
    main()
