from __future__ import annotations

from typing import Any, Iterable


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
    ordering relation ``source_n < target_n``.  No target outcome from the target
    presentation is inspected.
    """
    if min_len < 1 or max_len < min_len:
        raise ValueError("invalid macro length range")
    target_w_tuple = tuple(int(x) for x in target_w)

    candidates: list[tuple[int, int, tuple[int, ...]]] = []
    for trajectory in trajectories:
        source_n = int(trajectory["n"])
        source_w = tuple(int(x) for x in trajectory.get("w_vector", ()))
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
