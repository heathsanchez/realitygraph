from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from realitygraph.acc import free_reduce


SPLIT_VERSION = "acc-scientific-family-v1"


@dataclass(frozen=True)
class ScientificSplit:
    seed: str
    acquisition_ids: tuple[str, ...]
    calibration_ids: tuple[str, ...]
    future_ids: tuple[str, ...]
    manifest_digest: str

    def canonical_json(self) -> str:
        return json.dumps(
            {
                "version": SPLIT_VERSION,
                "seed": self.seed,
                "acquisition_ids": list(self.acquisition_ids),
                "calibration_ids": list(self.calibration_ids),
                "future_ids": list(self.future_ids),
                "manifest_digest": self.manifest_digest,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )

    def learning_ids(self) -> tuple[str, ...]:
        return self.acquisition_ids + self.calibration_ids


def _family_key(row: dict[str, Any]) -> tuple[int, ...]:
    return free_reduce(tuple(int(x) for x in row.get("w_vector", ())))


def _row_key(row: dict[str, Any]) -> tuple[int, str]:
    n = row.get("n")
    return (0 if n is None else int(n), str(row["training_id"]))


def _singleton_stage(seed: str, family: tuple[int, ...], training_id: str) -> str:
    payload = f"{SPLIT_VERSION}|{seed}|{family}|{training_id}".encode()
    bucket = int.from_bytes(hashlib.sha256(payload).digest()[:4], "big") % 100
    if bucket < 60:
        return "acquisition"
    if bucket < 80:
        return "calibration"
    return "future"


def _partition_recurring(rows: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    ordered = sorted(rows, key=_row_key)
    count = len(ordered)
    if count == 2:
        return [str(ordered[0]["training_id"])], [], [str(ordered[1]["training_id"])]

    acquisition_count = max(1, int(count * 0.60))
    calibration_count = max(1, int(count * 0.20))
    if acquisition_count + calibration_count >= count:
        calibration_count = 1
        acquisition_count = max(1, count - 2)
    acquisition = [str(row["training_id"]) for row in ordered[:acquisition_count]]
    calibration = [
        str(row["training_id"])
        for row in ordered[acquisition_count : acquisition_count + calibration_count]
    ]
    future = [
        str(row["training_id"])
        for row in ordered[acquisition_count + calibration_count :]
    ]
    return acquisition, calibration, future


def freeze_split(trajectories: list[dict[str, Any]], seed: str) -> ScientificSplit:
    by_family: dict[tuple[int, ...], list[dict[str, Any]]] = defaultdict(list)
    seen_ids: set[str] = set()
    for row in trajectories:
        training_id = str(row["training_id"])
        if training_id in seen_ids:
            raise ValueError(f"duplicate training_id: {training_id}")
        seen_ids.add(training_id)
        by_family[_family_key(row)].append(row)

    acquisition: list[str] = []
    calibration: list[str] = []
    future: list[str] = []

    for family in sorted(by_family):
        rows = by_family[family]
        if len(rows) >= 2:
            a, c, f = _partition_recurring(rows)
            acquisition.extend(a)
            calibration.extend(c)
            future.extend(f)
            continue
        training_id = str(rows[0]["training_id"])
        stage = _singleton_stage(seed, family, training_id)
        if stage == "acquisition":
            acquisition.append(training_id)
        elif stage == "calibration":
            calibration.append(training_id)
        else:
            future.append(training_id)

    acquisition_ids = tuple(sorted(acquisition))
    calibration_ids = tuple(sorted(calibration))
    future_ids = tuple(sorted(future))
    payload = json.dumps(
        {
            "version": SPLIT_VERSION,
            "seed": str(seed),
            "acquisition_ids": list(acquisition_ids),
            "calibration_ids": list(calibration_ids),
            "future_ids": list(future_ids),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return ScientificSplit(
        str(seed),
        acquisition_ids,
        calibration_ids,
        future_ids,
        digest,
    )


def select_rows(
    trajectories: list[dict[str, Any]], ids: tuple[str, ...]
) -> list[dict[str, Any]]:
    wanted = set(ids)
    rows = [row for row in trajectories if str(row["training_id"]) in wanted]
    if len(rows) != len(wanted):
        found = {str(row["training_id"]) for row in rows}
        missing = sorted(wanted - found)
        raise ValueError(f"split references missing rows: {missing}")
    return sorted(rows, key=lambda row: str(row["training_id"]))
