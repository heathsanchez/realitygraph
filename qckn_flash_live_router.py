#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from realitygraph.flash import ExternalEventEnvelope
from qckn_flash_cross_repo_ingest import (
    _build_runtime,
    _load_bundle,
    _state_bundle_text,
    _summary,
    restore_state_bundle,
)


def _loaded_from_state_text(
    text: str,
) -> list[tuple[ExternalEventEnvelope, object]]:
    restore_state_bundle(text)
    payload=json.loads(text)
    loaded=[]
    for row in payload["events"]:
        event_text=json.dumps(row,sort_keys=True,separators=(",",":"))
        envelope=ExternalEventEnvelope.from_text(event_text)
        loaded.append((envelope,envelope.to_runtime_event()))
    return loaded


def update_live_state(
    previous_state_text: str | None,
    current_bundle_paths: Iterable[Path],
) -> dict[str, object]:
    previous_loaded = (
        _loaded_from_state_text(previous_state_text)
        if previous_state_text is not None
        else []
    )
    current_loaded=[_load_bundle(Path(path)) for path in current_bundle_paths]

    if not previous_loaded and not current_loaded:
        raise ValueError("live router requires prior state or current producer events")

    previous_by_id={
        event.event_id:(envelope,event)
        for envelope,event in previous_loaded
    }
    current_by_id={}
    for envelope,event in current_loaded:
        old=current_by_id.get(event.event_id)
        if old is not None and old[0].to_text()!=envelope.to_text():
            raise ValueError(f"event identity conflict in current producer set: {event.event_id}")
        current_by_id[event.event_id]=(envelope,event)

    new_event_ids=[]
    unchanged_event_ids=[]
    for event_id,(envelope,event) in sorted(current_by_id.items()):
        old=previous_by_id.get(event_id)
        if old is None:
            new_event_ids.append(event_id)
            continue
        if old[0].to_text()!=envelope.to_text():
            raise ValueError(f"event identity conflict: {event_id}")
        unchanged_event_ids.append(event_id)

    retained_past_event_ids=sorted(set(previous_by_id)-set(current_by_id))
    merged=dict(previous_by_id)
    merged.update(current_by_id)
    loaded=[merged[event_id] for event_id in sorted(merged)]

    closure,runtime,_ordered=_build_runtime(loaded)
    summary=_summary(loaded,closure,runtime)
    state_text=_state_bundle_text(loaded,runtime)

    return {
        "schema":"qckn-flash-live-router-cycle-v1",
        "new_event_ids":new_event_ids,
        "unchanged_event_ids":unchanged_event_ids,
        "retained_past_event_ids":retained_past_event_ids,
        "summary":summary,
        "state_bundle_text":state_text,
    }


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--previous",type=Path)
    parser.add_argument("--bundle",action="append",type=Path,default=[])
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()

    previous=(
        args.previous.read_text(encoding="utf-8")
        if args.previous is not None and args.previous.exists()
        else None
    )
    result=update_live_state(previous,args.bundle)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"cycle.json").write_text(
        json.dumps(
            {k:v for k,v in result.items() if k!="state_bundle_text"},
            indent=2,
            sort_keys=True,
        )+"\n",
        encoding="utf-8",
    )
    (args.out/"state-bundle.json").write_text(
        str(result["state_bundle_text"]),
        encoding="utf-8",
    )
    print("PASS_QCKN_FLASH_LIVE_ROUTER_V1")
    print("NEW_EVENTS="+str(len(result["new_event_ids"])))
    print("TOTAL_EVENTS="+str(result["summary"]["external_events"]))


if __name__=="__main__":
    main()
