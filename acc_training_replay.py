from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from realitygraph.acc import replay, sequence_hash, state_hash, state_observables

EXPECTED_MOVE_SPEC_VERSION = "ac-r2-v1"
STANDARD_TARGET = ((1,), (2,))


def _state_from_json(value: list[list[int]]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if len(value) != 2:
        raise ValueError("ordinary AC state must have exactly two relators")
    return tuple(tuple(int(x) for x in word) for word in value)  # type: ignore[return-value]


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def trajectory_record(instance: dict[str, Any]) -> dict[str, Any]:
    start = _state_from_json(instance["initial_relators"])
    target = _state_from_json(instance["target_relators"])
    moves = tuple(int(m) for m in instance["moves"])
    trace = replay(start, moves)
    accepted = trace[-1] == target
    states = [
        {
            "index": index,
            "state": _jsonable(state),
            "state_hash": state_hash(state),
            "observables": _jsonable(state_observables(state)),
        }
        for index, state in enumerate(trace)
    ]
    return {
        "training_id": instance["training_id"],
        "family": instance.get("family"),
        "n": instance.get("n"),
        "w_vector": list(instance.get("w_vector", [])),
        "source_hash": state_hash(start),
        "sequence_hash": sequence_hash(moves),
        "move_count": len(moves),
        "moves": list(moves),
        "accepted": accepted,
        "target": _jsonable(target),
        "states": states,
    }


def replay_training_document(document: dict[str, Any]) -> dict[str, Any]:
    version = document.get("move_spec_version")
    if version != EXPECTED_MOVE_SPEC_VERSION:
        raise ValueError(
            f"unexpected move spec {version!r}; expected {EXPECTED_MOVE_SPEC_VERSION!r}"
        )
    trajectories = [trajectory_record(instance) for instance in document["instances"]]
    accepted = sum(1 for record in trajectories if record["accepted"])
    return {
        "summary": {
            "move_spec_version": version,
            "instances": len(trajectories),
            "accepted": accepted,
            "rejected": len(trajectories) - accepted,
        },
        "trajectories": trajectories,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training", required=True, type=Path)
    parser.add_argument("--trajectories", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    args = parser.parse_args()

    document = json.loads(args.training.read_text(encoding="utf-8"))
    result = replay_training_document(document)
    args.trajectories.write_text(
        "\n".join(
            json.dumps(record, sort_keys=True, separators=(",", ":"))
            for record in result["trajectories"]
        )
        + "\n",
        encoding="utf-8",
    )
    args.summary.write_text(
        json.dumps(result["summary"], sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    if result["summary"]["rejected"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
