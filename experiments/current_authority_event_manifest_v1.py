#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def full_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


def make_event(entry: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    repository = str(entry["repository"])
    commit = str(entry["commit"])
    if "/" not in repository or not full_sha(commit):
        raise ValueError("entry requires repository and full lowercase commit SHA")

    run = int(entry["run"])
    artifact = int(entry["artifact"])
    event_spec = dict(entry["event"])
    authority = str(entry["authority_snapshot"])
    verifier = str(entry["verifier_id"])
    status = str(entry["epistemic_status"])

    evidence: dict[str, object] = {
        "schema": "current-authority-source-evidence-v1",
        "campaign": entry["campaign"],
        "epistemic_status": status,
        "repository": repository,
        "commit": commit,
        "run": run,
        "artifact": artifact,
        "artifact_name": entry["artifact_name"],
        "artifact_digest": entry["artifact_digest"],
        "authority_snapshot": authority,
        "verifier_id": verifier,
        "claim_boundary": event_spec["claim_boundary"],
    }
    evidence_text = canonical(evidence)

    kind = str(event_spec["kind"])
    event_id = str(event_spec["event_id"])
    if kind == "capability_admission":
        capability = {
            "capability_id": event_id,
            "input_type": event_spec["input_type"],
            "output_type": event_spec["output_type"],
            "semantics": [[event_spec["input"], event_spec["output"]]],
            "guard_inputs": [event_spec["input"]],
            "certificate_id": event_spec["certificate_id"],
            "dependencies": [],
            "authority_snapshot": authority,
            "verifier_id": verifier,
            "provenance_ids": [
                f"commit:{commit}",
                f"run:{run}",
                f"artifact:{artifact}",
            ],
            "cost": 0,
        }
        payload: dict[str, object] = {
            "capability": capability,
            "oracle": [[event_spec["input"], event_spec["output"]]],
            "support_ids": [],
            "origin": f"current-authority:{entry['campaign']}",
        }
    elif kind == "obstruction_admission":
        candidate = dict(event_spec["candidate"])
        obstruction = {
            "obstruction_id": event_id,
            "input_type": event_spec["input_type"],
            "output_type": event_spec["output_type"],
            "contract": {
                "authority_snapshot": authority,
                "verifier_id": verifier,
            },
            "candidate_fingerprint": digest_text(canonical(candidate)),
            "separating_input": event_spec["separating_input"],
            "expected_output": event_spec["expected_output"],
            "actual_output": event_spec["actual_output"],
            "provenance": f"commit:{commit}/run:{run}/artifact:{artifact}",
        }
        payload = {"obstruction": obstruction}
    else:
        raise ValueError(f"unsupported current-authority event kind: {kind}")

    event: dict[str, object] = {
        "schema": "qckn-flash-external-event-v1",
        "event_id": event_id,
        "event_kind": kind,
        "repository": repository,
        "commit": commit,
        "authority_snapshot": authority,
        "verifier_id": verifier,
        "source_evidence_sha256": digest_text(evidence_text),
        "payload": payload,
        "payload_sha256": digest_text(canonical(payload)),
    }
    return evidence, event


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schema") != "current-authority-event-manifest-v1":
        raise ValueError("unsupported manifest schema")
    policy = manifest.get("policy", {})
    if not policy.get("preserve_historical_events"):
        raise ValueError("v1 requires immutable historical evidence")
    if policy.get("truth_revocations") != []:
        raise ValueError("v1 forbids truth revocation for campaign-view supersession")

    args.out.mkdir(parents=True, exist_ok=True)
    expected_event_ids: list[str] = []
    preserve_event_ids: list[str] = []
    current_views: list[dict[str, object]] = []

    for entry in manifest["entries"]:
        evidence, event = make_event(entry)
        event_id = str(event["event_id"])
        expected_event_ids.append(event_id)

        bundle_dir = args.out / str(entry["campaign"])
        bundle_dir.mkdir(parents=True, exist_ok=True)
        (bundle_dir / "evidence.json").write_text(canonical(evidence), encoding="utf-8")
        (bundle_dir / "event.json").write_text(canonical(event), encoding="utf-8")

        supersedes = list(entry.get("supersedes_views", []))
        for row in supersedes:
            preserve_event_ids.extend(str(value) for value in row.get("preserve_event_ids", []))
        current_views.append(
            {
                "campaign": entry["campaign"],
                "current_event_id": event_id,
                "epistemic_status": entry["epistemic_status"],
                "repository": entry["repository"],
                "commit": entry["commit"],
                "run": entry["run"],
                "artifact": entry["artifact"],
                "supersedes_views": supersedes,
            }
        )

    if len(expected_event_ids) != len(set(expected_event_ids)):
        raise ValueError("manifest event IDs must be unique")

    view = {
        "schema": "current-authority-view-v1",
        "experiment_id": manifest["experiment_id"],
        "supersession_semantics": "view-only; prior warranted event records remain in Flash history",
        "views": current_views,
    }
    audit = {
        "schema": "current-authority-manifest-audit-v1",
        "expected_new_event_ids": sorted(expected_event_ids),
        "preserve_historical_event_ids": sorted(set(preserve_event_ids)),
        "truth_revocations": [],
        "entry_count": len(expected_event_ids),
    }
    (args.out / "current-authority-view.json").write_text(
        json.dumps(view, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out / "manifest-audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print("PASS_CURRENT_AUTHORITY_EVENT_EMISSION_V1")
    print("EVENT_IDS=" + canonical(sorted(expected_event_ids)))
    print("PRESERVE_EVENT_IDS=" + canonical(sorted(set(preserve_event_ids))))


if __name__ == "__main__":
    main()
