from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def _w_key(trajectory: dict[str, Any]) -> tuple[int, ...]:
    return tuple(int(x) for x in trajectory.get("w_vector", ()))


def source_family_split(
    trajectories: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Hold out the largest-n certified member of every recurring w-family.

    Singleton families stay in acquisition because they cannot provide a
    prospective same-family test.  Ties at the largest n are broken by
    training_id so exactly one row is held out per recurring family.
    """
    rows = list(trajectories)
    groups: dict[tuple[int, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[_w_key(row)].append(row)

    heldout_ids: set[str] = set()
    for family_rows in groups.values():
        if len(family_rows) < 2:
            continue
        chosen = max(
            family_rows,
            key=lambda row: (int(row["n"]), str(row["training_id"])),
        )
        heldout_ids.add(str(chosen["training_id"]))

    acquisition = [
        row for row in rows if str(row["training_id"]) not in heldout_ids
    ]
    heldout = [row for row in rows if str(row["training_id"]) in heldout_ids]
    return acquisition, heldout


def source_entry_macros(
    trajectories: Iterable[dict[str, Any]],
    *,
    target_n: int,
    target_w: Iterable[int],
    min_len: int = 2,
    max_len: int = 8,
    include_full: bool = True,
) -> list[tuple[int, ...]]:
    """Return deterministic entry macros learned only from lower-n proofs of the same w.

    The selection key is public source structure only: exact ``w_vector`` and the
    ordering relation ``source_n < target_n``. No target outcome from the target
    presentation is inspected.
    """
    if min_len < 1 or max_len < min_len:
        raise ValueError("invalid macro length range")
    target_w_tuple = tuple(int(x) for x in target_w)

    candidates: list[tuple[int, int, tuple[int, ...]]] = []
    for trajectory in trajectories:
        source_n = int(trajectory["n"])
        source_w = _w_key(trajectory)
        if source_w != target_w_tuple or source_n >= target_n:
            continue
        moves = tuple(int(m) for m in trajectory.get("moves", ()))
        upper = min(max_len, len(moves))
        for length in range(min_len, upper + 1):
            candidates.append((source_n, length, moves[:length]))
        if include_full and moves:
            candidates.append((source_n, len(moves), moves))

    # Prefer the nearest lower-n source, then the longest reusable prefix.
    candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
    result: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()
    for _, _, macro in candidates:
        if macro in seen:
            continue
        seen.add(macro)
        result.append(macro)
    return result
