#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from realitygraph.flash import ExternalEventEnvelope


LANES = {
    "v26": {
        "marker": "ENDOGENOUS_CLOSURE_GENESIS_V26=BOUNDED_POSITIVE",
        "capability_prefix": "lean:endogenous-closure-generator:v26",
        "input_type": "lean-developmental-residual",
        "output_type": "measurement-closure-generator",
        "semantics": [["initial-generator-closure-insufficient", "generated-measurement-closure"]],
        "verifier_id": "lean-v26-heldout-std-cedar-byte-equality",
    },
    "v38": {
        "marker": "DECISION=BLIND_INTERFACE_GENESIS_TRANSFER",
        "capability_prefix": "lean:blind-shared-interface:v38",
        "input_type": "lean-interface-residual",
        "output_type": "retained-shared-interface",
        "semantics": [["producer-consumer-rediscovery", "shared-interface"]],
        "verifier_id": "lean-v38-heldout-callgrind-and-byte-equality",
    },
    "v40_recursive": {
        "marker": "V40_DECISION=RECURSIVE_NATIVE_INTERFACE_GENESIS_TRANSFER",
        "capability_prefix": "lean:recursive-interface:v40",
        "input_type": "lean-post-interface-residual",
        "output_type": "second-retained-interface",
        "semantics": [["post-first-interface-rediscovery", "second-shared-interface"]],
        "verifier_id": "lean-v40-recursive-heldout-callgrind-and-byte-equality",
    },
    "v40_memory": {
        "marker": "DECISION=EARNED_MEMORY_POLICY_TRANSFER",
        "capability_prefix": "lean:earned-memory-policy:v40",
        "input_type": "lean-retained-interface",
        "output_type": "earned-memory-deployment-policy",
        "semantics": [["semantically-admissible-interface", "earned-deployment-policy"]],
        "verifier_id": "lean-v40-earned-memory-heldout-callgrind-and-byte-equality",
    },
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--harvest-root", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    emitted = []
    for lane, spec in LANES.items():
        lane_dir = args.harvest_root / lane
        result_path = lane_dir / "result.txt"
        meta_path = lane_dir / "meta.json"
        if not result_path.is_file() or not meta_path.is_file():
            raise SystemExit(f"missing harvested lane files: {lane}")

        result_bytes = result_path.read_bytes()
        result_text = result_bytes.decode("utf-8", errors="replace")
        if spec["marker"] not in result_text:
            raise SystemExit(f"missing expected scientific marker for {lane}")

        meta = json.loads(meta_path.read_text())
        run_id = int(meta["run_id"])
        artifact_id = int(meta["artifact_id"])
        head_sha = str(meta["head_sha"])
        branch = str(meta["branch"])
        artifact_name = str(meta["artifact_name"])

        authority = f"metalogiclabs/mathgraph-lean-kernel@{head_sha}:{branch}"
        capability_id = f"{spec['capability_prefix']}:run-{run_id}"
        certificate_id = (
            f"run:{run_id}/artifact:{artifact_id}/"
            f"artifact-name:{artifact_name}/marker:{spec['marker']}"
        )

        capability = {
            "capability_id": capability_id,
            "input_type": spec["input_type"],
            "output_type": spec["output_type"],
            "semantics": spec["semantics"],
            "guard_inputs": [spec["semantics"][0][0]],
            "certificate_id": certificate_id,
            "dependencies": [],
            "authority_snapshot": authority,
            "verifier_id": spec["verifier_id"],
            "provenance_ids": [
                f"branch:{branch}",
                f"commit:{head_sha}",
                f"run:{run_id}",
                f"artifact:{artifact_id}",
            ],
            "cost": 0,
        }

        event_id = f"{spec['capability_prefix']}:run-{run_id}"
        envelope = ExternalEventEnvelope.capability(
            event_id=event_id,
            repository="metalogiclabs/mathgraph-lean-kernel",
            commit=head_sha,
            authority_snapshot=authority,
            verifier_id=spec["verifier_id"],
            source_evidence=result_bytes,
            capability=capability,
            oracle=spec["semantics"],
            support_ids=[],
            origin="verified-lean-developmental-capital",
        )

        out_dir = args.out / lane
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "evidence.json").write_bytes(result_bytes)
        (out_dir / "event.json").write_text(envelope.to_text(), encoding="utf-8")
        (out_dir / "harvest-meta.json").write_text(
            json.dumps(
                {
                    **meta,
                    "lane": lane,
                    "event_id": event_id,
                    "capability_id": capability_id,
                    "authority_snapshot": authority,
                    "verifier_id": spec["verifier_id"],
                    "certificate_id": certificate_id,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        emitted.append(event_id)

    print(json.dumps({"emitted_event_ids": emitted}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
