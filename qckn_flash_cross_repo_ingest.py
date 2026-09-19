#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from realitygraph.flash import (
    CapabilityAdmissionEvent,
    CapabilityRevocationEvent,
    ExternalEventEnvelope,
    FlashClosure,
    FlashContract,
    FlashEventRuntime,
    LiveObligation,
    ObstructionAdmissionEvent,
    ObstructionRevocationEvent,
)


def _load_bundle(path: Path):
    event_path = path / "event.json"
    evidence_path = path / "evidence.json"
    if not event_path.is_file() or not evidence_path.is_file():
        raise ValueError(f"bundle missing event/evidence files: {path}")
    envelope = ExternalEventEnvelope.from_text(event_path.read_text(encoding="utf-8"))
    evidence = evidence_path.read_bytes()
    envelope.verify_source_bytes(evidence)
    return envelope, envelope.to_runtime_event()


def _obligation_for(envelope: ExternalEventEnvelope, event):
    oid = "external:" + event.event_id
    if isinstance(event, CapabilityAdmissionEvent):
        cap = event.capability
        oracle = tuple((str(a), str(b)) for a, b in event.oracle)
        transport = tuple((a, a) for a, _ in oracle)
        return LiveObligation(
            obligation_id=oid,
            input_type=cap.input_type,
            source_input_type=cap.input_type,
            output_type=cap.output_type,
            oracle=oracle,
            transport_to_source=transport,
            contract=FlashContract(cap.authority_snapshot, cap.verifier_id),
            domain=envelope.repository,
        )
    if isinstance(event, ObstructionAdmissionEvent):
        obs = event.obstruction
        key = str(obs.separating_input)
        return LiveObligation(
            obligation_id=oid,
            input_type=obs.input_type,
            source_input_type=obs.input_type,
            output_type=obs.output_type,
            oracle=((key, str(obs.expected_output)),),
            transport_to_source=((key, key),),
            contract=obs.contract,
            candidate_fingerprints=(
                obs.candidate_fingerprint,
                "control:" + event.event_id,
            ),
            domain=envelope.repository,
        )
    if isinstance(event, (CapabilityRevocationEvent, ObstructionRevocationEvent)):
        return None
    raise TypeError(f"unsupported external runtime event: {type(event).__name__}")


def _event_priority(event: object) -> tuple[int, str]:
    if isinstance(event, (CapabilityAdmissionEvent, ObstructionAdmissionEvent)):
        return (0, event.event_id)
    if isinstance(event, (CapabilityRevocationEvent, ObstructionRevocationEvent)):
        return (1, event.event_id)
    raise TypeError(f"unsupported external runtime event: {type(event).__name__}")


def _build_runtime(
    loaded: list[tuple[ExternalEventEnvelope, object]],
):
    event_ids = [event.event_id for _, event in loaded]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("duplicate external event identity")

    obligations = tuple(
        obligation
        for envelope, event in loaded
        if (obligation := _obligation_for(envelope, event)) is not None
    )
    closure = FlashClosure(obligations, kernel="qckn-flash-cross-repo-ingestion-v1")
    runtime = FlashEventRuntime(closure)

    ordered = sorted(loaded, key=lambda row: _event_priority(row[1]))
    for _envelope, event in ordered:
        runtime.apply(event)
    return closure, runtime, ordered


def _summary(
    loaded: list[tuple[ExternalEventEnvelope, object]],
    closure: FlashClosure,
    runtime: FlashEventRuntime,
    *,
    replay_added_events: int = 0,
) -> dict[str, object]:
    pruned = sum(len(row.pruned_fingerprints) for row in closure.obligations.values())
    repositories = sorted({envelope.repository for envelope, _event in loaded})
    return {
        "schema": "qckn-flash-cross-repo-ingestion-v1",
        "external_events": len(loaded),
        "repositories": repositories,
        "event_ids": list(runtime.event_ids()),
        "active_capabilities": len(closure.active_capability_ids()),
        "active_capability_ids": list(closure.active_capability_ids()),
        "revoked_capability_ids": sorted(closure.revoked_ids),
        "obstructions": len(closure.obstructions),
        "obstruction_ids": sorted(closure.obstructions),
        "discharged_obligations": len(closure.discharged_obligation_ids()),
        "discharged_obligation_ids": list(closure.discharged_obligation_ids()),
        "open_obligation_ids": list(closure.open_obligation_ids()),
        "pruned_candidate_occurrences": pruned,
        "event_count": closure.event_count,
        "closure_count": closure.closure_count,
        "replay_added_events": replay_added_events,
        "event_manifest": json.loads(runtime.event_manifest_text()),
        "source_commits": {
            envelope.repository: envelope.commit
            for envelope, _event in sorted(loaded, key=lambda row: row[0].repository)
        },
    }


def _state_bundle_text(
    loaded: list[tuple[ExternalEventEnvelope, object]],
    runtime: FlashEventRuntime,
) -> str:
    payload = {
        "schema": "qckn-flash-state-bundle-v1",
        "events": [
            json.loads(envelope.to_text())
            for envelope, _event in sorted(loaded, key=lambda row: row[1].event_id)
        ],
        "event_manifest": json.loads(runtime.event_manifest_text()),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def ingest_bundles(
    bundle_paths: Iterable[Path],
) -> tuple[dict[str, object], dict[str, object], str]:
    loaded = [_load_bundle(Path(path)) for path in bundle_paths]
    if not loaded:
        raise ValueError("at least one external bundle is required")

    closure, runtime, ordered = _build_runtime(loaded)

    manifest_text = runtime.event_manifest_text()
    manifest = json.loads(manifest_text)

    before_replay = closure.event_count
    restarted = FlashEventRuntime.from_event_manifest(closure, manifest_text)
    for _envelope, event in ordered:
        delta = restarted.apply(event)
        if delta.iterations != 0 or delta.changed_obligations:
            raise AssertionError("restart replay mutated shared Flash state")
    replay_added = closure.event_count - before_replay

    summary = _summary(
        loaded,
        closure,
        runtime,
        replay_added_events=replay_added,
    )
    state_text = _state_bundle_text(loaded, runtime)
    return summary, manifest, state_text


def restore_state_bundle(
    text: str,
) -> tuple[dict[str, object], FlashEventRuntime]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid Flash state bundle") from exc
    if payload.get("schema") != "qckn-flash-state-bundle-v1":
        raise ValueError("unsupported Flash state bundle schema")
    rows = payload.get("events")
    manifest = payload.get("event_manifest")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Flash state bundle requires events")
    if not isinstance(manifest, dict):
        raise ValueError("Flash state bundle requires event manifest")
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if canonical != text:
        raise ValueError("noncanonical Flash state bundle")

    loaded: list[tuple[ExternalEventEnvelope, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid Flash state bundle event")
        event_text = json.dumps(row, sort_keys=True, separators=(",", ":"))
        envelope = ExternalEventEnvelope.from_text(event_text)
        loaded.append((envelope, envelope.to_runtime_event()))

    closure, runtime, ordered = _build_runtime(loaded)
    actual_manifest = json.loads(runtime.event_manifest_text())
    if actual_manifest != manifest:
        raise ValueError("Flash state bundle manifest mismatch")

    summary = _summary(loaded, closure, runtime)
    summary["cold_restart_replayed_events"] = len(ordered)
    return summary, runtime

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", action="append", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    summary, manifest, state_text = ingest_bundles(args.bundle)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.out / "event-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    (args.out / "state-bundle.json").write_text(
        state_text,
        encoding="utf-8",
    )
    print("PASS_QCKN_FLASH_CROSS_REPO_INGESTION_V1")
    print("EVENTS=" + str(summary["external_events"]))
    print("CAPABILITIES=" + str(summary["active_capabilities"]))
    print("OBSTRUCTIONS=" + str(summary["obstructions"]))
    print("REPLAY_ADDED_EVENTS=" + str(summary["replay_added_events"]))


if __name__ == "__main__":
    main()
